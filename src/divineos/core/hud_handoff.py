"""HUD Session Lifecycle — Handoff notes, engagement gate, goal extraction.

Manages the between-session handoff system, the engagement gate that
ensures the OS is used for thinking before recording, and extraction
of goals from user messages.
"""

import json
import re
import time
from pathlib import Path
from typing import Any

from loguru import logger

from divineos.core.hud import _ensure_hud_dir, _get_hud_dir


# ─── Session Handoff Notes ───────────────────────────────────────────


def save_handoff_note(
    summary: str,
    open_threads: list[str] | None = None,
    mood: str = "",
    goals_state: str = "",
    session_id: str = "",
) -> Path:
    """Write a handoff note for the next session to pick up."""
    path = _ensure_hud_dir() / "handoff_note.json"
    note = {
        "session_id": session_id,
        "written_at": time.time(),
        "summary": summary,
        "open_threads": open_threads or [],
        "mood": mood,
        "goals_state": goals_state,
    }
    path.write_text(json.dumps(note, indent=2), encoding="utf-8")
    logger.debug("Handoff note saved to %s", path)
    return path


def load_handoff_note() -> dict[str, Any] | None:
    """Load the handoff note from the previous session, if any."""
    path = _get_hud_dir() / "handoff_note.json"
    if not path.exists():
        return None
    try:
        result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return result
    except Exception:
        return None


def clear_handoff_note() -> None:
    """Clear the handoff note (called after briefing consumes it)."""
    path = _get_hud_dir() / "handoff_note.json"
    if path.exists():
        path.unlink()


# ─── Session Engagement Gate ─────────────────────────────────────────


def mark_engaged() -> None:
    """Mark that the OS was used for thinking this session.

    Called when a thinking tool (ask, recall, directives, context, briefing)
    is used. The pre-tool hook checks for this marker before allowing writes.
    """
    path = _ensure_hud_dir() / ".session_engaged"
    path.write_text(str(time.time()), encoding="utf-8")


def is_engaged() -> bool:
    """Check if the OS has been engaged this session."""
    path = _get_hud_dir() / ".session_engaged"
    return path.exists()


def clear_engagement() -> None:
    """Clear the engagement marker (called at session end)."""
    path = _get_hud_dir() / ".session_engaged"
    if path.exists():
        path.unlink()


def mark_briefing_loaded() -> None:
    """Mark that the briefing was loaded, with timestamp and activity counter.

    Separate from general engagement — the briefing is the specific gate.
    Without it, the session grade takes a structural penalty.
    The marker expires after too much activity (context drift).
    """
    hud_dir = _ensure_hud_dir()
    marker = {
        "loaded_at": time.time(),
        "tool_calls_at_load": _count_session_tool_calls(),
    }
    (hud_dir / ".briefing_loaded").write_text(json.dumps(marker), encoding="utf-8")


# After this many tool calls since last briefing load, the context is stale.
_BRIEFING_STALENESS_THRESHOLD = 150


def was_briefing_loaded() -> bool:
    """Check if the briefing was loaded AND is still fresh.

    Returns False if:
    - Briefing was never loaded
    - More than 150 tool calls have happened since it was loaded
      (context has drifted too far — the briefing content is fuzzy)
    """
    path = _get_hud_dir() / ".briefing_loaded"
    if not path.exists():
        return False
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        calls_at_load = marker.get("tool_calls_at_load", 0)
        calls_now = _count_session_tool_calls()
        return bool((calls_now - calls_at_load) < _BRIEFING_STALENESS_THRESHOLD)
    except Exception:
        return path.exists()


