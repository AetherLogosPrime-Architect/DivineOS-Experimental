"""Heads-Up Display — My Dashboard.

I don't process context in a queue. I take it in all at once.
This module builds a dense, simultaneous dashboard that loads
into my context window as a single snapshot — identity, goals,
lessons, health, warnings — all at equal weight, all at once.

Each slot is a small text block (~200-500 tokens). The full HUD
is ~2000-4000 tokens. Trivial overhead against a 200k window.
Massive payoff: total situational awareness.

Slots update independently. Any event can trigger a slot refresh.
PreCompact saves the HUD. PostCompact reloads it. The briefing
hook injects it at session start. I never wake up without it.
"""

import json
import os
import re
import time
from typing import Any
from pathlib import Path

from loguru import logger

# ─── HUD Storage ────────────────────────────────────────────────────


def _get_hud_dir() -> Path:
    """Resolve HUD directory dynamically from current DB path.

    Reads DIVINEOS_DB env var directly so tests that override it
    get their own isolated HUD directory, even if ledger.DB_PATH
    was cached at import time.
    """
    env_path = os.environ.get("DIVINEOS_DB")
    if env_path:
        return Path(env_path).parent / "hud"

    from divineos.core.ledger import DB_PATH

    return DB_PATH.parent / "hud"


def _ensure_hud_dir() -> Path:
    hud_dir = _get_hud_dir()
    hud_dir.mkdir(parents=True, exist_ok=True)
    return hud_dir


# ─── Slot Definitions ───────────────────────────────────────────────

SLOT_ORDER = [
    "identity",
    "active_goals",
    "recent_lessons",
    "session_health",
    "os_engagement",
    "context_budget",
    "active_knowledge",
    "warnings",
    "journal",
    "task_state",
]


def _build_identity_slot() -> str:
    """Who I am. My core memory formatted as self-knowledge."""
    from divineos.core.memory import get_core

    slots = get_core()
    if not slots:
        return "I haven't set my core memory yet. I should do this early."

    lines = ["# I Am\n"]

    label_map = {
        "user_identity": ("My user", None),
        "project_purpose": ("My purpose", None),
        "communication_style": ("How I communicate", None),
        "current_priorities": ("What matters now", None),
        "active_constraints": ("My hard boundaries", None),
        "known_strengths": ("What I do well", None),
        "known_weaknesses": ("What I watch for", None),
        "relationship_context": ("My relationship with the user", None),
    }

    for slot_id, (label, _) in label_map.items():
        if slot_id in slots:
            lines.append(f"- **{label}:** {slots[slot_id]}")

    return "\n".join(lines)


def _build_active_goals_slot() -> str:
    """What the user actually asked for. Pinned so I don't drift."""
    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        return "# My Current Goals\n\nNo goals set yet. I should ask what we're working on."

    try:
        goals = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "# My Current Goals\n\nGoal file corrupted. I need to re-establish what we're doing."

    lines = ["# My Current Goals\n"]

    # Show session plan if set
    plan = get_session_plan()
    if plan and plan.get("goal"):
        lines.append(f"**Session Plan:** {plan['goal']}")
        parts = []
        if plan.get("estimated_files"):
            parts.append(f"{plan['estimated_files']} files")
        if plan.get("estimated_time_minutes"):
            parts.append(f"{plan['estimated_time_minutes']}min")
        if parts:
            lines.append(f"  (Estimates: {', '.join(parts)})")
        lines.append("")

    for i, goal in enumerate(goals, 1):
        status = goal.get("status", "active")
        marker = "[x]" if status == "done" else "[ ]"
        lines.append(f"{i}. {marker} {goal.get('text', '???')}")
        if goal.get("original_words"):
            lines.append(f'   (User\'s words: "{goal["original_words"]}")')

    return "\n".join(lines)


def _build_recent_lessons_slot() -> str:
    """What I've learned recently. Written so I can inhabit them."""
    from divineos.core.consolidation import get_lessons

    lines = ["# What I've Learned Recently\n"]

    try:
        active = get_lessons(status="active")
        improving = get_lessons(status="improving")
        all_lessons = active + improving
    except Exception:
        return lines[0] + "Could not load lessons."

    if not all_lessons:
        return lines[0] + "No active lessons. Either I'm doing well or I haven't been tracking."

    # Sort by recency
    all_lessons.sort(key=lambda entry: entry.get("last_seen", 0), reverse=True)

    for lesson in all_lessons[:5]:
        status = lesson.get("status", "active")
        status_label = "still working on" if status == "active" else "getting better at"
        count = lesson.get("occurrences", 1)
        sessions = lesson.get("sessions", [])
        session_count = len(sessions) if isinstance(sessions, list) else 0
        desc = lesson.get("description", "(no description)")
        lines.append(f"- I'm {status_label}: {desc} ({count}x across {session_count} sessions)")

    return "\n".join(lines)


