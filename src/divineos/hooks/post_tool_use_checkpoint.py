"""Consolidated PostToolUse checkpoint — single Python invocation for all tracking.

# AGENT_RUNTIME — Not wired into CLI pipeline. Invoked from
# .claude/hooks/session-checkpoint.sh as
# ``python -m divineos.hooks.post_tool_use_checkpoint``. This module
# collapses the 8+ separate Python invocations the old
# session-checkpoint.sh was making into a single interpreter run.

## Why this exists

The previous session-checkpoint.sh made many sequential Python calls:
reading state, writing state, recording tool use, recording code
actions, saving updated state, checking self-awareness practice,
context monitoring. On Windows each spawn costs ~200ms of startup
plus DivineOS import. Total was ~600ms per PostToolUse firing, and
this hook fires on every Edit / Write / Bash.

This module does all the same work in one interpreter invocation.
Expected improvement: ~4x faster (600ms → ~150ms) which compounds
across every tool call.

## What it does (same as old shell, consolidated)

1. Read hook input (tool_name, tool_input)
2. Load checkpoint state from ``~/.divineos/checkpoint_state.json``
3. Increment tool_calls counter; increment edits if Edit/Write
4. Record tool use for lesson-interrupt pattern detection
5. Record code action for periodic engagement gate (Edit/Write only)
6. Save updated state
7. If edits crossed a 15-multiple threshold, run ``divineos checkpoint``
8. Emit context-monitor warnings at 100 / 150 tool-call thresholds
9. Emit self-awareness practice nudge if tool_calls >= 100
10. Output ``additionalContext`` JSON for Claude Code if any warnings

All ten operations in one Python process. Fail-open design — if any
individual step errors, the hook keeps running; the OS never gets
bricked by the hook.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any


_CHECKPOINT_EDIT_INTERVAL = 15
_CONTEXT_WARNING_THRESHOLD = 100
_AUTO_SESSION_END_THRESHOLD = 150


def _state_path() -> Path:
    """Path to the checkpoint state JSON. Uses expanduser for Windows."""
    divineos_dir = Path(os.path.expanduser("~")) / ".divineos"
    divineos_dir.mkdir(exist_ok=True)
    return divineos_dir / "checkpoint_state.json"


def _auto_emitted_path() -> Path:
    """Path to the auto-emit marker file."""
    divineos_dir = Path(os.path.expanduser("~")) / ".divineos"
    return divineos_dir / "auto_session_end_emitted"


def _load_state() -> dict[str, Any]:
    """Load checkpoint state, creating defaults if missing."""
    path = _state_path()
    if not path.exists():
        return {"edits": 0, "tool_calls": 0, "last_checkpoint": 0, "checkpoints_run": 0}
    try:
        data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (OSError, json.JSONDecodeError):
        return {"edits": 0, "tool_calls": 0, "last_checkpoint": 0, "checkpoints_run": 0}


def _save_state(state: dict[str, Any]) -> None:
    """Write checkpoint state. Silent on error."""
    try:
        _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass


def _record_tool_for_interrupt(tool_name: str, file_path: str) -> None:
    """Record tool use for lesson-interrupt pattern detection."""
    try:
        from divineos.core.lesson_interrupt import record_tool_for_interrupt

        record_tool_for_interrupt(tool_name, file_path)
    except (ImportError, OSError, AttributeError):
        pass


def _record_code_action() -> None:
    """Record a code action for the periodic engagement gate."""
    try:
        from divineos.core.hud_handoff import record_code_action

        record_code_action()
    except (ImportError, OSError, AttributeError):
        pass


def _check_self_awareness_practice(tool_calls: int) -> str:
    """Check whether a self-awareness practice nudge should fire."""
    if tool_calls < _CONTEXT_WARNING_THRESHOLD:
        return ""
    try:
        from divineos.core.session_checkpoint import check_self_awareness_practice

        result = check_self_awareness_practice(tool_calls)
        return result or ""
    except (ImportError, OSError, AttributeError):
        return ""


def _run_checkpoint() -> None:
    """Run the ``divineos checkpoint`` CLI silently."""
    try:
        subprocess.run(
            ["divineos", "checkpoint"],
            capture_output=True,
            check=False,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def _auto_emit_session_end() -> None:
    """Auto-emit SESSION_END once; mark a file so we don't repeat."""
    marker = _auto_emitted_path()
    if marker.exists():
        return
    try:
        subprocess.run(
            ["divineos", "emit", "SESSION_END"],
            capture_output=True,
            check=False,
            timeout=60,
        )
        marker.write_text("1", encoding="utf-8")
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    """Entry point. Reads hook input, runs all checkpoint operations, emits
    optional additionalContext for Claude Code."""
    try:
        raw = sys.stdin.read()
        input_data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        input_data = {}

    tool_name = ""
    tool_input: dict[str, Any] = {}
    try:
        tool_name = input_data.get("tool_name", "") or ""
        tool_input = input_data.get("tool_input", {}) or {}
    except (AttributeError, TypeError):
        pass

    file_path = ""
    try:
        file_path = tool_input.get("file_path", tool_input.get("command", "")) or ""
    except (AttributeError, TypeError):
        pass

    state = _load_state()
    state["tool_calls"] = int(state.get("tool_calls", 0)) + 1
    if tool_name in ("Edit", "Write"):
        state["edits"] = int(state.get("edits", 0)) + 1

    # Track tool use for lesson-interrupt pattern detection
    if tool_name in ("Read", "Edit", "Write", "Bash"):
        _record_tool_for_interrupt(tool_name, file_path)

    # Code action → engagement gate tracking (writes only)
    if tool_name in ("Edit", "Write", "NotebookEdit"):
        _record_code_action()

    tool_calls = state["tool_calls"]
    edits = state["edits"]
    checkpoints_run = int(state.get("checkpoints_run", 0))

    # Check if periodic checkpoint needed (every 15 edits)
    edits_since = edits - (checkpoints_run * _CHECKPOINT_EDIT_INTERVAL)
    if edits_since >= _CHECKPOINT_EDIT_INTERVAL:
        _run_checkpoint()
        state["checkpoints_run"] = checkpoints_run + 1
        state["last_checkpoint"] = time.time()

    _save_state(state)

    # Build any warnings / nudges
    messages: list[str] = []

    practice = _check_self_awareness_practice(tool_calls)
    if practice:
        messages.append(practice)

    if tool_calls >= _AUTO_SESSION_END_THRESHOLD:
        _auto_emit_session_end()
        messages.append(
            f"SESSION_END auto-emitted at {tool_calls} tool calls. "
            "Knowledge saved. Continue working — compaction may happen soon."
        )
    elif tool_calls >= _CONTEXT_WARNING_THRESHOLD:
        messages.append(
            f"Context monitor: {tool_calls} tool calls, {edits} edits. "
            f"SESSION_END will auto-emit at {_AUTO_SESSION_END_THRESHOLD} "
            "to save knowledge."
        )

    if messages:
        payload = {"additionalContext": " | ".join(messages)}
        json.dump(payload, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
