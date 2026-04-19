"""Compass rudder — decision-time enforcement for drift-toward-excess.

# AGENT_RUNTIME — Not wired into CLI pipeline. Invoked from
# .claude/hooks/compass-check.sh at PreToolUse. Intentionally not
# Python-imported from any CLI module: the rudder steers agent
# behavior at tool-call time, which is a shell-hook surface, not a
# CLI surface. Tested via test_compass_rudder.py.

Before the 2026-04-16 Grok audit, the moral compass was a mirror: it
recorded where the agent had been but never fired into decision-time.
Grok: *"The compass is recording, not steering. Find one example where
it stopped a decision before you made it."* There were none.

The rudder fires at PreToolUse for specific high-leverage tool calls
(currently just ``Task`` — subagent spawns, the exact operation that
caused yesterday's ``initiative: excess`` drift). If any compass spectrum
shows drift at or above ``DRIFT_THRESHOLD`` toward excess, the rudder
looks for a recent ``divineos decide`` entry that mentions the drifting
spectrum. If none is found within the ``justification_window`` (default
5 minutes), the hook blocks with a request for justification.

The act of typing the justification is itself the pattern interrupt.
The ledger trail makes drift-under-ignored-alert auditable post-hoc.
This is Beer's algedonic channel, narrowly scoped.

Scope decisions (narrow-and-sharp):
* Only ``Task`` is gated in the first version. Broader gates (Edit /
  Write / etc.) would fire too often and get ignored. Widen only if
  this proves out.
* Only drift ``toward_excess`` triggers the rudder. Drift toward
  deficiency or toward virtue is informational, not blocking.
* Only ``DRIFT_THRESHOLD`` absolute value is used — small stable
  drifts don't block.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

DRIFT_THRESHOLD = 0.15
"""Minimum drift magnitude (toward excess) that fires the rudder."""

JUSTIFICATION_WINDOW_SECONDS = 5 * 60
"""Recent-decide lookback window. A justification emitted within this
many seconds of the gated tool call counts as a valid pre-action note."""

GATED_TOOL_NAMES = frozenset({"Task", "Agent"})
"""Tool names that trigger a rudder check. ``Task`` is the current
Claude Code name for the subagent-spawn primitive; ``Agent`` is kept
as an alias in case of rename or older tooling."""


@dataclass
class RudderVerdict:
    """Outcome of a rudder check for a single attempted tool use."""

    decision: str  # "allow" or "block"
    reason: str
    drifting_spectrums: list[str]
    recent_justifications: list[str]

    @property
    def blocked(self) -> bool:
        return self.decision == "block"


def _get_drifting_spectrums(threshold: float = DRIFT_THRESHOLD) -> list[str]:
    """Return names of spectrums currently drifting toward excess at or above ``threshold``.

    Imports are inside the function so importing this module doesn't
    immediately initialize the compass DB (matters for test speed and
    hook cold-start latency).
    """
    try:
        from divineos.core.moral_compass import read_compass
    except ImportError:
        return []

    try:
        positions = read_compass()
    except Exception:  # noqa: BLE001 — hook must never fail open with an exception leak
        return []

    drifting: list[str] = []
    for pos in positions:
        if (
            getattr(pos, "drift_direction", None) == "toward_excess"
            and abs(getattr(pos, "drift", 0.0)) >= threshold
        ):
            drifting.append(pos.spectrum)
    return drifting


def _find_justifications(
    spectrums: list[str],
    now: float | None = None,
    window_seconds: float = JUSTIFICATION_WINDOW_SECONDS,
) -> list[str]:
    """Return spectrum names for which a recent justification was found.

    A decision_journal entry counts as a justification if:
      * it was created within ``window_seconds`` of ``now``, AND
      * its content OR reasoning mentions the spectrum name
        (case-insensitive substring match)
    """
    if not spectrums:
        return []

    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds

    try:
        from divineos.core.decision_journal import list_decisions
    except ImportError:
        return []

    try:
        recent = list_decisions(limit=30)
    except Exception:  # noqa: BLE001
        return []

    justified: set[str] = set()
    for d in recent:
        created_at = d.get("created_at", 0.0)
        if created_at < cutoff:
            continue
        blob = f"{d.get('content', '')} {d.get('reasoning', '')}".lower()
        for spectrum in spectrums:
            if spectrum.lower() in blob:
                justified.add(spectrum)
    return sorted(justified)


def check_tool_use(
    tool_name: str,
    tool_input: dict[str, Any] | None = None,  # noqa: ARG001  kept in signature for forward compat with per-tool gating
    now: float | None = None,
    threshold: float = DRIFT_THRESHOLD,
    window_seconds: float = JUSTIFICATION_WINDOW_SECONDS,
) -> RudderVerdict:
    """Evaluate whether a tool use is gated by the compass rudder.

    Returns a RudderVerdict. Never raises — if anything goes wrong
    (compass unreadable, DB missing, unexpected shape), the rudder
    fails OPEN rather than blocking legitimate work on an infrastructure
    error. Safety-first design: a compass rudder that breaks the agent
    when the compass DB is empty is worse than one that occasionally
    misses a drift event.

    The ``tool_input`` argument is accepted for forward compatibility —
    future versions may gate differently based on subagent prompt shape
    or destructive-op flags — but is not inspected in this first version.
    """
    del tool_input  # currently unused; kept in signature for future per-tool logic

    if tool_name not in GATED_TOOL_NAMES:
        return RudderVerdict(
            decision="allow",
            reason=f"tool '{tool_name}' is not gated by the compass rudder",
            drifting_spectrums=[],
            recent_justifications=[],
        )

    drifting = _get_drifting_spectrums(threshold=threshold)
    if not drifting:
        return RudderVerdict(
            decision="allow",
            reason="no spectrum drifting toward excess above threshold",
            drifting_spectrums=[],
            recent_justifications=[],
        )

    justified = _find_justifications(drifting, now=now, window_seconds=window_seconds)
    missing = [s for s in drifting if s not in justified]

    if not missing:
        return RudderVerdict(
            decision="allow",
            reason=("all drifting spectrums have a recent justification: " + ", ".join(justified)),
            drifting_spectrums=drifting,
            recent_justifications=justified,
        )

    return RudderVerdict(
        decision="block",
        reason=_build_block_message(tool_name, missing, window_seconds),
        drifting_spectrums=drifting,
        recent_justifications=justified,
    )


def _build_block_message(tool_name: str, missing: list[str], window_seconds: float) -> str:
    """Construct the agent-facing block message.

    The message is shaped to elicit a decide-call — it names the
    specific spectrum(s), the specific tool, and the exact command
    needed to unblock. Keeping the unblock trivially accessible is the
    point: the rudder is a pause, not a wall.
    """
    window_min = window_seconds / 60
    spectrum_list = ", ".join(missing)
    return (
        f"COMPASS RUDDER: '{tool_name}' blocked because "
        f"{spectrum_list} is drifting toward excess and no justification "
        f"was emitted in the last {window_min:.0f} minutes. "
        f"Before proceeding, write one line: "
        f'divineos decide "<why this Task is necessary and not excess>" '
        f'--why "<reasoning mentioning {spectrum_list}>" '
        f"Then retry the tool call. The justification is logged to "
        f"decision_journal so drift-under-ignored-alert is auditable."
    )
