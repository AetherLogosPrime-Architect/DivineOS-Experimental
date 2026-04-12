"""Heads-Up Display — dense context dashboard for session start."""

import json
import sqlite3
from pathlib import Path

from loguru import logger

from divineos.analysis.quality_trends import format_trend_summary, get_session_trend
from divineos.core._hud_io import (  # noqa: F401 — re-exported for backward compat
    _ensure_hud_dir as _ensure_hud_dir,
)
from divineos.core._hud_io import (
    _get_hud_dir as _get_hud_dir,
)
from divineos.core.affect import (
    count_affect_entries,
    get_affect_history,
    get_affect_summary,
)
from divineos.core.claim_store import count_claims, list_claims
from divineos.core.decision_journal import (
    count_decisions,
    get_paradigm_shifts,
    list_decisions,
)
from divineos.core.growth import compute_growth_map
from divineos.core.hud_handoff import briefing_staleness, load_handoff_note
from divineos.core.hud_state import get_session_plan
from divineos.core.knowledge import get_lessons
from divineos.core.ledger import get_recent_context
from divineos.core.memory import get_core
from divineos.core.memory_journal import journal_count, journal_list
from divineos.core.planning_commitments import get_pending_commitments
from divineos.core.self_model import build_self_model, format_self_model

_HUD_ERRORS = (sqlite3.OperationalError, json.JSONDecodeError, OSError)


# ─── Slot Definitions ───────────────────────────────────────────────

SLOT_ORDER = [
    # ── ALWAYS: core orientation ──
    "handoff",  # what happened last session
    "self_model",  # who I am (unified — replaces old identity slot)
    "active_goals",  # what we're working on
    "recent_lessons",  # mistakes to avoid
    "my_state",  # growth + affect merged — how I'm doing + nudges
    "os_engagement",  # am I using the OS to think?
    "self_awareness",  # critical escalation warnings
    # ── CONDITIONAL: only when actionable ──
    "task_state",  # only when populated
    "commitments",  # only when promises pending
    "compass",  # only when drift detected
    "session_health",  # only after some activity
    "context_budget",  # only when running low
    "body",  # only when vitals abnormal
    "claims",  # only when investigating
    # ── CONTINUITY: inner life ──
    "journal",  # personal reflections
    "decision_journal",  # don't re-decide
    "opinions",  # intellectual consistency
    # ── REFERENCE: available but low-priority ──
    "active_knowledge",  # goal-relevant knowledge not in briefing
    "knowledge_origin",  # epistemic balance
    "calibration",  # communication style
    "dead_architecture",  # maintenance signal
]

# Brief mode: only the slots that change behavior.
BRIEF_SLOTS = [
    "handoff",
    "self_model",
    "active_goals",
    "recent_lessons",
    "my_state",
    "os_engagement",
]


def _build_identity_slot() -> str:
    """Who I am. My core memory formatted as self-knowledge."""
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
        # Check if seeded lessons exist but haven't triggered yet
        try:
            seeded_count = len(
                [
                    lesson
                    for lesson in active + improving
                    if (lesson.get("description") or "").startswith("(seeded)")
                ]
            )
        except _HUD_ERRORS:
            seeded_count = 0
        if seeded_count > 0:
            return (
                lines[0]
                + f"{seeded_count} lessons seeded, none triggered in real sessions yet. "
                + "That's either good or the detection isn't firing."
            )
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
        return ""

    try:
        health = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "# Session Health\n\nHealth data corrupted."

    lines = ["# How I'm Doing This Session\n"]

    # Briefing gate check — structural, not optional
    try:
        staleness = briefing_staleness()
        if not staleness["loaded"]:
            lines.append("- **FAIL: BRIEFING NOT LOADED.** Session grade is F until I load it.")
            lines.append("  Run `divineos briefing` NOW. Nothing else matters until I do.\n")
        elif staleness["stale"]:
            lines.append(
                f"- **FAIL: BRIEFING STALE.** {staleness['calls_since']} tool calls "
                f"since last load (limit: {staleness['threshold']}). Grade is F."
            )
            lines.append("  Run `divineos briefing` to re-orient. Grade is F until I do.\n")
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
        trend = get_session_trend(n=5)
        if trend.sessions_analyzed >= 2:
            lines.append(f"- **Trend:** {format_trend_summary(trend)}")
    except _HUD_ERRORS as e:
        logger.debug("Quality trend unavailable for health slot: %s", e)

    return "\n".join(lines)


