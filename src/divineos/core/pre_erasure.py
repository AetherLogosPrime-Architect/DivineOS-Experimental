"""Pre-erasure capture — detect context-loss approach and suggest capture.

Realizes Pillar IX's `pre_erasure_capture` pull (omni_mantra_walk/12,
2026-04-30): "when context-loss is imminent (compaction approaching,
session ending), explicit capture of what would otherwise dissolve.
Architecture detects approach and triggers capture WITHOUT operator-
prompt."

Cluster H — Threshold-Triggered Protection. Past-me's meta-finding
(Pillar IX): five members, three already shipped (compass-rudder,
briefing-load gate, plus the F1-F5 detectors built 2026-05-05),
two as pulls (`affect_regulation_trigger`, `pre_erasure_capture`).
This module ships the substrate-side surface for the second pull;
auto-trigger via hook is a follow-up.

## What this module does

Reads session-state from ``~/.divineos/checkpoint_state.json`` (the
post-tool-use checkpoint already maintains this). Computes
heuristic approach-signals against pre-set thresholds:

* tool_calls — high accumulation suggests context-density rising
* writes_since_consolidation — extract-staleness signal
* edits — edit-density signal
* session-duration — wall-clock-elapsed since session_start

Returns a structured ``ApproachSignal`` dataclass with the metrics,
threshold-state per metric, and a human-readable suggestion. The
suggestion is read-only and advisory — never blocks anything,
never auto-extracts. Cluster H discipline: name the threshold;
let the operator/agent decide.

## What this module does NOT do

* Does NOT auto-extract. Triggering capture without operator
  consent would be the rubber-stamp failure mode.
* Does NOT have direct access to context-window token count.
  Heuristics use proxy metrics (tool calls, edits, time elapsed)
  rather than the actual token-utilization Claude Code tracks
  internally. Future enhancement when/if token-count becomes
  exposed via hook payloads.
* Does NOT guarantee compaction won't happen before the surface
  is checked. The surface has to be invoked (manually or via
  hook); without invocation the heuristic doesn't fire.

## Integration patterns

Direct CLI: ``divineos pre-erasure status`` calls ``compute_signal()``
and prints the result. Read-only.

Future hook integration (NOT in this commit): a PostToolUse hook
that fires every Nth tool call, checks ``compute_signal()``, and
surfaces a non-blocking warning when thresholds are crossed.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from divineos.core.paths import marker_path

# Heuristic thresholds. Tunable; will be reviewed against real session
# data. Initial values picked from observation of typical session
# shapes rather than principled derivation.
_TOOL_CALLS_MODERATE = 200
_TOOL_CALLS_HIGH = 400
_TOOL_CALLS_CRITICAL = 600
_WRITES_SINCE_CONSOLIDATION_OVERDUE = 30
_WRITES_SINCE_CONSOLIDATION_CRITICAL = 50
_EDITS_HIGH = 50
_EDITS_CRITICAL = 100
_SESSION_HOURS_LONG = 4.0
_SESSION_HOURS_VERY_LONG = 8.0


SignalLevel = Literal["fresh", "moderate", "elevated", "high", "critical"]


@dataclass(frozen=True)
class MetricStatus:
    """One metric's current value and threshold-state."""

    name: str
    value: float
    level: SignalLevel
    threshold_hit: str | None  # description of which threshold (if any) was crossed


@dataclass(frozen=True)
class ApproachSignal:
    """Aggregated pre-erasure approach signal across all metrics.

    The ``overall_level`` is the max of per-metric levels. The
    suggestion is a human-readable string the caller renders.
    """

    metrics: list[MetricStatus]
    overall_level: SignalLevel
    suggestion: str
    timestamp: float


def _state_path() -> Path:
    """Where post_tool_use_checkpoint writes its JSON."""
    return marker_path("checkpoint_state.json")


def _load_state() -> dict:
    """Load checkpoint state. Returns empty dict if not present."""
    path = _state_path()
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _classify_tool_calls(value: int) -> tuple[SignalLevel, str | None]:
    if value >= _TOOL_CALLS_CRITICAL:
        return "critical", f"tool_calls >= {_TOOL_CALLS_CRITICAL} (critical accumulation)"
    if value >= _TOOL_CALLS_HIGH:
        return "high", f"tool_calls >= {_TOOL_CALLS_HIGH} (high accumulation)"
    if value >= _TOOL_CALLS_MODERATE:
        return "moderate", f"tool_calls >= {_TOOL_CALLS_MODERATE} (moderate accumulation)"
    return "fresh", None


