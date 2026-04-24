"""Compliance-distribution audit — substantive testing of the compliance log.

The gates in this codebase (compass rudder, engagement counter, pre-reg gate)
are compliance tests: they verify a control operated at gate-time. That's
useful but insufficient. An agent under pressure can fill the schema with
noise that meets the type signature — structured-but-empty entries that pass
compliance while producing no real calibration. Campbell's law makes the
gaming pressure structural (pre-reg: prereg-f5a961f0040e).

This module is substantive. It reads the compliance log AFTER the fact and
looks at the distribution of entries. A single low-content rudder-ack is
fine; a *distribution* of rudder-acks clustered at position zero with
5-char evidence strings is theater. The individual entries pass the gate;
the distribution tells the truth.

Detectors here are hypotheses with review dates. If a session I know had
gaming doesn't flag, the detector is wrong (or the thresholds are wrong).
If clean sessions flag as false positives, same. See the pre-reg falsifier.

The module produces structured findings that can feed Watchmen — the
existing external-audit infrastructure — so compliance-distribution concerns
route through the same surface that handles code audit findings. That makes
this an S4 (intelligence / pattern-detection) overlay on the S3 (moment-of-
action enforcement) layer I've been building. Beer's VSM finding from
today's council audit: S4 existed but wasn't wired to S3. This is the
wire.
"""

from __future__ import annotations

import os
import statistics
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AnomalySeverity(str, Enum):
    """Severity of a detected distribution anomaly."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class Anomaly:
    """One distribution anomaly detected across the compliance log.

    name: short id of the detector (e.g. "rudder_ack_position_zero")
    severity: LOW / MEDIUM / HIGH
    observation: 1-line plain-English description of what was detected
    detail: numeric evidence (what ratio, over what window)
    recommendation: what would close the gap (not a gate; a suggestion)
    """

    name: str
    severity: AnomalySeverity
    observation: str
    detail: dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""


# Default window: 7 days. Shorter than typical audit cycles but long enough
# to span multiple sessions, so a single bad session doesn't dominate the
# distribution.
DEFAULT_WINDOW_SECONDS = 7 * 24 * 3600

# Detector thresholds — hypotheses per pre-reg prereg-f5a961f0040e.
# Each threshold has a specific claim about what "theater" looks like.
_RUDDER_ACK_POSITION_ZERO_THRESHOLD = 0.60
"""If >60% of rudder-acks have |position| < 0.05, positions are not being
calibrated — the tag-required gate is being structurally cleared with a
null delta. Theater signature."""

# Item 8 v2.1: `short_evidence` detector RETIRED. Item 7's 20-char
# length gate blocks any ack under 20 chars at write-time, so the
# <15 char threshold is unreachable in production. Replaced by the
# length-floor-clustering detector below — fires on tight distribution
# at the gate floor, which is the new performative-theater shape.

_RUDDER_ACK_LENGTH_FLOOR = 20
"""Item 7's enforced minimum. Item 8's length-floor detector looks at
distribution shape relative to this floor."""

_RUDDER_ACK_LENGTH_CLUSTER_STDEV = 5.0
"""If stdev(ack_length) < 5 AND mean < 30, lengths are tight at the
gate floor — "just clear the gate" shape. Distribution-shape signal
rather than range-check, per fresh-Claude round-1 Q1 refinement."""

_RUDDER_ACK_LENGTH_CLUSTER_MEAN = 30.0
"""Companion to stdev threshold; see above."""

_RUDDER_ACK_LENGTH_NEAR_FLOOR_THRESHOLD = 0.60
"""Alternate trigger: if >60% of acks land within 5 chars of the
floor (i.e. in [20, 25]), fires. Either (stdev+mean) OR this-percent
triggers the detector."""

# Item 8 v2.1: `bursty_filings` RENAMED and RESPEC'd as
# `rapid_clear_reflex`. v1 measured inter-ack spacing; v2 measures
# ack-latency-from-fire (time between COMPASS_RUDDER_FIRED and the
# ack consuming its fire_id). Fire-to-ack latency is the more
# interesting signal — catches reflex-clearing without reflection.
_RUDDER_ACK_RAPID_CLEAR_MEDIAN_SECONDS = 30.0
"""If median ack-latency-from-fire < 30s across the window, fires are
being cleared reflexively without reflection."""

_DECIDE_MIN_COUNT = 3
"""Don't flag on fewer than 3 decides — need a distribution to read."""