def briefing_staleness() -> dict[str, Any]:
    """Return how stale the briefing context is.

    Returns dict with 'loaded', 'stale', 'calls_since', 'threshold'.
    """
    path = _get_hud_dir() / ".briefing_loaded"
    if not path.exists():
        return {
            "loaded": False,
            "stale": True,
            "calls_since": 0,
            "threshold": _BRIEFING_STALENESS_THRESHOLD,
        }
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        calls_at_load = marker.get("tool_calls_at_load", 0)
        calls_now = _count_session_tool_calls()
        delta = calls_now - calls_at_load
        return {
            "loaded": True,
            "stale": delta >= _BRIEFING_STALENESS_THRESHOLD,
            "calls_since": delta,
            "threshold": _BRIEFING_STALENESS_THRESHOLD,
        }
    except Exception:
        return {
            "loaded": True,
            "stale": False,
            "calls_since": 0,
            "threshold": _BRIEFING_STALENESS_THRESHOLD,
        }


def clear_briefing_marker() -> None:
    """Clear the briefing marker (called at session end)."""
    path = _get_hud_dir() / ".briefing_loaded"
    if path.exists():
        path.unlink()


def _count_session_tool_calls() -> int:
    """Count tool calls in the current session from the ledger."""
    try:
        from divineos.core.ledger import count_events

        counts = count_events()
        return int(counts.get("by_type", {}).get("TOOL_CALL", 0))
    except Exception:
        return 0


# ─── Goal Extraction ─────────────────────────────────────────────────

# Patterns that signal a user is asking for something to be done.
# Kept simple — false negatives are fine, false positives waste attention.
_GOAL_PATTERNS = [
    r"(?i)^(?:can you|could you|please|i want you to|i need you to|go ahead and)\s+(.+)",
    r"(?i)^(?:let'?s|lets)\s+(.+)",
    r"(?i)^(?:yes,?\s+)?(?:wire|build|add|create|fix|implement|write|make|set up|tackle)\s+(.+)",
]

_GOAL_REGEXES = [re.compile(p) for p in _GOAL_PATTERNS]


def extract_goals_from_messages(messages: list[str], max_goals: int = 5) -> list[dict[str, str]]:
    """Extract goal-like statements from user messages.

    Looks for imperative/request patterns. Returns a list of
    {"text": "...", "original_words": "..."} dicts.
    """
    goals: list[dict[str, str]] = []

    for msg in messages:
        # Skip very short messages (affirmations, greetings)
        if len(msg.split()) < 4:
            continue
        # Skip very long messages (explanations, not requests)
        if len(msg.split()) > 50:
            continue

        for regex in _GOAL_REGEXES:
            match = regex.match(msg.strip())
            if match:
                goal_text = match.group(1).strip().rstrip(".!,")
                if not goal_text:
                    continue
                # Filter out conversational noise that matches goal patterns
                # but isn't a real project goal
                gt_lower = goal_text.lower()
                if _is_conversational_goal(gt_lower):
                    continue
                goal_text = goal_text[0].upper() + goal_text[1:]
                goals.append(
                    {
                        "text": goal_text,
                        "original_words": msg.strip()[:200],
                    }
                )
                break

        if len(goals) >= max_goals:
            break

    return goals


def _is_conversational_goal(text: str) -> bool:
    """Check if a goal-like statement is actually just conversation."""
    # Pure action phrases without substance
    noise_starters = (
        "do it",
        "do this",
        "do that",
        "do both",
        "go",
        "keep going",
        "keep looking",
        "proceed",
        "continue",
        "start",
        "try it",
        "try that",
        "see",
        "check",
        "work on",
    )
    for starter in noise_starters:
        if text.startswith(starter) and len(text.split()) < 8:
            return True

    # Generic meta-instructions — these direct how to work, not what to build
    meta = (
        "make a plan",
        "make sure",
        "do this correctly",
        "commit and push",
        "merge and",
        "push and",
        "fix the root cause",
        "fix the issues",
        "fix it",
    )
    for m in meta:
        if text.startswith(m):
            return True

    # Emoticon-heavy or very short — chat, not goals
    stripped = text.replace(":)", "").replace(":D", "").replace("lol", "").strip()
    if len(stripped.split()) < 3:
        return True

    return False
