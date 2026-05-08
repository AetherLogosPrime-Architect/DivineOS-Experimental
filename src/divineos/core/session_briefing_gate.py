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
    """True if briefing was loaded with the current session_id.

    Reads the ``~/.divineos/hud/.briefing_loaded`` marker file and
    verifies its stored ``session_id`` matches ``get_current_session_id()``.
    The marker file is the canonical record of "briefing loaded this
    session" — it's written by ``mark_briefing_loaded()`` on every
    briefing run and persists across CLI invocations within a session.

    Fails open (returns True) if the session manager isn't available
    or the marker file can't be read — the existing TTL-based gate
    catches those cases and the strict check shouldn't double-deny.
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

    # Read the marker file directly. Cheap, no DB, no keyword-substring
    # bug. The marker is written by ``mark_briefing_loaded()`` and
    # contains the session_id of the briefing-load that wrote it. The
    # marker lives in the HUD directory (whose location depends on
    # which DB the install is using), so resolve via _get_hud_dir
    # rather than hardcoding the path.
    import json

    try:
        from divineos.core._hud_io import _get_hud_dir
    except ImportError:
        return True

    try:
        marker_path = _get_hud_dir() / ".briefing_loaded"
    except Exception:  # noqa: BLE001 — fail-soft if hud-dir resolution breaks
        return True

    if not marker_path.exists():
        return False
    try:
        marker = json.loads(marker_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return True
    if not isinstance(marker, dict):
        return True

    return marker.get("session_id") == current_session


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
