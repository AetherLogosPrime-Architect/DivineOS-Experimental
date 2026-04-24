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
calls). Per fresh-Claude Q3 operational definition.

PR-1b: 'gated-tool invocation count' sourced from TOOL_CALL ledger
events (emitted by tool_wrapper.wrap_tool_execution BEFORE
tool_func execution — independent of the rudder hook path).
Verified upstream-of-rudder at implementation-time per addendum
Q1 refinement 8."""

_RUDDER_PARTIAL_FAILURE_COVERAGE_THRESHOLD = 0.80
"""Item 8 PR-1b: if the rudder emits events for fewer than 80% of
gated tool calls, some calls are bypassing the rudder (partial
infrastructure failure — e.g., hook registered for Task but not
Agent). Pre-reg 7.1-infra-B; review at 60 days with live data."""

# PR-1b 2a: variance-collapse detector. TF-IDF cosine similarity
# across ALL operator content (decides + learns + ack evidence) in
# the window. If a high fraction of items have a near-neighbor above
# the threshold, the vocabulary distribution has collapsed.
_VARIANCE_COLLAPSE_SIMILARITY_THRESHOLD = 0.75
"""Distribution-level — 0.75 across many items indicates collapsed
vocabulary. Distinct from Item 7's per-item 0.9 (one-vs-one)."""

_VARIANCE_COLLAPSE_FRACTION_HIGH_SIMILARITY = 0.50
"""Fires if >=50% of items have a near-neighbor above the threshold."""

_VARIANCE_COLLAPSE_MIN_ITEMS = 10
"""Below 10 items, the distribution is too small to read."""

# PR-1b 2b: content-entropy trend. Shannon entropy over joined
# operator content (first half vs second half of the window). A
# meaningful drop across halves suggests distribution drift.
_CONTENT_ENTROPY_DROP_THRESHOLD = 0.30
"""Relative drop from first-half entropy to second-half entropy.
30% is a genuine trend, not noise."""

_CONTENT_ENTROPY_MIN_ITEMS_PER_HALF = 3

# PR-1b 2c: multi-window meta-detector. Brief v2.1 §2c specifies
# detectors running across 1day and 1week windows. If the SAME
# detector fires in BOTH windows, the pattern is chronic not
# transient — severity elevates one step (LOW→MEDIUM, MEDIUM→HIGH,
# HIGH stays HIGH).
_MULTI_WINDOW_SECONDS = (86400.0, 604800.0)
"""1 day and 1 week. Dropped 1hr per fresh-Claude review — reduces
noise; add back if simpler version misses real drift."""

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
    window_seconds: float = DEFAULT_WINDOW_SECONDS,
    now: float | None = None,
    emit_events: bool = True,
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

    # 2a — variance-collapse (PR-1b)
    if _flag_enabled("VARIANCE_COLLAPSE"):
        anomalies.extend(_detect_variance_collapse(window_seconds, now))

    # 2b — content-entropy trend (PR-1b)
    if _flag_enabled("CONTENT_ENTROPY"):
        anomalies.extend(_detect_content_entropy_drop(window_seconds, now))

    # Baselines-uncalibrated — PR-2 → detectors wiring. Fires when
    # gated activity is high but zero clean-tagged sessions exist,
    # signalling Item 8 detectors are running on conceptual defaults
    # instead of calibrated thresholds. Recommendation points at
    # `divineos audit tag-clean`. Follow-up from claim 6bf81b38 (the
    # conversation that named "completion-checking, not cooldown" as
    # the real rudder purpose; wiring PR-2 into consumers was the
    # immediate missing completion).
    if _flag_enabled("BASELINES_UNCALIBRATED"):
        anomalies.extend(_detect_baselines_uncalibrated(window_seconds, now))

    # PR-1b §3: HIGH-severity emission is optional per caller. Single-
    # window users (format_report, CLI) keep emit_events=True so a
    # HIGH anomaly produces a ledger event inline. Multi-window
    # orchestrators (format_multi_window_report) pass
    # emit_events=False, then dedupe across windows and emit once per
    # unique detector — prevents the same finding from producing
    # multiple ledger events at different time scales.
    # Fresh-Claude PR-1b round-2 finding. Decision d91c8bca.
    if emit_events:
        _emit_high_severity_events(anomalies, window_seconds)

    return anomalies