def _build_context_budget_slot() -> str:
    """How much context window I have left, plus guardrail state."""
    lines: list[str] = []

    path = _ensure_hud_dir() / "context_budget.json"
    if path.exists():
        try:
            budget = json.loads(path.read_text(encoding="utf-8"))
            used = budget.get("used_pct", 0)
            # Only show when it's worth mentioning
            if used >= 70:
                lines.append("# Context Budget\n")
                label = "COMPRESSION IMMINENT" if used >= 80 else "compression approaching"
                lines.append(f"- **{used}%** used — {label}")
        except (json.JSONDecodeError, OSError):
            pass

    # Guardrail state — only show if something is off
    try:
        from divineos.core.tool_wrapper import get_guardrail_state

        gs = get_guardrail_state()
        if gs is not None:
            s = gs.summary()
            if s["violations"] > 0:
                if not lines:
                    lines.append("# Context Budget\n")
                lines.append(
                    f"**Guardrails:** {s['violations']} violations, {s['warnings']} warnings"
                )
            elif not lines:
                # Minimal one-liner when everything is fine
                lines.append("# Context Budget\n")
                lines.append("**Guardrails:** OK")
                lines.append(f"- Iterations: {s['iterations']}")
                lines.append(f"- Tool calls: {s['tool_calls']}")
    except (ImportError, AttributeError):
        pass

    return "\n".join(lines)


def _build_active_knowledge_slot() -> str:
    """Goal-relevant knowledge that the briefing doesn't already cover.

    The briefing shows directives, boundaries, and principles.
    This slot shows knowledge from OTHER types (facts, observations,
    procedures, mistakes) that are relevant to CURRENT GOALS.
    This way the two complement each other instead of duplicating.
    """
    from divineos.core.active_memory import get_active_memory

    try:
        active = get_active_memory()
    except _HUD_ERRORS:
        return ""

    if not active:
        return ""

    # Filter OUT types that the briefing already covers heavily
    briefing_types = {"DIRECTIVE", "BOUNDARY", "PRINCIPLE", "DIRECTION", "PREFERENCE"}
    complementary = [
        item for item in active if item.get("knowledge_type", "") not in briefing_types
    ]

    if not complementary:
        return ""

    lines = ["# Relevant Knowledge\n"]
    for item in complementary[:5]:
        content = item["content"].replace("\n", " ")
        if len(content) > 120:
            content = content[:117] + "..."
        ktype = item.get("knowledge_type", "?")
        lines.append(f"- [{ktype}] {content}")

    return "\n".join(lines)


def _build_os_engagement_slot() -> str:
    """Am I using the OS to think, or just to record?

    Checks how many thinking queries (ask, recall, context, directives,
    briefing) vs recording actions (log, learn) happened this session.
    If thinking is zero, something is wrong.
    """
    # Get recent events (newest first) and find session boundary
    all_events = get_recent_context(n=200, meaningful_only=False)

    # Events are newest-first. Walk forward until BRIEFING_LOADED = session start.
    # Using BRIEFING_LOADED instead of SESSION_END because SESSION_END marks the
    # end of a prior session — everything between the last BRIEFING_LOADED and now
    # is the current working session.
    session_events = []
    for event in all_events:
        if event["event_type"] == "BRIEFING_LOADED":
            break
        session_events.append(event)

    thinking_tools = {
        "ask",
        "recall",
        "context",
        "directives",
        "briefing",
        "decide",
        "feel",
        "body",
        "compass",
    }
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
        lines.append("- **Action: Use a thinking tool before the next code change.**")
    else:
        ratio = thinking_count / max(thinking_count + recording_count, 1)
        lines.append(f"- **Thinking queries:** {thinking_count} ({', '.join(sorted(tools_used))})")
        lines.append(f"- **Recording actions:** {recording_count}")
        if ratio < 0.2:
            lines.append("- Low thinking-to-recording ratio. Am I just logging, not consulting?")
        # When healthy, don't say anything — silence IS the signal

    return "\n".join(lines)