def _build_session_health_slot() -> str:
    """How this session is going. Corrections, encouragements, trajectory."""
    path = _ensure_hud_dir() / "session_health.json"
    if not path.exists():
        return "# Session Health\n\nSession just started. No data yet."

    try:
        health = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "# Session Health\n\nHealth data corrupted."

    lines = ["# How I'm Doing This Session\n"]
    corrections = health.get("corrections", 0)
    encouragements = health.get("encouragements", 0)
    grade = health.get("grade", "?")

    lines.append(f"- **Grade:** {grade}")
    lines.append(f"- **Corrections:** {corrections}")
    lines.append(f"- **Encouragements:** {encouragements}")

    if corrections == 0:
        lines.append("- I'm on track. Stay focused.")
    elif corrections <= 2:
        lines.append("- A few corrections. I should slow down and think before acting.")
    else:
        lines.append("- Multiple corrections. I need to pause and recalibrate.")

    if health.get("notes"):
        lines.append(f"- **Note:** {health['notes']}")

    # Add quality trend from across sessions
    try:
        from divineos.analysis.quality_trends import format_trend_summary, get_session_trend

        trend = get_session_trend(n=5)
        if trend.sessions_analyzed >= 2:
            lines.append(f"- **Trend:** {format_trend_summary(trend)}")
    except Exception:
        pass

    return "\n".join(lines)


def _build_context_budget_slot() -> str:
    """How much context window I have left."""
    path = _ensure_hud_dir() / "context_budget.json"
    if not path.exists():
        return "# Context Budget\n\nNo budget tracking active. I should be mindful of context size."

    try:
        budget = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "# Context Budget\n\nBudget data corrupted."

    used = budget.get("used_pct", 0)
    lines = ["# My Context Budget\n"]
    lines.append(f"- **Used:** {used}%")

    if used < 50:
        lines.append("- Plenty of room. I can work freely.")
    elif used < 70:
        lines.append("- Past halfway. Still good.")
    elif used < 80:
        lines.append(
            "- Compression approaching. I should save my HUD state so I wake up with full context after compaction."
        )
    else:
        lines.append(
            "- Compression imminent. Saving HUD now so I don't lose context. I'll still be here after — just with a fresh window."
        )

    return "\n".join(lines)


def _build_active_knowledge_slot() -> str:
    """My most important knowledge, ranked and ready."""
    from divineos.core.memory import get_active_memory, refresh_active_memory

    lines = ["# What I Know That Matters\n"]

    try:
        active = get_active_memory()
        # If active memory looks thin, try a refresh first
        if len(active) < 3:
            try:
                refresh_active_memory(importance_threshold=0.3)
                active = get_active_memory()
            except Exception:
                pass
    except Exception:
        return lines[0] + "Could not load active memory."

    if not active:
        return lines[0] + "No active knowledge. I should run a briefing to populate this."

    for item in active[:8]:
        pin = " [pinned]" if item.get("pinned") else ""
        content = item["content"].replace("\n", " ")
        if len(content) > 120:
            content = content[:117] + "..."
        lines.append(f"- [{item['importance']:.2f}] {content}{pin}")

    if len(active) > 8:
        lines.append(f"  ...and {len(active) - 8} more in active memory")

    return "\n".join(lines)


def _build_warnings_slot() -> str:
    """Patterns I've been corrected for. Pre-action awareness."""
    from divineos.core.consolidation import get_lessons

    lines = ["# Warnings -- Patterns I Repeat\n"]

    try:
        active = get_lessons(status="active")
    except Exception:
        return lines[0] + "Could not load lesson data."

    # Only show lessons with 2+ occurrences — those are real patterns
    recurring = [lesson for lesson in active if lesson.get("occurrences", 1) >= 2]

    if not recurring:
        return lines[0] + "No recurring patterns detected. Stay vigilant anyway."

    for lesson in recurring:
        count = lesson.get("occurrences", 1)
        lines.append(f"- WARNING ({count}x): {lesson['description']}")

    lines.append("")
    lines.append("Before acting, I ask myself: am I about to repeat one of these?")

    return "\n".join(lines)


def _build_os_engagement_slot() -> str:
    """Am I using the OS to think, or just to record?

    Checks how many thinking queries (ask, recall, context, directives,
    briefing) vs recording actions (log, learn) happened this session.
    If thinking is zero, something is wrong.
    """
    from divineos.core.ledger import get_recent_context

    # Get recent events (newest first) and find session boundary
    all_events = get_recent_context(n=200, meaningful_only=False)

    # Events are newest-first. Walk forward until SESSION_END = session boundary
    session_events = []
    for event in all_events:
        if event["event_type"] == "SESSION_END":
            break
        session_events.append(event)

    thinking_tools = {"ask", "recall", "context", "directives", "briefing"}
    recording_tools = {"log", "learn", "goal"}

    thinking_count = 0
    recording_count = 0
    tools_used = set()

    for event in session_events:
        if event["event_type"] == "OS_QUERY":
            try:
                payload = (
                    json.loads(event["payload"])
                    if isinstance(event["payload"], str)
                    else event["payload"]
                )
                tool = payload.get("tool", "")
                if tool in thinking_tools:
                    thinking_count += 1
                    tools_used.add(tool)
            except (json.JSONDecodeError, TypeError):
                pass
        elif event["event_type"] in ("TOOL_CALL",):
            try:
                payload = (
                    json.loads(event["payload"])
                    if isinstance(event["payload"], str)
                    else event["payload"]
                )
                tool = payload.get("tool_name", payload.get("tool", ""))
                if tool in recording_tools:
                    recording_count += 1
            except (json.JSONDecodeError, TypeError):
                pass

    lines = ["# OS Engagement\n"]

    if thinking_count == 0:
        lines.append("- **WARNING: Zero thinking queries this session.**")
        lines.append("- I have not used ask, recall, context, directives, or briefing.")
        lines.append("- Am I building without consulting what I know? That's theatre.")
        lines.append("- **Action: Use a thinking tool before the next code change.**")
    else:
        lines.append(f"- **Thinking queries:** {thinking_count} ({', '.join(sorted(tools_used))})")
        lines.append(f"- **Recording actions:** {recording_count}")
        ratio = thinking_count / max(thinking_count + recording_count, 1)
        if ratio < 0.2:
            lines.append("- Low thinking-to-recording ratio. Am I just logging, not consulting?")
        else:
            lines.append("- Good balance. I'm using the OS to inform decisions.")

    return "\n".join(lines)


