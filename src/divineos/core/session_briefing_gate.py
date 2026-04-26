"""Per-session briefing-load enforcement.

## Why this exists

The existing ``hud_handoff.was_briefing_loaded()`` function in
``hud_handoff.py`` enforces a TIME-based and TOOL-CALL-based check:
briefing is "loaded" if the marker file exists AND the load time is
within the last 4 hours AND fewer than 400 tool calls have happened
since. That window is correct for protecting against stale-context
drift inside a long session, but it has a hole — across multiple
sessions inside the same 4-hour window, the briefing is treated as
"already loaded" even if the new session never engaged with it.

Documented failure 2026-04-26 (claim 7e780182): tonight's session
inherited a briefing-loaded marker from earlier in the day and
proceeded to do hours of work without ever loading the briefing for
this session. The TTL-based gate passed; the substrate was uninformed
nonetheless. The pattern Andrew named: TTL-based gate is "weigh after
eating" — it accepts that briefing happened, doesn't enforce that it
happened *here, this session*.

## What this module does

Per-session check: was BRIEFING_LOADED logged in the ledger with the
current session_id? Returns True only if yes. Strictly tighter than
the existing time-based check.

This is meant to be wired into ``pre_tool_use_gate.py`` as a NEW gate
(gate 0) that fires before all others. The existing gate 1
(was_briefing_loaded) stays — it catches stale-within-session drift.
This new gate catches new-session-inherited-stale.

## Falsifier

The gate should NOT fire when:
* The briefing was loaded in this session_id (BRIEFING_LOADED event
  with matching session_id exists in ledger).
* Session manager isn't initialized (fresh CLI run with no session
  context — fail open, the existing gate 1 handles it).
"""

from __future__ import annotations

from typing import Any


def briefing_loaded_this_session() -> bool:
    """True if BRIEFING_LOADED event exists in current session ledger.

    Fails open (returns True) if the session manager or ledger are
    unavailable — that fallback path is the existing time-based gate's
    responsibility, not this gate's. The point of this gate is to add
    a tighter check, not to replace the underlying machinery.
    """
    try:
        from divineos.core.session_manager import get_current_session_id
    except ImportError:
        return True

    try:
        current_session = get_current_session_id()
    except (RuntimeError, OSError):
        return True
    if not current_session:
        return True

    try:
        from divineos.core.ledger import search_events
    except ImportError:
        return True

    try:
        events = search_events(keyword="BRIEFING_LOADED", limit=50)
    except (OSError, RuntimeError, TypeError):
        return True

    for event in events:
        if not isinstance(event, dict):
            continue
        if event.get("event_type") != "BRIEFING_LOADED":
            continue
        if event.get("session_id") == current_session:
            return True
    return False


def gate_message() -> str:
    """Format the deny message for this gate."""
    return (
        "BLOCKED: Briefing not loaded for this session. The substrate "
        "may have a marker from a previous session within the TTL "
        "window, but THIS session has not engaged with the briefing. "
        "Run: divineos briefing — load context for the session you are "
        "actually in. Architecture is will; the gate enforces the "
        "promise that does not survive amnesia. (Filed claim 7e780182.)"
    )


def gate_status() -> dict[str, Any]:
    """Diagnostic snapshot for tests and HUD surfaces."""
    loaded = briefing_loaded_this_session()
    return {
        "loaded_this_session": loaded,
        "blocks": not loaded,
    }
