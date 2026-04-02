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
from divineos.core.anticipation import _get_active_warnings
from divineos.core.decision_journal import get_paradigm_shifts
from divineos.core.growth import compute_growth_map
from divineos.core.knowledge import get_connection, get_knowledge, get_lessons
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


def _refresh_strengths(analysis: Any | None = None) -> bool:
    """Rebuild known_strengths from test data, session health, and knowledge."""
    parts: list[str] = []

    # Knowledge count from the store
    try:
        conn = get_connection()
        row = conn.execute("SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL").fetchone()
        knowledge_count = row[0] if row else 0
        conn.close()
        if knowledge_count:
            parts.append(f"Knowledge store: {knowledge_count} active entries.")
    except sqlite3.OperationalError:
        pass

    # Session health trend
    try:
        growth = compute_growth_map(limit=10)
        if growth["sessions"] >= 2:
            parts.append(
                f"Growth trend: {growth['trend']} over {growth['sessions']} sessions "
                f"(avg score {growth['avg_health_score']:.2f})."
            )
    except sqlite3.OperationalError:
        pass

    # Strengths from knowledge (PRINCIPLE type, high confidence)
    try:
        principles = get_knowledge(knowledge_type="PRINCIPLE", limit=100)
        high_conf = [p for p in principles if p.get("confidence", 0) >= 0.8]
        if high_conf:
            parts.append(f"{len(high_conf)} confirmed principles in knowledge store.")
    except sqlite3.OperationalError:
        pass

    # Current session performance
    if analysis:
        encouragements = len(getattr(analysis, "encouragements", []))
        if encouragements > 0:
            parts.append(f"Last session: {encouragements} encouragement(s) received.")

    if not parts:
        return False

    new_content = " ".join(parts)

    current = get_core("known_strengths")
    if current and current.get("known_strengths", "").strip() == new_content.strip():
        return False

    set_core("known_strengths", new_content)
    return True


def _refresh_weaknesses(analysis: Any | None = None) -> bool:
    """Rebuild known_weaknesses from corrections, active lessons, and patterns."""
    parts: list[str] = []

    # Active lessons (things I'm still working on)
    try:
        active = get_lessons(status="active")
        improving = get_lessons(status="improving")
        if active:
            parts.append(f"{len(active)} active lesson(s) being worked on.")
            for lesson in active[:3]:
                desc = lesson.get("description", "")[:100]
                parts.append(f"- {desc}")
        if improving:
            parts.append(f"{len(improving)} lesson(s) improving.")
    except sqlite3.OperationalError:
        pass

    # Recent corrections from this session
    if analysis:
        corrections = len(getattr(analysis, "corrections", []))
        if corrections > 0:
            parts.append(f"Last session: {corrections} correction(s) to learn from.")

    # Anticipation warnings (recurring issues)
    try:
        warnings = _get_active_warnings()
        if warnings:
            parts.append(f"{len(warnings)} active pattern warning(s) to watch for.")
    except (sqlite3.OperationalError, json.JSONDecodeError):
        pass

    if not parts:
        return False

    new_content = "\n".join(parts)

    current = get_core("known_weaknesses")
    if current and current.get("known_weaknesses", "").strip() == new_content.strip():
        return False

    set_core("known_weaknesses", new_content)
    return True
