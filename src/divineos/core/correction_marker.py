"""Correction-unlogged marker — structural enforcement of `divineos learn` usage.

When a user message contains correction-shaped language (detected by the
UserPromptSubmit hook against CORRECTION_PATTERNS from session_analyzer),
a marker file is written at ~/.divineos/correction_unlogged.json. The
PreToolUse gate checks this marker and blocks non-bypass tools until the
correction is logged via `divineos learn` or `divineos correction`.

This closes the enforcement gap named in ChatGPT audit claim-964493
(theater-learning bypass) by making "log the correction" mechanically
required rather than an intent-based promise.

Design:
  - Marker is a JSON file. Contains timestamp and the first ~200 chars of
    the user message that triggered detection.
  - When the marker is present AND the PreToolUse gate fires AND the tool
    is not a bypass command (learn, correction, briefing, etc.), gate
    denies with instructions to run `divineos learn "..."`.
  - `divineos learn` and `divineos correction` clear the marker.
  - Fail-open: if marker read fails, gate does not block (consistent
    with other gate machinery in pre_tool_use_gate).
"""

from __future__ import annotations

import json
import time
from pathlib import Path


def marker_path() -> Path:
    """Absolute path to the correction-unlogged marker."""
    return Path.home() / ".divineos" / "correction_unlogged.json"


def set_marker(trigger_text: str) -> None:
    """Write the marker. Called by the UserPromptSubmit hook on detection.

    ``trigger_text`` is the user message (first ~200 chars) that tripped
    the correction pattern. Stored so the agent sees what correction was
    detected when the gate fires, not just that one was.
    """
    path = marker_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {"ts": time.time(), "trigger": (trigger_text or "")[:200]}
        path.write_text(json.dumps(payload), encoding="utf-8")
    except OSError:
        pass  # fail open — don't crash the hook on disk issues


def read_marker() -> dict | None:
    """Return the marker payload, or None if absent/unreadable."""
    path = marker_path()
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def clear_marker() -> None:
    """Remove the marker. Called by `divineos learn` and `divineos correction`."""
    path = marker_path()
    if path.exists():
        try:
            path.unlink()
        except OSError:
            pass


def format_gate_message(marker: dict) -> str:
    """Return the deny-reason string for the PreToolUse gate."""
    trigger = marker.get("trigger", "")
    ts = marker.get("ts")
    age_str = ""
    if ts:
        age_sec = time.time() - ts
        if age_sec < 60:
            age_str = f" ({int(age_sec)}s ago)"
        elif age_sec < 3600:
            age_str = f" ({int(age_sec // 60)}m ago)"
        else:
            age_str = f" ({age_sec / 3600:.1f}h ago)"
    preview = trigger[:120].replace("\n", " ")
    return (
        f"BLOCKED: User correction detected{age_str}, not logged. "
        f'Trigger: "{preview}". '
        f'Run: divineos learn "..." (or divineos correction "...") to clear.'
    )
