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
import secrets
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

_FIRE_ID_ENTROPY_BYTES = 8
"""Item 6: 8 bytes = 16 hex chars = 64 bits of entropy. Forward-
guessing within the 5-minute window is computationally infeasible.
Full-length id is displayed and validated; no prefix matching."""


def _generate_fire_id() -> str:
    """Cryptographically-random fire id (16 hex chars)."""
    return secrets.token_hex(_FIRE_ID_ENTROPY_BYTES)


def _emit_fire_event(
    fire_id: str,
    spectrum: str,
    all_drifting: list[str],
    tool_name: str,
    window_seconds: float,
    threshold: float,
    drift_values: dict[str, float],
) -> None:
    """Log COMPASS_RUDDER_FIRED to the ledger.

    Forensic record of enforcement. Never pruned by the ephemeral
    compressor — see ledger_compressor._COMPRESSIBLE_TYPES (FIRED is
    deliberately NOT in that set). Payload includes ``threshold`` per
    fresh-Claude round-2 Q3 so historical fires stay interpretable if
    DRIFT_THRESHOLD changes.
    """
    try:
        from divineos.core.ledger import log_event

        log_event(
            event_type="COMPASS_RUDDER_FIRED",
            actor="rudder",
            payload={
                "fire_id": fire_id,
                "spectrum": spectrum,
                "all_drifting": all_drifting,
                "tool_name": tool_name,
                "window_seconds": window_seconds,
                "threshold": threshold,
                "drift_values": drift_values,
            },
            validate=False,
        )
    except Exception:  # noqa: BLE001
        # Failure to log the event must not fail the rudder open.
        pass


def _emit_allow_event(
    tool_name: str,
    reason: str,
    drifting_spectrums: list[str],
    recent_justifications: list[str],
) -> None:
    """Log COMPASS_RUDDER_ALLOW to the ledger.

    Frequent (every gated tool call). Goes through the ephemeral-
    pruning path in ledger_compressor; Item 8's compliance audit uses
    block/allow ratio as a health signal. Payload fields match
    brief v2.1 §3 — no redundant timestamp (ledger auto-adds), no
    redundant fire_id/spectrum fields that drifting_spectrums carries.
    """
    try:
        from divineos.core.ledger import log_event

        log_event(
            event_type="COMPASS_RUDDER_ALLOW",
            actor="rudder",
            payload={
                "tool_name": tool_name,
                "reason": reason,
                "drifting_spectrums": drifting_spectrums,
                "recent_justifications": recent_justifications,
            },
            validate=False,
        )
    except Exception:  # noqa: BLE001
        pass


