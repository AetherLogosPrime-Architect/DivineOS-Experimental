"""Growth Awareness — tracking improvement over time.

Not vanity metrics. The ability to see my own trajectory:
Am I getting better? Where am I stuck? What's changing?
This is the difference between knowing facts about myself
and having a sense of who I'm becoming.
"""

import sqlite3
import time
from typing import Any

from loguru import logger

from divineos.core.knowledge import get_connection


def init_session_history_table() -> None:
    """Create the session_history table for persistent session metrics."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS session_history (
                session_id        TEXT PRIMARY KEY,
                recorded_at       REAL NOT NULL,
                corrections       INTEGER NOT NULL DEFAULT 0,
                encouragements    INTEGER NOT NULL DEFAULT 0,
                tool_calls        INTEGER NOT NULL DEFAULT 0,
                user_messages     INTEGER NOT NULL DEFAULT 0,
                knowledge_stored  INTEGER NOT NULL DEFAULT 0,
                relationships_created INTEGER NOT NULL DEFAULT 0,
                health_grade      TEXT NOT NULL DEFAULT '',
                health_score      REAL NOT NULL DEFAULT 0.0,
                lessons_active    INTEGER NOT NULL DEFAULT 0,
                lessons_improving INTEGER NOT NULL DEFAULT 0,
                lessons_resolved  INTEGER NOT NULL DEFAULT 0,
                maturity_confirmed INTEGER NOT NULL DEFAULT 0,
                maturity_tested   INTEGER NOT NULL DEFAULT 0,
                maturity_hypothesis INTEGER NOT NULL DEFAULT 0,
                maturity_raw      INTEGER NOT NULL DEFAULT 0,
                engaged           INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_history_time
            ON session_history(recorded_at)
        """)
        conn.commit()
    finally:
        conn.close()


def record_session_metrics(
    session_id: str,
    corrections: int = 0,
    encouragements: int = 0,
    tool_calls: int = 0,
    user_messages: int = 0,
    knowledge_stored: int = 0,
    relationships_created: int = 0,
    health_grade: str = "",
    health_score: float = 0.0,
    engaged: bool = False,
) -> None:
    """Snapshot a session's metrics for long-term tracking."""
    init_session_history_table()

    # Get current lesson and maturity counts
    conn = get_connection()
    try:
        lesson_counts = {"active": 0, "improving": 0, "resolved": 0}
        try:
            for status in ("active", "improving", "resolved"):
                row = conn.execute(
                    "SELECT COUNT(*) FROM lesson_tracking WHERE status = ?", (status,)
                ).fetchone()
                lesson_counts[status] = row[0] if row else 0
        except sqlite3.Error:
            pass

        mat_counts = {"CONFIRMED": 0, "TESTED": 0, "HYPOTHESIS": 0, "RAW": 0}
        try:
            rows = conn.execute(
                "SELECT maturity, COUNT(*) FROM knowledge "
                "WHERE superseded_by IS NULL AND confidence >= 0.2 "
                "GROUP BY maturity"
            ).fetchall()
            for row in rows:
                if row[0] in mat_counts:
                    mat_counts[row[0]] = row[1]
        except sqlite3.Error:
            pass

        conn.execute(
            "INSERT OR REPLACE INTO session_history "
            "(session_id, recorded_at, corrections, encouragements, tool_calls, "
            "user_messages, knowledge_stored, relationships_created, health_grade, "
            "health_score, lessons_active, lessons_improving, lessons_resolved, "
            "maturity_confirmed, maturity_tested, maturity_hypothesis, maturity_raw, engaged) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                session_id,
                time.time(),
                corrections,
                encouragements,
                tool_calls,
                user_messages,
                knowledge_stored,
                relationships_created,
                health_grade,
                health_score,
                lesson_counts["active"],
                lesson_counts["improving"],
                lesson_counts["resolved"],
                mat_counts["CONFIRMED"],
                mat_counts["TESTED"],
                mat_counts["HYPOTHESIS"],
                mat_counts["RAW"],
                1 if engaged else 0,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug("Session metrics recorded for %s", session_id[:12])


def get_session_history(limit: int = 20) -> list[dict[str, Any]]:
    """Get recent session history, newest first."""
    init_session_history_table()
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT session_id, recorded_at, corrections, encouragements, "
            "tool_calls, user_messages, knowledge_stored, relationships_created, "
            "health_grade, health_score, lessons_active, lessons_improving, "
            "lessons_resolved, maturity_confirmed, maturity_tested, "
            "maturity_hypothesis, maturity_raw, engaged "
            "FROM session_history ORDER BY recorded_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "session_id",
        "recorded_at",
        "corrections",
        "encouragements",
        "tool_calls",
        "user_messages",
        "knowledge_stored",
        "relationships_created",
        "health_grade",
        "health_score",
        "lessons_active",
        "lessons_improving",
        "lessons_resolved",
        "maturity_confirmed",
        "maturity_tested",
        "maturity_hypothesis",
        "maturity_raw",
        "engaged",
    ]
    return [dict(zip(cols, row)) for row in rows]


