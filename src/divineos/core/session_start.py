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