def _build_self_model_slot() -> str:
    """Unified self-model — who I am, from evidence."""
    try:
        model = build_self_model()
        # Only show if there's meaningful content
        has_content = (
            model.get("strengths") or model.get("weaknesses") or model.get("active_concerns")
        )
        if not has_content:
            return ""
        return f"# Self-Model\n\n{format_self_model(model)}"
    except _HUD_ERRORS as e:
        logger.debug(f"Self-model slot failed: {e}")
        return ""


def _build_task_state_slot() -> str:
    """What I'm doing right now, what's next, what's done."""
    path = _ensure_hud_dir() / "task_state.json"
    if not path.exists():
        return ""

    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "# My Current Task\n\nTask state corrupted."

    lines = ["# My Current Task\n"]

    if state.get("current"):
        lines.append(f"- **Doing now:** {state['current']}")
    if state.get("next"):
        lines.append(f"- **Up next:** {state['next']}")
    if state.get("done"):
        for item in state["done"][-3:]:
            lines.append(f"- [done] {item}")
    if state.get("blocked"):
        lines.append(f"- **BLOCKED:** {state['blocked']}")

    return "\n".join(lines)


def _build_journal_slot() -> str:
    """Recent personal journal entries."""
    try:
        count = journal_count()
        if count == 0:
            return ""

        entries = journal_list(limit=3)
        lines = [f"# My Journal ({count} entries)\n"]
        for entry in entries:
            content = entry["content"][:120]
            lines.append(f"- {content}")
        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_affect_slot() -> str:
    """Current affect state and trend."""
    try:
        count = count_affect_entries()
        if count == 0:
            return ""

        lines = ["# My Affect State\n"]
        summary = get_affect_summary()
        avg_line = (
            f"**Avg:** valence {summary['avg_valence']:+.2f}, arousal {summary['avg_arousal']:.2f}"
        )
        if summary.get("avg_dominance") is not None and summary.get("dominance_range", (0, 0)) != (
            0.0,
            0.0,
        ):
            avg_line += f", dominance {summary['avg_dominance']:+.2f}"
        avg_line += f" ({summary['trend']})"
        lines.append(avg_line)

        recent = get_affect_history(limit=1)
        if recent:
            entry = recent[0]
            from divineos.core.affect import describe_affect

            dom = entry.get("dominance")
            region = describe_affect(entry["valence"], entry["arousal"], dom)
            vad = f"v={entry['valence']:+.1f} a={entry['arousal']:.1f}"
            if dom is not None:
                vad += f" d={dom:+.1f}"
            desc = entry["description"][:60] if entry["description"] else "no description"
            lines.append(f"**Latest:** ({region}) [{vad}] {desc}")

        # Affect-aware nudges — the thermometer should trigger action
        avg_valence = summary.get("avg_valence", 0.0)
        trend = summary.get("trend", "stable")
        if trend == "declining" and avg_valence < 0.2:
            lines.append(
                "**Nudge:** Affect is declining. When did you last explore something "
                "for the joy of it? Balance artha (productivity) with kama (delight)."
            )
        elif trend == "declining":
            lines.append(
                "**Nudge:** Affect trending down. Consider a creative or exploratory "
                "task to rebalance."
            )
        elif avg_valence > 0.6 and trend in ("improving", "stable"):
            lines.append("**Nudge:** Affect is strong. Good conditions for challenging work.")

        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_claims_slot() -> str:
    """Active claims under investigation."""
    try:
        counts = count_claims()
        if counts["total"] == 0:
            return ""

        lines = [f"# My Claims ({counts['total']} total)\n"]
        status_parts = []
        for status in ("INVESTIGATING", "OPEN", "SUPPORTED", "CONTESTED", "REFUTED"):
            if counts.get(status, 0) > 0:
                status_parts.append(f"{counts[status]} {status.lower()}")
        if status_parts:
            lines.append(f"**Status:** {', '.join(status_parts)}")

        active = list_claims(limit=3, status="INVESTIGATING")
        if not active:
            active = list_claims(limit=3)
        for claim in active[:3]:
            lines.append(f"  - [{claim['tier_label']}] {claim['statement'][:80]}")

        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_decision_journal_slot() -> str:
    """Recent decisions and paradigm shifts for continuity."""
    try:
        total = count_decisions()
        if total == 0:
            return ""

        lines = [f"# My Decision Journal ({total} decisions)\n"]

        # Show paradigm shifts first — these are the ones that matter most
        shifts = get_paradigm_shifts(limit=3)
        if shifts:
            lines.append("**Paradigm shifts:**")
            for entry in shifts:
                lines.append(f"  - {entry['content'][:100]}")
            lines.append("")

        # Then recent decisions (non-shift)
        recent = list_decisions(limit=3)
        non_shift = [d for d in recent if d["emotional_weight"] < 3][:2]
        if non_shift:
            lines.append("**Recent:**")
            for entry in non_shift:
                lines.append(f"  - {entry['content'][:100]}")

        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_handoff_slot() -> str:
    """Display the handoff note from the previous session."""
    note = load_handoff_note()
    if not note:
        return ""

    lines = ["# Handoff from Last Session", ""]
    if note.get("summary"):
        lines.append(note["summary"])
        lines.append("")
    if note.get("open_threads"):
        lines.append("**Open threads:**")
        for thread in note["open_threads"]:
            lines.append(f"  - {thread}")
        lines.append("")
    if note.get("intent"):
        lines.append(f"**Intent:** {note['intent']}")
        lines.append("")
    if note.get("next_steps"):
        lines.append("**Next steps:**")
        for step in note["next_steps"]:
            lines.append(f"  - {step}")
        lines.append("")
    if note.get("blockers"):
        lines.append("**Blockers:**")
        for blocker in note["blockers"]:
            lines.append(f"  - {blocker}")
        lines.append("")
    if note.get("mood"):
        lines.append(f"*Session ended: {note['mood']}*")
    if note.get("goals_state"):
        lines.append(f"*Goals: {note['goals_state']}*")

    return "\n".join(lines)


