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
from divineos.core.tone_texture import format_tone_insight, get_tone_history

_GROWTH_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)


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


def _gather_recent_lessons(limit: int = 5) -> list[dict[str, Any]]:
    """Return recent lesson_tracking entries with status + occurrences."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT description, status, occurrences, last_seen, "
            "positive_evidence_sessions "
            "FROM lesson_tracking "
            "WHERE status IN ('active', 'improving', 'resolved') "
            "ORDER BY last_seen DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {
                "text": r[0],
                "status": r[1],
                "occurrences": r[2],
                "last_seen": r[3],
                "positive_evidence": r[4],
            }
            for r in rows
        ]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _gather_recent_instructions(limit: int = 5) -> list[dict[str, Any]]:
    """Return recent INSTRUCTION-typed knowledge entries."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT content, created_at FROM knowledge "
            "WHERE knowledge_type = 'INSTRUCTION' AND superseded_by IS NULL "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [{"content": r[0], "created_at": r[1]} for r in rows]
    except sqlite3.Error:
        return []
    finally:
        conn.close()


def _gather_correction_summary() -> dict[str, Any]:
    """Count corrections logged in the corrections JSONL file and surface
    the most recent text if available. The corrections store is a flat
    JSONL — see ``divineos.core.corrections`` for the design rationale."""
    try:
        from divineos.core.corrections import load_corrections

        entries = load_corrections() or []
        total = len(entries)
        recent_text = ""
        if entries:
            recent_text = (entries[-1].get("text") or "")[:200]
        return {"total": total, "recent_text": recent_text}
    except Exception:  # noqa: BLE001 — corrections is optional surface
        return {"total": 0, "recent_text": ""}


def compute_growth_map(limit: int = 20) -> dict[str, Any]:
    """Compute a growth map from session history.

    Updated 2026-05-05 (Andrew's spec): the prior version graded sessions
    on a trajectory ("declining"/"improving") derived from health-score
    deltas. That was judgment-shaped, not information-shaped. The
    rewrite removes the trajectory-as-grade and replaces it with
    informational content: mistakes made and corrected, lessons in
    progress, instructions accumulated, repeated patterns. The point
    is self-correction, not self-judgment.

    Backward-compat: keeps all prior dict keys (``trend``, ``trend_detail``,
    ``avg_health_score``, ``grade_distribution``) so existing callers
    (hud, core_memory_refresh) keep working. New keys add the
    informational content the formatter now displays.
    """
    sessions = get_session_history(limit=limit)
    if not sessions:
        return {"sessions": 0, "summary": "No session history yet."}

    n = len(sessions)

    # Aggregate metrics — kept for backward-compat dict consumers.
    avg_corrections = sum(s["corrections"] for s in sessions) / n
    avg_encouragements = sum(s["encouragements"] for s in sessions) / n
    avg_score = sum(s["health_score"] for s in sessions) / n
    total_corrections = sum(s["corrections"] for s in sessions)
    total_encouragements = sum(s["encouragements"] for s in sessions)

    grades: dict[str, int] = {}
    for s in sessions:
        g = s["health_grade"]
        grades[g] = grades.get(g, 0) + 1

    # Trajectory removed as a judgment. The dict still exposes "trend"
    # for backward compat with callers, but it is now always "neutral".
    trend_direction = "neutral"
    trend_detail = ""
    if n >= 2:
        first_corr = sessions[-1]["corrections"]
        last_corr = sessions[0]["corrections"]
        delta = last_corr - first_corr
        if delta > 0:
            trend_detail = (
                f"Most recent session had {delta:+d} more corrections than the "
                "oldest in this window. Information for review, not a grade."
            )
        elif delta < 0:
            trend_detail = (
                f"Most recent session had {abs(delta)} fewer corrections than "
                "the oldest in this window. Information for review, not a grade."
            )
        else:
            trend_detail = "Correction count even across this window."

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
        tone_history = get_tone_history(limit=limit)
        if tone_history:
            tone_insight = format_tone_insight(tone_history)
    except _GROWTH_ERRORS:
        pass

    return {
        "sessions": n,
        # Backward-compat keys (consumed by hud and core_memory_refresh).
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
        # New informational keys (consumed by the rewritten formatter).
        "totals": {
            "corrections": total_corrections,
            "encouragements": total_encouragements,
        },
        "recent_lessons": _gather_recent_lessons(limit=5),
        "recent_instructions": _gather_recent_instructions(limit=5),
        "correction_summary": _gather_correction_summary(),
    }


