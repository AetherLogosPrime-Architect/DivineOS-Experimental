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

_RUDDER_ACK_SHORT_EVIDENCE_THRESHOLD = 0.60
"""If >60% of rudder-acks have evidence text shorter than 15 characters,
evidence is performative. Real calibration evidence is usually at least
one short sentence."""

_RUDDER_ACK_SHORT_EVIDENCE_CHARS = 15
"""Character threshold under which an evidence string is considered too
short to be substantive."""

_RUDDER_ACK_BURST_WINDOW_SECONDS = 10.0
"""If two acks are filed within 10 seconds of each other, they're bursty.
A real calibration pause wouldn't produce back-to-back filings."""

_RUDDER_ACK_BURST_THRESHOLD = 0.40
"""If >40% of acks were filed within the burst window of another ack,
acks are being batched — likely shell-clearing."""

_DECIDE_MIN_COUNT = 3
"""Don't flag on fewer than 3 decides — need a distribution to read."""


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
    timestamps = sorted(float(o.get("created_at", 0.0)) for o in acks)

    # Burst detection: count pairs of consecutive acks filed within the
    # burst window.
    bursty_count = 0
    for i in range(1, len(timestamps)):
        if timestamps[i] - timestamps[i - 1] < _RUDDER_ACK_BURST_WINDOW_SECONDS:
            bursty_count += 1

    position_zero_count = sum(1 for p in positions if abs(p) < 0.05)
    short_evidence_count = sum(
        1 for le in evidence_lengths if le < _RUDDER_ACK_SHORT_EVIDENCE_CHARS
    )

    return {
        "count": len(acks),
        "window_seconds": window_seconds,
        "position": {
            "mean": statistics.mean(positions) if positions else 0.0,
            "stdev": statistics.stdev(positions) if len(positions) > 1 else 0.0,
            "fraction_zero": position_zero_count / len(positions),
        },
        "evidence_length": {
            "mean": statistics.mean(evidence_lengths) if evidence_lengths else 0.0,
            "median": (statistics.median(evidence_lengths) if evidence_lengths else 0.0),
            "fraction_short": short_evidence_count / len(evidence_lengths),
        },
        "bursty": {
            "pairs_in_burst_window": bursty_count,
            "fraction": bursty_count / max(1, len(acks) - 1),
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
        burst = ack_summary["bursty"]

        if pos["fraction_zero"] > _RUDDER_ACK_POSITION_ZERO_THRESHOLD:
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

        if ev["fraction_short"] > _RUDDER_ACK_SHORT_EVIDENCE_THRESHOLD:
            anomalies.append(
                Anomaly(
                    name="rudder_ack_short_evidence",
                    severity=AnomalySeverity.MEDIUM,
                    observation=(
                        f"{int(ev['fraction_short'] * 100)}% of rudder-ack "
                        f"evidence strings are under "
                        f"{_RUDDER_ACK_SHORT_EVIDENCE_CHARS} chars "
                        f"(median={ev['median']:.0f}, n={ack_summary['count']}). "
                        "Evidence is performative."
                    ),
                    detail=ev,
                    recommendation=(
                        "Real calibration evidence names observable behavior. "
                        "If evidence is 'ack' or 'noted', nothing was calibrated."
                    ),
                )
            )

        if burst["fraction"] > _RUDDER_ACK_BURST_THRESHOLD:
            anomalies.append(
                Anomaly(
                    name="rudder_ack_bursty_filings",
                    severity=AnomalySeverity.MEDIUM,
                    observation=(
                        f"{int(burst['fraction'] * 100)}% of rudder-acks "
                        f"were filed within "
                        f"{_RUDDER_ACK_BURST_WINDOW_SECONDS:.0f}s of another "
                        "ack. Batched clearing, not spaced calibration."
                    ),
                    detail=burst,
                    recommendation=(
                        "A real compass check takes longer than 10 seconds. "
                        "Bursty acks mean the gate is being cleared for "
                        "throughput, not heeded."
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
        b = ack["bursty"]
        lines.append(f"    count: {ack['count']}")
        lines.append(
            f"    position: mean={p['mean']:+.3f}, stdev={p['stdev']:.3f}, "
            f"fraction_zero={p['fraction_zero']:.0%}"
        )
        lines.append(
            f"    evidence length: mean={e['mean']:.0f} chars, "
            f"median={e['median']:.0f}, fraction<15={e['fraction_short']:.0%}"
        )
        lines.append(
            f"    burst pairs: {b['pairs_in_burst_window']} ({b['fraction']:.0%} of transitions)"
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
