"""HUD State Management — Goals, health, budget, tasks, and session plans.

Mutable slot files that let the dashboard reflect real-time state changes.
"""

import json
import sqlite3
import time
from typing import Any

from loguru import logger

from divineos.core._hud_io import _ensure_hud_dir
from divineos.core.constants import SECONDS_PER_DAY

_HS_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


# ─── Slot Update Functions ───────────────────────────────────────────


def update_goals(goals: list[dict[str, str]]) -> None:
    """Update the active goals slot.

    Each goal: {"text": "...", "original_words": "...", "status": "active"|"done"}
    """
    path = _ensure_hud_dir() / "active_goals.json"
    path.write_text(json.dumps(goals, indent=2), encoding="utf-8")


def update_session_health(
    corrections: int = 0,
    encouragements: int = 0,
    grade: str = "?",
    notes: str = "",
) -> None:
    """Update session health metrics."""
    path = _ensure_hud_dir() / "session_health.json"
    data = {
        "corrections": corrections,
        "encouragements": encouragements,
        "grade": grade,
        "notes": notes,
        "updated_at": time.time(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_context_budget(used_pct: int) -> None:
    """Update context budget percentage."""
    path = _ensure_hud_dir() / "context_budget.json"
    data = {"used_pct": used_pct, "updated_at": time.time()}
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def update_task_state(
    current: str = "",
    next_task: str = "",
    done: list[str] | None = None,
    blocked: str = "",
) -> None:
    """Update current task state."""
    path = _ensure_hud_dir() / "task_state.json"

    # Merge with existing done list
    existing_done: list[str] = []
    if path.exists():
        try:
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_done = existing.get("done", [])
        except _HS_ERRORS as e:
            logger.warning("Could not read existing session plan done list (starting fresh): %s", e)

    if done:
        existing_done.extend(done)

    data = {
        "current": current,
        "next": next_task,
        "done": existing_done[-10:],  # keep last 10
        "blocked": blocked,
        "updated_at": time.time(),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def add_goal(text: str, original_words: str = "") -> None:
    """Add a single goal to the active goals list."""
    if not text.strip():
        return
    path = _ensure_hud_dir() / "active_goals.json"
    goals: list[dict[str, str]] = []
    if path.exists():
        try:
            goals = json.loads(path.read_text(encoding="utf-8"))
        except _HS_ERRORS as e:
            logger.warning("Could not read active goals file (starting with empty list): %s", e)

    # Deduplicate — don't add if an active goal with the same text exists
    for goal in goals:
        if goal.get("text") == text and goal.get("status") != "done":
            return

    goal_entry: dict[str, Any] = {
        "text": text,
        "original_words": original_words,
        "status": "active",
        "added_at": time.time(),
    }
    goals.append(goal_entry)
    path.write_text(json.dumps(goals, indent=2), encoding="utf-8")


def _increment_lifetime_goals(count: int = 1) -> None:
    """Increment the lifetime goals completed counter."""
    path = _ensure_hud_dir() / "goals_lifetime.json"
    current = 0
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            current = data.get("lifetime_completed", 0)
        except (json.JSONDecodeError, OSError):
            pass
    path.write_text(
        json.dumps({"lifetime_completed": current + count}, indent=2),
        encoding="utf-8",
    )


def get_lifetime_goals_completed() -> int:
    """Read the lifetime goals completed counter."""
    path = _ensure_hud_dir() / "goals_lifetime.json"
    if not path.exists():
        return 0
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return int(data.get("lifetime_completed", 0))
    except (json.JSONDecodeError, OSError):
        return 0


def complete_goal(text: str) -> bool:
    """Mark a goal as done by matching text. Returns True if found."""
    if not text.strip():
        return False
    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        return False

    try:
        goals = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    found = False
    for goal in goals:
        if text.lower() in goal.get("text", "").lower():
            goal["status"] = "done"
            found = True
            break

    if found:
        path.write_text(json.dumps(goals, indent=2), encoding="utf-8")
        _increment_lifetime_goals(1)
    return found


def _record_goal_outcome(goal: dict[str, Any], outcome: str) -> None:
    """Append a goal outcome record to the outcomes log.

    Called by auto_clean_goals when a goal exits the active list via
    timeout or dedup (as opposed to actual completion). Recent
    outcomes feed the action-loop-closure briefing surface — surfacing
    goals that aged out without progression so they're visible at next
    session start (claim 5b38a31c, salvaged from old-OS ACTION LOOP
    CLOSURE spec).
    """
    path = _ensure_hud_dir() / "goal_outcomes.json"
    outcomes: list[dict[str, Any]] = []
    if path.exists():
        try:
            outcomes = json.loads(path.read_text(encoding="utf-8"))
        except _HS_ERRORS:
            outcomes = []
    outcomes.append(
        {
            "text": goal.get("text", ""),
            "original_words": goal.get("original_words", ""),
            "added_at": goal.get("added_at", 0),
            "archived_at": time.time(),
            "outcome": outcome,
        }
    )
    # Cap at 200 entries to prevent unbounded growth — the surface
    # only reads recent entries anyway.
    outcomes = outcomes[-200:]
    path.write_text(json.dumps(outcomes, indent=2), encoding="utf-8")


def auto_clean_goals(max_age_days: float = 1.0) -> dict[str, int]:
    """Auto-clean goals at session end.

    - Completed goals (status='done' from complete_goal) are removed from
      the active list entirely; they were already counted in lifetime
      when complete_goal ran
    - Active goals older than max_age_days are stale-archived (recorded
      to goal_outcomes.json with outcome='stale_archived', NOT counted
      as completed — fixes goodhart-shape where staleness inflated
      completion count)
    - Duplicate/near-duplicate goals are deduplicated; recorded as
      outcome='superseded'
    - Goals that are subsets of newer goals are removed; outcome='superseded'

    Returns counts of actions taken.
    """
    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        return {"stale_archived": 0, "deduped": 0, "completed_cleared": 0}

    try:
        goals = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"stale_archived": 0, "deduped": 0, "completed_cleared": 0}

    # Remove completed goals — they've served their purpose. Already
    # counted in lifetime by complete_goal; do NOT double-count here.
    completed_cleared = sum(1 for g in goals if g.get("status") == "done")
    goals = [g for g in goals if g.get("status") != "done"]

    cutoff = time.time() - (max_age_days * SECONDS_PER_DAY)
    stale_archived = 0
    deduped = 0

    # Archive stale active goals — record outcome before status change
    # so the briefing surface can show what timed out
    for goal in goals:
        if goal.get("status") == "active" and goal.get("added_at", 0) < cutoff:
            _record_goal_outcome(goal, "stale_archived")
            goal["status"] = "done"
            stale_archived += 1

    # Deduplicate: word overlap OR substring containment
    active = [g for g in goals if g.get("status") == "active"]
    to_dedup: set[int] = set()
    for i, g1 in enumerate(active):
        if i in to_dedup:
            continue
        text1 = g1.get("text", "").lower()
        words1 = set(text1.split())
        for j in range(i + 1, len(active)):
            if j in to_dedup:
                continue
            text2 = active[j].get("text", "").lower()
            words2 = set(text2.split())
            if not words1 or not words2:
                continue

            # Word overlap check
            overlap = len(words1 & words2) / max(len(words1 | words2), 1)

            # Substring containment: one goal's core text inside another
            short, long = (text1, text2) if len(text1) < len(text2) else (text2, text1)
            is_subset = len(short) > 10 and short[:40] in long

            if overlap > 0.6 or is_subset:
                older = i if g1.get("added_at", 0) < active[j].get("added_at", 0) else j
                to_dedup.add(older)
                deduped += 1

    for idx in to_dedup:
        _record_goal_outcome(active[idx], "superseded")
        active[idx]["status"] = "done"

    # Stop counting stale-archived + deduped as "completed" — that was
    # the goodhart-shape (auto-archival inflated completion count).
    # complete_goal() is the only path that counts toward lifetime.
    total_cleared = completed_cleared + stale_archived + deduped
    changed = total_cleared > 0
    if changed:
        # Remove any newly-marked-done goals too
        goals = [g for g in goals if g.get("status") != "done"]
        path.write_text(json.dumps(goals, indent=2), encoding="utf-8")

    return {
        "stale_archived": stale_archived,
        "deduped": deduped,
        "completed_cleared": completed_cleared,
    }


def has_session_fresh_goal(max_age_seconds: float = 7200.0) -> bool:
    """Check if any goal was added recently (within max_age_seconds).

    Old goals from previous sessions don't count — the AI must set
    a goal for THIS session's work before it can start editing.
    Default: 2 hours, generous enough for long sessions.
    """
    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        return False
    try:
        goals = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    cutoff = time.time() - max_age_seconds
    for goal in goals:
        added_at = goal.get("added_at", 0)
        if added_at > cutoff and goal.get("status") == "active":
            return True
    return False


# ─── Session Plan ────────────────────────────────────────────────────


def set_session_plan(
    goal: str,
    estimated_files: int = 0,
    estimated_tool_calls: int = 0,
    estimated_time_minutes: int = 0,
) -> None:
    """Store a session plan so the clarity system can compare plan vs actual."""
    if not goal.strip():
        return
    path = _ensure_hud_dir() / "session_plan.json"

    plan = {
        "goal": goal,
        "estimated_files": estimated_files,
        "estimated_tool_calls": estimated_tool_calls,
        "estimated_time_minutes": estimated_time_minutes,
        "created_at": time.time(),
    }
    path.write_text(json.dumps(plan, indent=2), encoding="utf-8")


def get_session_plan() -> dict[str, Any] | None:
    """Load the current session plan, if any."""
    path = _ensure_hud_dir() / "session_plan.json"
    if not path.exists():
        return None
    try:
        result: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return result
    except (json.JSONDecodeError, OSError):
        return None


def clear_session_plan() -> None:
    """Clear the session plan (called at session end)."""
    path = _ensure_hud_dir() / "session_plan.json"
    if path.exists():
        path.unlink()
