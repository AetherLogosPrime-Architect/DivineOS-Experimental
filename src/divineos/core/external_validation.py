"""External Validation — breaking the self-referential loop.

The council diagnosed that DivineOS evaluates itself with no external
anchor. This module provides that anchor: user feedback on session grades,
tracked over time so we can measure whether self-assessment correlates
with reality.

Also surfaces the learned-vs-seeded knowledge ratio — making the gap
between "told" and "learned" visible instead of hidden.
"""

from __future__ import annotations

import sqlite3
import time

from loguru import logger

from divineos.core.knowledge._base import _get_connection

# ─── Schema ─────────────────────────────────────────────────────────


def init_validation_table() -> None:
    """Create the session_validation table for external feedback."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_validation (
                validation_id  TEXT PRIMARY KEY,
                session_id     TEXT NOT NULL,
                created_at     REAL NOT NULL,
                self_grade     TEXT NOT NULL,
                self_score     REAL NOT NULL,
                user_grade     TEXT DEFAULT NULL,
                user_notes     TEXT DEFAULT NULL,
                grade_match    INTEGER DEFAULT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_validation_session
            ON session_validation(session_id)
        """)
        conn.commit()
    except sqlite3.OperationalError as e:
        logger.debug(f"Validation table setup: {e}")
    finally:
        conn.close()


# ─── Record Feedback ─────────────────────────────────────────────────


def record_self_grade(session_id: str, grade: str, score: float) -> str:
    """Record the system's self-assigned grade for later comparison."""
    import uuid

    init_validation_table()
    vid = f"val-{uuid.uuid4().hex[:12]}"
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR REPLACE INTO session_validation "
            "(validation_id, session_id, created_at, self_grade, self_score) "
            "VALUES (?, ?, ?, ?, ?)",
            (vid, session_id, time.time(), grade, score),
        )
        conn.commit()
    finally:
        conn.close()
    return vid


def record_user_feedback(session_id: str, user_grade: str, notes: str = "") -> bool:
    """Record the user's assessment of a session.

    user_grade: A/B/C/D/F or 'agree'/'disagree' (converted to match/no-match).
    Returns True if stored successfully.
    """
    init_validation_table()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT validation_id, self_grade FROM session_validation "
            "WHERE session_id = ? ORDER BY created_at DESC LIMIT 1",
            (session_id,),
        ).fetchone()
        if not row:
            return False

        vid, self_grade = row[0], row[1]

        # Normalize feedback
        if user_grade.lower() in ("agree", "y", "yes", "correct"):
            effective_grade = self_grade
            match = 1
        elif user_grade.lower() in ("disagree", "n", "no", "wrong"):
            effective_grade = "?"
            match = 0
        else:
            effective_grade = user_grade.upper()
            # Same letter = match, one grade apart = close, more = mismatch
            grade_order = "ABCDF"
            self_idx = grade_order.find(self_grade)
            user_idx = grade_order.find(effective_grade)
            match = 1 if self_idx == user_idx else 0

        conn.execute(
            "UPDATE session_validation SET user_grade = ?, user_notes = ?, grade_match = ? "
            "WHERE validation_id = ?",
            (effective_grade, notes, match, vid),
        )
        conn.commit()
        return True
    finally:
        conn.close()


def get_validation_accuracy(n: int = 20) -> dict:
    """Compute how well self-grades match user grades over recent sessions.

    Returns:
        total: number of sessions with user feedback
        matches: number where user agreed
        accuracy: match rate (0.0 to 1.0)
        recent_mismatches: list of (session_id, self_grade, user_grade)
    """
    init_validation_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT session_id, self_grade, user_grade, grade_match "
            "FROM session_validation WHERE user_grade IS NOT NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (n,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {"total": 0, "matches": 0, "accuracy": 0.0, "recent_mismatches": []}

    total = len(rows)
    matches = sum(1 for r in rows if r[3] == 1)
    mismatches = [
        {"session_id": r[0][:12], "self_grade": r[1], "user_grade": r[2]} for r in rows if r[3] == 0
    ]

    return {
        "total": total,
        "matches": matches,
        "accuracy": matches / total if total > 0 else 0.0,
        "recent_mismatches": mismatches[:5],
    }


# ─── Knowledge Origin Ratio ─────────────────────────────────────────