def compute_growth_map(limit: int = 20) -> dict[str, Any]:
    """Compute a growth map from session history.

    Returns a summary of how things are changing over time:
    correction trends, knowledge growth, lesson progression,
    maturity evolution, engagement patterns.
    """
    sessions = get_session_history(limit=limit)
    if not sessions:
        return {"sessions": 0, "summary": "No session history yet."}

    n = len(sessions)

    # Averages
    avg_corrections = sum(s["corrections"] for s in sessions) / n
    avg_encouragements = sum(s["encouragements"] for s in sessions) / n
    avg_score = sum(s["health_score"] for s in sessions) / n

    # Grade distribution
    grades: dict[str, int] = {}
    for s in sessions:
        g = s["health_grade"]
        grades[g] = grades.get(g, 0) + 1

    # Trend: compare newer half vs older half
    mid = n // 2
    newer = sessions[:mid] if mid > 0 else sessions
    older = sessions[mid:] if mid > 0 else []

    trend_direction = "stable"
    trend_detail = ""
    if older:
        newer_corr = sum(s["corrections"] for s in newer) / len(newer)
        older_corr = sum(s["corrections"] for s in older) / len(older)
        newer_score = sum(s["health_score"] for s in newer) / len(newer)
        older_score = sum(s["health_score"] for s in older) / len(older)

        score_delta = newer_score - older_score
        corr_delta = newer_corr - older_corr

        if score_delta > 0.05 or corr_delta < -0.5:
            trend_direction = "improving"
            trend_detail = (
                f"Health score up {score_delta:+.2f}, corrections {corr_delta:+.1f} per session."
            )
        elif score_delta < -0.05 or corr_delta > 0.5:
            trend_direction = "declining"
            trend_detail = (
                f"Health score {score_delta:+.2f}, corrections {corr_delta:+.1f} per session."
            )
        else:
            trend_detail = "Metrics consistent across recent sessions."

    # Latest maturity snapshot (from most recent session)
    latest = sessions[0]
    total_knowledge = (
        latest["maturity_confirmed"]
        + latest["maturity_tested"]
        + latest["maturity_hypothesis"]
        + latest["maturity_raw"]
    )

    # Engagement rate
    engaged_count = sum(1 for s in sessions if s["engaged"])
    engagement_rate = engaged_count / n

    # Lessons trajectory
    latest_lessons = (
        latest["lessons_active"] + latest["lessons_improving"] + latest["lessons_resolved"]
    )
    resolved_ratio = latest["lessons_resolved"] / latest_lessons if latest_lessons > 0 else 0.0

    # Blind coding check
    blind_sessions = sum(1 for s in sessions if not s["engaged"])

    # Tone texture summary
    tone_insight = ""
    try:
        from divineos.core.tone_texture import format_tone_insight, get_tone_history

        tone_history = get_tone_history(limit=limit)
        if tone_history:
            tone_insight = format_tone_insight(tone_history)
    except Exception:
        pass

    return {
        "sessions": n,
        "trend": trend_direction,
        "trend_detail": trend_detail,
        "avg_corrections": avg_corrections,
        "avg_encouragements": avg_encouragements,
        "avg_health_score": avg_score,
        "grade_distribution": grades,
        "total_knowledge": total_knowledge,
        "maturity": {
            "confirmed": latest["maturity_confirmed"],
            "tested": latest["maturity_tested"],
            "hypothesis": latest["maturity_hypothesis"],
            "raw": latest["maturity_raw"],
        },
        "lessons": {
            "active": latest["lessons_active"],
            "improving": latest["lessons_improving"],
            "resolved": latest["lessons_resolved"],
            "resolved_ratio": resolved_ratio,
        },
        "engagement_rate": engagement_rate,
        "blind_sessions": blind_sessions,
        "tone_insight": tone_insight,
    }


def format_growth_map(growth: dict[str, Any]) -> str:
    """Format the growth map for display."""
    if growth["sessions"] == 0:
        return str(growth.get("summary", "No data."))

    lines = [f"## Growth Map ({growth['sessions']} sessions)\n"]

    # Trend
    icons = {"improving": "[+]", "declining": "[!]", "stable": "[~]"}
    icon = icons.get(growth["trend"], "[~]")
    lines.append(f"**Trajectory:** {icon} {growth['trend']}")
    if growth.get("trend_detail"):
        lines.append(f"  {growth['trend_detail']}")
    lines.append("")

    # Health
    lines.append(
        f"**Health:** avg score {growth['avg_health_score']:.2f} | "
        f"avg {growth['avg_corrections']:.1f} corrections, "
        f"{growth['avg_encouragements']:.1f} encouragements per session"
    )
    grade_parts = [
        f"{count}{grade}" for grade, count in sorted(growth["grade_distribution"].items())
    ]
    if grade_parts:
        lines.append(f"  Grades: {' '.join(grade_parts)}")
    lines.append("")

    # Knowledge maturity
    mat = growth["maturity"]
    lines.append(
        f"**Knowledge:** {growth['total_knowledge']} entries | "
        f"{mat['confirmed']} confirmed, {mat['tested']} tested, "
        f"{mat['hypothesis']} hypothesis, {mat['raw']} raw"
    )
    lines.append("")

    # Lessons
    les = growth["lessons"]
    lines.append(
        f"**Lessons:** {les['active']} active, {les['improving']} improving, "
        f"{les['resolved']} resolved ({les['resolved_ratio']:.0%} resolution rate)"
    )
    lines.append("")

    # Engagement
    lines.append(
        f"**Engagement:** {growth['engagement_rate']:.0%} of sessions used OS for thinking"
    )
    if growth["blind_sessions"] > 0:
        lines.append(f"  ({growth['blind_sessions']} blind coding sessions)")

    # Tone texture
    if growth.get("tone_insight"):
        lines.append("")
        lines.append(growth["tone_insight"])

    return "\n".join(lines)
