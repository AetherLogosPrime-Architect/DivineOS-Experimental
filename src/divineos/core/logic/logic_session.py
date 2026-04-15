"""Logic session — session-level logic pass and summary/health display.

Merged from session_logic.py and logic_summary.py.

Sections:
1. SESSION_END logic pass (consistency, inference, defeat scanning)
2. Logic health summary and warrant chain display
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from divineos.core.knowledge import get_connection
from divineos.core.logic.logic_reasoning import propagate_from
from divineos.core.logic.logic_validation import (
    check_consistency,
    register_contradiction,
    scan_defeated_only_entries,
)
from divineos.core.logic.warrants import get_warrants

_SL_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


# ═══════════════════════════════════════════════════════════════════════
# Section 1: SESSION_END Logic Pass
# ═══════════════════════════════════════════════════════════════════════
#
# Called once per SESSION_END, after knowledge extraction and maturity cycle.
# Orchestrates the logic layer modules and returns stats for display.


@dataclass
class LogicPassResult:
    """Results from running the logic layer on a session's knowledge."""

    contradictions_found: int = 0
    warrants_created: int = 0
    inferences_made: int = 0
    defeats_triggered: int = 0
    entries_checked: int = 0
    defeated_only_count: int = 0
    lessons_from_defeats: int = 0
    details: list[str] = field(default_factory=list)


def run_session_logic_pass(
    new_knowledge_ids: list[str],
    promoted_ids: list[str] | None = None,
    session_id: str | None = None,
    max_entries: int = 50,
) -> LogicPassResult:
    """Run the logic layer on newly extracted and promoted knowledge.

    Steps:
    1. For each new entry, run consistency check
       - If contradictions found, register them
    2. For each promoted entry, run inference propagation
    3. Scan for defeated-only entries
    """
    result = LogicPassResult()
    ids_to_check = new_knowledge_ids[:max_entries]
    result.entries_checked = len(ids_to_check)

    # Step 1: Consistency checks on new entries
    try:
        for kid in ids_to_check:
            inconsistencies = check_consistency(kid, max_depth=2)
            for inc in inconsistencies:
                if inc.confidence >= 0.5:
                    register_contradiction(
                        inc.entry_a,
                        inc.entry_b,
                        confidence=inc.confidence,
                        notes=f"Detected during session {session_id or 'unknown'}",
                    )
                    result.contradictions_found += 1
                    result.details.append(
                        f"Contradiction: {inc.entry_a[:8]}..{inc.entry_b[:8]}.. ({inc.contradiction_type})"
                    )
    except _SL_ERRORS as e:
        logger.warning(f"Consistency check failed: {e}")

    # Step 2: Inference propagation on promoted entries
    if promoted_ids:
        try:
            for kid in promoted_ids[:max_entries]:
                derivations = propagate_from(kid, source_session=session_id)
                if derivations:
                    result.inferences_made += len(derivations)
                    result.warrants_created += len(derivations)
                    result.details.append(f"Inferred {len(derivations)} from {kid[:8]}.. promotion")
        except _SL_ERRORS as e:
            logger.warning(f"Inference propagation failed: {e}")

    # Step 3: Scan for defeated-only entries
    try:
        defeated = scan_defeated_only_entries(limit=50)
        result.defeated_only_count = len(defeated)
    except _SL_ERRORS as e:
        logger.warning(f"Defeated-only scan failed: {e}")

    return result


def format_logic_summary(result: LogicPassResult) -> str:
    """Format a one-line summary for SESSION_END output."""
    parts: list[str] = []
    if result.contradictions_found:
        parts.append(f"{result.contradictions_found} contradictions")
    if result.inferences_made:
        parts.append(f"{result.inferences_made} inferences")
    if result.defeated_only_count:
        parts.append(f"{result.defeated_only_count} unjustified entries")
    if not parts:
        parts.append(f"{result.entries_checked} entries checked, clean")
    return "Logic: " + ", ".join(parts)


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Logic Health Summary and Warrant Chain Display
# ═══════════════════════════════════════════════════════════════════════
#
# Surfaces the logic layer in the briefing and `ask` command so I can
# see why I believe things, not just what I believe.


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

        # Active contradiction edges — count and fetch details
        # Only count edges where BOTH entries are still active (not superseded).
        # Superseded entries are dead — they can't contradict anything.
        contradictions = 0
        contradiction_details: list[dict[str, str]] = []
        _contra_q = (
            "SELECT e.source_id, e.target_id FROM knowledge_edges e "
            "JOIN knowledge k1 ON e.source_id = k1.knowledge_id "
            "JOIN knowledge k2 ON e.target_id = k2.knowledge_id "
            "WHERE e.edge_type = 'CONTRADICTS' AND e.status = 'ACTIVE' "
            "AND k1.superseded_by IS NULL AND k2.superseded_by IS NULL"
        )
        try:
            edges = conn.execute(_contra_q + " LIMIT 5").fetchall()
            contradictions = len(edges)

            # If we hit the limit, get the real count
            if contradictions >= 5:
                row = conn.execute(
                    f"SELECT COUNT(*) FROM ({_contra_q})"  # nosec B608
                ).fetchone()
                contradictions = row[0] if row else contradictions

            for src, tgt in edges:
                src_row = conn.execute(
                    "SELECT content FROM knowledge WHERE knowledge_id = ?", (src,)
                ).fetchone()
                tgt_row = conn.execute(
                    "SELECT content FROM knowledge WHERE knowledge_id = ?", (tgt,)
                ).fetchone()
                contradiction_details.append(
                    {
                        "a": (src_row[0][:137] + "...")
                        if src_row and len(src_row[0]) > 140
                        else (src_row[0] if src_row else "?"),
                        "b": (tgt_row[0][:137] + "...")
                        if tgt_row and len(tgt_row[0]) > 140
                        else (tgt_row[0] if tgt_row else "?"),
                    }
                )
        except sqlite3.OperationalError:
            pass

        return {
            "total_entries": total,
            "unwarranted": unwarranted,
            "defeated_only": defeated_only,
            "contradictions": contradictions,
            "contradiction_details": contradiction_details,
        }
    finally:
        conn.close()


def format_logic_health_line(stats: dict[str, Any]) -> str:
    """Format logic health summary for the briefing.

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

    summary = ", ".join(parts)

    # Append contradiction details so you can see WHAT contradicts WHAT
    details = stats.get("contradiction_details", [])
    if details:
        for d in details[:3]:
            summary += f"\n    <-> '{d['a']}' vs '{d['b']}'"

    return summary


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
        status_icon = "+" if w["status"] == "ACTIVE" else "x"
        parts.append(f"{w['warrant_type']} {status_icon}")
    return "         warrants: " + " | ".join(parts)
