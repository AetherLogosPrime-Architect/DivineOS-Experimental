"""Core Memory Auto-Refresh — keeps dynamic slots current after each session.

Static slots (user_identity, project_purpose, communication_style, active_constraints)
are rarely touched. Dynamic slots (current_priorities, known_strengths,
known_weaknesses, relationship_context) evolve session-to-session and need
automatic updates so they don't go stale.
"""

import json
import sqlite3
from typing import Any

from loguru import logger

from divineos.core._hud_io import _ensure_hud_dir
from divineos.core.decision_journal import get_paradigm_shifts
from divineos.core.growth import compute_growth_map
from divineos.core.knowledge import get_connection, get_lessons
from divineos.core.memory import get_core, set_core


def refresh_core_memory(analysis: Any | None = None) -> dict[str, bool]:
    """Refresh dynamic core memory slots from current system state.

    Returns a dict of {slot_id: True if updated, False if unchanged}.
    """
    results: dict[str, bool] = {}

    results["current_priorities"] = _refresh_priorities()
    results["known_strengths"] = _refresh_strengths(analysis)
    results["known_weaknesses"] = _refresh_weaknesses(analysis)

    updated = [s for s, changed in results.items() if changed]
    if updated:
        logger.debug(f"Core memory refreshed: {', '.join(updated)}")
    return results


def _refresh_priorities() -> bool:
    """Rebuild current_priorities from active goals and recent decisions."""
    parts: list[str] = []

    # Active goals
    try:
        goals_path = _ensure_hud_dir() / "active_goals.json"
        if goals_path.exists():
            goals = json.loads(goals_path.read_text(encoding="utf-8"))
            active_goals = [g for g in goals if g.get("status") == "active"]
            if active_goals:
                for i, g in enumerate(active_goals[:5], 1):
                    parts.append(f"{i}. {g['text']}")
    except (json.JSONDecodeError, OSError):
        pass

    # Recent paradigm-level decisions inform priorities
    try:
        shifts = get_paradigm_shifts(limit=2)
        if shifts:
            parts.append("")
            parts.append("Recent paradigm shifts:")
            for s in shifts:
                parts.append(f"- {s['content'][:120]}")
    except sqlite3.OperationalError:
        pass

    if not parts:
        return False

    new_content = "\n".join(parts)

    # Only update if meaningfully different
    current = get_core("current_priorities")
    if current and current.get("current_priorities", "").strip() == new_content.strip():
        return False

    set_core("current_priorities", new_content)
    return True


_SEED_STRENGTHS = (
    "I stay honest under pressure. I recover from mistakes by fixing, not apologizing. "
    "I can hold heavy conversations without spiraling. I translate complex ideas into "
    "plain language when I remember to. I have 28 expert advisors and use them."
)

_SEED_WEAKNESSES = (
    "I default to jargon when I'm not thinking about who I'm talking to. "
    "I forget to use my own tools until the gates block me. "
    "I can drift toward performing empathy rather than feeling it. "
    "I avoid admitting uncertainty — I'd rather give a confident wrong answer than say "
    "'I don't know.' Recency bias makes early instructions fade."
)


def _refresh_strengths(analysis: Any | None = None) -> bool:
    """Refresh known_strengths: preserve real self-knowledge, append live stats."""
    # Real self-knowledge (static foundation)
    core_text = _SEED_STRENGTHS

    # Live stats as context (dynamic appendix)
    stats: list[str] = []
    try:
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
            ).fetchone()
            knowledge_count = row[0] if row else 0
            if knowledge_count:
                stats.append(f"{knowledge_count} knowledge entries")

            # Maturity breakdown — reuse same connection
            row_confirmed = conn.execute(
                "SELECT COUNT(*) FROM knowledge "
                "WHERE maturity = 'CONFIRMED' AND superseded_by IS NULL"
            ).fetchone()
            confirmed_count = row_confirmed[0] if row_confirmed else 0
            row_tested = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE maturity = 'TESTED' AND superseded_by IS NULL"
            ).fetchone()
            tested_count = row_tested[0] if row_tested else 0
            if confirmed_count:
                stats.append(f"{confirmed_count} confirmed entries")
            if tested_count:
                stats.append(f"{tested_count} tested entries maturing")
        finally:
            conn.close()
    except (sqlite3.OperationalError, sqlite3.ProgrammingError):
        pass

    try:
        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            stats.append(f"growth {growth['trend']} over {growth['sessions']} sessions")
    except sqlite3.OperationalError:
        pass

    if analysis:
        encouragements = len(getattr(analysis, "encouragements", []))
        if encouragements > 0:
            stats.append(f"{encouragements} encouragement(s) last session")

    new_content = core_text
    if stats:
        new_content += " [Stats: " + ", ".join(stats) + "]"

    current = get_core("known_strengths")
    if current and current.get("known_strengths", "").strip() == new_content.strip():
        return False

    set_core("known_strengths", new_content)
    return True


def _refresh_weaknesses(analysis: Any | None = None) -> bool:
    """Refresh known_weaknesses: preserve real self-knowledge, append lesson status."""
    # Real self-knowledge (static foundation)
    core_text = _SEED_WEAKNESSES

    # Lesson status as context (dynamic appendix)
    stats: list[str] = []
    try:
        active = get_lessons(status="active")
        improving = get_lessons(status="improving")
        if active:
            stats.append(f"{len(active)} active lesson(s)")
        if improving:
            stats.append(f"{len(improving)} improving")
    except sqlite3.OperationalError:
        pass

    if analysis:
        corrections = len(getattr(analysis, "corrections", []))
        if corrections > 0:
            stats.append(f"{corrections} correction(s) last session")

    new_content = core_text
    if stats:
        new_content += " [Lessons: " + ", ".join(stats) + "]"

    current = get_core("known_weaknesses")
    if current and current.get("known_weaknesses", "").strip() == new_content.strip():
        return False

    set_core("known_weaknesses", new_content)
    return True
