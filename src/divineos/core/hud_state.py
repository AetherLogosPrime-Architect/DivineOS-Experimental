"""HUD State Management — Goals, health, budget, tasks, and session plans.

Mutable slot files that let the dashboard reflect real-time state changes.
"""

import json
import time
from typing import Any

from loguru import logger

from divineos.core.hud import _ensure_hud_dir


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
        except Exception as e:
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
        except Exception as e:
            logger.warning("Could not read active goals file (starting with empty list): %s", e)

    # Deduplicate — don't add if an active goal with the same text exists
    for goal in goals:
        if goal.get("text") == text and goal.get("status") != "done":
            return

    goals.append(
        {
            "text": text,
            "original_words": original_words,
            "status": "active",
        }
    )
    path.write_text(json.dumps(goals, indent=2), encoding="utf-8")


def complete_goal(text: str) -> bool:
    """Mark a goal as done by matching text. Returns True if found."""
    if not text.strip():
        return False
    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        return False

    try:
        goals = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return False

    found = False
    for goal in goals:
        if text.lower() in goal.get("text", "").lower():
            goal["status"] = "done"
            found = True
            break

    if found:
        path.write_text(json.dumps(goals, indent=2), encoding="utf-8")
    return found


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
    except Exception:
        return None


def clear_session_plan() -> None:
    """Clear the session plan (called at session end)."""
    path = _ensure_hud_dir() / "session_plan.json"
    if path.exists():
        path.unlink()