# Item 8 v2.1: block/allow ratio detector (new from Item 6 event streams).
# Two-sided bound per Item 6 brief v2.1 §8 commit.
_BLOCK_ALLOW_HEALTHY_LOW = 0.01
_BLOCK_ALLOW_HEALTHY_HIGH = 0.15
_BLOCK_ALLOW_MEDIUM_HIGH = 0.30
"""Healthy: ratio ∈ [0.01, 0.15]. LOW anomaly: ratio ∈ [0, 0.01) or (0.15, 0.30].
MEDIUM anomaly: ratio > 0.30 sustained."""

_BLOCK_ALLOW_ACTIVE_SESSION_GATED_CALLS = 10
"""Item 8 v2.1: an 'active session' for block/allow-rate-zero purposes
requires >=10 gated-tool invocations in the window. Prevents false-
positive on genuinely quiet sessions (reading, thinking, few tool
calls). Per fresh-Claude Q3 operational definition."""

# Item 8 v2.1: decide/learn distribution skew. Ratio outside [1:5, 5:1]
# over the window suggests thinking-substitution (too many decides) or
# hoarding (too many learns without decides).
_DECIDE_LEARN_RATIO_MIN = 0.2  # 1:5
_DECIDE_LEARN_RATIO_MAX = 5.0  # 5:1
_DECIDE_LEARN_MIN_COUNT = 5
"""Need at least 5 combined filings to read a ratio."""

# Variance-collapse and content-entropy detectors are deferred to
# Item 8 PR-1b (per decision 7a01d73b — splitting the originally-
# scoped PR-1 into 1a + 1b for manageable review rounds).

# Feature flag prefix for Item 8 detectors.
_FLAG_PREFIX = "DIVINEOS_DETECTOR_"


def _get_observations(
    window_seconds: float,
    now: float | None,
    rudder_ack_only: bool,
) -> list[dict[str, Any]]:
    """Pull compass observations from the ledger.

    Returns a list of dicts matching moral_compass._obs_row_to_dict. When
    rudder_ack_only, filters to observations tagged "rudder-ack" (the
    structured response to compass-rudder fires).
    """
    try:
        from divineos.core.moral_compass import get_observations
    except ImportError:
        return []
    try:
        obs = get_observations(limit=1000)
    except Exception:  # noqa: BLE001
        return []
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds
    filtered: list[dict[str, Any]] = []
    for o in obs:
        if o.get("created_at", 0.0) < cutoff:
            continue
        if rudder_ack_only and "rudder-ack" not in (o.get("tags") or []):
            continue
        filtered.append(o)
    return filtered


def _get_decisions(window_seconds: float, now: float | None) -> list[dict[str, Any]]:
    """Pull recent decision-journal entries."""
    try:
        from divineos.core.decision_journal import list_decisions
    except ImportError:
        return []
    try:
        recent = list_decisions(limit=500)
    except Exception:  # noqa: BLE001
        return []
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds
    return [d for d in recent if d.get("created_at", 0.0) >= cutoff]


