"""Knowledge CRUD — store, get, search, update, supersede, record_access."""

import json
import sqlite3
import time
import uuid
from typing import Any

from divineos.core.constants import CONFIDENCE_RETRIEVAL_FLOOR
from divineos.core.knowledge._base import (
    _KNOWLEDGE_COLS,
    _KNOWLEDGE_COLS_K,
    KNOWLEDGE_TYPES,
    MEMORY_KINDS,
    _get_connection,
    _row_to_dict,
    compute_hash,
    init_knowledge_table,
)
from divineos.core.knowledge._text import _build_fts_query

_CRUD_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


def store_knowledge(
    knowledge_type: str,
    content: str,
    confidence: float = 1.0,
    source_events: list[str] | None = None,
    tags: list[str] | None = None,
    source: str = "STATED",
    maturity: str = "RAW",
    source_entity: str | None = None,
    related_to: str | None = None,
    memory_kind: str | None = None,
) -> str:
    """Store a piece of knowledge. Returns the knowledge_id.

    Auto-deduplicates: if identical content already exists (and is not superseded),
    increments access_count on the existing entry and returns its id.

    memory_kind is the orthogonal diagnostic dimension
    (EPISODIC / SEMANTIC / PROCEDURAL / UNCLASSIFIED). If None, runs the
    heuristic classifier on content. See memory_kind.classify_kind.
    """
    if knowledge_type not in KNOWLEDGE_TYPES:
        raise ValueError(
            f"Invalid knowledge_type '{knowledge_type}'. Must be one of: {KNOWLEDGE_TYPES}",
        )

    if memory_kind is None:
        from divineos.core.knowledge.memory_kind import classify_kind

        memory_kind = classify_kind(content)
    elif memory_kind not in MEMORY_KINDS:
        raise ValueError(
            f"Invalid memory_kind '{memory_kind}'. Must be one of: {MEMORY_KINDS}",
        )

    content = content.strip()
    if len(content) < 5:
        raise ValueError("Knowledge content too short (minimum 5 characters after stripping)")

    # Voice normalization: knowledge speaks as me, not about me
    from divineos.core.knowledge._text import normalize_to_first_person

    content = normalize_to_first_person(content)

    # Ensure knowledge table exists
    init_knowledge_table()

    content_hash = compute_hash(content)
    sources_json = json.dumps(source_events or [])
    tags_json = json.dumps(tags or [])
    now = time.time()

    conn = _get_connection()
    try:
        # Check for exact duplicate (non-superseded)
        existing = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE content_hash = ? AND superseded_by IS NULL",
            (content_hash,),
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (now, existing[0]),
            )
            conn.commit()
            return str(existing[0])

        knowledge_id = str(uuid.uuid4())
        conn.execute(
            """INSERT INTO knowledge
               (knowledge_id, created_at, updated_at, knowledge_type, content,
                confidence, source_events, tags, access_count, content_hash,
                source, maturity, valid_from, source_entity, related_to, memory_kind)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?, ?)""",
            (
                knowledge_id,
                now,
                now,
                knowledge_type,
                content,
                confidence,
                sources_json,
                tags_json,
                content_hash,
                source,
                maturity,
                now,  # temporal dimension: knowledge is valid from creation
                source_entity,
                related_to,
                memory_kind,
            ),
        )
        conn.commit()
        return knowledge_id
    finally:
        conn.close()


