"""User ratings — the one metric the system cannot game.

The user rates each session 1-10 after it ends. This is the ground truth
signal that validates (or invalidates) all internal metrics. If the system
gives itself an A but the user rates it 3/10, something is wrong with the
internal metrics, not the user.

Only the user writes to this table. The system reads from it to correlate
internal metrics against external reality.
"""

import sqlite3
import time
from typing import Any

from loguru import logger

from divineos.core.knowledge import _get_connection


def init_ratings_table() -> None:
    """Create the user_ratings table. Idempotent."""
    conn = _get_connection()
    try:
        conn.execute(
            """CREATE TABLE IF NOT EXISTS user_ratings (
                rating_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id    TEXT NOT NULL,
                rating        INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 10),
                comment       TEXT NOT NULL DEFAULT '',
                created_at    REAL NOT NULL
            )"""
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ratings_session ON user_ratings(session_id)")
        conn.commit()
    finally:
        conn.close()


def record_rating(session_id: str, rating: int, comment: str = "") -> int:
    """Record a user rating for a session.

    Args:
        session_id: The session being rated.
        rating: 1-10 score from the user.
        comment: Optional free-text note.

    Returns:
        The rating_id of the new record.
    """
    if not 1 <= rating <= 10:
        raise ValueError(f"Rating must be 1-10, got {rating}")

    init_ratings_table()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO user_ratings (session_id, rating, comment, created_at) "
            "VALUES (?, ?, ?, ?)",
            (session_id, rating, comment, time.time()),
        )
        conn.commit()
        rating_id = cursor.lastrowid or 0
        logger.info(f"User rated session {session_id[:12]}: {rating}/10")
        return rating_id
    finally:
        conn.close()


def get_ratings(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent user ratings, newest first."""
    init_ratings_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT rating_id, session_id, rating, comment, created_at "
            "FROM user_ratings ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "rating_id": r[0],
                "session_id": r[1],
                "rating": r[2],
                "comment": r[3],
                "created_at": r[4],
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_rating_stats() -> dict[str, Any]:
    """Compute rating statistics for the progress dashboard."""
    init_ratings_table()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*), AVG(rating), MIN(rating), MAX(rating) FROM user_ratings"
        ).fetchone()

        count = row[0] or 0
        if count == 0:
            return {
                "count": 0,
                "avg": 0.0,
                "min": 0,
                "max": 0,
                "recent_avg": 0.0,
                "trend": "no_data",
            }

        avg = round(row[1], 1)
        min_r = row[2]
        max_r = row[3]

        # Recent average (last 5)
        recent = conn.execute(
            "SELECT rating FROM user_ratings ORDER BY created_at DESC LIMIT 5"
        ).fetchall()
        recent_ratings = [r[0] for r in recent]
        recent_avg = round(sum(recent_ratings) / len(recent_ratings), 1)

        # Trend: compare first half to second half
        all_ratings = conn.execute(
            "SELECT rating FROM user_ratings ORDER BY created_at ASC"
        ).fetchall()
        all_values = [r[0] for r in all_ratings]

        if len(all_values) < 4:
            trend = "insufficient_data"
        else:
            mid = len(all_values) // 2
            early_avg = sum(all_values[:mid]) / mid
            late_avg = sum(all_values[mid:]) / len(all_values[mid:])
            if late_avg > early_avg + 0.5:
                trend = "improving"
            elif late_avg < early_avg - 0.5:
                trend = "declining"
            else:
                trend = "stable"

        return {
            "count": count,
            "avg": avg,
            "min": min_r,
            "max": max_r,
            "recent_avg": recent_avg,
            "trend": trend,
        }
    finally:
        conn.close()


def correlate_with_internal(limit: int = 20) -> dict[str, Any]:
    """Compare user ratings against internal session metrics.

    This is the Goodhart detector. If internal health scores correlate
    with user ratings, the metrics are tracking reality. If they diverge,
    the metrics are measuring something the user doesn't care about.
    """
    init_ratings_table()
    conn = _get_connection()
    try:
        # Get sessions that have both a user rating and a session grade
        rated = conn.execute(
            "SELECT session_id, rating FROM user_ratings ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()

        if not rated:
            return {"pairs": [], "correlation": "no_data", "divergences": []}

        pairs: list[dict[str, Any]] = []
        divergences: list[dict[str, Any]] = []

        for session_id, user_rating in rated:
            # Look up internal grade for this session
            try:
                grade_row = conn.execute(
                    "SELECT self_score FROM session_validation "
                    "WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
                    (session_id,),
                ).fetchone()
            except sqlite3.OperationalError:
                grade_row = None

            if grade_row and grade_row[0] is not None:
                internal_score = round(float(grade_row[0]) * 10, 1)  # normalize to 1-10
                pair = {
                    "session_id": session_id[:12],
                    "user_rating": user_rating,
                    "internal_score": internal_score,
                    "gap": round(abs(user_rating - internal_score), 1),
                }
                pairs.append(pair)

                # Flag divergences (gap > 3 points on 10-point scale)
                if pair["gap"] > 3:
                    divergences.append(pair)

        if not pairs:
            return {"pairs": [], "correlation": "no_grades", "divergences": []}

        # Simple correlation assessment
        avg_gap = sum(p["gap"] for p in pairs) / len(pairs)
        if avg_gap < 1.5:
            correlation = "strong"
        elif avg_gap < 3.0:
            correlation = "moderate"
        else:
            correlation = "weak"

        return {
            "pairs": pairs,
            "correlation": correlation,
            "avg_gap": round(avg_gap, 1),
            "divergences": divergences,
        }
    finally:
        conn.close()