def format_growth_map(growth: dict[str, Any]) -> str:
    """Format the growth map as information for self-correction.

    Updated 2026-05-05 (Andrew's spec): no grade letters, no
    trajectory-as-judgment ("declining"/"improving"). Surfaces what
    actually moved across the window — corrections received, lessons
    in progress, instructions integrated, knowledge accumulated. Read
    it to inform next moves; not as a score.
    """
    if growth["sessions"] == 0:
        return str(growth.get("summary", "No data."))

    n = growth["sessions"]
    lines = [
        f"## Growth Map — {n} session(s) of self-information",
        "",
        "*This is data for self-correction, not a grade. Read what moved;",
        "decide what to do next.*",
        "",
    ]

    # What happened in this window
    totals = growth.get("totals", {})
    lines.append("### What happened across this window")
    lines.append(
        f"  Corrections received: {totals.get('corrections', 0)} "
        f"(avg {growth['avg_corrections']:.1f}/session)"
    )
    lines.append(
        f"  Encouragements received: {totals.get('encouragements', 0)} "
        f"(avg {growth['avg_encouragements']:.1f}/session)"
    )
    if growth.get("trend_detail"):
        lines.append(f"  Note: {growth['trend_detail']}")
    lines.append("")

    # Lessons in progress — the most direct self-correction signal
    recent_lessons = growth.get("recent_lessons", [])
    if recent_lessons:
        lines.append("### Lessons in progress (recent)")
        for lesson in recent_lessons:
            text = (lesson.get("text") or "").replace("\n", " ")[:80]
            occurrences = lesson.get("occurrences", 0)
            # positive_evidence is stored as a JSON dict of session_id -> note;
            # the count is what's load-bearing here.
            pe = lesson.get("positive_evidence", 0)
            if isinstance(pe, str):
                try:
                    import json as _json

                    pe_dict = _json.loads(pe) if pe else {}
                    pe_count = len(pe_dict) if isinstance(pe_dict, dict) else 0
                except (ValueError, TypeError):
                    pe_count = 0
            elif isinstance(pe, dict):
                pe_count = len(pe)
            elif isinstance(pe, int):
                pe_count = pe
            else:
                pe_count = 0
            status = lesson.get("status", "active")
            shape = (
                f"{occurrences}x recurrence, {pe_count}x corrected" if occurrences else "tracked"
            )
            lines.append(f"  [{status}] {text}")
            lines.append(f"      ({shape})")
        lines.append("")

    # Instructions accumulated
    recent_instructions = growth.get("recent_instructions", [])
    if recent_instructions:
        lines.append("### Recent instructions integrated")
        for instr in recent_instructions:
            text = (instr.get("content") or "").replace("\n", " ")[:80]
            lines.append(f"  - {text}")
        lines.append("")

    # Correction store
    corr_summary = growth.get("correction_summary", {})
    if corr_summary.get("total", 0) > 0:
        lines.append("### Corrections logged in store")
        lines.append(f"  Total: {corr_summary['total']}")
        if corr_summary.get("recent_text"):
            recent = corr_summary["recent_text"].replace("\n", " ")[:120]
            lines.append(f"  Most recent: {recent}")
        lines.append("")

    # Knowledge accumulated (informational)
    mat = growth["maturity"]
    lines.append("### Knowledge accumulated")
    lines.append(
        f"  {growth['total_knowledge']} active entries — "
        f"{mat['confirmed']} confirmed, {mat['tested']} tested, "
        f"{mat['hypothesis']} hypothesis, {mat['raw']} raw"
    )
    les = growth["lessons"]
    lines.append(
        f"  {les['active']} active lessons, {les['improving']} improving, "
        f"{les['resolved']} resolved"
    )
    lines.append("")

    # Engagement
    eng = growth["engagement_rate"]
    lines.append(f"### Engagement: {eng:.0%} of sessions used OS for thinking")
    if growth["blind_sessions"] > 0:
        lines.append(
            f"  {growth['blind_sessions']} session(s) coded without consulting "
            "the substrate (worth noticing)"
        )
    lines.append("")

    # Tone insight (already informational)
    if growth.get("tone_insight"):
        lines.append("### Tone arc")
        lines.append(f"  {growth['tone_insight']}")

    return "\n".join(lines)