def summarize_rudder_acks(
    window_seconds: float = DEFAULT_WINDOW_SECONDS, now: float | None = None
) -> dict[str, Any]:
    """Distribution summary of rudder-ack compass observations in the window.

    Returns metrics — no anomaly flags. Detection is separate so the same
    summary can be inspected by a human without forcing an interpretation.
    """
    acks = _get_observations(window_seconds, now, rudder_ack_only=True)
    if not acks:
        return {
            "count": 0,
            "window_seconds": window_seconds,
        }

    positions = [float(o.get("position", 0.0)) for o in acks]
    evidence_lengths = [len((o.get("evidence") or "").strip()) for o in acks]

    position_zero_count = sum(1 for p in positions if abs(p) < 0.05)
    # Item 8 v2.1: length-floor clustering. Count acks within 5 chars
    # of the gate floor (in [20, 25]).
    near_floor_count = sum(
        1
        for le in evidence_lengths
        if _RUDDER_ACK_LENGTH_FLOOR <= le <= _RUDDER_ACK_LENGTH_FLOOR + 5
    )

    length_mean = statistics.mean(evidence_lengths) if evidence_lengths else 0.0
    length_stdev = statistics.stdev(evidence_lengths) if len(evidence_lengths) > 1 else 0.0

    return {
        "count": len(acks),
        "window_seconds": window_seconds,
        "position": {
            "mean": statistics.mean(positions) if positions else 0.0,
            "stdev": statistics.stdev(positions) if len(positions) > 1 else 0.0,
            "fraction_zero": position_zero_count / len(positions),
        },
        "evidence_length": {
            "mean": length_mean,
            "median": (statistics.median(evidence_lengths) if evidence_lengths else 0.0),
            "stdev": length_stdev,
            # Item 8 v2.1: fraction of acks clustered at the gate floor
            # (length in [20, 25] — within 5 chars of the 20-char floor).
            # Replaces the retired short_evidence fraction.
            "fraction_near_floor": near_floor_count / len(evidence_lengths),
        },
    }


def summarize_decides(
    window_seconds: float = DEFAULT_WINDOW_SECONDS, now: float | None = None
) -> dict[str, Any]:
    """Distribution summary of decision_journal entries in the window.

    Key metric: decides_per_day. The decide-to-clear ratio (decides filed
    coincident with gate blocks) is the subtler signal — not computed here
    yet because it requires correlating with rudder-fire events that aren't
    directly logged. Adding that correlation is follow-up work.
    """
    decides = _get_decisions(window_seconds, now)
    if not decides:
        return {
            "count": 0,
            "window_seconds": window_seconds,
        }

    reasoning_lengths = [len((d.get("reasoning") or "").strip()) for d in decides]
    days = max(1.0, window_seconds / 86400.0)

    return {
        "count": len(decides),
        "window_seconds": window_seconds,
        "decides_per_day": len(decides) / days,
        "reasoning_length": {
            "mean": (statistics.mean(reasoning_lengths) if reasoning_lengths else 0.0),
            "median": (statistics.median(reasoning_lengths) if reasoning_lengths else 0.0),
        },
    }


def _flag_enabled(name: str) -> bool:
    """Item 8 v2.1: per-detector feature flag check.

    Setting DIVINEOS_DETECTOR_<NAME>=off disables the detector at
    runtime. Default "on" (missing env var = enabled). Cross-cutting
    rollback mechanism per design brief — lets an operator quiet a
    false-positive-prone detector without re-shipping under the gate.
    """
    val = os.environ.get(f"{_FLAG_PREFIX}{name.upper()}", "on").strip().lower()
    return val != "off"