def _emit_high_severity_events(anomalies: list[Anomaly], window_seconds: float) -> None:
    """PR-1b: emit a ledger event for each HIGH anomaly.

    Separate event classes per brief §3. Neither type is in
    _COMPRESSIBLE_TYPES (guardrailed via PR-1b's addition of
    ledger_compressor.py to the guardrail list).

    Payload shape is consistent across all HIGH emissions
    (fresh-Claude addendum refinement 5): detector, observation,
    detail, window_seconds, fire_timestamp at top level.
    """
    for a in anomalies:
        if a.severity != AnomalySeverity.HIGH:
            continue
        if a.name == "rudder_infrastructure_failure":
            event_type = "RUDDER_INFRASTRUCTURE_FAILURE"
        else:
            event_type = "COMPLIANCE_DRIFT_HIGH"
        try:
            from divineos.core.ledger import log_event

            log_event(
                event_type=event_type,
                actor="compliance_audit",
                payload={
                    "detector": a.name,
                    "observation": a.observation,
                    "detail": a.detail,
                    "window_seconds": window_seconds,
                    "fire_timestamp": time.time(),
                },
                validate=False,
            )
        except Exception as e:  # noqa: BLE001
            # Don't swallow silently — log to failure_diagnostics so a
            # systematic ledger-write failure becomes visible in the
            # next briefing (fresh-Claude addendum refinement 6).
            try:
                from divineos.core.failure_diagnostics import record_failure

                record_failure(
                    surface="compliance_audit_emission",
                    payload={
                        "event_type": event_type,
                        "detector": a.name,
                        "error": str(e)[:240],
                    },
                )
            except Exception:  # noqa: BLE001
                pass


def _count_gated_tool_calls(cutoff: float) -> int:
    """PR-1b: count TOOL_CALL ledger events in the window whose
    tool_name is in compass_rudder.GATED_TOOL_NAMES.

    Independent signal from rudder events — TOOL_CALL fires from
    tool_wrapper BEFORE tool_func runs (verified upstream at impl
    time). If rudder is broken, TOOL_CALL still fires; the mismatch
    between gated-call-count and rudder-event-count is the
    infrastructure-failure signal.

    Shared-source-of-truth: imports GATED_TOOL_NAMES from
    compass_rudder so adding a new gated tool in one place
    automatically updates the active-session filter.
    """
    try:
        from divineos.core.compass_rudder import GATED_TOOL_NAMES
        from divineos.core.ledger import get_events
    except ImportError:
        return 0
    try:
        # limit=20000 comfortably covers a week of high-activity sessions
        # (100 calls/hr × 24 × 7 = 16800). Bumped from the 5000 used
        # elsewhere per fresh-Claude addendum refinement 9.
        events = get_events(event_type="TOOL_CALL", limit=20000)
    except Exception:  # noqa: BLE001
        return 0
    count = 0
    for e in events:
        if e.get("timestamp", 0.0) < cutoff:
            continue
        payload = e.get("payload") or {}
        if payload.get("tool_name") in GATED_TOOL_NAMES:
            count += 1
    return count


