"""Heads-Up Display — dense context dashboard for session start."""

import json
import sqlite3
from pathlib import Path

from loguru import logger

from divineos.core._hud_io import (  # noqa: F401 — re-exported for backward compat
    _ensure_hud_dir as _ensure_hud_dir,
    _get_hud_dir as _get_hud_dir,
)

_HUD_ERRORS = (ImportError, sqlite3.OperationalError, json.JSONDecodeError, OSError)


# ─── Slot Definitions ───────────────────────────────────────────────

SLOT_ORDER = [
    "handoff",
    "identity",
    "active_goals",
    "commitments",
    "recent_lessons",
    "growth_awareness",
    "session_health",
    "os_engagement",
    "context_budget",
    "active_knowledge",
    "warnings",
    "journal",
    "decision_journal",
    "affect",
    "claims",
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
    from divineos.core.hud_state import get_session_plan

    path = _ensure_hud_dir() / "active_goals.json"
    if not path.exists():
        return "# My Current Goals\n\nNo goals set yet. I should ask what we're working on."

    try:
        goals = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
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

    active_goals = [g for g in goals if g.get("status", "active") != "done"]
    done_goals = [g for g in goals if g.get("status", "active") == "done"]

    if not active_goals and done_goals:
        lines.append("All goals completed! Time for new ones.")
        lines.append(f"({len(done_goals)} done — use 'divineos goal clear' to archive)")
        return "\n".join(lines)

    for i, goal in enumerate(active_goals, 1):
        lines.append(f"{i}. [ ] {goal.get('text', '???')}")
        if goal.get("original_words"):
            lines.append(f'   (User\'s words: "{goal["original_words"]}")')

    if done_goals:
        lines.append(f"\n({len(done_goals)} completed — use 'divineos goal clear' to archive)")

    return "\n".join(lines)


def _build_commitments_slot() -> str:
    """Promises I made. Tracked so I don't quietly drop them."""
    from divineos.core.planning_commitments import get_pending_commitments

    pending = get_pending_commitments()
    if not pending:
        return ""  # empty = skip slot entirely

    lines = ["# My Pending Commitments\n"]
    for c in pending:
        lines.append(f"- {c.text}")
    lines.append("\nI promised these. I should follow through or explicitly defer them.")
    return "\n".join(lines)


def _build_recent_lessons_slot() -> str:
    """What I've learned recently. Written so I can inhabit them."""
    from divineos.core.knowledge import get_lessons

    lines = ["# What I've Learned Recently\n"]

    try:
        active = get_lessons(status="active")
        improving = get_lessons(status="improving")
        # Filter out seeded lessons that have never actually fired
        all_lessons = [
            lesson
            for lesson in active + improving
            if not (
                lesson.get("occurrences", 1) <= 1
                and (lesson.get("description") or "").startswith("(seeded)")
            )
        ]
    except _HUD_ERRORS:
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
    except (json.JSONDecodeError, OSError):
        return "# Session Health\n\nHealth data corrupted."

    lines = ["# How I'm Doing This Session\n"]

    # Briefing gate check — structural, not optional
    try:
        from divineos.core.hud_handoff import briefing_staleness

        staleness = briefing_staleness()
        if not staleness["loaded"]:
            lines.append("- **FAIL: BRIEFING NOT LOADED.** Session grade is F until you load it.")
            lines.append("  Run `divineos briefing` NOW. Nothing else matters until you do.\n")
        elif staleness["stale"]:
            lines.append(
                f"- **FAIL: BRIEFING STALE.** {staleness['calls_since']} tool calls "
                f"since last load (limit: {staleness['threshold']}). Grade is F."
            )
            lines.append("  Run `divineos briefing` to re-orient. Grade is F until you do.\n")
    except _HUD_ERRORS:
        pass

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
    except _HUD_ERRORS as e:
        logger.debug("Quality trend unavailable for health slot: %s", e)

    return "\n".join(lines)


def _build_context_budget_slot() -> str:
    """How much context window I have left."""
    path = _ensure_hud_dir() / "context_budget.json"
    if not path.exists():
        return "# Context Budget\n\nNo budget tracking active. I should be mindful of context size."

    try:
        budget = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
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
    from divineos.core.active_memory import get_active_memory, refresh_active_memory

    lines = ["# What I Know That Matters\n"]

    try:
        active = get_active_memory()
        # If active memory looks thin, try a refresh first
        if len(active) < 3:
            try:
                refresh_active_memory(importance_threshold=0.3)
                active = get_active_memory()
            except _HUD_ERRORS as e:
                logger.debug("Active memory refresh failed (proceeding with thin memory): %s", e)
    except _HUD_ERRORS:
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
    from divineos.core.knowledge import get_lessons

    lines = ["# Warnings -- Patterns I Repeat\n"]

    try:
        active = get_lessons(status="active")
    except _HUD_ERRORS:
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


from divineos.core.hud_slots_extra import (  # noqa: E402
    _build_affect_slot,
    _build_claims_slot,
    _build_decision_journal_slot,
    _build_growth_awareness_slot,
    _build_handoff_slot,
    _build_journal_slot,
    _build_task_state_slot,
)


# ─── Slot Registry ──────────────────────────────────────────────────

SLOT_BUILDERS = {
    "handoff": _build_handoff_slot,
    "identity": _build_identity_slot,
    "active_goals": _build_active_goals_slot,
    "commitments": _build_commitments_slot,
    "recent_lessons": _build_recent_lessons_slot,
    "growth_awareness": _build_growth_awareness_slot,
    "session_health": _build_session_health_slot,
    "os_engagement": _build_os_engagement_slot,
    "context_budget": _build_context_budget_slot,
    "active_knowledge": _build_active_knowledge_slot,
    "warnings": _build_warnings_slot,
    "task_state": _build_task_state_slot,
    "journal": _build_journal_slot,
    "decision_journal": _build_decision_journal_slot,
    "affect": _build_affect_slot,
    "claims": _build_claims_slot,
}


# ─── HUD Operations ─────────────────────────────────────────────────


def build_hud(slots: list[str] | None = None) -> str:
    """Build the full HUD as a single text block."""
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
        except _HUD_ERRORS as e:
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