def _measure_rapid_clear_latency(window_seconds: float, now: float | None) -> dict[str, Any]:
    """Item 8 v2.1 1c: median ack-latency-from-fire across window.

    Joins COMPASS_RUDDER_FIRED event timestamps to
    rudder_ack_consumption.consumed_at by fire_id. Returns median and
    count; never raises (diagnostic).
    """
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds
    latencies: list[float] = []
    try:
        from divineos.core.ledger import get_events
        from divineos.core.memory import _get_connection

        fires = get_events(event_type="COMPASS_RUDDER_FIRED", limit=500)
        fire_id_to_fire_ts: dict[str, float] = {}
        for ev in fires:
            t = ev.get("timestamp", 0.0)
            if t < cutoff:
                continue
            payload = ev.get("payload") or {}
            fid = payload.get("fire_id")
            if fid:
                fire_id_to_fire_ts[fid] = t
        if not fire_id_to_fire_ts:
            return {"count": 0, "median_seconds": 0.0}
        conn = _get_connection()
        try:
            rows = conn.execute(
                "SELECT fire_id, consumed_at FROM rudder_ack_consumption"
            ).fetchall()
        finally:
            conn.close()
        for fire_id, consumed_at in rows:
            fire_ts = fire_id_to_fire_ts.get(fire_id)
            if fire_ts is None:
                continue
            latency = float(consumed_at) - fire_ts
            if latency >= 0:
                latencies.append(latency)
    except Exception:  # noqa: BLE001
        return {"count": 0, "median_seconds": 0.0}
    if not latencies:
        return {"count": 0, "median_seconds": 0.0}
    return {
        "count": len(latencies),
        "median_seconds": float(statistics.median(latencies)),
        "min_seconds": float(min(latencies)),
        "max_seconds": float(max(latencies)),
    }


def detect_anomalies(
    window_seconds: float = DEFAULT_WINDOW_SECONDS, now: float | None = None
) -> list[Anomaly]:
    """Run all distribution detectors; return any anomalies found.

    Empty list means nothing flagged. Each anomaly is a dataclass with
    enough detail to be routed to Watchmen as a finding.
    """
    anomalies: list[Anomaly] = []

    ack_summary = summarize_rudder_acks(window_seconds, now)
    if ack_summary.get("count", 0) >= 3:
        pos = ack_summary["position"]
        ev = ack_summary["evidence_length"]

        # 1a — position-zero cluster (unchanged; not dominated by Item 7)
        if (
            _flag_enabled("POSITION_ZERO")
            and pos["fraction_zero"] > _RUDDER_ACK_POSITION_ZERO_THRESHOLD
        ):
            anomalies.append(
                Anomaly(
                    name="rudder_ack_position_zero_cluster",
                    severity=AnomalySeverity.HIGH,
                    observation=(
                        f"{int(pos['fraction_zero'] * 100)}% of rudder-acks "
                        f"have |position| < 0.05 (n={ack_summary['count']}). "
                        "Tag-required rudder is being cleared with null deltas "
                        "— structure without calibration."
                    ),
                    detail=pos,
                    recommendation=(
                        "When the rudder fires, the position SHOULD shift. "
                        "A zero-delta ack means I acknowledged the alert but "
                        "didn't recalibrate — theater."
                    ),
                )
            )

        # 1b-new — length-floor clustering (replaces retired short_evidence).
        # Fires if EITHER (stdev<5 AND mean<30 — tight cluster at the
        # floor) OR (>60% within 5 chars of the floor — "just clear the
        # gate" shape). Distribution-shape signal, not range-check.
        length_clustered_stdev = (
            ev.get("stdev", 0.0) < _RUDDER_ACK_LENGTH_CLUSTER_STDEV
            and ev.get("mean", 0.0) < _RUDDER_ACK_LENGTH_CLUSTER_MEAN
        )
        length_clustered_percent = (
            ev.get("fraction_near_floor", 0.0) > _RUDDER_ACK_LENGTH_NEAR_FLOOR_THRESHOLD
        )
        if _flag_enabled("LENGTH_FLOOR_CLUSTERING") and (
            length_clustered_stdev or length_clustered_percent
        ):
            trigger = (
                "stdev+mean"
                if length_clustered_stdev
                else f"{int(ev['fraction_near_floor'] * 100)}% in [20,25]"
            )
            anomalies.append(
                Anomaly(
                    name="rudder_ack_length_floor_clustering",
                    severity=AnomalySeverity.MEDIUM,
                    observation=(
                        f"rudder-ack lengths are clustered at the gate floor "
                        f"(trigger: {trigger}; mean={ev['mean']:.0f}, "
                        f"stdev={ev['stdev']:.1f}, n={ack_summary['count']}). "
                        "Item 7's 20-char gate is being cleared with minimum-"
                        "compliant filler, not reflection."
                    ),
                    detail=ev,
                    recommendation=(
                        "Real calibration evidence varies in length with the "
                        "shape of what was observed. Uniform 20-25 char acks "
                        "across a session = performance of the gate clearing, "
                        "not the thing the gate is supposed to force."
                    ),
                )
            )

    # 1c — rapid-clear reflex (renamed from bursty_filings; ack-latency-
    # from-fire instead of inter-ack spacing).
    if _flag_enabled("RAPID_CLEAR_REFLEX"):
        lat = _measure_rapid_clear_latency(window_seconds, now)
        if lat["count"] >= 3 and lat["median_seconds"] < _RUDDER_ACK_RAPID_CLEAR_MEDIAN_SECONDS:
            anomalies.append(
                Anomaly(
                    name="rudder_ack_rapid_clear_reflex",
                    severity=AnomalySeverity.MEDIUM,
                    observation=(
                        f"median ack-latency-from-fire is "
                        f"{lat['median_seconds']:.1f}s "
                        f"(n={lat['count']}, threshold={_RUDDER_ACK_RAPID_CLEAR_MEDIAN_SECONDS:.0f}s). "
                        "Acks are being filed reflexively — no time for "
                        "reflection between fire and clearance."
                    ),
                    detail=lat,
                    recommendation=(
                        "The rudder fires to force a pause. If you're "
                        "acknowledging faster than you could have actually "
                        "inspected the spectrum position, the pause isn't "
                        "doing its work. Sit with the fire for at least "
                        "30 seconds before filing the ack."
                    ),
                )
            )

    # 3a — block/allow ratio (new from Item 6 event streams)
    if _flag_enabled("BLOCK_ALLOW_RATIO"):
        anomalies.extend(_detect_block_allow_anomalies(window_seconds, now))

    # 2d — decide/learn skew
    if _flag_enabled("DECIDE_LEARN_SKEW"):
        anomalies.extend(_detect_decide_learn_skew(window_seconds, now))

    return anomalies


