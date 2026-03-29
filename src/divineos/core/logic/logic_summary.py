"""Logic layer visibility — health stats and warrant chain display.

Surfaces the logic layer in the briefing and `ask` command so I can
see why I believe things, not just what I believe.
"""

from __future__ import annotations

import sqlite3
from typing import Any


from divineos.core.knowledge import get_connection
from divineos.core.logic.warrants import get_warrants


def get_logic_health_summary() -> dict[str, Any]:
    """Compute logic layer health stats.

    Returns counts of unwarranted entries, defeated-only entries,
    and active contradictions.
    """
    conn = get_connection()
    try:
        # Total active knowledge entries
        total = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
        ).fetchone()[0]

        # Entries that have at least one warrant (any status)
        warranted_ids = set()
        try:
            rows = conn.execute("SELECT DISTINCT knowledge_id FROM warrants").fetchall()
            warranted_ids = {r[0] for r in rows}
        except sqlite3.OperationalError:
            pass

        # Active entries with warrants
        active_ids = set()
        try:
            rows = conn.execute(
                "SELECT knowledge_id FROM knowledge WHERE superseded_by IS NULL"
            ).fetchall()
            active_ids = {r[0] for r in rows}
        except sqlite3.OperationalError:
            pass

        # Unwarranted = active entries with no warrant at all
        unwarranted = len(active_ids - warranted_ids)

        # Defeated-only = entries where all warrants are DEFEATED/WITHDRAWN
        defeated_only = 0
        for kid in active_ids & warranted_ids:
            warrants = get_warrants(kid)
            if warrants and not any(w.status == "ACTIVE" for w in warrants):
                defeated_only += 1

        # Active contradiction edges
        contradictions = 0
        try:
            # Count unique CONTRADICTS edges across all entries would be expensive,
            # so just count total CONTRADICTS edges in the table
            row = conn.execute(
                "SELECT COUNT(*) FROM knowledge_edges WHERE edge_type = 'CONTRADICTS' AND status = 'ACTIVE'"
            ).fetchone()
            contradictions = row[0] if row else 0
        except sqlite3.OperationalError:
            pass

        return {
            "total_entries": total,
            "unwarranted": unwarranted,
            "defeated_only": defeated_only,
            "contradictions": contradictions,
        }
    finally:
        conn.close()


def format_logic_health_line(stats: dict[str, Any]) -> str:
    """Format a one-line logic health summary for the briefing.

    Returns empty string if everything is clean.
    """
    parts: list[str] = []
    if stats.get("unwarranted"):
        parts.append(f"{stats['unwarranted']} unwarranted")
    if stats.get("defeated_only"):
        parts.append(f"{stats['defeated_only']} lost all justification")
    if stats.get("contradictions"):
        parts.append(f"{stats['contradictions']} contradictions")
    if not parts:
        return ""
    return ", ".join(parts)


def get_warrant_chain(knowledge_id: str) -> list[dict[str, Any]]:
    """Get warrant info for display in `ask` results."""
    warrants = get_warrants(knowledge_id)
    return [
        {
            "warrant_type": w.warrant_type,
            "grounds": w.grounds,
            "status": w.status,
        }
        for w in warrants
    ]


def format_warrant_chain(warrants: list[dict[str, Any]]) -> str:
    """Format warrants for CLI display.

    E.g. "  warrants: EMPIRICAL (active) | TESTIMONIAL (defeated)"
    """
    if not warrants:
        return ""
    parts = []
    for w in warrants:
        status_icon = "✓" if w["status"] == "ACTIVE" else "✗"
        parts.append(f"{w['warrant_type']} {status_icon}")
    return "         warrants: " + " | ".join(parts)
