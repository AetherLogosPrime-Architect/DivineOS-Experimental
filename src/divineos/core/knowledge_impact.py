"""Knowledge Impact Tracking — did retrieved knowledge change behavior?

The council identified that DivineOS has no way to tell whether knowledge
retrieval actually helps. This module tracks the causal chain:

    briefing loads knowledge -> agent acts -> corrections (or not) -> measurable impact

If knowledge about "prefer concise answers" was loaded but the agent got
corrected for verbosity in the same session, that's a measurable failure.
If loaded and NOT corrected, that's weak evidence of impact.
"""

from __future__ import annotations

import sqlite3
import time

from loguru import logger

from divineos.core.knowledge import _get_connection

# ─── Schema ─────────────────────────────────────────────────────────


def init_impact_table() -> None:
    """Create the knowledge_impact table."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_impact (
                impact_id      TEXT PRIMARY KEY,
                session_id     TEXT NOT NULL,
                created_at     REAL NOT NULL,
                knowledge_id   TEXT NOT NULL,
                content_brief  TEXT NOT NULL,
                retrieved_at   TEXT NOT NULL,
                outcome        TEXT DEFAULT NULL,
                correction_overlap INTEGER DEFAULT 0,
                notes          TEXT DEFAULT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_impact_session
            ON knowledge_impact(session_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_impact_knowledge
            ON knowledge_impact(knowledge_id)
        """)
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Impact table setup: {e}")
    finally:
        conn.close()


# ─── Track Retrieval ─────────────────────────────────────────────────


def record_knowledge_retrieval(
    session_id: str,
    knowledge_id: str,
    content_brief: str,
) -> str:
    """Record that a knowledge entry was retrieved during briefing/recall."""
    import uuid

    init_impact_table()
    iid = f"imp-{uuid.uuid4().hex[:12]}"
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO knowledge_impact "
            "(impact_id, session_id, created_at, knowledge_id, content_brief, retrieved_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (iid, session_id, time.time(), knowledge_id, content_brief[:200], "briefing"),
        )
        conn.commit()
    finally:
        conn.close()
    return iid


def assess_session_impact(
    session_id: str,
    corrections: list[str],
) -> dict:
    """At SESSION_END, check if retrieved knowledge overlaps with corrections.

    For each retrieved knowledge entry, check if the session's corrections
    mention similar topics — indicating the knowledge didn't help.

    Returns:
        retrieved: number of entries loaded this session
        correction_overlaps: entries where correction matched loaded knowledge
        clean: entries loaded with no related correction (knowledge may have helped)
        impact_score: clean / retrieved (higher = knowledge had more positive impact)
    """
    init_impact_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT impact_id, knowledge_id, content_brief FROM knowledge_impact "
            "WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"retrieved": 0, "correction_overlaps": 0, "clean": 0, "impact_score": 1.0}

    corrections_text = " ".join(
        c.lower() if isinstance(c, str) else str(c).lower() for c in corrections
    )
    correction_words = set(corrections_text.split())

    overlaps = 0
    stop = {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "i",
        "to",
        "and",
        "of",
        "in",
        "for",
        "it",
        "that",
        "this",
        "with",
        "on",
        "not",
        "be",
    }

    conn = _get_connection()
    try:
        for impact_id, kid, brief in rows:
            brief_words = set(brief.lower().split())
            shared = (brief_words & correction_words) - stop
            has_overlap = len(shared) >= 3

            outcome = "correction_overlap" if has_overlap else "clean"
            conn.execute(
                "UPDATE knowledge_impact SET outcome = ?, correction_overlap = ? "
                "WHERE impact_id = ?",
                (outcome, 1 if has_overlap else 0, impact_id),
            )
            if has_overlap:
                overlaps += 1
        conn.commit()
    finally:
        conn.close()

    total = len(rows)
    clean = total - overlaps
    return {
        "retrieved": total,
        "correction_overlaps": overlaps,
        "clean": clean,
        "impact_score": clean / total if total > 0 else 1.0,
    }


def get_impact_history(n: int = 50) -> dict:
    """Aggregate impact across recent sessions.

    Returns overall effectiveness of knowledge retrieval.
    """
    init_impact_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT outcome, COUNT(*) FROM knowledge_impact "
            "WHERE outcome IS NOT NULL "
            "GROUP BY outcome"
        ).fetchall()
    finally:
        conn.close()

    by_outcome = {r[0]: r[1] for r in rows}
    total = sum(by_outcome.values())
    clean = by_outcome.get("clean", 0)
    overlaps = by_outcome.get("correction_overlap", 0)

    return {
        "total_tracked": total,
        "clean": clean,
        "correction_overlaps": overlaps,
        "effectiveness": clean / total if total > 0 else 1.0,
    }


def format_impact_summary() -> str:
    """One-line summary for HUD display."""
    h = get_impact_history()
    if h["total_tracked"] == 0:
        return "No knowledge impact data yet"

    pct = h["effectiveness"] * 100
    return (
        f"Knowledge effectiveness: {pct:.0f}% "
        f"({h['clean']} clean, {h['correction_overlaps']} overlapped with corrections)"
    )
