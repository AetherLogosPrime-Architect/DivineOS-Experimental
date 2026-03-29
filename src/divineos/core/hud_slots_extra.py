"""Extra HUD slot builders — task state, journal, handoff, growth."""

import json

from divineos.core.hud import _ensure_hud_dir


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
        for item in state["done"][-3:]:
            lines.append(f"- [done] {item}")
    if state.get("blocked"):
        lines.append(f"- **BLOCKED:** {state['blocked']}")

    return "\n".join(lines)


def _build_journal_slot() -> str:
    """Recent personal journal entries."""
    try:
        from divineos.core.memory_journal import journal_count, journal_list

        count = journal_count()
        if count == 0:
            return ""

        entries = journal_list(limit=3)
        lines = [f"# My Journal ({count} entries)\n"]
        for entry in entries:
            content = entry["content"][:120]
            lines.append(f"- {content}")
        return "\n".join(lines)
    except Exception:
        return ""


def _build_handoff_slot() -> str:
    """Display the handoff note from the previous session."""
    from divineos.core.hud_handoff import load_handoff_note

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
    if note.get("mood"):
        lines.append(f"*Session ended: {note['mood']}*")
    if note.get("goals_state"):
        lines.append(f"*Goals: {note['goals_state']}*")

    return "\n".join(lines)


def _build_growth_awareness_slot() -> str:
    """Growth trend, tone patterns, and anticipation."""
    lines: list[str] = []

    try:
        from divineos.core.growth import compute_growth_map

        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            icons = {"improving": "↑", "declining": "↓", "stable": "→"}
            icon = icons.get(growth["trend"], "→")
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

            lessons = growth.get("lessons", {})
            resolved = lessons.get("resolved", 0)
            if resolved > 0:
                lines.append(f"**Milestones:** {resolved} lessons resolved")
        else:
            return ""
    except Exception:
        return ""

    return "\n".join(lines)