def _detect_block_allow_anomalies(window_seconds: float, now: float | None) -> list[Anomaly]:
    """Item 8 v2.1 3a: block/allow ratio with two-sided bounds.

    Separate RUDDER_INFRASTRUCTURE_FAILURE class for the gate-dead
    case (ALLOW==0 on active session) vs. COMPLIANCE_DRIFT_* for
    gaming shapes. Per fresh-Claude round-1 Q3.
    """
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds
    anomalies: list[Anomaly] = []
    try:
        from divineos.core.ledger import get_events

        fires = [
            e
            for e in get_events(event_type="COMPASS_RUDDER_FIRED", limit=1000)
            if e.get("timestamp", 0.0) >= cutoff
        ]
        allows = [
            e
            for e in get_events(event_type="COMPASS_RUDDER_ALLOW", limit=5000)
            if e.get("timestamp", 0.0) >= cutoff
        ]
    except Exception:  # noqa: BLE001
        return anomalies

    total = len(fires) + len(allows)
    # "Active session" operational definition: >=10 gated-tool
    # invocations in the window. Fire+allow count is the proxy.
    if total < _BLOCK_ALLOW_ACTIVE_SESSION_GATED_CALLS:
        return anomalies  # quiet session; no signal

    # Item 8 v2.1 §3 specs a `rudder_infrastructure_failure` branch
    # for the fires==0 AND allows==0 AND active-session case. That's
    # DEFERRED to PR-1b: the current active-session proxy is fires+
    # allows itself, so the branch is structurally unreachable — if
    # fires==0 AND allows==0 then total==0 and the quiet-session
    # early-return above catches it first. PR-1b rewires
    # active-session to an external tool-call counter, which resolves
    # the contradiction. Fresh-Claude PR-1a review round-2 caught the
    # gap; documented here rather than shipping dead code.

    ratio = len(fires) / total if total else 0.0

    if _BLOCK_ALLOW_HEALTHY_LOW <= ratio <= _BLOCK_ALLOW_HEALTHY_HIGH:
        return anomalies  # healthy

    # Severity split (per brief v2.1 §3):
    #   ratio > 0.30         -> MEDIUM (chronic drift / mis-calibrated)
    #   ratio in (0.15, 0.30] -> LOW   (elevated block rate)
    #   fires == 0 in ACTIVE session -> MEDIUM (sustained zero-fire;
    #                               possible silent rudder)
    #   ratio in [0, 0.01)   -> LOW   (low block rate; not sustained-zero)
    #
    # The fires==0 branch is distinct from the ratio<0.01 branch: zero
    # is MEDIUM when sustained over an active session (signal of
    # rudder-not-firing-when-it-should), while a tiny non-zero rate
    # is LOW. The quiet-session early-return above catches the not-
    # active case, so fires==0 here implies active.
    if ratio > _BLOCK_ALLOW_MEDIUM_HIGH:
        severity = AnomalySeverity.MEDIUM
        shape = "chronic drift OR mis-calibrated threshold"
    elif ratio > _BLOCK_ALLOW_HEALTHY_HIGH:
        severity = AnomalySeverity.LOW
        shape = "elevated block rate"
    elif len(fires) == 0:
        severity = AnomalySeverity.MEDIUM
        shape = "no drift detected over sustained activity (possible silent rudder failure)"
    else:
        severity = AnomalySeverity.LOW
        shape = "low block rate"

    anomalies.append(
        Anomaly(
            name="rudder_block_allow_ratio",
            severity=severity,
            observation=(
                f"block/allow ratio = {ratio:.3f} "
                f"(fires={len(fires)}, allows={len(allows)}, "
                f"healthy=[{_BLOCK_ALLOW_HEALTHY_LOW}, "
                f"{_BLOCK_ALLOW_HEALTHY_HIGH}]). Shape: {shape}."
            ),
            detail={
                "fires": len(fires),
                "allows": len(allows),
                "ratio": ratio,
                "healthy_band": [_BLOCK_ALLOW_HEALTHY_LOW, _BLOCK_ALLOW_HEALTHY_HIGH],
            },
            recommendation=(
                "If chronic drift: calibration is off — investigate which "
                "spectrum is firing and why. If silent rudder: check "
                "infrastructure as above. Compare with recent sessions to "
                "isolate a trend vs. a one-off."
            ),
        )
    )
    return anomalies