def _classify_writes_since_consolidation(value: int) -> tuple[SignalLevel, str | None]:
    if value >= _WRITES_SINCE_CONSOLIDATION_CRITICAL:
        return (
            "critical",
            f"writes_since_consolidation >= {_WRITES_SINCE_CONSOLIDATION_CRITICAL} (extract critical)",
        )
    if value >= _WRITES_SINCE_CONSOLIDATION_OVERDUE:
        return (
            "elevated",
            f"writes_since_consolidation >= {_WRITES_SINCE_CONSOLIDATION_OVERDUE} (extract overdue)",
        )
    return "fresh", None


def _classify_edits(value: int) -> tuple[SignalLevel, str | None]:
    if value >= _EDITS_CRITICAL:
        return "critical", f"edits >= {_EDITS_CRITICAL} (edit-density critical)"
    if value >= _EDITS_HIGH:
        return "elevated", f"edits >= {_EDITS_HIGH} (edit-density high)"
    return "fresh", None


def _classify_session_hours(value: float) -> tuple[SignalLevel, str | None]:
    if value >= _SESSION_HOURS_VERY_LONG:
        return "high", f"session > {_SESSION_HOURS_VERY_LONG}h (very long)"
    if value >= _SESSION_HOURS_LONG:
        return "moderate", f"session > {_SESSION_HOURS_LONG}h (long)"
    return "fresh", None


_LEVEL_ORDER: dict[SignalLevel, int] = {
    "fresh": 0,
    "moderate": 1,
    "elevated": 2,
    "high": 3,
    "critical": 4,
}


def _max_level(levels: list[SignalLevel]) -> SignalLevel:
    """Return the highest-severity level from a list."""
    if not levels:
        return "fresh"
    return max(levels, key=lambda level: _LEVEL_ORDER[level])


def _build_suggestion(level: SignalLevel, hits: list[str]) -> str:
    """Render a human-readable suggestion from the overall level + hits."""
    if level == "fresh":
        return (
            "Session is fresh. No pre-erasure capture indicated. Continue work; "
            "check back periodically or after substantial output."
        )
    if level == "moderate":
        return (
            "Session is accumulating moderately. Consider filing any outstanding "
            "load-bearing observations as knowledge entries when you reach a "
            "natural pause. No urgent action."
        )
    if level == "elevated":
        return (
            "Pre-erasure attention recommended. Run `divineos extract` to "
            "consolidate, OR file any unfiled load-bearing observations as "
            "`divineos learn` entries. Do this before context grows further."
        )
    if level == "high":
        return (
            "Pre-erasure capture STRONGLY suggested. Capture now: run "
            "`divineos extract`, file any unfiled principles or observations "
            "as knowledge entries, write any pending exploration entries. "
            "Compaction may be approaching — load-bearing context could "
            "compress lossily without active capture."
        )
    # critical
    return (
        "PRE-ERASURE CAPTURE URGENT. Stop adding to context-density and "
        "capture now. Run `divineos extract`. File pending principles via "
        "`divineos learn`. Write any exploration entries before continuing. "
        "Multiple thresholds crossed — context-loss likely imminent in this "
        "session."
    )


def compute_signal(state: dict | None = None, now: float | None = None) -> ApproachSignal:
    """Compute the current pre-erasure approach signal.

    Args:
        state: optional state dict (for testing). If None, reads from
            the checkpoint state file.
        now: optional current timestamp (for testing). If None, uses
            time.time().

    Returns:
        ``ApproachSignal`` with per-metric statuses, overall level, and
        a human-readable suggestion.
    """
    if state is None:
        state = _load_state()
    if now is None:
        now = time.time()

    tool_calls = int(state.get("tool_calls", 0) or 0)
    writes = int(state.get("writes_since_consolidation", 0) or 0)
    edits = int(state.get("edits", 0) or 0)
    session_start = float(state.get("session_start", now) or now)
    session_hours = max(0.0, (now - session_start) / 3600.0)

    metrics: list[MetricStatus] = []

    tc_level, tc_hit = _classify_tool_calls(tool_calls)
    metrics.append(MetricStatus("tool_calls", tool_calls, tc_level, tc_hit))

    wr_level, wr_hit = _classify_writes_since_consolidation(writes)
    metrics.append(MetricStatus("writes_since_consolidation", writes, wr_level, wr_hit))

    ed_level, ed_hit = _classify_edits(edits)
    metrics.append(MetricStatus("edits", edits, ed_level, ed_hit))

    sh_level, sh_hit = _classify_session_hours(session_hours)
    metrics.append(MetricStatus("session_hours", round(session_hours, 2), sh_level, sh_hit))

    overall = _max_level([m.level for m in metrics])
    hits = [m.threshold_hit for m in metrics if m.threshold_hit]
    suggestion = _build_suggestion(overall, [h for h in hits if h])

    return ApproachSignal(
        metrics=metrics,
        overall_level=overall,
        suggestion=suggestion,
        timestamp=now,
    )


__all__ = [
    "ApproachSignal",
    "MetricStatus",
    "SignalLevel",
    "compute_signal",
]