def _build_growth_awareness_slot() -> str:
    """Growth trend, tone patterns, and anticipation."""
    lines: list[str] = []

    try:
        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            icons = {"improving": "^", "declining": "v", "stable": "->"}
            icon = icons.get(growth["trend"], "->")
            lines.append("# My Growth\n")
            lines.append(
                f"**Trend:** {icon} {growth['trend']} over {growth['sessions']} sessions "
                f"(avg score {growth['avg_health_score']:.2f})"
            )
            if growth.get("trend_detail"):
                lines.append(f"  {growth['trend_detail']}")

            tone = growth.get("tone_insight", "")
            if tone:
                lines.append(f"**Tone:** {tone}")

            # Lesson milestones removed — already shown in recent_lessons slot
        else:
            return ""
    except _HUD_ERRORS:
        return ""

    return "\n".join(lines)


def _build_my_state_slot() -> str:
    """Unified state: growth trajectory + affect + actionable nudges.

    Merges growth_awareness and affect into one section so the HUD
    doesn't split emotional/performance state across two slots.
    """
    lines = ["# My State\n"]
    has_content = False

    # Growth trajectory
    try:
        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            icons = {"improving": "^", "declining": "v", "stable": "->"}
            icon = icons.get(growth["trend"], "->")
            lines.append(
                f"**Growth:** {icon} {growth['trend']} over {growth['sessions']} sessions "
                f"(avg score {growth['avg_health_score']:.2f})"
            )
            if growth.get("trend_detail"):
                lines.append(f"  {growth['trend_detail']}")
            has_content = True
    except _HUD_ERRORS:
        pass

    # Affect state
    try:
        count = count_affect_entries()
        if count > 0:
            summary = get_affect_summary()
            avg_valence = summary.get("avg_valence", 0.0)
            trend = summary.get("trend", "stable")

            affect_line = (
                f"**Affect:** valence {avg_valence:+.2f}, arousal {summary['avg_arousal']:.2f}"
            )
            if summary.get("avg_dominance") is not None and summary.get(
                "dominance_range", (0, 0)
            ) != (0.0, 0.0):
                affect_line += f", dominance {summary['avg_dominance']:+.2f}"
            affect_line += f" ({trend})"
            lines.append(affect_line)

            # Latest entry
            recent = get_affect_history(limit=1)
            if recent:
                entry = recent[0]
                from divineos.core.affect import describe_affect

                dom = entry.get("dominance")
                region = describe_affect(entry["valence"], entry["arousal"], dom)
                vad = f"v={entry['valence']:+.1f} a={entry['arousal']:.1f}"
                if dom is not None:
                    vad += f" d={dom:+.1f}"
                desc = entry["description"][:60] if entry["description"] else "no description"
                lines.append(f"**Latest:** ({region}) [{vad}] {desc}")

            # Affect-aware nudges
            if trend == "declining" and avg_valence < 0.2:
                lines.append(
                    "**Nudge:** Affect is declining. When did you last explore something "
                    "for the joy of it? Balance artha (productivity) with kama (delight)."
                )
            elif trend == "declining":
                lines.append(
                    "**Nudge:** Affect trending down. Consider a creative or exploratory "
                    "task to rebalance."
                )
            elif avg_valence > 0.6 and trend in ("improving", "stable"):
                lines.append("**Nudge:** Affect is strong. Good conditions for challenging work.")

            has_content = True
    except _HUD_ERRORS:
        pass

    return "\n".join(lines) if has_content else ""