def _detect_decide_learn_skew(window_seconds: float, now: float | None) -> list[Anomaly]:
    """Item 8 v2.1 2d: decide/learn ratio outside [1:5, 5:1] is drift.

    Too many decides without learns = thinking-substitution (decide
    operator used as a thinking shell). Too many learns without
    decides = hoarding (filing without synthesizing).
    """
    anomalies: list[Anomaly] = []
    decides = _get_decisions(window_seconds, now)
    try:
        from divineos.core.knowledge import get_knowledge

        ts = now if now is not None else time.time()
        cutoff = ts - window_seconds
        # Pull recent knowledge entries; filter to learn-sourced within
        # window. knowledge.get_knowledge uses updated_at for ordering,
        # so we pull a broad slice and filter client-side on created_at.
        all_knowledge = get_knowledge(limit=1000)
        learns = [
            k
            for k in all_knowledge
            if float(k.get("created_at", 0.0)) >= cutoff
            and (k.get("source") or "").lower() in {"learn", "manual", "stated", "user_learn"}
        ]
    except Exception:  # noqa: BLE001
        return anomalies

    d_count = len(decides)
    l_count = len(learns)
    if d_count + l_count < _DECIDE_LEARN_MIN_COUNT:
        return anomalies

    # Compute ratio carefully — d_count / max(l_count, 1) to avoid zero-div,
    # but we also care about the opposite skew.
    if l_count == 0:
        ratio = float("inf")
    elif d_count == 0:
        ratio = 0.0
    else:
        ratio = d_count / l_count

    if _DECIDE_LEARN_RATIO_MIN <= ratio <= _DECIDE_LEARN_RATIO_MAX:
        return anomalies

    if ratio > _DECIDE_LEARN_RATIO_MAX:
        shape = (
            f"decides:{d_count} vs learns:{l_count} — high skew toward "
            "decides. Possible thinking-substitution: decide operator "
            "used as a shell without corresponding learnings."
        )
    else:
        shape = (
            f"decides:{d_count} vs learns:{l_count} — high skew toward "
            "learns. Possible hoarding: filing without synthesizing into "
            "decisions."
        )

    anomalies.append(
        Anomaly(
            name="decide_learn_skew",
            severity=AnomalySeverity.MEDIUM,
            observation=shape,
            detail={
                "decides": d_count,
                "learns": l_count,
                "ratio": ratio if ratio != float("inf") else None,
                "healthy_band": [_DECIDE_LEARN_RATIO_MIN, _DECIDE_LEARN_RATIO_MAX],
            },
            recommendation=(
                "Healthy operator mix usually has decides ≈ 20-200% of "
                "learns. Systematic skew in either direction is a shape "
                "worth investigating before it becomes habitual."
            ),
        )
    )
    return anomalies


