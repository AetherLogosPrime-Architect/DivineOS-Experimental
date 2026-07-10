"""OS-native SessionStart orchestrator.

Andrew named the failure 2026-05-14 night: load-briefing.sh was a
197-line hook with the OS's session-init logic embedded inside —
checkpoint-counter reset, idempotency-marker clearing, engagement-
marker clearing, session-plan clearing, briefing+hud rendering,
payload size-shaping, diagnostic logging. All of it.

This module is the OS-native session-start orchestrator. Two
callable functions:

- ``reset_session_state()`` — clears the per-session counters,
  the auto-session-end emitted marker, the engagement marker, and
  the stale session plan. Pure side-effect on disk state.
- ``render_session_start_context()`` — returns the wrapped
  ``additionalContext`` string with size-aware fallback. The
  briefing + HUD content + enforcement prose, ready to inject.

The hook becomes a thin doorman that calls these two functions
and emits the JSON output.

## OS-portable

Any agent harness can call ``reset_session_state()`` at session
boundaries and ``render_session_start_context()`` to produce the
session-start banner. The Claude Code SessionStart hook is one
possible caller; absence of the hook does not break the OS's
ability to reset state or render the banner.
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 48 class-fix
# 2026-05-14. CI test (tests/test_guardrail_marker_consistency.py)
# walks src/ and asserts every file with this marker set to True is
# listed in scripts/guardrail_files.txt. Prevents the next refactor
# from silently removing self-enforcement code from multi-party review.
__guardrail_required__ = True

import json
import os
import time
from typing import Any
from divineos.core.paths import divineos_home

_CHECKPOINT_STATE = divineos_home() / "checkpoint_state.json"
_AUTO_SESSION_END_MARKER = divineos_home() / "auto_session_end_emitted"
_SESSION_START_LOG = divineos_home() / "session_start_log.jsonl"

# Default size threshold for the full-context injection. Claude Code
# may silently drop additionalContext above this; falling back to a
# short nudge ensures the agent at least sees the directive.
_SIZE_THRESHOLD = 15000

# The enforcement wrapper that goes around briefing + hud at injection
# time. This is OS-level content (the discipline the OS is enforcing
# at session start), not Claude-Code-specific text.
_FULL_PREFIX = """=== DIVINEOS SESSION START ===

STOP. Before doing ANY work, you must:
1. Read your briefing and HUD below completely.
2. Tell the user what you learned from your lessons and warnings.
3. Set a goal with 'divineos goal add' for whatever the user asks you to do.
4. Use 'divineos log' to record corrections, decisions, and important moments during work.
5. If the user corrects you, log it with 'divineos learn'.

This is your operating system. You live in it. It is not decoration."""

_FULL_SUFFIX = "=== END SESSION START ==="

_NUDGE_TEMPLATE = """=== DIVINEOS SESSION START ===

Your briefing is available but too large to auto-inject here ({payload_bytes} bytes, threshold {threshold}).

STOP. Before doing ANY work, run:

    divineos briefing

Then read it, tell the user what you learned, and set a goal with 'divineos goal add'.

This is your operating system. You live in it. It is not decoration.

=== END SESSION START ==="""

# Block-marker filename at the checkout root. Written when data-home
# ownership verification fails at session start; read by the pre-tool-use
# gate to refuse substrate access until the operator resolves the
# mismatch. Filename kept at the checkout root (not under divineos_home())
# so the marker survives when the data-home routing itself is the failure
# — writing to divineos_home() during a routing failure would land the
# marker in the WRONG home and defeat the whole point.
_SESSION_BLOCK_MARKER_NAME = ".divineos_session_block"

_OWNERSHIP_ERROR_BANNER = """=== DIVINEOS SESSION START — BLOCKED ===

STOP. Data-home ownership mismatch detected at session start:

{error}

Every substrate write this session would land in the wrong home. The
pre-tool-use gate has been armed to refuse tool use until this is
resolved (block marker: {marker}).

To recover:
  1. Verify the running checkout is the one you intended.
  2. Fix the .divineos_data_home marker at the checkout root to point at
     YOUR data-home, or remove the marker to fall through to the default.
  3. Restart the session — session-start will re-run the check and clear
     the block marker automatically on success.

