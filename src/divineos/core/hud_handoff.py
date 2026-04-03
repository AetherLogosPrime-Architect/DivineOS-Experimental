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
import sqlite3

from loguru import logger

from divineos.core._hud_io import _ensure_hud_dir, _get_hud_dir
from divineos.core.hud_state import has_session_fresh_goal
from divineos.core.ledger import count_events

_HH_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


# ─── Session Handoff Notes ───────────────────────────────────────────


def save_handoff_note(
    summary: str,
    open_threads: list[str] | None = None,
    mood: str = "",
    goals_state: str = "",
    session_id: str = "",
    intent: str = "",
    blockers: list[str] | None = None,
    next_steps: list[str] | None = None,
    context_snapshot: dict[str, Any] | None = None,
) -> Path:
    """Write a handoff note for the next session to pick up.

    New structured fields for richer continuation:
    - intent: what the user was trying to accomplish
    - blockers: what stopped progress
    - next_steps: concrete actions for the next session
    - context_snapshot: key facts (knowledge IDs, recent decisions, grade)
    """
    path = _ensure_hud_dir() / "handoff_note.json"
    note: dict[str, Any] = {
        "session_id": session_id,
        "written_at": time.time(),
        "summary": summary,
        "open_threads": open_threads or [],
        "mood": mood,
        "goals_state": goals_state,
    }
    if intent:
        note["intent"] = intent
    if blockers:
        note["blockers"] = blockers
    if next_steps:
        note["next_steps"] = next_steps
    if context_snapshot:
        note["context_snapshot"] = context_snapshot
    path.write_text(json.dumps(note, indent=2), encoding="utf-8")
    logger.debug("Handoff note saved to %s", path)
    return path


_HANDOFF_EXPIRY_SECONDS = 43200  # 12 hours — older handoffs are from a different context


def load_handoff_note() -> dict[str, Any] | None:
    """Load the handoff note from the previous session, if any.

    Returns None and auto-clears if the note is older than 48 hours.
    """
    path = _get_hud_dir() / "handoff_note.json"
    if not path.exists():
        return None
    try:
        result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        # Auto-expire stale handoff notes
        written_at = result.get("written_at", 0)
        if written_at and (time.time() - written_at) > _HANDOFF_EXPIRY_SECONDS:
            logger.debug("Handoff note expired (>48h old), clearing")
            path.unlink(missing_ok=True)
            return None
        return result
    except (json.JSONDecodeError, OSError):
        return None


def clear_handoff_note() -> None:
    """Clear the handoff note (called after briefing consumes it)."""
    path = _get_hud_dir() / "handoff_note.json"
    if path.exists():
        path.unlink()


# ─── Session Engagement Gate ─────────────────────────────────────────

# After this many code-changing actions (Edit, Write, Bash) without
# consulting the OS (ask, recall, decide, feel, context, directives),
# the engagement gate blocks until the AI re-engages.
# Was 8 — too tight for mechanical repetitive work (same edit across
# 9 files).  15 gives room for a batch of related changes before
# requiring a thinking pause, while still catching runaway coding.
_ENGAGEMENT_DECAY_THRESHOLD = 15


def mark_engaged() -> None:
    """Mark that the OS was used for thinking this session.

    Called when a thinking tool (ask, recall, directives, context, briefing,
    decide, feel) is used. Resets the code-action counter so the engagement
    gate reopens. This means engagement is PERIODIC — you must keep
    consulting the OS throughout your work, not just once at the start.
    """
    path = _ensure_hud_dir() / ".session_engaged"
    marker = {
        "engaged_at": time.time(),
        "code_actions_since": 0,
    }
    path.write_text(json.dumps(marker), encoding="utf-8")


def record_code_action() -> None:
    """Record that a code-changing action (Edit/Write/Bash) occurred.

    Increments the counter that tracks how many code actions have happened
    since the last OS query. When this counter exceeds _ENGAGEMENT_DECAY_THRESHOLD,
    is_engaged() returns False and the PreToolUse gate blocks until the AI
    consults the OS again.
    """
    path = _ensure_hud_dir() / ".session_engaged"
    if not path.exists():
        return
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            # Old format — upgrade to new format
            marker = {"engaged_at": float(marker), "code_actions_since": 0}
        marker["code_actions_since"] = marker.get("code_actions_since", 0) + 1
        path.write_text(json.dumps(marker), encoding="utf-8")
    except (json.JSONDecodeError, OSError):
        pass


