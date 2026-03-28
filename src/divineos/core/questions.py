"""Open questions — track uncertainty and remember what I don't know yet.

An open question is something I noticed I was uncertain about during work.
Questions persist across sessions so I remember what to investigate.
They can be answered when new knowledge arrives, or explicitly via CLI.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from loguru import logger

from divineos.core.knowledge import get_connection


QUESTION_STATUSES = {"OPEN", "ANSWERED", "ABANDONED"}


def init_questions_table() -> None:
    """Create the open_questions table. Idempotent."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS open_questions (
                question_id  TEXT PRIMARY KEY,
                question     TEXT NOT NULL,
                context      TEXT NOT NULL DEFAULT '',
                created_at   REAL NOT NULL,
                status       TEXT NOT NULL DEFAULT 'OPEN',
                resolution   TEXT DEFAULT NULL,
                resolved_at  REAL DEFAULT NULL,
                session_id   TEXT DEFAULT NULL,
                tags         TEXT NOT NULL DEFAULT '[]'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_questions_status
            ON open_questions(status)
        """)
        conn.commit()
    finally:
        conn.close()


def add_question(
    question: str,
    context: str = "",
    session_id: str | None = None,
    tags: list[str] | None = None,
) -> str:
    """Record an open question. Returns question_id."""
    qid = str(uuid.uuid4())
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO open_questions "
            "(question_id, question, context, created_at, status, session_id, tags) "
            "VALUES (?, ?, ?, ?, 'OPEN', ?, ?)",
            (qid, question, context, time.time(), session_id, json.dumps(tags or [])),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug("Added open question {}: {}", qid[:8], question[:60])
    return qid


def get_questions(
    status: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get questions, optionally filtered by status."""
    conn = get_connection()
    try:
        if status:
            rows = conn.execute(
                "SELECT question_id, question, context, created_at, status, "
                "resolution, resolved_at, session_id, tags "
                "FROM open_questions WHERE status = ? ORDER BY created_at DESC LIMIT ?",
                (status, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT question_id, question, context, created_at, status, "
                "resolution, resolved_at, session_id, tags "
                "FROM open_questions ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
    finally:
        conn.close()

    return [_row_to_dict(r) for r in rows]


def answer_question(question_id: str, resolution: str) -> bool:
    """Mark a question as ANSWERED with a resolution."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE open_questions SET status = 'ANSWERED', resolution = ?, resolved_at = ? "
            "WHERE question_id = ?",
            (resolution, time.time(), question_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def abandon_question(question_id: str, reason: str = "") -> bool:
    """Mark a question as ABANDONED."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE open_questions SET status = 'ABANDONED', resolution = ?, resolved_at = ? "
            "WHERE question_id = ?",
            (reason or "abandoned", time.time(), question_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def check_auto_answers(
    new_content: str,
    new_knowledge_id: str,
    threshold: float = 0.4,
) -> list[dict[str, Any]]:
    """Check if new knowledge content might answer any OPEN questions.

    Uses word overlap to find candidates. Does NOT auto-answer —
    just flags candidates for the pipeline to surface.
    """
    from divineos.core.knowledge._text import _compute_overlap

    open_qs = get_questions(status="OPEN", limit=50)
    candidates: list[dict[str, Any]] = []

    for q in open_qs:
        overlap = _compute_overlap(new_content, q["question"])
        if overlap >= threshold:
            candidates.append(
                {
                    "question_id": q["question_id"],
                    "question": q["question"],
                    "overlap": overlap,
                    "knowledge_id": new_knowledge_id,
                }
            )

    return sorted(candidates, key=lambda c: c["overlap"], reverse=True)


def get_open_questions_summary(max_items: int = 5) -> str:
    """Format open questions for briefing inclusion.

    Returns empty string if no open questions.
    """
    open_qs = get_questions(status="OPEN", limit=max_items + 1)
    if not open_qs:
        return ""

    lines = [f"### OPEN QUESTIONS ({len(open_qs)})"]
    for q in open_qs[:max_items]:
        display = q["question"].replace("\n", " ")
        if len(display) > 120:
            display = display[:117] + "..."
        lines.append(f"- {display}")
    if len(open_qs) > max_items:
        lines.append("  ...and more")
    return "\n".join(lines)


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    return {
        "question_id": row[0],
        "question": row[1],
        "context": row[2],
        "created_at": row[3],
        "status": row[4],
        "resolution": row[5],
        "resolved_at": row[6],
        "session_id": row[7],
        "tags": json.loads(row[8]) if row[8] else [],
    }
