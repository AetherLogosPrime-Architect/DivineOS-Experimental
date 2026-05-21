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
    confidence: float = 0.5,
    source_events: list[str] | None = None,
    tags: list[str] | None = None,
    source: str = "STATED",
    maturity: str = "RAW",
    source_entity: str | None = None,
    related_to: str | None = None,
    memory_kind: str | None = None,
    allow_resurrect: bool = False,
) -> str:
    """Store a piece of knowledge. Returns the knowledge_id.

    Auto-deduplicates: if identical content already exists (and is not superseded),
    increments access_count on the existing entry and returns its id. On such a
    hit, a caller-provided maturity that is HIGHER than the existing entry's is
    applied (upgrade-only, never downgrade) — Finding W.

    If the identical content was previously SUPERSEDED (and no active copy
    exists), it is NOT resurrected: store_knowledge returns "" rather than
    re-inserting it as fresh. Pass allow_resurrect=True to force re-insertion —
    Finding Y.

    memory_kind is the orthogonal diagnostic dimension
    (EPISODIC / SEMANTIC / PROCEDURAL / UNCLASSIFIED). If None, runs the
    heuristic classifier on content. See memory_kind.classify_kind.

    Default confidence is 0.5 (Aletheia round-ba785844a791 Finding 31,
    family-audit round-335aaeeffc26 default-value-drift class). The
    prior default of 1.0 meant any caller that forgot to pass
    confidence got MAX confidence silently — bias toward over-confident
    knowledge entries that would advance maturity faster than warranted.
    0.5 matches the CLI's --confidence default; both paths now err
    toward needing more evidence before high-confidence claims.
    """
    if knowledge_type not in KNOWLEDGE_TYPES:
        raise ValueError(
            f"Invalid knowledge_type '{knowledge_type}'. Must be one of: {KNOWLEDGE_TYPES}",
        )

    # Source provenance validation — Aletheia Finding 46 (2026-05-14):
    # KNOWLEDGE_SOURCES was documented-as-whitelist but not enforced.
    # Now any source string passed in must be in the canonical set
    # (or empty for "unknown").
    from divineos.core.knowledge._base import validate_source

    validate_source(source)

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
            "SELECT knowledge_id, maturity FROM knowledge WHERE content_hash = ? AND superseded_by IS NULL",
            (content_hash,),
        ).fetchone()

        if existing:
            # Finding W (Aletheia audit 2026-05-20): on a dedup hit, honor a
            # caller-provided maturity UPGRADE (never a downgrade). Previously
            # the caller's maturity was silently ignored, so a verified
            # re-store (e.g. RAW -> CONFIRMED) was lost. Upgrade-only keeps the
            # demote-protection while letting genuine promotion intent land.
            from divineos.core.knowledge.compression import _MATURITY_RANK

            existing_maturity = existing[1] or "RAW"
            if _MATURITY_RANK.get(maturity, 1) > _MATURITY_RANK.get(existing_maturity, 1):
                conn.execute(
                    "UPDATE knowledge SET access_count = access_count + 1, updated_at = ?, "
                    "maturity = ? WHERE knowledge_id = ?",
                    (now, maturity, existing[0]),
                )
            else:
                conn.execute(
                    "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? "
                    "WHERE knowledge_id = ?",
                    (now, existing[0]),
                )
            conn.commit()
            return str(existing[0])

        # Finding Y (Aletheia audit 2026-05-20): guard against resurrecting
        # deliberately-superseded content. If this exact content was superseded
        # (and no active copy exists), re-inserting it as fresh silently undoes
        # the supersession. extraction.py already guards this; the direct API
        # path did not. Default: skip and return "" (mirrors extraction.py).
        # allow_resurrect=True opts into the old insert-anyway behavior.
        if not allow_resurrect:
            superseded = conn.execute(
                "SELECT 1 FROM knowledge WHERE content_hash = ? AND superseded_by IS NOT NULL LIMIT 1",
                (content_hash,),
            ).fetchone()
            if superseded:
                return ""

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
    integration_state: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Query knowledge with optional filters.

    integration_state:
      - None (default): all states — used by ask/recall/search/audit/sleep
      - "active": foreground only — used by briefing/active-memory surfacers
      - "internalized" / "archived": filter to that specific state
    """
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
        if integration_state is not None:
            conditions.append("COALESCE(integration_state, 'active') = ?")
            params.append(integration_state)

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
    additional_tags: list[str] | None = None,
    new_confidence_cap: float | None = None,
) -> str:
    """Create a new knowledge entry that supersedes an existing one.
    Returns the new knowledge_id.

    Args:
        knowledge_id: The old entry to supersede.
        new_content: Replacement content for the new entry.
        new_confidence: Explicit confidence for the new entry. If None,
            inherits the old entry's confidence (optionally capped via
            new_confidence_cap).
        additional_sources: Source events to append to the old entry's list.
        additional_tags: Tags to add to the new entry (union with old tags).
            Useful when the supersession marks a transformation (e.g.
            "sis-translated", "sis-quarantined").
        new_confidence_cap: If set, the new entry's confidence is
            min(inherited_or_new, cap). Used when the transformation
            should reduce confidence (e.g. quarantine drops confidence
            to 0.4 or below).
    """
    conn = _get_connection()
    try:
        # Finding ZZZ (Aletheia audit 2026-05-20): serialize the
        # read-modify-write so two concurrent supersessions of the same
        # entry cannot both create successors and leave superseded_by
        # ambiguous. autocommit + BEGIN IMMEDIATE mirrors the main-ledger
        # fix (ledger.py log_event). The already-superseded guard below is
        # the supersession analog of "read latest chain hash under lock":
        # once locked, we re-verify the entry is still current.
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        old = conn.execute(
            "SELECT knowledge_type, confidence, source_events, tags, superseded_by "
            "FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not old:
            conn.execute("ROLLBACK")
            raise ValueError(f"Knowledge entry '{knowledge_id}' not found")

        old_type, old_confidence, old_sources_json, old_tags_json, old_superseded_by = old
        if old_superseded_by is not None:
            conn.execute("ROLLBACK")
            raise ValueError(
                f"Knowledge entry '{knowledge_id}' is already superseded by "
                f"'{old_superseded_by}' (concurrent supersession detected)"
            )
        old_sources = json.loads(old_sources_json)
        old_tags = json.loads(old_tags_json) if old_tags_json else []

        confidence = new_confidence if new_confidence is not None else old_confidence
        if new_confidence_cap is not None:
            confidence = min(confidence, new_confidence_cap)
        sources = old_sources + (additional_sources or [])

        # Merge tags — additions are appended if not already present.
        merged_tags = list(old_tags)
        for tag in additional_tags or []:
            if tag not in merged_tags:
                merged_tags.append(tag)

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
                json.dumps(merged_tags),
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


def link_supersession(old_id: str, new_id: str, reason: str = "") -> None:
    """Link an old knowledge entry to its actual successor.

    Audit finding 2026-05-03 round 19: callers like
    ``compression.py::compress_dedup`` were using
    ``supersede_knowledge(old_id, best_id)`` — but
    ``supersede_knowledge``'s second parameter is ``reason``, not
    ``successor``. Result: ``superseded_by`` was set to the literal
    string ``"FORGET:1ce6c458-..."`` instead of the successor's
    actual UUID. The supersession chain was broken — readers walking
    ``superseded_by`` got a string that didn't resolve to any
    knowledge_id.

    This helper is the correct path for "we have a survivor, link
    the loser to it." Use it whenever a real successor exists.

    Use ``supersede_knowledge`` only when there's NO replacement
    (entry is being marked as no-longer-active without a survivor).
    """
    if not new_id:
        raise ValueError("link_supersession requires a non-empty successor id")
    conn = _get_connection()
    try:
        old = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE knowledge_id = ?",
            (old_id,),
        ).fetchone()
        if not old:
            raise ValueError(f"Knowledge entry '{old_id}' not found")
        new = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE knowledge_id = ?",
            (new_id,),
        ).fetchone()
        if not new:
            raise ValueError(f"Successor entry '{new_id}' not found")

        conn.execute(
            "UPDATE knowledge SET superseded_by = ?, valid_until = ?, "
            "supersession_reason = ? WHERE knowledge_id = ?",
            (new_id, time.time(), reason[:200] if reason else "", old_id),
        )
        conn.commit()
    finally:
        conn.close()

    try:
        from divineos.core.logic.logic_reasoning import deactivate_relation, get_relations

        relations = get_relations(old_id, direction="both")
        for rel in relations:
            deactivate_relation(rel.relation_id)
    except _CRUD_ERRORS:
        pass


def supersede_knowledge(knowledge_id: str, reason: str) -> None:
    """Mark a knowledge entry as superseded without creating a replacement.

    Use this when there's NO actual successor — the entry is being
    deprecated/forgotten standalone. The ``superseded_by`` field gets
    set to ``"FORGET:<reason>"`` (a non-UUID marker indicating no
    successor exists).

    For "we have a survivor, link the loser to it," use
    :func:`link_supersession` instead.
    """
    conn = _get_connection()
    try:
        # Finding ZZZ (Aletheia audit 2026-05-20): serialize read-modify-write
        # so a blind FORGET marker cannot race a real successor link. The
        # already-superseded guard prevents clobbering an existing
        # superseded_by (which would destroy a valid supersession chain).
        conn.isolation_level = None
        conn.execute("BEGIN IMMEDIATE")
        old = conn.execute(
            "SELECT superseded_by FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not old:
            conn.execute("ROLLBACK")
            raise ValueError(f"Knowledge entry '{knowledge_id}' not found")
        if old[0] is not None:
            conn.execute("ROLLBACK")
            raise ValueError(
                f"Knowledge entry '{knowledge_id}' is already superseded by "
                f"'{old[0]}' — refusing to overwrite with a FORGET marker"
            )

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


def set_integration_state(
    knowledge_id: str,
    state: str,
    *,
    marked_by: str = "user",
    notes: str | None = None,
) -> dict[str, Any]:
    """Mark a knowledge entry's integration state.

    States:
      - active        : currently shaping behavior, surfaces in briefing (default)
      - internalized  : behavior is now consistent; suppress from foreground but keep queryable
      - archived      : retired (no longer applicable, deprecated, or replaced)

    Returns the updated row dict.
    """
    from divineos.core.knowledge._base import INTEGRATION_STATES

    if state not in INTEGRATION_STATES:
        raise ValueError(
            f"Invalid integration_state {state!r}. Must be one of {sorted(INTEGRATION_STATES)}"
        )

    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT knowledge_id, knowledge_type, content, integration_state "
            "FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not row:
            raise ValueError(f"Knowledge entry {knowledge_id!r} not found")

        prior_state = row[3] or "active"
        now = time.time()

        conn.execute(
            "UPDATE knowledge "
            "SET integration_state = ?, integration_marked_at = ?, "
            "    integration_marked_by = ?, integration_notes = ?, updated_at = ? "
            "WHERE knowledge_id = ?",
            (state, now, marked_by, notes, now, knowledge_id),
        )
        conn.commit()
    finally:
        conn.close()

    # Log the state change to the ledger (forensic trail)
    try:
        from divineos.core.ledger import log_event

        log_event(
            "KNOWLEDGE_INTEGRATION_CHANGED",
            actor=marked_by,
            payload={
                "knowledge_id": knowledge_id,
                "knowledge_type": row[1],
                "content_preview": row[2][:120],
                "prior_state": prior_state,
                "new_state": state,
                "marked_by": marked_by,
                "notes": notes,
            },
            validate=False,
        )
    except (sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError, ImportError):
        # Ledger logging is best-effort; the state change itself already committed.
        pass

    return {
        "knowledge_id": knowledge_id,
        "knowledge_type": row[1],
        "content": row[2],
        "prior_state": prior_state,
        "new_state": state,
        "marked_by": marked_by,
        "notes": notes,
        "marked_at": now,
    }


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

    # Trigger maturity promotion check after corroboration
    if new_access % 5 == 0:
        try:
            from divineos.core.knowledge_maintenance import promote_maturity

            promote_maturity(knowledge_id)
        except (ImportError, OSError):
            pass  # Promotion is best-effort


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