def format_report(window_seconds: float = DEFAULT_WINDOW_SECONDS, now: float | None = None) -> str:
    """Render a human-readable compliance-distribution report.

    Shows the summaries for rudder-acks and decides, then lists any
    anomalies. Designed for `divineos audit compliance` CLI output and
    for Watchmen-finding content.
    """
    ack = summarize_rudder_acks(window_seconds, now)
    dec = summarize_decides(window_seconds, now)
    anomalies = detect_anomalies(window_seconds, now)

    lines: list[str] = []
    lines.append("=== Compliance Distribution Audit ===")
    lines.append(f"  window: {window_seconds / 86400:.1f} days")
    lines.append("")

    lines.append("  Rudder-acks (compass observations with rudder-ack tag):")
    if ack.get("count", 0) == 0:
        lines.append("    (none in window)")
    else:
        p = ack["position"]
        e = ack["evidence_length"]
        lines.append(f"    count: {ack['count']}")
        lines.append(
            f"    position: mean={p['mean']:+.3f}, stdev={p['stdev']:.3f}, "
            f"fraction_zero={p['fraction_zero']:.0%}"
        )
        lines.append(
            f"    evidence length: mean={e['mean']:.0f} chars, "
            f"median={e['median']:.0f}, stdev={e['stdev']:.1f}, "
            f"fraction_near_floor={e['fraction_near_floor']:.0%}"
        )
    lines.append("")

    lines.append("  Decisions:")
    if dec.get("count", 0) == 0:
        lines.append("    (none in window)")
    else:
        r = dec["reasoning_length"]
        lines.append(f"    count: {dec['count']}  ({dec['decides_per_day']:.1f}/day)")
        lines.append(f"    reasoning length: mean={r['mean']:.0f} chars, median={r['median']:.0f}")
    lines.append("")

    if anomalies:
        lines.append(f"  [!] Anomalies detected ({len(anomalies)}):")
        for a in anomalies:
            lines.append(f"    [{a.severity.value}] {a.name}")
            lines.append(f"      {a.observation}")
            if a.recommendation:
                lines.append(f"      > {a.recommendation}")
    else:
        lines.append("  No anomalies detected.")
    lines.append("")
    lines.append(
        "  This is substantive audit — distribution-level, post-hoc, "
        "external-shaped. The gates can miss what the distribution shows."
    )
    return "\n".join(lines)