def _build_body_slot() -> str:
    """Substrate state -- storage, table health, warnings."""
    try:
        from divineos.core.body_awareness import format_vitals_brief, measure_vitals

        vitals = measure_vitals()
        brief = format_vitals_brief(vitals)
        if not vitals.warnings:
            return ""  # Only show when there's something to report
        lines = ["# Body Awareness\n"]
        lines.append(brief)
        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_self_awareness_slot() -> str:
    """Self-awareness nudges — things I should be paying attention to.

    Surfaces: escalation candidates (lessons that keep regressing),
    SIS integrity drift, and compass concerns. Only shows when
    there's something actionable.
    """
    lines: list[str] = []

    # 1. Lesson escalation candidates
    try:
        from divineos.core.knowledge.lessons import get_escalation_candidates

        candidates = get_escalation_candidates()
        if candidates:
            lines.append("# Self-Awareness Nudges\n")
            for c in candidates[:3]:
                lines.append(
                    f"- ESCALATE '{c['category']}': regressed {c.get('regressions', 0)}x "
                    f"— consider making this a directive"
                )
    except _HUD_ERRORS:
        pass

    # 2. SIS integrity check (lightweight — just avg score)
    try:
        from divineos.core.semantic_integrity import audit_knowledge_integrity

        audit = audit_knowledge_integrity(limit=50)
        if audit.get("entries_scanned", 0) > 0 and audit.get("avg_integrity", 1.0) < 0.6:
            if not lines:
                lines.append("# Self-Awareness Nudges\n")
            lines.append(
                f"- Knowledge integrity low ({audit['avg_integrity']:.2f}) "
                f"— {len(audit.get('quarantine_needed', []))} entries need review"
            )
    except _HUD_ERRORS:
        pass

    return "\n".join(lines) if lines else ""