def is_engaged() -> bool:
    """Check if the OS has been engaged recently enough.

    Returns False if:
    - No engagement marker exists (never engaged)
    - More than _ENGAGEMENT_DECAY_THRESHOLD code-changing actions have
      happened since the last OS query (engagement has decayed)
    """
    path = _get_hud_dir() / ".session_engaged"
    if not path.exists():
        return False
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            # Old format (plain timestamp) — treat as engaged, will be
            # overwritten on next mark_engaged() call
            return True
        code_actions = marker.get("code_actions_since", 0)
        return bool(code_actions < _ENGAGEMENT_DECAY_THRESHOLD)
    except (json.JSONDecodeError, OSError):
        return path.exists()


def engagement_status() -> dict[str, Any]:
    """Return detailed engagement status for HUD display."""
    path = _get_hud_dir() / ".session_engaged"
    if not path.exists():
        return {
            "engaged": False,
            "code_actions_since": 0,
            "threshold": _ENGAGEMENT_DECAY_THRESHOLD,
            "remaining": 0,
        }
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(marker, dict):
            # Old format (plain timestamp) — treat as fully engaged
            return {
                "engaged": True,
                "code_actions_since": 0,
                "threshold": _ENGAGEMENT_DECAY_THRESHOLD,
                "remaining": _ENGAGEMENT_DECAY_THRESHOLD,
            }
        code_actions = marker.get("code_actions_since", 0)
        remaining = max(0, _ENGAGEMENT_DECAY_THRESHOLD - code_actions)
        return {
            "engaged": code_actions < _ENGAGEMENT_DECAY_THRESHOLD,
            "code_actions_since": code_actions,
            "threshold": _ENGAGEMENT_DECAY_THRESHOLD,
            "remaining": remaining,
        }
    except (json.JSONDecodeError, OSError):
        return {
            "engaged": True,
            "code_actions_since": 0,
            "threshold": _ENGAGEMENT_DECAY_THRESHOLD,
            "remaining": _ENGAGEMENT_DECAY_THRESHOLD,
        }


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
# Was 150 — too low for productive sessions (a single audit fix pass can be
# 200+ tool calls).  400 means roughly "one full context window of work."
_BRIEFING_STALENESS_THRESHOLD = 400

# Time-based TTL: briefing stays valid for 4 hours regardless of tool calls.
# Was 2 hours — but productive sessions can easily run 3+ hours.
_BRIEFING_TTL_SECONDS = 14400


def was_briefing_loaded() -> bool:
    """Check if the briefing was loaded AND is still fresh.

    Returns False if:
    - Briefing was never loaded
    - More than 2 hours have passed since loading (time-based TTL)
    - More than 150 tool calls have happened since loading (activity drift)

    The time check prevents false blocks after context compaction,
    which resets the tool call counter but doesn't invalidate the briefing.
    """
    path = _get_hud_dir() / ".briefing_loaded"
    if not path.exists():
        return False
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        loaded_at = marker.get("loaded_at", 0)

        # Time-based check: valid if loaded within TTL window
        age = time.time() - loaded_at
        if age > _BRIEFING_TTL_SECONDS:
            return False

        # Activity-based check: valid if under tool call threshold
        calls_at_load = marker.get("tool_calls_at_load", 0)
        calls_now = _count_session_tool_calls()
        # After compaction, calls_now may be less than calls_at_load.
        # In that case, trust the time-based check (already passed above).
        if calls_now < calls_at_load:
            return True
        return bool((calls_now - calls_at_load) < _BRIEFING_STALENESS_THRESHOLD)
    except (json.JSONDecodeError, OSError):
        return path.exists()


