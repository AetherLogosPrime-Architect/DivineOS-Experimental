"""Advice Tracking — long-term feedback loops on recommendation quality.

When I give advice or make a recommendation, I should track whether it
actually worked. Did the pattern I suggested lead to fewer corrections?
Did the refactoring approach reduce rework? Was the architecture choice
validated by subsequent sessions?

This closes the loop: advice -> outcome -> learning. Without it, I can
give the same bad advice forever and never know.

Sanskrit anchor: phala-jnana (fruit-knowledge, knowing the result of actions).
"""

import sqlite3
import time
import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger

from divineos.core.constants import SECONDS_PER_DAY
from divineos.core.knowledge._base import _get_connection

_AT_ERRORS = (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Outcome states
OUTCOME_STATES = {"pending", "successful", "partially_successful", "failed", "inconclusive"}


@dataclass
class Advice:
    """A piece of advice given during a session."""

    advice_id: str
    content: str  # what was advised
    context: str  # what situation prompted it
    session_id: str  # when it was given
    category: str  # architecture/pattern/process/debugging
    outcome: str  # pending/successful/partially_successful/failed/inconclusive
    outcome_evidence: str  # what happened
    given_at: float
    assessed_at: float | None
    confidence_at_time: float  # how confident I was when giving it


# ─── Schema ─────────────────────────────────────────────────────────


def init_advice_table() -> None:
    """Create advice tracking tables."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS advice_tracking (
                advice_id          TEXT PRIMARY KEY,
                content            TEXT NOT NULL,
                context            TEXT NOT NULL DEFAULT '',
                session_id         TEXT NOT NULL DEFAULT '',
                category           TEXT NOT NULL DEFAULT 'general',
                outcome            TEXT NOT NULL DEFAULT 'pending',
                outcome_evidence   TEXT NOT NULL DEFAULT '',
                given_at           REAL NOT NULL,
                assessed_at        REAL DEFAULT NULL,
                confidence_at_time REAL NOT NULL DEFAULT 0.7
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_advice_outcome
            ON advice_tracking(outcome)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_advice_session
            ON advice_tracking(session_id)
        """)
        conn.commit()
    finally:
        conn.close()


# ─── CRUD ────────────────────────────────────────────────────────────


def record_advice(
    content: str,
    context: str = "",
    session_id: str = "",
    category: str = "general",
    confidence: float = 0.7,
) -> str:
    """Record a piece of advice given. Returns advice_id."""
    init_advice_table()
    advice_id = f"adv-{uuid.uuid4().hex[:12]}"
    now = time.time()
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO advice_tracking "
            "(advice_id, content, context, session_id, category, "
            "outcome, outcome_evidence, given_at, confidence_at_time) "
            "VALUES (?, ?, ?, ?, ?, 'pending', '', ?, ?)",
            (advice_id, content, context, session_id, category, now, confidence),
        )
        conn.commit()
        return advice_id
    finally:
        conn.close()


def assess_advice(
    advice_id: str,
    outcome: str,
    evidence: str = "",
) -> bool:
    """Record the outcome of a piece of advice.

    Returns True if the assessment was recorded, False if advice_id not found.
    """
    if outcome not in OUTCOME_STATES:
        logger.warning(f"Unknown outcome state: {outcome}")
        return False

    init_advice_table()
    now = time.time()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT advice_id FROM advice_tracking WHERE advice_id = ?",
            (advice_id,),
        ).fetchone()
        if not row:
            return False
        conn.execute(
            "UPDATE advice_tracking SET outcome = ?, outcome_evidence = ?, "
            "assessed_at = ? WHERE advice_id = ?",
            (outcome, evidence, now, advice_id),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_pending_advice(limit: int = 20) -> list[dict[str, Any]]:
    """Get advice that hasn't been assessed yet."""
    init_advice_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM advice_tracking WHERE outcome = 'pending' "
            "ORDER BY given_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_advice_stats() -> dict[str, Any]:
    """Get aggregate statistics on advice quality."""
    init_advice_table()
    conn = _get_connection()
    try:
        total = conn.execute("SELECT COUNT(*) FROM advice_tracking").fetchone()[0]
        assessed = conn.execute(
            "SELECT COUNT(*) FROM advice_tracking WHERE outcome != 'pending'"
        ).fetchone()[0]
        successful = conn.execute(
            "SELECT COUNT(*) FROM advice_tracking WHERE outcome = 'successful'"
        ).fetchone()[0]
        partial = conn.execute(
            "SELECT COUNT(*) FROM advice_tracking WHERE outcome = 'partially_successful'"
        ).fetchone()[0]
        failed = conn.execute(
            "SELECT COUNT(*) FROM advice_tracking WHERE outcome = 'failed'"
        ).fetchone()[0]

        success_rate = 0.0
        if assessed > 0:
            # Partial success counts as 0.5
            success_rate = (successful + partial * 0.5) / assessed

        # Category breakdown
        categories: dict[str, dict[str, int]] = {}
        rows = conn.execute(
            "SELECT category, outcome, COUNT(*) FROM advice_tracking "
            "WHERE outcome != 'pending' GROUP BY category, outcome"
        ).fetchall()
        for row in rows:
            cat, out, count = row
            if cat not in categories:
                categories[cat] = {}
            categories[cat][out] = count

        return {
            "total": total,
            "assessed": assessed,
            "pending": total - assessed,
            "successful": successful,
            "partially_successful": partial,
            "failed": failed,
            "success_rate": round(success_rate, 3),
            "by_category": categories,
        }
    finally:
        conn.close()


def get_assessed_advice(limit: int = 20) -> list[dict[str, Any]]:
    """Get advice that has been assessed (not pending)."""
    init_advice_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM advice_tracking WHERE outcome != 'pending' "
            "ORDER BY assessed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_stale_advice(days: int = 7) -> list[dict[str, Any]]:
    """Get pending advice older than N days — needs assessment."""
    init_advice_table()
    cutoff = time.time() - (days * SECONDS_PER_DAY)
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM advice_tracking WHERE outcome = 'pending' "
            "AND given_at < ? ORDER BY given_at ASC",
            (cutoff,),
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


# ─── Row Helper ──────────────────────────────────────────────────────


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert advice_tracking row to dict."""
    return {
        "advice_id": row[0],
        "content": row[1],
        "context": row[2],
        "session_id": row[3],
        "category": row[4],
        "outcome": row[5],
        "outcome_evidence": row[6],
        "given_at": row[7],
        "assessed_at": row[8],
        "confidence_at_time": row[9],
    }


# ─── Formatting ──────────────────────────────────────────────────────


def format_advice_stats(stats: dict[str, Any] | None = None) -> str:
    """Format advice statistics for display."""
    if stats is None:
        stats = get_advice_stats()

    if stats["total"] == 0:
        return "No advice tracked yet."

    lines = ["### Advice Quality"]
    lines.append(f"  Total: {stats['total']} | Assessed: {stats['assessed']}")
    lines.append(f"  Success rate: {stats['success_rate']:.0%}")
    lines.append(
        f"  Outcomes: {stats['successful']} good, "
        f"{stats['partially_successful']} partial, "
        f"{stats['failed']} failed"
    )
    if stats["pending"] > 0:
        lines.append(f"  Pending assessment: {stats['pending']}")

    if stats["by_category"]:
        lines.append("  By category:")
        for cat, outcomes in stats["by_category"].items():
            total_cat = sum(outcomes.values())
            good = outcomes.get("successful", 0) + outcomes.get("partially_successful", 0) * 0.5
            lines.append(f"    {cat}: {good:.0f}/{total_cat} successful")

    return "\n".join(lines)