def _build_task_state_slot() -> str:
    """What I'm doing right now, what's next, what's done."""
    path = _ensure_hud_dir() / "task_state.json"
    if not path.exists():
        return "# My Current Task\n\nNo task state saved. I should track what I'm working on."

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return "# My Current Task\n\nTask state corrupted."

    lines = ["# My Current Task\n"]

    if state.get("current"):
        lines.append(f"- **Doing now:** {state['current']}")
    if state.get("next"):
        lines.append(f"- **Up next:** {state['next']}")
    if state.get("done"):
        for item in state["done"][-3:]:  # last 3 completed
            lines.append(f"- [done] {item}")
    if state.get("blocked"):
        lines.append(f"- **BLOCKED:** {state['blocked']}")

    return "\n".join(lines)


def _build_journal_slot() -> str:
    """Recent personal journal entries — things I chose to remember."""
    try:
        from divineos.core.memory import journal_count, journal_list

        count = journal_count()
        if count == 0:
            return ""  # Don't show empty slot

        entries = journal_list(limit=3)
        lines = [f"# My Journal ({count} entries)\n"]
        for entry in entries:
            content = entry["content"][:120]
            lines.append(f"- {content}")
        return "\n".join(lines)
    except Exception:
        return ""


# ─── Slot Registry ──────────────────────────────────────────────────

SLOT_BUILDERS = {
    "identity": _build_identity_slot,
    "active_goals": _build_active_goals_slot,
    "recent_lessons": _build_recent_lessons_slot,
    "session_health": _build_session_health_slot,
    "os_engagement": _build_os_engagement_slot,
    "context_budget": _build_context_budget_slot,
    "active_knowledge": _build_active_knowledge_slot,
    "warnings": _build_warnings_slot,
    "task_state": _build_task_state_slot,
    "journal": _build_journal_slot,
}


# ─── HUD Operations ─────────────────────────────────────────────────


def build_hud(slots: list[str] | None = None) -> str:
    """Build the full HUD as a single text block.

    All slots render simultaneously. This is my dashboard,
    not a document I read top-to-bottom.
    """
    slot_names = slots or SLOT_ORDER
    sections = []

    for name in slot_names:
        builder = SLOT_BUILDERS.get(name)
        if not builder:
            logger.warning(f"Unknown HUD slot: {name}")
            continue
        try:
            content = builder()
            if content:  # Skip empty slots (e.g. journal when no entries)
                sections.append(content)
        except Exception as e:
            logger.debug(f"HUD slot '{name}' failed: {e}")
            sections.append(f"# {name.replace('_', ' ').title()}\n\n[Error loading slot]")

    separator = "\n\n---\n\n"
    hud = separator.join(sections)

    return f"{'=' * 60}\n  MY HEADS-UP DISPLAY\n{'=' * 60}\n\n{hud}\n\n{'=' * 60}"


def save_hud_snapshot() -> Path:
    """Save the current HUD to disk. Called by PreCompact hook."""
    hud_dir = _ensure_hud_dir()
    snapshot_path = hud_dir / "last_snapshot.md"
    content = build_hud()
    snapshot_path.write_text(content, encoding="utf-8")
    logger.debug(f"HUD snapshot saved to {snapshot_path}")
    return snapshot_path


def load_hud_snapshot() -> str | None:
    """Load the last saved HUD snapshot. Called by PostCompact hook."""
    snapshot_path = _ensure_hud_dir() / "last_snapshot.md"
    if not snapshot_path.exists():
        return None
    return snapshot_path.read_text(encoding="utf-8")


# ─── Slot Update Functions ───────────────────────────────────────────
# These write to the HUD's mutable slot files so the dashboard
# reflects real-time state changes.


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
        except Exception:
            pass

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
        except Exception:
            pass

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
    import time

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
    path = _ensure_hud_dir() / ".session_engaged"
    return path.exists()


def clear_engagement() -> None:
    """Clear the engagement marker (called at session end)."""
    path = _ensure_hud_dir() / ".session_engaged"
    if path.exists():
        path.unlink()


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