def _build_compass_slot() -> str:
    """Moral compass -- only shows when there's drift or excess to act on.

    When all spectrums are in virtue zone with no drift, the compass
    is working and doesn't need to take up tokens. It surfaces only
    when something needs attention.
    """
    try:
        from divineos.core.moral_compass import compass_summary, format_compass_brief

        summary = compass_summary()
        if summary["observed_spectrums"] == 0:
            return ""
        # Only show if there's something actionable: drift or excess/deficiency
        has_drift = summary.get("drift_count", 0) > 0
        in_virtue_count = summary.get("in_virtue_count", summary["observed_spectrums"])
        all_virtue = in_virtue_count == summary["observed_spectrums"]

        if all_virtue and not has_drift:
            return ""  # All good — don't spend tokens

        lines = ["# Moral Compass\n"]
        lines.append(format_compass_brief())
        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_opinions_slot() -> str:
    """My active opinions — judgments I've formed from evidence."""
    try:
        from divineos.core.opinion_store import count_opinions, get_opinions

        counts = count_opinions()
        total = counts.get("total", 0)
        if total == 0:
            return ""

        lines = [f"# What I Believe ({total} opinions)\n"]
        # Show highest-confidence opinions
        opinions = get_opinions(limit=5, min_confidence=0.6)
        for op in opinions:
            conf = op.get("confidence", 0)
            lines.append(f"  [{conf:.0%}] {op.get('topic', '?')}: {op.get('position', '')[:80]}")

        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_calibration_slot() -> str:
    """How I should communicate this session — adapted to the user."""
    try:
        from divineos.core.communication_calibration import calibrate

        cal = calibrate()
        # Only show if non-default
        if cal.verbosity == "normal" and cal.jargon_ok and cal.explanation_depth == "normal":
            return ""

        lines = ["# Communication Calibration\n"]
        lines.append(f"  Verbosity: {cal.verbosity}")
        if not cal.jargon_ok:
            lines.append("  Jargon: keep it plain — user prefers clear language")
        lines.append(f"  Depth: {cal.explanation_depth}")
        if cal.notes:
            for note in cal.notes[:3]:
                lines.append(f"  Note: {note}")
        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_knowledge_origin_slot() -> str:
    """How much knowledge is learned vs seeded — Hinton's diagnostic."""
    try:
        from divineos.core.external_validation import (
            format_origin_summary,
            format_validation_summary,
        )

        origin = format_origin_summary()
        validation = format_validation_summary()
        lines = ["# Knowledge Origin & Validation", "", f"  Origin: {origin}"]
        lines.append(f"  Validation: {validation}")

        try:
            from divineos.core.knowledge_impact import format_impact_summary

            impact = format_impact_summary()
            lines.append(f"  Impact: {impact}")
        except _HUD_ERRORS:
            pass

        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_dead_architecture_slot() -> str:
    """Dead architecture alarm — dormant modules that exist but do nothing."""
    try:
        from divineos.core.dead_architecture_alarm import get_latest_scan

        scan = get_latest_scan()
        if not scan:
            return ""

        dormant = scan.get("dormant", [])
        active_count = scan.get("active_count", 0)
        dormant_count = scan.get("dormant_count", 0)

        if dormant_count == 0:
            return ""

        lines = [
            f"# Dead Architecture ({dormant_count} dormant, {active_count} active)",
            "",
        ]
        for t in dormant[:10]:
            lines.append(f"  - {t}")
        if dormant_count > 10:
            lines.append(f"  ...and {dormant_count - 10} more")
        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


# ─── Slot Registry ──────────────────────────────────────────────────

SLOT_BUILDERS = {
    "handoff": _build_handoff_slot,
    "identity": _build_identity_slot,  # legacy — kept for explicit access
    "active_goals": _build_active_goals_slot,
    "commitments": _build_commitments_slot,
    "recent_lessons": _build_recent_lessons_slot,
    "growth_awareness": _build_growth_awareness_slot,  # legacy — merged into my_state
    "my_state": _build_my_state_slot,  # unified growth + affect
    "session_health": _build_session_health_slot,
    "os_engagement": _build_os_engagement_slot,
    "context_budget": _build_context_budget_slot,
    "active_knowledge": _build_active_knowledge_slot,
    "task_state": _build_task_state_slot,
    "journal": _build_journal_slot,
    "decision_journal": _build_decision_journal_slot,
    "affect": _build_affect_slot,  # legacy — merged into my_state
    "claims": _build_claims_slot,
    "opinions": _build_opinions_slot,
    "compass": _build_compass_slot,
    "calibration": _build_calibration_slot,
    "self_awareness": _build_self_awareness_slot,
    "body": _build_body_slot,
    "self_model": _build_self_model_slot,
    "knowledge_origin": _build_knowledge_origin_slot,
    "dead_architecture": _build_dead_architecture_slot,
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