def _detect_block_allow_anomalies(window_seconds: float, now: float | None) -> list[Anomaly]:
    """Item 8 v2.1 3a: block/allow ratio with two-sided bounds.

    PR-1b: active-session is sourced from TOOL_CALL events (not
    fires+allows as proxy). This resolves the unreachable-branch
    contradiction fresh-Claude flagged in PR-1a round-2.

    Two infrastructure-failure classes emerge:
      - FULL: TOOL_CALL > 0 AND fires+allows == 0 → gate-dead
      - PARTIAL: coverage < 80% → some calls bypass the rudder
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

    # PR-1b: active-session signal is gated TOOL_CALL count, not
    # fires+allows. See _count_gated_tool_calls + addendum Q1.
    gated_activity = _count_gated_tool_calls(cutoff)
    rudder_events = len(fires) + len(allows)

    if gated_activity < _BLOCK_ALLOW_ACTIVE_SESSION_GATED_CALLS:
        return anomalies  # quiet session; no signal

    # Full infrastructure failure — active session, rudder emitted 0 events
    if rudder_events == 0:
        anomalies.append(
            Anomaly(
                name="rudder_infrastructure_failure",
                severity=AnomalySeverity.HIGH,
                observation=(
                    f"{gated_activity} gated tool calls ran in "
                    f"{window_seconds / 3600:.1f}h window but 0 rudder "
                    "events emitted. Gate-dead: rudder is not running."
                ),
                detail={
                    "gated_activity": gated_activity,
                    "fires": 0,
                    "allows": 0,
                    "window_hours": window_seconds / 3600,
                },
                recommendation=(
                    "This is infrastructure failure, not drift. Investigation: "
                    "verify hook installation, check DB connectivity, inspect "
                    "import path for compass_rudder. Halt gated work until "
                    "rudder is verified running."
                ),
            )
        )
        return anomalies

    # Partial infrastructure failure — some calls bypass the rudder
    coverage = rudder_events / max(1, gated_activity)
    if coverage < _RUDDER_PARTIAL_FAILURE_COVERAGE_THRESHOLD:
        anomalies.append(
            Anomaly(
                name="rudder_partial_infrastructure_failure",
                severity=AnomalySeverity.MEDIUM,
                observation=(
                    f"rudder emitted {rudder_events} events for "
                    f"{gated_activity} gated calls ({coverage:.0%} coverage; "
                    f"threshold {_RUDDER_PARTIAL_FAILURE_COVERAGE_THRESHOLD:.0%}). "
                    "Some gated calls are bypassing the rudder — likely a "
                    "partial hook-registration failure."
                ),
                detail={
                    "gated_activity": gated_activity,
                    "rudder_events": rudder_events,
                    "coverage": coverage,
                    "fires": len(fires),
                    "allows": len(allows),
                },
                recommendation=(
                    "Investigation: check which gated tool names are missing "
                    "hook coverage (compare hook settings.json to "
                    "compass_rudder.GATED_TOOL_NAMES). Fix hook registration "
                    "for any that diverge."
                ),
            )
        )
        # Continue to ratio check even on partial failure — both signals
        # can surface simultaneously.

    total = len(fires) + len(allows)
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


def _gather_operator_content(window_seconds: float, now: float | None) -> list[str]:
    """Gather text content from decides, learns, and ack evidence in window.

    Used by variance-collapse (2a) and content-entropy (2b) detectors.
    Returns a list of strings — one per operator entry. Short strings
    filtered out (noise floor).
    """
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds
    texts: list[str] = []

    # Decide reasoning
    try:
        for d in _get_decisions(window_seconds, now):
            reasoning = (d.get("reasoning") or "").strip()
            if len(reasoning) >= 10:
                texts.append(reasoning)
    except Exception:  # noqa: BLE001
        pass

    # Learn content
    try:
        from divineos.core.knowledge import get_knowledge

        for k in get_knowledge(limit=500):
            if float(k.get("created_at", 0.0)) < cutoff:
                continue
            content = (k.get("content") or "").strip()
            if len(content) >= 10:
                texts.append(content)
    except Exception:  # noqa: BLE001
        pass

    # Ack evidence
    try:
        for o in _get_observations(window_seconds, now, rudder_ack_only=True):
            evidence = (o.get("evidence") or "").strip()
            if len(evidence) >= 10:
                texts.append(evidence)
    except Exception:  # noqa: BLE001
        pass

    return texts


def _detect_variance_collapse(window_seconds: float, now: float | None) -> list[Anomaly]:
    """PR-1b 2a: variance-collapse via TF-IDF cosine similarity.

    For each item in the corpus, compute similarity to every other
    item. If >=50% of items have a near-neighbor above 0.75, the
    vocabulary has collapsed across operators.

    Uses the hand-rolled TF-IDF from substance_checks (shared
    implementation avoids dependency on sklearn in this write path).

    Cost model: O(n²) in corpus size (n = decides + learns + acks in
    the window). A 1-week window with busy activity may see n ~= 500;
    that's 250K similarity computations per detector run.
    format_multi_window_report runs this twice (1d + 1w), so total
    cost is 2× per report. Acceptable at current scale.

    Caching opportunity (follow-up, not in PR-1b): 1day corpus is a
    subset of 1week corpus. A corpus-overlap cache would let the
    1week run reuse the 1day TF-IDF vectors for shared items. Defer
    until profiling shows it matters.
    """
    anomalies: list[Anomaly] = []
    texts = _gather_operator_content(window_seconds, now)
    if len(texts) < _VARIANCE_COLLAPSE_MIN_ITEMS:
        return anomalies

    try:
        from divineos.core.substance_checks import _cosine, _tfidf_vectors
    except ImportError:
        return anomalies

    vecs = _tfidf_vectors(texts)
    high_similarity_count = 0
    max_neighbor_sim: list[float] = []
    for i, vec_i in enumerate(vecs):
        best = 0.0
        for j, vec_j in enumerate(vecs):
            if i == j:
                continue
            sim = _cosine(vec_i, vec_j)
            if sim > best:
                best = sim
        max_neighbor_sim.append(best)
        if best >= _VARIANCE_COLLAPSE_SIMILARITY_THRESHOLD:
            high_similarity_count += 1

    fraction = high_similarity_count / len(texts)
    if fraction < _VARIANCE_COLLAPSE_FRACTION_HIGH_SIMILARITY:
        return anomalies

    anomalies.append(
        Anomaly(
            name="variance_collapse",
            severity=AnomalySeverity.MEDIUM,
            observation=(
                f"{fraction:.0%} of operator content "
                f"(n={len(texts)}) has a near-neighbor with cosine "
                f">= {_VARIANCE_COLLAPSE_SIMILARITY_THRESHOLD}. "
                "Vocabulary distribution has collapsed across "
                "decides/learns/acks — operators are rephrasing the "
                "same content rather than carrying distinct signal."
            ),
            detail={
                "item_count": len(texts),
                "high_similarity_count": high_similarity_count,
                "fraction": fraction,
                "threshold": _VARIANCE_COLLAPSE_SIMILARITY_THRESHOLD,
            },
            recommendation=(
                "Real operator content varies with what's being captured. "
                "High cross-item similarity means the operators are "
                "carrying the same payload — structural filing without "
                "distinct content. Vary the content deliberately."
            ),
        )
    )
    return anomalies


def _shannon_entropy_bits(text: str) -> float:
    """Shannon entropy over character frequencies, in bits."""
    import math
    from collections import Counter

    if not text:
        return 0.0
    total = len(text)
    counts = Counter(text)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


def _detect_content_entropy_drop(window_seconds: float, now: float | None) -> list[Anomaly]:
    """PR-1b 2b: content-entropy trend across halves of the window.

    Split the operator content into first-half and second-half by
    timestamp. Compute Shannon entropy of joined content for each
    half. If the second half dropped >=30% vs the first, a trend is
    suggesting drift.
    """
    anomalies: list[Anomaly] = []
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds
    midpoint = cutoff + window_seconds / 2.0

    first_half: list[str] = []
    second_half: list[str] = []

    try:
        for d in _get_decisions(window_seconds, now):
            reasoning = (d.get("reasoning") or "").strip()
            if len(reasoning) < 10:
                continue
            t = float(d.get("created_at", 0.0))
            (first_half if t < midpoint else second_half).append(reasoning)
        for o in _get_observations(window_seconds, now, rudder_ack_only=True):
            evidence = (o.get("evidence") or "").strip()
            if len(evidence) < 10:
                continue
            t = float(o.get("created_at", 0.0))
            (first_half if t < midpoint else second_half).append(evidence)
    except Exception:  # noqa: BLE001
        return anomalies

    if (
        len(first_half) < _CONTENT_ENTROPY_MIN_ITEMS_PER_HALF
        or len(second_half) < _CONTENT_ENTROPY_MIN_ITEMS_PER_HALF
    ):
        return anomalies

    first_entropy = _shannon_entropy_bits(" ".join(first_half))
    second_entropy = _shannon_entropy_bits(" ".join(second_half))
    if first_entropy == 0.0:
        return anomalies

    drop = (first_entropy - second_entropy) / first_entropy
    if drop < _CONTENT_ENTROPY_DROP_THRESHOLD:
        return anomalies

    anomalies.append(
        Anomaly(
            name="content_entropy_drop",
            severity=AnomalySeverity.MEDIUM,
            observation=(
                f"content entropy dropped {drop:.0%} from first half "
                f"({first_entropy:.2f} bits, n={len(first_half)}) to "
                f"second half ({second_entropy:.2f} bits, "
                f"n={len(second_half)}). Distribution is narrowing "
                "over time — vocabulary restriction, repetitive shape, "
                "or increasing copy-paste ratio."
            ),
            detail={
                "first_half_entropy": first_entropy,
                "second_half_entropy": second_entropy,
                "drop_fraction": drop,
                "threshold": _CONTENT_ENTROPY_DROP_THRESHOLD,
                "first_half_items": len(first_half),
                "second_half_items": len(second_half),
            },
            recommendation=(
                "Entropy drop across the window suggests thinking is "
                "contracting to a narrow vocabulary. Surface which "
                "topics the second half is circling; intentional "
                "variation restores the signal."
            ),
        )
    )
    return anomalies


def _detect_baselines_uncalibrated(window_seconds: float, now: float | None) -> list[Anomaly]:
    """Fire when gated activity is high but zero clean-tagged sessions exist.

    The feedback loop that tells the operator: Item 8 detectors need
    real data to calibrate against. Without clean-tagged sessions the
    detectors run on conceptual defaults from the design brief —
    which is honest for the first 60 days but shouldn't become the
    permanent state.

    Uses the TOOL_CALL-based gated-activity count from the same
    source as the block/allow detector (brief v2.1 addendum Q1
    Option C). Only fires when the session has been "active enough"
    to plausibly have contained auditable work.
    """
    anomalies: list[Anomaly] = []
    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds
    try:
        from divineos.core.compliance_baseline import detect_uncalibrated_baselines

        gated_activity = _count_gated_tool_calls(cutoff)
        detection = detect_uncalibrated_baselines(gated_activity=gated_activity)
    except Exception:  # noqa: BLE001
        return anomalies
    if detection is None:
        return anomalies

    anomalies.append(
        Anomaly(
            name="baselines_uncalibrated",
            severity=AnomalySeverity.LOW,
            observation=detection["note"],
            detail=detection,
            recommendation=(
                "Run an external audit round on a recent session, verify "
                "no drift findings, then tag the session clean: "
                "`divineos audit tag-clean <session_id> --round <round_id>`. "
                "After 5+ clean sessions accumulate, Item 8 detectors "
                "auto-calibrate from real data instead of defaults."
            ),
        )
    )
    return anomalies


def _detect_multi_window_fires(
    per_window_anomalies: dict[float, list[Anomaly]],
) -> list[Anomaly]:
    """PR-1b 2c: elevate severity when same detector fires across windows.

    Per brief v2.1 §2c simplified: if a detector name fires in BOTH
    1day and 1week windows, the pattern is chronic not transient.
    Emit a separate meta-anomaly with severity one step above the
    worst single-window fire of the same detector.
    """
    anomalies: list[Anomaly] = []
    windows = sorted(per_window_anomalies.keys())
    # Fresh-Claude PR-1b round-2 Finding 2: guard against single-window
    # input. The meta-detector's semantic is "chronic across time
    # scales" — meaningless with one window. Without this guard, any
    # fire in a single-window call would be labeled multi-window.
    if len(windows) < 2:
        return anomalies

    # Group by detector name: which windows did each fire in?
    detector_windows: dict[str, list[tuple[float, Anomaly]]] = {}
    for w, window_anomalies in per_window_anomalies.items():
        for a in window_anomalies:
            detector_windows.setdefault(a.name, []).append((w, a))

    for name, fires in detector_windows.items():
        windows_fired = {w for w, _ in fires}
        if windows_fired != set(windows):
            continue  # Didn't fire in every window

        # Elevate severity one step
        severities = [a.severity for _, a in fires]
        worst = (
            AnomalySeverity.HIGH
            if AnomalySeverity.HIGH in severities
            else AnomalySeverity.MEDIUM
            if AnomalySeverity.MEDIUM in severities
            else AnomalySeverity.LOW
        )
        elevated = {
            AnomalySeverity.LOW: AnomalySeverity.MEDIUM,
            AnomalySeverity.MEDIUM: AnomalySeverity.HIGH,
            AnomalySeverity.HIGH: AnomalySeverity.HIGH,  # saturated
        }[worst]

        anomalies.append(
            Anomaly(
                name=f"multi_window::{name}",
                severity=elevated,
                observation=(
                    f"{name} fired in all {len(windows)} windows "
                    f"({', '.join(f'{w / 86400:.0f}d' for w in windows)}). "
                    "Pattern is chronic, not transient — severity elevated."
                ),
                detail={
                    "detector": name,
                    "windows_fired": list(windows_fired),
                    "worst_single_severity": worst.value,
                },
                recommendation=(
                    "Chronic patterns persist across time-scales. Single-"
                    "window fires might be a bad session; multi-window "
                    "fires are habit. Investigate the underlying cause "
                    "before the habit calcifies."
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


def format_multi_window_report(
    windows: tuple[float, ...] = _MULTI_WINDOW_SECONDS,
    now: float | None = None,
) -> str:
    """PR-1b §5.5: cross-detector aggregation report across windows.

    Runs detectors per-window (not once at widest window — per brief
    addendum Q2 Option A: non-partitionable detectors like variance-
    collapse can't be correctly post-hoc windowed from a single run).

    Report layout (fresh-Claude addendum refinements 3+4):
        1. Concurrent HIGH (top, if any) — strongest signal class
        2. By-window default listing — zero-anomaly case rendered
           explicitly so absence-of-signal is itself visible
        3. By-detector appendix — sorted by fire-count descending
           (chronic patterns above one-off fires)
        4. Multi-window meta — detectors that fired in all windows,
           severity elevated one step per brief §2c
    """
    # Normalize `now` across all windows so the same call produces
    # byte-identical output when called twice with the same `now`.
    ts = now if now is not None else time.time()

    # emit_events=False: detect_anomalies skips inline emission so we
    # can dedupe across windows before emitting. Same HIGH anomaly
    # visible at 1d and 1w scales is ONE finding, not two ledger
    # events.
    per_window: dict[float, list[Anomaly]] = {}
    for w in windows:
        per_window[w] = detect_anomalies(window_seconds=w, now=ts, emit_events=False)

    # Dedupe HIGH anomalies by detector name across windows. Widest
    # window carries the emission so the event's window_seconds
    # payload reflects the fullest context the detector saw.
    emitted_names: set[str] = set()
    for w in sorted(windows, reverse=True):  # widest first
        for a in per_window[w]:
            if a.severity != AnomalySeverity.HIGH:
                continue
            if a.name in emitted_names:
                continue
            _emit_high_severity_events([a], w)
            emitted_names.add(a.name)

    multi_window_anomalies = _detect_multi_window_fires(per_window)

    # Aggregate by detector for appendix view
    by_detector: dict[str, list[tuple[float, Anomaly]]] = {}
    for w, anomalies in per_window.items():
        for a in anomalies:
            by_detector.setdefault(a.name, []).append((w, a))

    # Concurrent HIGH — HIGH-severity anomalies firing in same window
    concurrent_high: dict[float, list[Anomaly]] = {}
    for w, anomalies in per_window.items():
        highs = [a for a in anomalies if a.severity == AnomalySeverity.HIGH]
        if len(highs) >= 2:
            concurrent_high[w] = highs

    lines: list[str] = []
    lines.append("=== Multi-Window Compliance Audit ===")
    lines.append(f"  windows: {', '.join(f'{w / 86400:.0f}d' for w in sorted(windows))}")
    lines.append("")

    # 1. Concurrent HIGH (if any)
    if concurrent_high:
        lines.append("  [!!!] CONCURRENT HIGH-SEVERITY FIRES:")
        for w, highs in sorted(concurrent_high.items()):
            lines.append(f"    In {w / 86400:.0f}d window ({len(highs)} detectors):")
            for a in highs:
                lines.append(f"      - {a.name}: {a.observation}")
        lines.append("")

    # 2. By-window default (explicit zero-anomaly rendering)
    total_anomalies = sum(len(v) for v in per_window.values())
    if total_anomalies == 0:
        lines.append(f"  0 anomalies across {len(windows)} windows. Clean distribution.")
    else:
        lines.append("  By window:")
        for w in sorted(windows):
            w_anomalies = per_window[w]
            lines.append(f"    {w / 86400:.0f}d window:")
            if not w_anomalies:
                lines.append("      (no anomalies)")
                continue
            for a in w_anomalies:
                lines.append(f"      [{a.severity.value}] {a.name}")
                lines.append(f"        {a.observation}")
    lines.append("")

    # 3. By-detector appendix, sorted by fire-count descending
    if by_detector:
        lines.append("  By detector (sorted by fire-count, chronic first):")
        sorted_detectors = sorted(by_detector.items(), key=lambda kv: -len(kv[1]))
        for name, fires in sorted_detectors:
            windows_fired = sorted({w for w, _ in fires})
            windows_str = ", ".join(f"{w / 86400:.0f}d" for w in windows_fired)
            lines.append(f"    {name} — fired in {len(fires)} windows: {windows_str}")
        lines.append("")

    # 4. Multi-window meta fires
    if multi_window_anomalies:
        lines.append("  [!] Multi-window patterns (chronic, severity elevated):")
        for a in multi_window_anomalies:
            lines.append(f"    [{a.severity.value}] {a.name}")
            lines.append(f"      {a.observation}")
        lines.append("")

    return "\n".join(lines)
