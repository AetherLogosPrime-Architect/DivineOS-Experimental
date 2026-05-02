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
import re
import time
from pathlib import Path

# Two-axis detection (claim 986b4750): the correction-detector pattern-matches
# CORRECTION_PATTERNS (surface axis) but pre-relay-stripping conflates "Andrew
# correcting the agent" with "AI text relayed by Andrew that contains
# correction-shaped words about itself." Strip relayed/quoted content first,
# then match — the surface check fires only on first-person Andrew text.
_RELAY_INTRODUCERS: tuple[str, ...] = (
    "here is the reply",
    "here is the response",
    "here is the report",
    "here is the update",
    "here is the review",
    "heres the reply",
    "heres the response",
    "heres the report",
    "heres the update",
    "heres the review",
    "here is what",  # 'here is what claude said', 'here is what they sent', etc.
    "heres what",
    "this is what they said",
    "they replied",
    "their reply was",
    "reply was:",
)
_BLOCKQUOTE_LINE = re.compile(r"^>.*$", re.MULTILINE)
_FENCED_BLOCK = re.compile(r"```[\s\S]*?```")


def strip_relayed(text: str) -> str:
    """Remove markdown blockquotes, fenced code, and relayed-AI tail from text.

    Used by the correction-detector hook so correction-shaped words inside
    relayed AI text don't false-fire as Andrew corrections of the agent.
    """
    if not text:
        return ""
    text = _BLOCKQUOTE_LINE.sub("", text)
    text = _FENCED_BLOCK.sub("", text)
    lower = text.lower()
    earliest = -1
    for marker in _RELAY_INTRODUCERS:
        idx = lower.find(marker)
        if idx >= 0 and (earliest == -1 or idx < earliest):
            earliest = idx
    if earliest >= 0:
        text = text[:earliest]
    return text


def should_mark(prompt: str) -> bool:
    """True if prompt contains a correction directed at the agent.

    Two-axis check: strip relayed content (target axis), then match
    CORRECTION_PATTERNS (surface axis). Returns False on empty or
    relay-only input even if correction-shaped words appear in the
    relayed section.
    """
    if not prompt:
        return False
    try:
        from divineos.analysis.session_analyzer import CORRECTION_PATTERNS
    except ImportError:
        return False
    scan_text = strip_relayed(prompt)
    if not scan_text.strip():
        return False
    return any(re.search(pat, scan_text, re.IGNORECASE) for pat in CORRECTION_PATTERNS)


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

    # Cascade: a correction is virtue-relevant by definition (the user
    # named drift). Set the compass-required marker so the next tool
    # use also requires compass observation. See gate 1.47.
    try:
        from divineos.core.compass_required_marker import (
            set_marker as _cr_set,
        )

        _cr_set("correction", (trigger_text or "")[:120])
    except (ImportError, OSError, AttributeError):
        pass


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
