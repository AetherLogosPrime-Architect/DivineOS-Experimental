"""Extra HUD slot builders — task state, journal, handoff, growth."""

import json
import sqlite3

from divineos.core._hud_io import _ensure_hud_dir

_HUD_ERRORS = (ImportError, sqlite3.OperationalError, json.JSONDecodeError, OSError)


def _build_task_state_slot() -> str:
    """What I'm doing right now, what's next, what's done."""
    path = _ensure_hud_dir() / "task_state.json"
    if not path.exists():
        return "# My Current Task\n\nNo task state saved. I should track what I'm working on."

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
    except _HUD_ERRORS:
        return ""


def _build_affect_slot() -> str:
    """Current affect state and trend."""
    try:
        from divineos.core.affect_log import (
            count_affect_entries,
            get_affect_history,
            get_affect_summary,
        )

        count = count_affect_entries()
        if count == 0:
            return ""

        lines = ["# My Affect State\n"]
        summary = get_affect_summary()
        lines.append(
            f"**Avg:** valence {summary['avg_valence']:+.2f}, "
            f"arousal {summary['avg_arousal']:.2f} "
            f"({summary['trend']})"
        )

        recent = get_affect_history(limit=1)
        if recent:
            entry = recent[0]
            desc = entry["description"][:80] if entry["description"] else "no description"
            lines.append(f"**Latest:** {desc}")

        return "\n".join(lines)
    except _HUD_ERRORS:
        return ""


def _build_claims_slot() -> str:
    """Active claims under investigation."""
    try:
        from divineos.core.claim_store import count_claims, list_claims

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
        from divineos.core.decision_journal import (
            count_decisions,
            get_paradigm_shifts,
            list_decisions,
        )

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
    except _HUD_ERRORS:
        return ""

    return "\n".join(lines)