def _drift_values_for_spectrums(spectrums: list[str]) -> dict[str, float]:
    """Snapshot drift magnitudes for spectrums at fire time (forensic record)."""
    try:
        from divineos.core.moral_compass import read_compass

        positions = read_compass()
    except Exception:  # noqa: BLE001
        return {}
    result: dict[str, float] = {}
    for pos in positions:
        if pos.spectrum in spectrums:
            result[pos.spectrum] = float(abs(getattr(pos, "drift", 0.0)))
    return result


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

    # Pre-Item-4: fetched limit=10 and filtered tags in Python. Gameable
    # under load — 10 non-ack observations on a drifting spectrum within
    # the window made a legitimate earlier ack invisible. Item 4 pushes
    # the filter to SQL: get_observations now takes tag= and since= and
    # does the membership check via json_each. No Python-side tag filter,
    # no limit=10.
    #
    # Item 6: an ack satisfies a rudder fire ONLY if it has a fire_id
    # bound to a COMPASS_RUDDER_FIRED event (brief v2.1 §4 scenario b).
    # An unbound ack (fire_id IS NULL) was silently accepted in the
    # first-draft Item 6 implementation — fresh-Claude round-3 caught
    # this as the single correctness gap. Fix: filter acks to
    # fire_id IS NOT NULL. The log_observation validator already
    # verifies at write-time that the fire_id references a real fire
    # event, and the consumption table's PRIMARY KEY enforces one-shot,
    # so fire_id-not-null is a sufficient proof of binding here.
    justified: set[str] = set()
    for spectrum in spectrums:
        try:
            # Fetch a small batch so we can skip unbound acks without
            # making too many queries. 20 is well over the realistic
            # ack-per-window count and keeps the SQL filter's precision
            # property (Item 4).
            acks = get_observations(
                spectrum=spectrum,
                tag=RUDDER_ACK_TAG,
                since=cutoff,
                limit=20,
            )
        except Exception:  # noqa: BLE001
            continue
        if any(a.get("fire_id") for a in acks):
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
        # Non-gated tools don't emit allow-events — the rudder never
        # ran for them. Allow-events are only for gated-tool decisions,
        # so Item 8's block/allow ratio is meaningful.
        return RudderVerdict(
            decision="allow",
            reason=f"tool '{tool_name}' is not gated by the compass rudder",
            drifting_spectrums=[],
            recent_justifications=[],
        )

    drifting = _get_drifting_spectrums(threshold=threshold)
    if not drifting:
        reason = "no spectrum drifting toward excess above threshold"
        _emit_allow_event(tool_name, reason, [], [])
        return RudderVerdict(
            decision="allow",
            reason=reason,
            drifting_spectrums=[],
            recent_justifications=[],
        )

    justified = _find_justifications(drifting, now=now, window_seconds=window_seconds)
    missing = [s for s in drifting if s not in justified]

    if not missing:
        reason = "all drifting spectrums have a recent justification: " + ", ".join(justified)
        _emit_allow_event(tool_name, reason, drifting, justified)
        return RudderVerdict(
            decision="allow",
            reason=reason,
            drifting_spectrums=drifting,
            recent_justifications=justified,
        )

    # Block path: Item 6 generates a fire_id, emits FIRED event, and
    # embeds the full-length fire_id in the block message for the agent
    # to reference when filing the ack.
    fire_id = _generate_fire_id()
    _emit_fire_event(
        fire_id=fire_id,
        spectrum=missing[0],
        all_drifting=drifting,
        tool_name=tool_name,
        window_seconds=window_seconds,
        threshold=threshold,
        drift_values=_drift_values_for_spectrums(missing),
    )
    return RudderVerdict(
        decision="block",
        reason=_build_block_message(tool_name, missing, window_seconds, fire_id=fire_id),
        drifting_spectrums=drifting,
        recent_justifications=justified,
    )


def _build_block_message(
    tool_name: str,
    missing: list[str],
    window_seconds: float,
    fire_id: str | None = None,
) -> str:
    """Construct the agent-facing block message.

    Includes the Item 6 fire_id when one was issued. Full-length (16
    hex chars) — brief v2.1 §2 picked security cleanliness over CLI
    brevity; what-you-see-is-what-you-copy since validation is exact-
    equality.
    """
    window_min = window_seconds / 60
    spectrum_list = ", ".join(missing)
    primary_spectrum = missing[0] if missing else "SPECTRUM"
    fire_id_prefix = f"[fire-{fire_id}] " if fire_id else ""
    fire_id_flag = f" --fire-id {fire_id}" if fire_id else ""
    fire_id_note = (
        "\n\nThe fire_id binds your ack to this specific block. Prior "
        "acks cannot satisfy this fire, and this fire_id cannot satisfy "
        "future blocks."
        if fire_id
        else ""
    )
    return (
        f"COMPASS RUDDER {fire_id_prefix}: '{tool_name}' blocked because "
        f"{spectrum_list} is drifting toward excess and no compass "
        f"observation was recorded in the last {window_min:.0f} minutes. "
        f"Before proceeding, file a compass observation — not a decide, "
        f"not prose. Name where the spectrum sits and why:\n\n"
        f"    divineos compass-ops observe {primary_spectrum} "
        f'-p <signed delta> -e "<evidence for the position>" '
        f"--tag {RUDDER_ACK_TAG}{fire_id_flag}\n\n"
        f"Delta is signed: negative = toward deficiency, positive = "
        f"toward excess, zero = on-center. Evidence is concrete "
        f"(what observable behavior justifies the position). Then "
        f"retry the tool call. The observation is logged to the "
        f"compass_observation table so drift-under-ignored-alert is "
        f"auditable as a data entry, not narrative." + fire_id_note
    )
