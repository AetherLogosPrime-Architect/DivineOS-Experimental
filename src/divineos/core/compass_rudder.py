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

RUDDER_ACK_TAG = "rudder-ack"
"""Tag required on a compass observation for it to count as a rudder
response. Distinguishes intentional acknowledgement of the drift alert
from the background observations that caused the drift in the first
place. Unguessable by accident (a typo becomes a no-op)."""


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

    Previously: a decision_journal entry that mentioned the spectrum name
    was enough. That was gameable — I caught myself doing it — because
    a decide is free-form prose and the spectrum name is one word.

    Now: justification requires a compass_observation on the drifting
    spectrum, recorded within the window. An observation is structured:
    it names the spectrum (can't be missing), states a position delta
    (signed number — can't be a shell), and supplies evidence (non-empty
    string). You cannot game an observation the way you can game a
    decide; the schema forces you to say where the spectrum actually
    sits and why.

    File one with:
        divineos compass-ops observe SPECTRUM -p <delta> -e "<evidence>"
    """
    if not spectrums:
        return []

    ts = now if now is not None else time.time()
    cutoff = ts - window_seconds

    try:
        from divineos.core.moral_compass import get_observations
    except ImportError:
        return []

    justified: set[str] = set()
    for spectrum in spectrums:
        try:
            recent = get_observations(spectrum=spectrum, limit=10)
        except Exception:  # noqa: BLE001
            continue
        for obs in recent:
            if obs.get("created_at", 0.0) < cutoff:
                continue
            if RUDDER_ACK_TAG in (obs.get("tags") or []):
                justified.add(spectrum)
                break
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

    Shape: name the specific spectrum, the specific tool, and the exact
    command needed to unblock. Keep the unblock trivially accessible —
    the rudder is a pause, not a wall — but require a structured
    compass observation, not free-form prose. Observations have a
    spectrum name, a signed position delta, and evidence text;
    together they force the operator to actually say where the
    spectrum sits and why.
    """
    window_min = window_seconds / 60
    spectrum_list = ", ".join(missing)
    primary_spectrum = missing[0] if missing else "SPECTRUM"
    return (
        f"COMPASS RUDDER: '{tool_name}' blocked because "
        f"{spectrum_list} is drifting toward excess and no compass "
        f"observation was recorded in the last {window_min:.0f} minutes. "
        f"Before proceeding, file a compass observation — not a decide, "
        f"not prose. Name where the spectrum sits and why:\n\n"
        f"    divineos compass-ops observe {primary_spectrum} "
        f'-p <signed delta> -e "<evidence for the position>" '
        f"--tag {RUDDER_ACK_TAG}\n\n"
        f"Delta is signed: negative = toward deficiency, positive = "
        f"toward excess, zero = on-center. Evidence is concrete "
        f"(what observable behavior justifies the position). Then "
        f"retry the tool call. The observation is logged to the "
        f"compass_observation table so drift-under-ignored-alert is "
        f"auditable as a data entry, not narrative."
    )