def get_knowledge_origin_ratio() -> dict:
    """Compute the ratio of seeded (INHERITED) vs learned knowledge.

    Returns:
        total: active knowledge entries
        inherited: entries with source=INHERITED
        learned: entries from other sources
        learned_ratio: learned / total (0.0 to 1.0)
        by_source: breakdown by source type
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT source, COUNT(*) FROM knowledge WHERE superseded_by IS NULL GROUP BY source"
        ).fetchall()
    except sqlite3.OperationalError:
        # source column might not exist yet
        return {"total": 0, "inherited": 0, "learned": 0, "learned_ratio": 0.0, "by_source": {}}
    finally:
        conn.close()

    by_source = {}
    for row in rows:
        source = row[0] if row[0] else "INHERITED"
        by_source[source] = row[1]

    total = sum(by_source.values())
    inherited = by_source.get("INHERITED", 0)
    learned = total - inherited

    return {
        "total": total,
        "inherited": inherited,
        "learned": learned,
        "learned_ratio": learned / total if total > 0 else 0.0,
        "by_source": by_source,
    }


def format_origin_summary() -> str:
    """One-line summary of knowledge origin for HUD display."""
    ratio = get_knowledge_origin_ratio()
    if ratio["total"] == 0:
        return "No knowledge stored"

    pct = ratio["learned_ratio"] * 100
    parts = []
    for source, count in sorted(ratio["by_source"].items()):
        if source == "INHERITED":
            parts.append(f"{count} seeded")
        else:
            parts.append(f"{count} {source.lower()}")

    return f"{ratio['learned']}/{ratio['total']} learned ({pct:.0f}%) — {', '.join(parts)}"


def get_validation_divergence(n: int = 20) -> dict:
    """Compare self-grades vs user-grades across sessions where both exist.

    This is the calibration drift detector. If I consistently grade myself
    higher than the user grades me, I'm overconfident in my self-assessment.
    If I grade lower, I'm being too harsh. Either way, the divergence is
    the signal that breaks the self-referential loop.

    Returns:
        total: sessions with both self and user grades
        avg_self_score: average numeric self-score
        overestimates: count where self_grade > user_grade
        underestimates: count where self_grade < user_grade
        accurate: count where grades match
        calibration: "overconfident" | "underconfident" | "calibrated" | "insufficient_data"
    """
    init_validation_table()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT self_grade, self_score, user_grade, grade_match "
            "FROM session_validation WHERE user_grade IS NOT NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (n,),
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return {
            "total": 0,
            "avg_self_score": 0.0,
            "overestimates": 0,
            "underestimates": 0,
            "accurate": 0,
            "calibration": "insufficient_data",
        }

    grade_order = "ABCDF"
    overestimates = 0
    underestimates = 0
    accurate = 0
    total_self_score = 0.0

    for self_grade, self_score, user_grade, grade_match in rows:
        total_self_score += self_score
        self_idx = grade_order.find(self_grade)
        user_idx = grade_order.find(user_grade)
        if self_idx < 0 or user_idx < 0:
            # Unknown grade letter (e.g. "?") — count as mismatch
            if grade_match == 1:
                accurate += 1
            else:
                overestimates += 1
            continue
        if self_idx < user_idx:
            overestimates += 1  # self thinks better than user does
        elif self_idx > user_idx:
            underestimates += 1  # self is harsher than user
        else:
            accurate += 1

    total = len(rows)
    avg_self_score = total_self_score / total if total > 0 else 0.0

    if total < 3:
        calibration = "insufficient_data"
    elif overestimates > total * 0.6:
        calibration = "overconfident"
    elif underestimates > total * 0.6:
        calibration = "underconfident"
    else:
        calibration = "calibrated"

    return {
        "total": total,
        "avg_self_score": round(avg_self_score, 3),
        "overestimates": overestimates,
        "underestimates": underestimates,
        "accurate": accurate,
        "calibration": calibration,
    }


def get_validation_calibration(n: int = 20) -> dict:
    """Compute a quality gate adjustment from validation divergence.

    This closes the feedback loop: user grades -> divergence detection ->
    threshold tightening. If I consistently self-rate higher than the user
    rates me (overconfident), the quality gate gets stricter. If divergence
    data is insufficient, returns neutral.

    Returns:
        adjustment: float (0.0 = neutral, positive = tighten gate)
        reason: str explaining the adjustment
    """
    from divineos.core.constants import QUALITY_VALIDATION_TIGHTEN

    div = get_validation_divergence(n)

    if div["calibration"] == "insufficient_data":
        return {"adjustment": 0.0, "reason": "Insufficient validation data"}

    if div["calibration"] == "overconfident":
        # Overconfident: self-grades higher than user grades.
        # Scale adjustment by how dominant the overestimation is.
        ratio = div["overestimates"] / div["total"] if div["total"] > 0 else 0.0
        adjustment = QUALITY_VALIDATION_TIGHTEN * ratio
        return {
            "adjustment": round(adjustment, 3),
            "reason": (
                f"Overconfident: {div['overestimates']}/{div['total']} sessions "
                f"self-rated higher than user — tightening by +{adjustment:.3f}"
            ),
        }

    if div["calibration"] == "underconfident":
        # Underconfident: being too harsh on myself. No gate tightening needed,
        # but surface the signal so it's visible.
        return {
            "adjustment": 0.0,
            "reason": (
                f"Underconfident: {div['underestimates']}/{div['total']} sessions "
                f"self-rated lower than user — no gate adjustment needed"
            ),
        }

    # Calibrated
    return {"adjustment": 0.0, "reason": "Self-assessment calibrated with user feedback"}


def format_validation_summary() -> str:
    """One-line summary of validation accuracy for HUD display."""
    acc = get_validation_accuracy()
    if acc["total"] == 0:
        return "No user feedback yet"

    pct = acc["accuracy"] * 100
    result = f"Self-grade accuracy: {pct:.0f}% ({acc['matches']}/{acc['total']} match)"
    if acc["recent_mismatches"]:
        last = acc["recent_mismatches"][0]
        result += f" — last miss: self={last['self_grade']}, user={last['user_grade']}"
    return result