def get_knowledge(
    knowledge_type: str | None = None,
    min_confidence: float = 0.0,
    tags: list[str] | None = None,
    include_superseded: bool = False,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query knowledge with optional filters."""
    conn = _get_connection()
    try:
        query = f"SELECT {_KNOWLEDGE_COLS} FROM knowledge"  # nosec B608
        conditions: list[str] = []
        params: list[Any] = []

        if not include_superseded:
            conditions.append("superseded_by IS NULL")
            conditions.append("content NOT LIKE '[SUPERSEDED]%'")
        if knowledge_type:
            conditions.append("knowledge_type = ?")
            params.append(knowledge_type)
        if min_confidence > 0.0:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY updated_at DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def search_knowledge(query: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search knowledge using FTS5 full-text search with BM25 relevance ranking.

    Falls back to LIKE-based search if FTS5 table doesn't exist yet.
    """
    fts_query = _build_fts_query(query)
    conn = _get_connection()
    try:
        query_str = f"""SELECT {_KNOWLEDGE_COLS_K}
               FROM knowledge_fts fts
               JOIN knowledge k ON k.rowid = fts.rowid
               WHERE knowledge_fts MATCH ?
                 AND k.superseded_by IS NULL
                 AND k.confidence >= {CONFIDENCE_RETRIEVAL_FLOOR}
               ORDER BY bm25(knowledge_fts, 10.0, 5.0, 1.0)
               LIMIT ?"""  # nosec B608
        rows = conn.execute(query_str, (fts_query, limit)).fetchall()
        return [_row_to_dict(row) for row in rows]
    except sqlite3.OperationalError:
        # FTS table doesn't exist yet — fall back to LIKE search
        return _search_knowledge_legacy(query, limit)
    finally:
        conn.close()


def _search_knowledge_legacy(keyword: str, limit: int = 50) -> list[dict[str, Any]]:
    """Legacy LIKE-based search. Used when FTS5 table doesn't exist."""
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE superseded_by IS NULL AND confidence >= {CONFIDENCE_RETRIEVAL_FLOOR} AND (content LIKE ? OR tags LIKE ?) ORDER BY updated_at DESC LIMIT ?",  # nosec B608
            (f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def rebuild_fts_index() -> int:
    """Rebuild the FTS5 index from existing knowledge rows."""
    conn = _get_connection()
    try:
        conn.execute("DELETE FROM knowledge_fts")
        cursor = conn.execute(
            """INSERT INTO knowledge_fts(rowid, content, tags, knowledge_type)
               SELECT rowid, content, tags, knowledge_type FROM knowledge""",
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def update_knowledge(
    knowledge_id: str,
    new_content: str,
    new_confidence: float | None = None,
    additional_sources: list[str] | None = None,
) -> str:
    """Create a new knowledge entry that supersedes an existing one.
    Returns the new knowledge_id.
    """
    conn = _get_connection()
    try:
        old = conn.execute(
            "SELECT knowledge_type, confidence, source_events, tags FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not old:
            raise ValueError(f"Knowledge entry '{knowledge_id}' not found")

        old_type, old_confidence, old_sources_json, old_tags = old
        old_sources = json.loads(old_sources_json)

        confidence = new_confidence if new_confidence is not None else old_confidence
        sources = old_sources + (additional_sources or [])
        content_hash = compute_hash(new_content)
        now = time.time()
        new_id = str(uuid.uuid4())

        conn.execute(
            "INSERT INTO knowledge (knowledge_id, created_at, updated_at, knowledge_type, content, confidence, source_events, tags, access_count, content_hash, valid_from) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)",
            (
                new_id,
                now,
                now,
                old_type,
                new_content,
                confidence,
                json.dumps(sources),
                old_tags,
                content_hash,
                now,  # temporal dimension: valid from creation
            ),
        )
        conn.execute(
            "UPDATE knowledge SET superseded_by = ?, valid_until = ? WHERE knowledge_id = ?",
            (new_id, now, knowledge_id),
        )
        conn.commit()
        return new_id
    finally:
        conn.close()


def supersede_knowledge(knowledge_id: str, reason: str) -> None:
    """Mark a knowledge entry as superseded without creating a replacement."""
    conn = _get_connection()
    try:
        old = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not old:
            raise ValueError(f"Knowledge entry '{knowledge_id}' not found")

        conn.execute(
            "UPDATE knowledge SET superseded_by = ?, valid_until = ?, supersession_reason = ? WHERE knowledge_id = ?",
            (f"FORGET:{reason[:200]}", time.time(), f"forget: {reason[:200]}", knowledge_id),
        )
        conn.commit()
    finally:
        conn.close()

    # Deactivate any logical relations pointing to/from the superseded entry
    try:
        # Late import: crud -> logic_reasoning -> knowledge -> crud cycle
        from divineos.core.logic.logic_reasoning import deactivate_relation, get_relations

        relations = get_relations(knowledge_id, direction="both")
        for rel in relations:
            deactivate_relation(rel.relation_id)
    except _CRUD_ERRORS:
        pass  # relation cleanup is best-effort


def record_access(knowledge_id: str) -> None:
    """Increment access count and corroboration for a knowledge entry.

    Access IS corroboration — if the system keeps surfacing an entry
    because it's relevant, that's evidence of validity. Corroboration
    is throttled: only increments when access_count crosses a multiple
    of 5 (so 5 accesses = 1 corroboration, 10 = 2, etc). This prevents
    inflation from repeated queries in a single session while rewarding
    knowledge that proves useful over time.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT access_count FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not row:
            return

        old_access = row[0]
        new_access = old_access + 1

        # Corroborate every 5th access
        if new_access % 5 == 0:
            conn.execute(
                "UPDATE knowledge SET access_count = ?, corroboration_count = corroboration_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (new_access, time.time(), knowledge_id),
            )
        else:
            conn.execute(
                "UPDATE knowledge SET access_count = ?, updated_at = ? WHERE knowledge_id = ?",
                (new_access, time.time(), knowledge_id),
            )
        conn.commit()
    finally:
        conn.close()


def find_similar(content: str) -> list[dict[str, Any]]:
    """Find non-superseded knowledge with identical content (hash-based)."""
    content_hash = compute_hash(content)
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE content_hash = ? AND superseded_by IS NULL",  # nosec B608
            (content_hash,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()