def briefing_staleness() -> dict[str, Any]:
    """Return how stale the briefing context is.

    Returns dict with 'loaded', 'stale', 'calls_since', 'threshold',
    'age_seconds', 'ttl_seconds', 'ttl_expired'.
    """
    base: dict[str, Any] = {
        "loaded": False,
        "stale": True,
        "calls_since": 0,
        "threshold": _BRIEFING_STALENESS_THRESHOLD,
        "age_seconds": 0,
        "ttl_seconds": _BRIEFING_TTL_SECONDS,
        "ttl_expired": False,
    }
    path = _get_hud_dir() / ".briefing_loaded"
    if not path.exists():
        return base
    try:
        marker = json.loads(path.read_text(encoding="utf-8"))
        loaded_at = marker.get("loaded_at", 0)
        age = time.time() - loaded_at
        ttl_expired = age > _BRIEFING_TTL_SECONDS

        calls_at_load = marker.get("tool_calls_at_load", 0)
        calls_now = _count_session_tool_calls()
        delta = max(0, calls_now - calls_at_load)
        activity_stale = delta >= _BRIEFING_STALENESS_THRESHOLD

        return {
            "loaded": True,
            "stale": ttl_expired or activity_stale,
            "calls_since": delta,
            "threshold": _BRIEFING_STALENESS_THRESHOLD,
            "age_seconds": int(age),
            "ttl_seconds": _BRIEFING_TTL_SECONDS,
            "ttl_expired": ttl_expired,
        }
    except (json.JSONDecodeError, OSError):
        base["loaded"] = True
        base["stale"] = False
        return base


def clear_briefing_marker() -> None:
    """Clear the briefing marker (called at session end)."""
    path = _get_hud_dir() / ".briefing_loaded"
    if path.exists():
        path.unlink()


def _count_session_tool_calls() -> int:
    """Count tool calls in the current session from the ledger."""
    try:
        counts = count_events()
        return int(counts.get("by_type", {}).get("TOOL_CALL", 0))
    except _HH_ERRORS:
        return 0


# ─── Preflight Check ────────────────────────────────────────────────


def preflight_check() -> dict[str, Any]:
    """Check session readiness before work begins.

    Returns a dict with:
        ready: bool — True if all gates pass
        briefing_loaded: bool
        engaged: bool
        has_handoff: bool — previous session left a handoff note
        checks: list of {name, passed, detail}
    """
    checks: list[dict[str, Any]] = []

    # 1. Briefing loaded?
    briefing_ok = was_briefing_loaded()
    checks.append(
        {
            "name": "briefing",
            "passed": briefing_ok,
            "detail": "Briefing loaded and fresh"
            if briefing_ok
            else "Briefing not loaded — run: divineos briefing",
        }
    )

    # 2. Engaged with thinking tools? (periodic — decays after code actions)
    eng_status = engagement_status()
    engaged = eng_status["engaged"]
    if engaged:
        remaining = eng_status["remaining"]
        eng_detail = f"OS engaged ({remaining} code actions before next check-in needed)"
    else:
        actions = eng_status["code_actions_since"]
        eng_detail = (
            f"Engagement expired — {actions} code actions without OS consultation. "
            "Run: divineos ask <topic> or divineos recall"
        )
    checks.append(
        {
            "name": "engagement",
            "passed": engaged,
            "detail": eng_detail,
        }
    )

    # 3. Handoff note from previous session?
    handoff = load_handoff_note()
    has_handoff = handoff is not None and bool(handoff.get("summary"))
    checks.append(
        {
            "name": "handoff",
            "passed": has_handoff,
            "detail": "Handoff note available from last session"
            if has_handoff
            else "No handoff note found (first session or cleared)",
        }
    )

    # 4. Active goals set?
    try:
        goals_path = _ensure_hud_dir() / "active_goals.json"
        if goals_path.exists():
            goals = json.loads(goals_path.read_text(encoding="utf-8"))
            active_goals = [g for g in goals if g.get("status") != "done"]
        else:
            active_goals = []
    except (json.JSONDecodeError, OSError):
        active_goals = []

    has_goals = len(active_goals) > 0
    checks.append(
        {
            "name": "goals",
            "passed": has_goals,
            "detail": f"{len(active_goals)} active goal(s)"
            if has_goals
            else 'No active goals — consider: divineos goal "..."',
        }
    )

    # 5. Session-fresh goal? (not just old goals from prior sessions)
    try:
        fresh_goal = has_session_fresh_goal()
    except (sqlite3.OperationalError, OSError, KeyError, TypeError) as exc:
        logger.debug(f"Session fresh goal check failed, defaulting to True: {exc}")
        fresh_goal = True  # don't block if function unavailable
    checks.append(
        {
            "name": "session_goal",
            "passed": fresh_goal,
            "detail": "Goal set for this session"
            if fresh_goal
            else 'No goal for THIS session — run: divineos goal add "..."',
        }
    )

    # Ready = briefing loaded (the hard requirement)
    ready = briefing_ok
    return {
        "ready": ready,
        "briefing_loaded": briefing_ok,
        "engaged": engaged,
        "has_handoff": has_handoff,
        "checks": checks,
    }


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
