"""Personal Journal — The AI's own memory.

Things the AI chooses to remember, not filtered or scored.
Save, list, search, link, and count journal entries.
"""

import time
import uuid
from typing import Any, cast

from divineos.core.memory import _get_connection, init_memory_tables


def journal_save(
    content: str,
    context: str = "",
    tags: str = "",
    linked_knowledge_id: str | None = None,
) -> str:
    """Save a personal journal entry. Returns the entry ID.

    This is the AI's own memory — things it chooses to remember,
    not filtered or scored. If it matters to me, that's enough.
    """
    init_memory_tables()
    entry_id = str(uuid.uuid4())
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO personal_journal (entry_id, content, created_at, context, tags, linked_knowledge_id) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (entry_id, content, time.time(), context, tags, linked_knowledge_id),
        )
        conn.commit()
    finally:
        conn.close()
    return entry_id


def journal_list(limit: int = 20) -> list[dict[str, Any]]:
    """Get personal journal entries, newest first."""
    init_memory_tables()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT entry_id, content, created_at, context, tags, linked_knowledge_id "
            "FROM personal_journal ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "entry_id": r[0],
            "content": r[1],
            "created_at": r[2],
            "context": r[3],
            "tags": r[4] if len(r) > 4 else "",
            "linked_knowledge_id": r[5] if len(r) > 5 else None,
        }
        for r in rows
    ]


def journal_count() -> int:
    """Count personal journal entries."""
    init_memory_tables()
    conn = _get_connection()
    try:
        return cast(int, conn.execute("SELECT COUNT(*) FROM personal_journal").fetchone()[0])
    finally:
        conn.close()


def journal_search(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Full-text search across journal entries using FTS5."""
    init_memory_tables()
    # Quote each term so FTS5 special characters (-, *, etc.) are treated as literals
    safe_query = " ".join(f'"{t}"' for t in query.split() if t)
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT j.entry_id, j.content, j.created_at, j.context, j.tags, j.linked_knowledge_id "
            "FROM journal_fts f "
            "JOIN personal_journal j ON f.rowid = j.rowid "
            "WHERE journal_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (safe_query, limit),
        ).fetchall()
    finally:
        conn.close()
    return [
        {
            "entry_id": r[0],
            "content": r[1],
            "created_at": r[2],
            "context": r[3],
            "tags": r[4] if len(r) > 4 else "",
            "linked_knowledge_id": r[5] if len(r) > 5 else None,
        }
        for r in rows
    ]


def journal_link(entry_id: str, knowledge_id: str) -> bool:
    """Link a journal entry to a knowledge entry. Returns True if updated."""
    init_memory_tables()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "UPDATE personal_journal SET linked_knowledge_id = ? WHERE entry_id = ?",
            (knowledge_id, entry_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