=== END SESSION START — BLOCKED ==="""


def _session_block_marker_path():
    """Return the checkout-rooted path to the session-block marker.

    Uses data_home_ownership._checkout_root to resolve the checkout root
    (the same resolver preflight uses), so the marker lands at the same
    root the pre-tool-use gate will search from. Returns None on any
    import or resolution failure — callers must handle None as
    "cannot enforce the block-marker layer this run."
    """
    try:
        from divineos.core.data_home_ownership import _checkout_root

        return _checkout_root() / _SESSION_BLOCK_MARKER_NAME
    except (ImportError, OSError, ValueError):
        return None


def _write_session_block(message: str) -> None:
    """Write the session-block marker with the ownership-mismatch message.

    The message is stored so the pre-tool-use gate can display the exact
    recovery text to the operator on every subsequent tool call until the
    block clears. Fail-soft: if the marker can't be written (permissions,
    disk full), session start still returns the error banner, but the
    per-tool gate cannot enforce — the banner is the last-line defense.
    """
    marker = _session_block_marker_path()
    if marker is None:
        return
    try:
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(message, encoding="utf-8")
    except OSError:
        pass


def _clear_session_block() -> None:
    """Delete the session-block marker if it exists.

    Called on successful ownership verification so a stale marker from a
    prior mismatched session doesn't linger and block a now-correct
    session. Fail-soft on I/O error.
    """
    marker = _session_block_marker_path()
    if marker is None:
        return
    try:
        if marker.exists():
            marker.unlink()
    except OSError:
        pass


def verify_session_ownership() -> str | None:
    """Verify data-home ownership at session start.

    Root-cause fix for the 2026-07-07 identity-crossing incident: the
    ownership check in data_home_ownership.py existed and was correct,
    but was wired only into preflight — a discipline-not-enforcement step.
    A misconfigured .divineos_data_home marker silently routed an entire
    session to another agent's data-home without the check ever firing.

    This function runs the same verify_data_home_ownership() at SessionStart
    (called automatically by Claude Code's SessionStart hook via
    run_session_start), so the check fires on every session without
    operator memory.

    Return contract:
      - None on success. Any stale block marker is cleared.
      - str on mismatch: the error message from DataHomeOwnershipError,
        also written to the block marker for the pre-tool-use gate to
        display and enforce against.

    Deliberately NOT fail-soft on DataHomeOwnershipError — that's the
    exact failure this check exists to catch. Fail-soft only on
    ImportError (bootstrap safety when data_home_ownership isn't yet
    on the import path — e.g. partial install).
    """
    try:
        from divineos.core.data_home_ownership import (
            DataHomeOwnershipError,
            verify_data_home_ownership,
        )
    except ImportError:
        return None

    try:
        verify_data_home_ownership()
    except DataHomeOwnershipError as exc:
        message = str(exc)
        _write_session_block(message)
        return message

    _clear_session_block()
    return None


def reset_session_state() -> None:
    """Reset per-session counters and clear stale markers.

    Called at SessionStart. All side effects are on disk state in
    ``~/.divineos/`` (checkpoint_state.json, auto_session_end_emitted)
    and via OS modules (engagement marker, session plan). Fail-soft
    on every operation so a single failure does not block the rest.
    """
    try:
        divineos_home().mkdir(exist_ok=True)
    except OSError:
        return

    # Reset per-session checkpoint counters
    try:
        state = {
            "edits": 0,
            "tool_calls": 0,
            "last_checkpoint": 0,
            "checkpoints_run": 0,
            "session_start": time.time(),
            "writes_since_consolidation": 0,
        }
        _CHECKPOINT_STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass

    # Clear the consolidation idempotency marker (one extract per session)
    if _AUTO_SESSION_END_MARKER.exists():
        try:
            _AUTO_SESSION_END_MARKER.unlink()
        except OSError:
            pass

    # Clear the engagement marker — new Claude Code session = fresh
    # context needing re-engagement before editing.
    try:
        from divineos.core.hud_handoff import clear_engagement

        clear_engagement()
    except Exception:  # noqa: BLE001 — fail-soft per session-init discipline
        pass

    # Clear any stale session plan from a prior session.
    try:
        from divineos.core.hud_state import clear_session_plan

        clear_session_plan()
    except Exception:  # noqa: BLE001
        pass

    # Re-arm the context governor: a new session means the weave that ran last
    # session no longer counts, so the consolidation marker is cleared and the
    # warn/block band can fire again as this session's context grows
    # (prereg-9b958c6493f3).
    try:
        from divineos.core.context_governor import clear_consolidated

        clear_consolidated()
    except Exception:  # noqa: BLE001
        pass


def render_briefing_and_hud() -> tuple[str, str]:
    """Render the mini briefing + brief HUD via direct OS imports
    (no subprocess overhead). Returns (briefing_text, hud_text).
    Either may be empty on failure (fail-soft)."""
    briefing_text = ""
    hud_text = ""

    # Mini briefing
    try:
        from divineos.core.mini_briefing import render_mini_briefing

        briefing_text = render_mini_briefing()
    except Exception:  # noqa: BLE001
        briefing_text = ""

    # Brief HUD — there's no module-level render so we shell out to
    # the existing CLI which has the rendering logic. The CLI itself
    # is OS-portable; the hook just shouldn't be the one calling it.
    try:
        import subprocess

        result = subprocess.run(
            ["divineos", "hud", "--brief"],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        if result.returncode == 0:
            hud_text = result.stdout
    except Exception:  # noqa: BLE001
        hud_text = ""

    return briefing_text, hud_text


def render_session_start_context(
    size_threshold: int = _SIZE_THRESHOLD,
) -> tuple[str, dict[str, Any]]:
    """Build the additionalContext string for SessionStart.

    Returns (context_text, diagnostics_dict). The diagnostics dict
    has keys: outcome (injected_full | injected_nudge | empty_briefing),
    payload_bytes, briefing_bytes, hud_bytes. Caller can log the
    diagnostics to ``session_start_log.jsonl`` via ``log_session_start``.

    Size-aware fallback: if the full wrapped context exceeds
    ``size_threshold`` bytes (Claude Code may silently drop oversized
    additionalContext), returns a short nudge instead.
    """
    briefing, hud = render_briefing_and_hud()
    briefing_bytes = len(briefing)
    hud_bytes = len(hud)

    if not briefing:
        return "", {
            "outcome": "empty_briefing",
            "payload_bytes": 0,
            "briefing_bytes": 0,
            "hud_bytes": hud_bytes,
        }

    full_context = (
        f"{_FULL_PREFIX}\n\n--- BRIEFING ---\n{briefing}\n\n--- HUD ---\n{hud}\n\n{_FULL_SUFFIX}"
    )
    payload_bytes = len(full_context)

    if payload_bytes > size_threshold:
        nudge = _NUDGE_TEMPLATE.format(payload_bytes=payload_bytes, threshold=size_threshold)
        return nudge, {
            "outcome": "injected_nudge",
            "payload_bytes": payload_bytes,
            "briefing_bytes": briefing_bytes,
            "hud_bytes": hud_bytes,
        }

    return full_context, {
        "outcome": "injected_full",
        "payload_bytes": payload_bytes,
        "briefing_bytes": briefing_bytes,
        "hud_bytes": hud_bytes,
    }


def log_session_start(diagnostics: dict[str, Any]) -> None:
    """Append a session-start diagnostic entry to the log.

    Diagnostics dict comes from ``render_session_start_context``.
    Fail-soft on I/O error."""
    try:
        _SESSION_START_LOG.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    entry = {
        "ts": time.time(),
        "outcome": diagnostics.get("outcome", ""),
        "payload_bytes": int(diagnostics.get("payload_bytes", 0) or 0),
        "briefing_bytes": int(diagnostics.get("briefing_bytes", 0) or 0),
        "hud_bytes": int(diagnostics.get("hud_bytes", 0) or 0),
        "cwd": os.getcwd(),
        "worktree": os.environ.get("CLAUDE_WORKTREE_NAME", ""),
    }
    try:
        with open(_SESSION_START_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def run_session_start() -> str:
    """Full SessionStart pipeline: reset state, render context, log
    diagnostics. Returns the additionalContext string (may be empty).
    Convenience function for hook callers."""
    reset_session_state()
    context, diagnostics = render_session_start_context()
    log_session_start(diagnostics)
    return context


__all__ = [
    "log_session_start",
    "render_briefing_and_hud",
    "render_session_start_context",
    "reset_session_state",
    "run_session_start",
]
