"""Lesson Interrupt — mid-session questions for chronic lessons.

# AGENT_RUNTIME — Not wired into CLI pipeline. Invoked from
# .claude/hooks/lesson-interrupt.sh (PreToolUse) and
# .claude/hooks/session-checkpoint.sh (periodic). Intentionally not
# Python-imported from any CLI module: interrupts surface to the
# agent mid-session via shell hooks, not via CLI commands.

Design principle: a lightweight interrupt that fires mid-session when
a chronic lesson signal is detected — not a gate, not a block, just a
single sentence surfaced to attention. A question instead of a
warning. Questions are harder to dismiss than warnings.

This module checks whether the current tool use matches a chronic
lesson pattern and returns a named question if it does. Some interrupts
carry a named expert voice (e.g., Bengio on blind retry) to make them
harder to dismiss; others stand on their own.

Designed to be FAST — called on every Edit/Write via PostToolUse hook.
Must complete in <100ms. No database queries. File-based state only.
"""

import json
import os
import time
from pathlib import Path
from typing import Any

_INTERRUPT_ERRORS = (OSError, json.JSONDecodeError, KeyError, TypeError)

# Cooldown: don't fire the same interrupt more than once per N seconds
_COOLDOWN_SECONDS = 300  # 5 minutes between same-category interrupts


def _state_path() -> Path:
    """Path to the interrupt state file."""
    divineos_dir = Path(os.path.expanduser("~")) / ".divineos"
    divineos_dir.mkdir(exist_ok=True)
    return divineos_dir / "lesson_interrupt_state.json"


def _load_state() -> dict[str, Any]:
    """Load interrupt state (last fire times per category)."""
    path = _state_path()
    if not path.exists():
        return {"last_fired": {}, "recent_tools": []}
    try:
        result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return result
    except _INTERRUPT_ERRORS:
        return {"last_fired": {}, "recent_tools": []}


def _save_state(state: dict[str, Any]) -> None:
    """Save interrupt state."""
    try:
        _state_path().write_text(json.dumps(state), encoding="utf-8")
    except _INTERRUPT_ERRORS:
        pass


def check_lesson_interrupt(tool_input: dict[str, Any]) -> str:
    """Check if current tool use triggers a chronic lesson interrupt.

    Returns the interrupt question string, or empty string if no interrupt.
    Called on every Edit/Write — must be fast.
    """
    state = _load_state()
    now = time.time()

    # Track recent tools for pattern detection
    file_path = tool_input.get("file_path", "")
    recent = state.get("recent_tools", [])
    recent.append({"file": file_path, "time": now})
    # Keep only last 10
    recent = recent[-10:]
    state["recent_tools"] = recent

    # Check each interrupt pattern
    interrupt = ""
    last_fired = state.get("last_fired", {})

    # Pattern: Edit without Read (read-before-edit lesson)
    # Check if this file was Read in recent tools
    if file_path:
        was_read = any(
            t.get("file") == file_path and t.get("tool") == "Read"
            for t in recent[:-1]  # exclude current
        )
        if not was_read and _can_fire("read_before_edit", last_fired, now):
            interrupt = (
                "Did you read this file before editing it? "
                "You have a chronic lesson about this (8x across 4 sessions). "
                "If you already read it, carry on. If not — read first."
            )
            last_fired["read_before_edit"] = now

    # Pattern: Consecutive EDITS of same file (possible blind retry)
    if len(recent) >= 3:
        # Only count Edit/Write operations, not Read/Bash
        recent_edits = [
            t for t in recent if t.get("tool", "") in ("Edit", "Write", "NotebookEdit", "")
        ]
        if len(recent_edits) >= 3:
            last_three = recent_edits[-3:]
            files = [t.get("file", "") for t in last_three]
            if files[0] == files[1] == files[2] and files[0]:
                if _can_fire("blind_retry", last_fired, now):
                    interrupt = (
                        "Bengio asks: you've edited the same file 3 times in a row. "
                        "Are you investigating or retrying blind? "
                        "Your chronic lesson says: investigate the root cause first."
                    )
                last_fired["blind_retry"] = now

    state["last_fired"] = last_fired
    _save_state(state)

    return interrupt


def _can_fire(category: str, last_fired: dict[str, float], now: float) -> bool:
    """Check cooldown — don't spam the same interrupt."""
    last = last_fired.get(category, 0)
    return (now - last) > _COOLDOWN_SECONDS


def record_tool_for_interrupt(tool_name: str, file_path: str = "") -> None:
    """Record a tool use for pattern detection.

    Called from session-checkpoint hook to track Read/Bash tools
    (not just Edit/Write) so the interrupt can check preconditions.
    """
    state = _load_state()
    now = time.time()
    recent = state.get("recent_tools", [])
    recent.append({"file": file_path, "tool": tool_name, "time": now})
    recent = recent[-10:]
    state["recent_tools"] = recent
    _save_state(state)
