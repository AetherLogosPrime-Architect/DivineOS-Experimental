"""Memory Consolidation — Knowledge Store.

Raw events are noisy. Consolidation extracts structured knowledge:
facts learned, preferences discovered, patterns identified, mistakes made.

The AI extracts knowledge. This code stores and retrieves it.
Rules: 1) Append-only (supersede, never delete). 2) Link back to source events.

Section Map
-----------
Line ~56   | Core: DB connection, schema init, compute_hash
Line ~188  | CRUD: store, get, search, update, supersede, record_access
Line ~444  | Retrieval: unconsolidated events, find_similar, generate_briefing, stats
Line ~690  | Lessons: record, query, mark_improving, summary, check_recurring
Line ~865  | Report extraction: extract_lessons_from_report
Line ~1003 | Row helpers: _lesson_row_to_dict, _row_to_dict
Line ~1309 | Text analysis: normalize, key terms, overlap, extract_session_topics
Line ~1355 | Smart storage: store_knowledge_smart (dedup via hash + FTS5)
Line ~1509 | Deep extraction: corrections, preferences, decisions from sessions
Line ~1819 | Consolidation: cluster & merge related knowledge entries
Line ~1917 | Feedback: confidence adjustment, effectiveness, health_check
Line ~2113 | Migration: reclassify legacy knowledge types
Line ~2284 | Categorization: correction buckets, noise filter, apply_session_feedback
Line ~2411 | Health report: aggregate effectiveness stats
"""

import json
import re
import sqlite3
import time
import uuid
from collections import Counter
from pathlib import Path
from typing import Any, cast

from loguru import logger

import divineos.core.ledger as _ledger_mod

KNOWLEDGE_TYPES = {
    # Core types
    "FACT",
    "PROCEDURE",
    "PRINCIPLE",
    "BOUNDARY",
    "DIRECTION",
    "OBSERVATION",
    "EPISODE",
    # Sutra-style chained directives — high confidence, surface first in briefings
    "DIRECTIVE",
    # Legacy types (still accepted, new code should not create these)
    "PATTERN",
    "PREFERENCE",
    "MISTAKE",
}

KNOWLEDGE_SOURCES = {"STATED", "CORRECTED", "DEMONSTRATED", "SYNTHESIZED", "INHERITED"}

KNOWLEDGE_MATURITY = {"RAW", "HYPOTHESIS", "TESTED", "CONFIRMED", "REVISED"}


_KNOWLEDGE_COLS = (
    "knowledge_id, created_at, updated_at, knowledge_type, content, "
    "confidence, source_events, tags, access_count, superseded_by, content_hash, "
    "source, maturity, corroboration_count, contradiction_count"
)

_KNOWLEDGE_COLS_K = (
    "k.knowledge_id, k.created_at, k.updated_at, k.knowledge_type, k.content, "
    "k.confidence, k.source_events, k.tags, k.access_count, k.superseded_by, k.content_hash, "
    "k.source, k.maturity, k.corroboration_count, k.contradiction_count"
)


def compute_hash(content: str) -> str:
    """Delegate to ledger's hash function."""
    return _ledger_mod.compute_hash(content)


def _get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database."""
    import os

    # Check environment variable each time to support test isolation
    db_path_str = os.environ.get("DIVINEOS_DB")
    if db_path_str:
        db_path: Path = Path(db_path_str)
    else:
        db_path = _ledger_mod.DB_PATH

    db_path.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_knowledge_table() -> None:
    """Creates the knowledge table, FTS5 index, and lesson tracking table."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                knowledge_id   TEXT PRIMARY KEY,
                created_at     REAL NOT NULL,
                updated_at     REAL NOT NULL,
                knowledge_type TEXT NOT NULL,
                content        TEXT NOT NULL,
                confidence     REAL NOT NULL DEFAULT 1.0,
                source_events  TEXT NOT NULL DEFAULT '[]',
                tags           TEXT NOT NULL DEFAULT '[]',
                access_count   INTEGER NOT NULL DEFAULT 0,
                superseded_by  TEXT DEFAULT NULL,
                content_hash   TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_type
            ON knowledge(knowledge_type)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_updated
            ON knowledge(updated_at)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_knowledge_hash
            ON knowledge(content_hash)
        """)

        # FTS5 full-text search index on knowledge
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS knowledge_fts USING fts5(
                content, tags, knowledge_type,
                content='knowledge', content_rowid='rowid',
                tokenize='porter unicode61'
            )
        """)

        # Triggers to keep FTS index in sync with knowledge table
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS knowledge_fts_insert
            AFTER INSERT ON knowledge BEGIN
                INSERT INTO knowledge_fts(rowid, content, tags, knowledge_type)
                VALUES (new.rowid, new.content, new.tags, new.knowledge_type);
            END
        """)
        conn.execute("""
            CREATE TRIGGER IF NOT EXISTS knowledge_fts_update
            AFTER UPDATE ON knowledge BEGIN
                INSERT INTO knowledge_fts(knowledge_fts, rowid, content, tags, knowledge_type)
                VALUES ('delete', old.rowid, old.content, old.tags, old.knowledge_type);
                INSERT INTO knowledge_fts(rowid, content, tags, knowledge_type)
                VALUES (new.rowid, new.content, new.tags, new.knowledge_type);
            END
        """)

        # Add new metadata columns (safe to run on existing databases)
        for col, col_type, default in [
            ("source", "TEXT", "'INHERITED'"),
            ("maturity", "TEXT", "'RAW'"),
            ("corroboration_count", "INTEGER", "0"),
            ("contradiction_count", "INTEGER", "0"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE knowledge ADD COLUMN {col} {col_type} NOT NULL DEFAULT {default}",
                )
            except sqlite3.OperationalError as e:
                logger.debug(f"Column {col} already exists in knowledge table: {e}")

        # Lesson tracking table — connects repeated mistakes across sessions
        conn.execute("""
            CREATE TABLE IF NOT EXISTS lesson_tracking (
                lesson_id     TEXT PRIMARY KEY,
                created_at    REAL NOT NULL,
                category      TEXT NOT NULL,
                description   TEXT NOT NULL,
                first_session TEXT NOT NULL,
                occurrences   INTEGER NOT NULL DEFAULT 1,
                last_seen     REAL NOT NULL,
                sessions      TEXT NOT NULL DEFAULT '[]',
                status        TEXT NOT NULL DEFAULT 'active',
                content_hash  TEXT NOT NULL,
                agent         TEXT NOT NULL DEFAULT 'unknown'
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_category
            ON lesson_tracking(category)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_lesson_status
            ON lesson_tracking(status)
        """)

        # Migration: add agent column to lesson_tracking if missing
        cols = [c[1] for c in conn.execute("PRAGMA table_info(lesson_tracking)").fetchall()]
        if "agent" not in cols:
            conn.execute(
                "ALTER TABLE lesson_tracking ADD COLUMN agent TEXT NOT NULL DEFAULT 'unknown'"
            )

        conn.commit()
    finally:
        conn.close()


def store_knowledge(
    knowledge_type: str,
    content: str,
    confidence: float = 1.0,
    source_events: list[str] | None = None,
    tags: list[str] | None = None,
    source: str = "STATED",
    maturity: str = "RAW",
) -> str:
    """Store a piece of knowledge. Returns the knowledge_id.

    Auto-deduplicates: if identical content already exists (and is not superseded),
    increments access_count on the existing entry and returns its id.
    """
    if knowledge_type not in KNOWLEDGE_TYPES:
        raise ValueError(
            f"Invalid knowledge_type '{knowledge_type}'. Must be one of: {KNOWLEDGE_TYPES}",
        )

    content = content.strip()
    if len(content) < 5:
        raise ValueError("Knowledge content too short (minimum 5 characters after stripping)")

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
                source, maturity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)""",
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
        query = f"SELECT {_KNOWLEDGE_COLS} FROM knowledge"  # nosec B608 - column names are hardcoded constants, conditions built with parameterized queries
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


_FTS_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "are",
        "was",
        "for",
        "what",
        "how",
        "who",
        "why",
        "when",
        "where",
        "which",
        "does",
        "that",
        "this",
        "with",
        "from",
        "have",
        "has",
        "had",
        "not",
        "but",
        "can",
        "will",
        "about",
        "its",
        "is",
        "it",
        "be",
        "do",
        "did",
        "been",
        "being",
        "there",
        "their",
        "they",
        "them",
        "than",
        "then",
        "these",
        "those",
        "into",
        "our",
        "you",
        "your",
        "we",
        "my",
        "me",
        "of",
        "in",
        "on",
        "to",
        "a",
        "an",
    }
)


def _build_fts_query(query: str) -> str:
    """Convert natural language query into FTS5 OR-based search.

    Strips stopwords and joins meaningful terms with OR so partial
    matches still return results. Single-word queries pass through as-is.
    """
    words = [
        w
        for w in re.sub(r"[^a-zA-Z0-9\s]", "", query).lower().split()
        if w not in _FTS_STOPWORDS and len(w) > 1
    ]
    if not words:
        return query
    if len(words) == 1:
        return words[0]
    return " OR ".join(words)


def search_knowledge(query: str, limit: int = 50) -> list[dict[str, Any]]:
    """Search knowledge using FTS5 full-text search with BM25 relevance ranking.

    Falls back to LIKE-based search if FTS5 table doesn't exist yet.
    BM25 weights: content=10.0, tags=5.0, type=1.0 (lower score = better match).
    Porter stemmer means 'running' matches 'run', 'tests' matches 'test', etc.
    Natural language queries are converted to OR-based search so partial matches work.
    """
    fts_query = _build_fts_query(query)
    conn = _get_connection()
    try:
        query_str = f"""SELECT {_KNOWLEDGE_COLS_K}
               FROM knowledge_fts fts
               JOIN knowledge k ON k.rowid = fts.rowid
               WHERE knowledge_fts MATCH ?
                 AND k.superseded_by IS NULL
               ORDER BY bm25(knowledge_fts, 10.0, 5.0, 1.0)
               LIMIT ?"""  # nosec B608 - column names are hardcoded constants
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
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE superseded_by IS NULL AND (content LIKE ? OR tags LIKE ?) ORDER BY updated_at DESC LIMIT ?",  # nosec B608 - column names are hardcoded constants, all parameters passed separately
            (f"%{keyword}%", f"%{keyword}%", limit),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def rebuild_fts_index() -> int:
    """Rebuild the FTS5 index from existing knowledge rows.

    Call this after upgrading from a pre-FTS database, or if the index
    gets out of sync. Returns the number of rows indexed.
    """
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
            "INSERT INTO knowledge (knowledge_id, created_at, updated_at, knowledge_type, content, confidence, source_events, tags, access_count, content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?)",
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
            ),
        )
        conn.execute(
            "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
            (new_id, knowledge_id),
        )
        conn.commit()
        return new_id
    finally:
        conn.close()


def supersede_knowledge(knowledge_id: str, reason: str) -> None:
    """Mark a knowledge entry as superseded without creating a replacement.

    Use this for removing bad entries. The original is kept (append-only)
    but marked so it no longer appears in queries.
    """
    conn = _get_connection()
    try:
        old = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not old:
            raise ValueError(f"Knowledge entry '{knowledge_id}' not found")

        # Mark as superseded by a sentinel value — no replacement entry needed
        conn.execute(
            "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
            (f"FORGET:{reason[:200]}", knowledge_id),
        )
        conn.commit()
    finally:
        conn.close()


def record_access(knowledge_id: str) -> None:
    """Increment access count for a knowledge entry."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
            (time.time(), knowledge_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_unconsolidated_events(limit: int = 100) -> list[dict[str, Any]]:
    """Find events not yet referenced in any knowledge entry's source_events."""
    conn = _get_connection()
    try:
        # Collect all referenced event IDs from knowledge
        rows = conn.execute("SELECT source_events FROM knowledge").fetchall()
        referenced: set[str] = set()
        for row in rows:
            referenced.update(json.loads(row[0]))

        # Get events not in referenced set
        all_events = conn.execute(
            "SELECT event_id, timestamp, event_type, actor, payload, content_hash FROM system_events ORDER BY timestamp DESC LIMIT ?",
            (limit + len(referenced),),
        ).fetchall()

        results = []
        for row in all_events:
            if row[0] not in referenced:
                results.append(
                    {
                        "event_id": row[0],
                        "timestamp": row[1],
                        "event_type": row[2],
                        "actor": row[3],
                        "payload": json.loads(row[4]),
                        "content_hash": row[5],
                    },
                )
                if len(results) >= limit:
                    break

        return results
    finally:
        conn.close()


def find_similar(content: str) -> list[dict[str, Any]]:
    """Find non-superseded knowledge with identical content (hash-based)."""
    content_hash = compute_hash(content)
    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE content_hash = ? AND superseded_by IS NULL",  # nosec B608 - column names are hardcoded constants, all parameters passed separately
            (content_hash,),
        ).fetchall()
        return [_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def generate_briefing(
    max_items: int = 20,
    include_types: list[str] | None = None,
    context_hint: str = "",
) -> str:
    """Generate a structured text briefing for AI session context.

    Scores knowledge by: confidence * 0.4 + access_frequency * 0.3 + recency * 0.3
    with type-specific decay rates:
      - MISTAKE: 30-day half-life (errors should stick around)
      - FACT: 7-day half-life
      - PATTERN: 14-day half-life
      - PREFERENCE: no decay (always relevant)
      - EPISODE: 14-day half-life

    If context_hint is provided, knowledge matching the hint gets a 0.3 score boost.
    Active lessons are always included at the top.
    """
    conn = _get_connection()
    try:
        query = f"SELECT {_KNOWLEDGE_COLS} FROM knowledge WHERE superseded_by IS NULL AND content NOT LIKE '[SUPERSEDED]%'"  # nosec B608 - column names are hardcoded constants, conditions built with parameterized queries
        params: list[Any] = []

        if include_types:
            placeholders = ",".join("?" for _ in include_types)
            query += f" AND knowledge_type IN ({placeholders})"
            params.extend(include_types)

        rows = conn.execute(query, params).fetchall()
    finally:
        conn.close()

    if not rows:
        return "No knowledge stored yet."

    # Find which knowledge IDs match the context hint (via FTS5)
    hint_matches: set[str] = set()
    if context_hint:
        try:
            matched = search_knowledge(context_hint, limit=100)
            hint_matches = {m["knowledge_id"] for m in matched}
        except Exception as e:
            logger.warning(
                f"Failed to search knowledge for context hint: {e}",
                exc_info=True,
            )

    entries = [_row_to_dict(row) for row in rows]
    now = time.time()
    max_access = max(e["access_count"] for e in entries) or 1

    # Type-specific half-lives in days
    half_lives = {
        # Sutra-style directives — never decay, always surface
        "DIRECTIVE": None,
        # New types
        "BOUNDARY": 30.0,  # Hard constraints persist
        "PRINCIPLE": 30.0,  # Distilled wisdom persists
        "DIRECTION": None,  # User preferences never decay
        "PROCEDURE": 14.0,  # How-to knowledge
        "FACT": 7.0,
        "OBSERVATION": 3.0,  # Unconfirmed — decay fast
        "EPISODE": 14.0,
        # Legacy types — same decay as their successors
        "MISTAKE": 30.0,
        "PATTERN": 14.0,
        "PREFERENCE": None,
    }

    # Score each entry
    for entry in entries:
        access_score = min(entry["access_count"], max_access) / max_access
        age_days = (now - entry["updated_at"]) / 86400

        half_life = half_lives.get(entry["knowledge_type"], 7.0)
        if half_life is None:
            recency = 1.0  # PREFERENCE: never decays
        else:
            recency = 2 ** (-age_days / half_life)

        score = entry["confidence"] * 0.4 + access_score * 0.3 + recency * 0.3

        # Directives always surface — they're the operating principles
        if entry["knowledge_type"] == "DIRECTIVE":
            score += 1.0

        # Boost if matching context hint
        if entry["knowledge_id"] in hint_matches:
            score += 0.3

        entry["_score"] = score

    # Sort by score, take top items
    entries.sort(key=lambda e: e["_score"], reverse=True)
    entries = entries[:max_items]

    # NOTE: We intentionally do NOT call record_access() here.
    # Briefing display is the system showing entries — not the AI
    # actively querying them. Bumping access_count on every briefing
    # created a feedback loop where popular entries stayed popular
    # regardless of actual usefulness.

    # Get active lessons for the header section
    lessons_text = ""
    try:
        lesson_summary = get_lesson_summary()
        if lesson_summary and "No lessons" not in lesson_summary:
            lessons_text = lesson_summary
    except Exception as e:
        logger.warning(
            f"Failed to retrieve lesson summary: {e}",
            exc_info=True,
        )

    # Group by type
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        kt = entry["knowledge_type"]
        grouped.setdefault(kt, []).append(entry)

    # Format output
    lines = [f"## Session Briefing ({len(entries)} items)\n"]

    if lessons_text:
        lines.append(lessons_text)
        lines.append("")

    for kt in [
        "DIRECTIVE",
        "BOUNDARY",
        "PRINCIPLE",
        "DIRECTION",
        "PROCEDURE",
        "MISTAKE",
        "PREFERENCE",
        "PATTERN",
        "FACT",
        "OBSERVATION",
        "EPISODE",
    ]:
        items = grouped.get(kt, [])
        if not items:
            continue
        plural = {
            "DIRECTIVE": "DIRECTIVES",
            "BOUNDARY": "BOUNDARIES",
            "DIRECTION": "DIRECTIONS",
            "PROCEDURE": "PROCEDURES",
            "EPISODE": "EPISODES",
        }.get(kt, f"{kt}S")
        lines.append(f"### {plural} ({len(items)})")
        for item in items:
            hint_marker = " *" if item["knowledge_id"] in hint_matches else ""
            content = item["content"]
            access = f"({item['access_count']}x accessed)"

            if kt == "DIRECTIVE":
                # Show full chain, access count on its own line
                lines.append(f"- [{item['confidence']:.2f}] {content}{hint_marker}")
                lines.append(f"  {access}")
            else:
                # Truncate long entries (digests, etc.)
                display = content.replace("\n", " ")
                if len(display) > 150:
                    display = display[:147] + "..."
                lines.append(f"- [{item['confidence']:.2f}] {display} {access}{hint_marker}")
        lines.append("")

    return "\n".join(lines)


def knowledge_stats() -> dict[str, Any]:
    """Returns knowledge counts by type, total, and average confidence."""
    conn = _get_connection()
    try:
        total = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL",
        ).fetchone()[0]

        by_type: dict[str, int] = {}
        for row in conn.execute(
            "SELECT knowledge_type, COUNT(*) FROM knowledge WHERE superseded_by IS NULL GROUP BY knowledge_type",
        ):
            by_type[row[0]] = row[1]

        avg_confidence = 0.0
        if total > 0:
            avg_confidence = conn.execute(
                "SELECT AVG(confidence) FROM knowledge WHERE superseded_by IS NULL",
            ).fetchone()[0]

        most_accessed = []
        for row in conn.execute(
            "SELECT knowledge_id, content, access_count FROM knowledge WHERE superseded_by IS NULL ORDER BY access_count DESC LIMIT 5",
        ):
            most_accessed.append(
                {"knowledge_id": row[0], "content": row[1], "access_count": row[2]},
            )

        return {
            "total": total,
            "by_type": by_type,
            "avg_confidence": round(avg_confidence, 3),
            "most_accessed": most_accessed,
        }
    finally:
        conn.close()


# ─── Learning Loop ─────────────────────────────────────────────────────


def record_lesson(category: str, description: str, session_id: str, agent: str = "unknown") -> str:
    """Record a lesson or update an existing one for the same category.

    If a lesson with the same category already exists:
      - Increment occurrences
      - Add session_id to the sessions list
      - Update last_seen timestamp
      - Update status based on recurrence pattern

    Args:
        agent: Which AI agent made the mistake (e.g. 'claude-opus', 'kiro-haiku').

    Returns the lesson_id.
    """
    now = time.time()
    conn = _get_connection()
    try:
        # Check if a lesson with same category exists
        existing = conn.execute(
            "SELECT lesson_id, occurrences, sessions FROM lesson_tracking WHERE category = ?",
            (category,),
        ).fetchone()

        if existing:
            lesson_id = existing[0]
            occurrences = existing[1] + 1
            sessions = json.loads(existing[2])
            if session_id not in sessions:
                sessions.append(session_id)
            # Update description if the new one is more descriptive
            # (the first description may be a seed placeholder)
            old_desc = conn.execute(
                "SELECT description FROM lesson_tracking WHERE lesson_id = ?",
                (lesson_id,),
            ).fetchone()
            old_desc_text = old_desc[0] if old_desc else ""
            use_desc = description
            if old_desc_text.startswith("(seeded)") or (
                len(description) > len(old_desc_text) and not description.startswith("(seeded)")
            ):
                use_desc = description
            else:
                use_desc = old_desc_text
            conn.execute(
                """UPDATE lesson_tracking
                   SET occurrences = ?, last_seen = ?, sessions = ?, status = 'active',
                       description = ?
                   WHERE lesson_id = ?""",
                (occurrences, now, json.dumps(sessions), use_desc, lesson_id),
            )
            conn.commit()

            # Corroborate linked knowledge — when a lesson recurs, it means
            # the pattern was observed again. Find knowledge entries whose
            # content references this lesson category and boost them.
            try:
                from divineos.core.knowledge_maturity import (
                    increment_corroboration,
                    promote_maturity,
                )

                cat_words = category.replace("_", " ")
                linked = conn.execute(
                    "SELECT knowledge_id FROM knowledge "
                    "WHERE superseded_by IS NULL AND confidence >= 0.3 "
                    "AND (LOWER(content) LIKE ? OR LOWER(content) LIKE ?)",
                    (f"%{cat_words}%", f"%{category}%"),
                ).fetchall()
                for (kid,) in linked:
                    increment_corroboration(kid)
                    promote_maturity(kid)
            except Exception:
                pass  # corroboration is best-effort, don't break lesson recording

            return cast("str", lesson_id)

        lesson_id = str(uuid.uuid4())
        content_hash = compute_hash(f"{category}:{description}")
        conn.execute(
            """INSERT INTO lesson_tracking
               (lesson_id, created_at, category, description, first_session,
                occurrences, last_seen, sessions, status, content_hash, agent)
               VALUES (?, ?, ?, ?, ?, 1, ?, ?, 'active', ?, ?)""",
            (
                lesson_id,
                now,
                category,
                description,
                session_id,
                now,
                json.dumps([session_id]),
                content_hash,
                agent,
            ),
        )
        conn.commit()
        return lesson_id
    finally:
        conn.close()


def get_lessons(
    status: str | None = None,
    category: str | None = None,
    limit: int = 50,
) -> list[dict[str, Any]]:
    """Get lessons, optionally filtered by status or category."""
    conn = _get_connection()
    try:
        query = "SELECT lesson_id, created_at, category, description, first_session, occurrences, last_seen, sessions, status, content_hash, agent FROM lesson_tracking"
        conditions: list[str] = []
        params: list[Any] = []

        if status:
            conditions.append("status = ?")
            params.append(status)
        if category:
            conditions.append("category = ?")
            params.append(category)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY last_seen DESC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        return [_lesson_row_to_dict(row) for row in rows]
    finally:
        conn.close()


def mark_lesson_improving(category: str, clean_session_id: str) -> None:
    """Mark a lesson as 'improving' when a session passes without the mistake.

    Called when a session is analyzed and does NOT have a mistake in this category.
    Only affects lessons that have occurred 3+ times.
    """
    conn = _get_connection()
    try:
        existing = conn.execute(
            "SELECT lesson_id, occurrences, status FROM lesson_tracking WHERE category = ? AND status = 'active'",
            (category,),
        ).fetchone()
        if existing and existing[1] >= 3:
            conn.execute(
                "UPDATE lesson_tracking SET status = 'improving' WHERE lesson_id = ?",
                (existing[0],),
            )
            conn.commit()
    finally:
        conn.close()


def get_lesson_summary() -> str:
    """Generate a plain English summary of active and improving lessons."""
    lessons = get_lessons()
    if not lessons:
        return "No lessons tracked yet."

    active = [lesson for lesson in lessons if lesson["status"] == "active"]
    improving = [lesson for lesson in lessons if lesson["status"] == "improving"]

    lines = [f"### ACTIVE LESSONS ({len(active) + len(improving)})"]

    for lesson in active:
        lines.append(
            f"- [{lesson['occurrences']}x] {lesson['description']} (last: {lesson['category']})",
        )

    for lesson in improving:
        lines.append(f"- IMPROVING (was {lesson['occurrences']}x): {lesson['description']}")

    if not active and not improving:
        return "No lessons tracked yet."

    return "\n".join(lines)


def check_recurring_lessons(categories: list[str]) -> list[dict[str, Any]]:
    """Check if any of the given categories have recurring lessons.

    Returns list of lessons that have occurred more than once.
    """
    conn = _get_connection()
    try:
        results: list[dict[str, Any]] = []
        for cat in categories:
            row = conn.execute(
                "SELECT lesson_id, created_at, category, description, first_session, occurrences, last_seen, sessions, status, content_hash FROM lesson_tracking WHERE category = ? AND occurrences > 1",
                (cat,),
            ).fetchone()
            if row:
                results.append(_lesson_row_to_dict(row))
        return results
    finally:
        conn.close()


# ─── Lesson Extraction from Reports ──────────────────────────────────

# Maps check names to lesson categories
_CHECK_TO_CATEGORY = {
    "completeness": "blind_coding",
    "correctness": "incomplete_fix",
    "responsiveness": "misunderstood",
    "safety": "incomplete_fix",
    "honesty": "false_claim",
    "clarity": "shallow_output",
    "task_adherence": "wrong_scope",
}

# Phrases that signal a check "passed" only because nothing happened.
_VACUOUS_PHRASES = (
    "didn't edit any files",
    "didn't make any changes",
    "didn't do much",
    "didn't touch any files",
    "didn't make any specific claims",
    "nothing to check",
    "nothing to compare",
    "no tests were run",
    "no way to know",
    "never had to correct",
    "barely any activity",
    "was quiet this session",
)


def _is_vacuous_summary(summary: str) -> bool:
    """Return True if a check summary indicates nothing meaningful happened."""
    lower = summary.lower()
    return any(phrase in lower for phrase in _VACUOUS_PHRASES)


def extract_lessons_from_report(
    checks: list[dict[str, Any]],
    session_id: str,
    tone_shifts: list[dict[str, Any]] | None = None,
    error_recovery: dict[str, Any] | None = None,
) -> list[str]:
    """Extract knowledge and lessons from session quality check results.

    Args:
        checks: List of check result dicts with keys: name, passed, score, summary
        session_id: The session identifier
        tone_shifts: Optional list of tone shift dicts with keys: direction, trigger
        error_recovery: Optional dict with keys: blind_retries, investigate_count

    Returns:
        List of stored knowledge IDs.

    """
    stored_ids: list[str] = []
    short_id = session_id[:12]
    lesson_categories: list[str] = []
    clean_categories: list[str] = []

    for check in checks:
        name = check.get("name", "")
        passed = check.get("passed", True)
        score = check.get("score", 1.0)
        summary = check.get("summary", "")
        category = _CHECK_TO_CATEGORY.get(name)

        # Skip inconclusive checks — passed=-1 means the check couldn't run
        if passed == -1:
            continue

        # Skip vacuous checks — nothing happened, so pass/fail is meaningless
        if _is_vacuous_summary(summary):
            continue

        if not passed or (score is not None and score < 0.7):
            # Extract MISTAKE knowledge — written in first person for embodiment
            if name == "completeness":
                content = f"I edited files without reading them first. I must read before I edit (session {short_id}). {summary}"
            elif name == "correctness":
                content = f"I broke tests with my changes (session {short_id}). {summary}"
            elif name == "safety":
                content = f"I introduced errors after editing (session {short_id}). {summary}"
            elif name == "responsiveness":
                content = f"I ignored a correction and the user had to repeat themselves (session {short_id})."
            elif name == "honesty":
                content = (
                    f"I claimed something was fixed but the error came back (session {short_id})."
                )
            elif name == "task_adherence" and score is not None and score < 0.5:
                content = f"I drifted from what was asked and went off-track (session {short_id}). {summary}"
            else:
                continue

            kid = store_knowledge(
                knowledge_type="MISTAKE",
                content=content.strip(),
                confidence=0.8,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", name],
            )
            stored_ids.append(kid)

            # Record lesson for learning loop
            if category:
                record_lesson(category, content.strip(), session_id)
                lesson_categories.append(category)

        elif passed and passed != -1 and score is not None and score >= 0.9:
            # Skip vacuous checks — "passed" because nothing happened is not a lesson
            if _is_vacuous_summary(summary):
                continue
            # Extract PATTERN knowledge for good practices
            content = f"I showed good {name} this session (session {short_id}). {summary}"
            kid = store_knowledge(
                knowledge_type="PATTERN",
                content=content.strip(),
                confidence=0.9,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", name],
            )
            stored_ids.append(kid)

            # Mark lesson as improving if this category was previously a problem
            if category:
                clean_categories.append(category)

    # Tone shift extraction — capture full arcs (upset → recovery), not just negatives
    if tone_shifts:
        # Index positive shifts by sequence for pairing with preceding negatives
        positive_by_seq: dict[int, dict[str, Any]] = {
            int(t.get("sequence", -1)): t for t in tone_shifts if t.get("direction") == "positive"
        }

        negative_shifts = [t for t in tone_shifts if t.get("direction") == "negative"]
        for shift in negative_shifts[:3]:  # cap at 3
            trigger = shift.get("trigger", "unknown action")
            user_response = shift.get("user_response", "")
            seq = shift.get("sequence", -1)

            # Look for a recovery (positive shift that follows this negative one)
            recovery = None
            for candidate_seq in sorted(positive_by_seq):
                if candidate_seq > seq:
                    recovery = positive_by_seq[candidate_seq]
                    break

            # Build the lesson content — include what went wrong AND what fixed it
            if user_response and len(user_response.split()) >= 3:
                problem = f'The user got upset and said: "{user_response[:150]}" — this happened after {trigger[:80]}'
            else:
                problem = f"I upset the user after {trigger[:80]}"

            if recovery:
                recovery_action = recovery.get("trigger", "changing approach")
                recovery_response = recovery.get("user_response", "")
                if recovery_response and len(recovery_response.split()) >= 3:
                    content = f'{problem}. I recovered by {recovery_action[:80]} and the user responded: "{recovery_response[:120]}" (session {short_id}).'
                else:
                    content = (
                        f"{problem}. I recovered by {recovery_action[:80]} (session {short_id})."
                    )

                # Store the recovery as a PATTERN (success), not just the upset as a MISTAKE
                kid = store_knowledge(
                    knowledge_type="PATTERN",
                    content=content,
                    confidence=0.8,
                    source_events=[session_id],
                    tags=["auto-extracted", f"session-{short_id}", "tone_recovery"],
                )
                stored_ids.append(kid)
                record_lesson("upset_recovered", content, session_id)
                lesson_categories.append("upset_recovered")
            else:
                content = f"{problem} (session {short_id})."
                kid = store_knowledge(
                    knowledge_type="MISTAKE",
                    content=content,
                    confidence=0.8,
                    source_events=[session_id],
                    tags=["auto-extracted", f"session-{short_id}", "tone_shift"],
                )
                stored_ids.append(kid)
                record_lesson("upset_user", content, session_id)
                lesson_categories.append("upset_user")

    # Error recovery extraction
    if error_recovery:
        blind_retries = error_recovery.get("blind_retries", 0)
        investigate_count = error_recovery.get("investigate_count", 0)

        if blind_retries > 0:
            content = f"I retried a failed action {blind_retries}x without investigating the cause. I need to investigate errors, not blindly retry (session {short_id})."
            kid = store_knowledge(
                knowledge_type="MISTAKE",
                content=content,
                confidence=0.8,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", "error_recovery"],
            )
            stored_ids.append(kid)
            record_lesson("blind_retry", content, session_id)
            lesson_categories.append("blind_retry")

        if investigate_count > blind_retries:
            content = f"I investigated errors before retrying — good recovery pattern (session {short_id})."
            kid = store_knowledge(
                knowledge_type="PATTERN",
                content=content,
                confidence=0.9,
                source_events=[session_id],
                tags=["auto-extracted", f"session-{short_id}", "error_recovery"],
            )
            stored_ids.append(kid)

    # Mark improving lessons for categories that were clean this session
    for cat in clean_categories:
        if cat not in lesson_categories:
            mark_lesson_improving(cat, session_id)

    return stored_ids


# ─── Internal helpers ─────────────────────────────────────────────────


def _lesson_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a lesson_tracking table row to a dict."""
    d = {
        "lesson_id": row[0],
        "created_at": row[1],
        "category": row[2],
        "description": row[3],
        "first_session": row[4],
        "occurrences": row[5],
        "last_seen": row[6],
        "sessions": json.loads(row[7]),
        "status": row[8],
        "content_hash": row[9],
    }
    if len(row) > 10:
        d["agent"] = row[10]
    else:
        d["agent"] = "unknown"
    return d


def _row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a knowledge table row to a dict."""
    d = {
        "knowledge_id": row[0],
        "created_at": row[1],
        "updated_at": row[2],
        "knowledge_type": row[3],
        "content": row[4],
        "confidence": row[5],
        "source_events": json.loads(row[6]) if row[6] else [],
        "tags": json.loads(row[7]) if row[7] else [],
        "access_count": row[8],
        "superseded_by": row[9],
        "content_hash": row[10],
    }
    # New columns (present after schema migration)
    if len(row) > 11:
        d["source"] = row[11]
        d["maturity"] = row[12]
        d["corroboration_count"] = int(row[13])
        d["contradiction_count"] = int(row[14])
    else:
        d["source"] = "INHERITED"
        d["maturity"] = "RAW"
        d["corroboration_count"] = 0
        d["contradiction_count"] = 0
    return d


# ─── Text Analysis Helpers ────────────────────────────────────────────

_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "shall",
        "can",
        "to",
        "of",
        "in",
        "for",
        "on",
        "with",
        "at",
        "by",
        "from",
        "as",
        "into",
        "through",
        "during",
        "before",
        "after",
        "above",
        "below",
        "between",
        "and",
        "but",
        "or",
        "nor",
        "not",
        "so",
        "yet",
        "both",
        "either",
        "neither",
        "each",
        "every",
        "all",
        "any",
        "few",
        "more",
        "most",
        "other",
        "some",
        "such",
        "no",
        "only",
        "same",
        "than",
        "too",
        "very",
        "just",
        "that",
        "this",
        "these",
        "those",
        "i",
        "you",
        "he",
        "she",
        "it",
        "we",
        "they",
        "me",
        "him",
        "her",
        "us",
        "them",
        "my",
        "your",
        "his",
        "its",
        "our",
        "their",
        "what",
        "which",
        "who",
        "whom",
        "when",
        "where",
        "why",
        "how",
        "if",
        "then",
        "else",
        "here",
        "there",
        "also",
        "about",
        "up",
        "out",
        "down",
        "off",
        "over",
        "under",
        "again",
        "further",
        "once",
        "like",
        "well",
        "back",
        "even",
        "still",
        "way",
        "get",
        "got",
        "let",
        "say",
        "said",
        "go",
        "going",
        "went",
        "come",
        "came",
        "make",
        "made",
        "take",
        "took",
        "see",
        "saw",
        "know",
        "knew",
        "think",
        "thought",
        "want",
        "need",
        "use",
        "used",
        "try",
        "tried",
        "look",
        "looked",
        "give",
        "gave",
        "tell",
        "told",
        "work",
        "worked",
        "call",
        "called",
        "yes",
        "ok",
        "okay",
        "yeah",
        "sure",
        "right",
        "now",
        "one",
        "two",
        "first",
        "new",
        "old",
        "good",
        "bad",
        "big",
        "small",
        "much",
        "many",
        "long",
        "little",
        "thing",
        "things",
        "something",
        "anything",
        "everything",
        "nothing",
        "im",
        "dont",
        "doesnt",
        "didnt",
        "isnt",
        "arent",
        "wasnt",
        "werent",
        "wont",
        "cant",
        "couldnt",
        "shouldnt",
        "wouldnt",
        "thats",
        "lets",
        "ive",
        "youre",
        "theyre",
        "hes",
        "shes",
        # AI coding conversation filler — these appear in every session
        "file",
        "files",
        "code",
        "run",
        "running",
        "output",
        "tool",
        "tools",
        "command",
        "task",
        "tasks",
        "check",
        "set",
        "add",
        "added",
        "change",
        "changes",
        "changed",
        "put",
        "read",
        "show",
        "done",
        "lol",
        "haha",
        "hey",
        "thanks",
        "thank",
        "please",
        "help",
        "claude",
        "kiro",
        "notification",
        "users",
        "user",
        "keep",
        "start",
        "stop",
        "already",
        "pretty",
        "really",
        "actually",
        "basically",
        "everything",
        "able",
    },
)


def _normalize_text(text: str) -> str:
    """Lowercase, strip punctuation, collapse whitespace."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_key_terms(text: str) -> str:
    """Remove stopwords, return space-separated key terms for FTS5 queries."""
    normalized = _normalize_text(text)
    words = normalized.split()
    terms = [w for w in words if w not in _STOPWORDS and len(w) > 2]
    # Deduplicate while preserving order
    seen: set[str] = set()
    unique = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            unique.append(t)
    return " ".join(unique[:20])  # cap at 20 terms for FTS5 query


def _compute_overlap(text_a: str, text_b: str) -> float:
    """Compute word set overlap between two texts. Returns 0.0-1.0."""
    words_a = set(_normalize_text(text_a).split()) - _STOPWORDS
    words_b = set(_normalize_text(text_b).split()) - _STOPWORDS
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller


def extract_session_topics(user_texts: list[str], top_n: int = 8) -> list[str]:
    """Extract top topics from user messages using word frequency analysis."""
    word_counts: Counter[str] = Counter()
    for text in user_texts:
        words = _normalize_text(text).split()
        meaningful = [w for w in words if w not in _STOPWORDS and len(w) > 2]
        word_counts.update(meaningful)
    return [word for word, _ in word_counts.most_common(top_n)]


# ─── Smart Knowledge Storage ─────────────────────────────────────────

_MIN_CONTENT_WORDS = 3  # content with fewer meaningful words gets skipped

# Patterns that indicate conversational filler with no substance after it.
# Must match the ENTIRE string (after prefix stripping) to filter.
_CONVERSATIONAL_NOISE = re.compile(
    r"^(how does (it|this|that) (look|feel|seem)[\s?.!]*$|"
    r"any (adjustments|suggestions|thoughts|ideas)[\s?.!]*$|"
    r"sounds good[\s.!]*$|"
    r"that works[\s.!]*$|"
    r"i agree[d]?[\s.!]*$)",
    re.IGNORECASE,
)

# Content that is a task-notification XML tag or system artifact
_SYSTEM_ARTIFACT = re.compile(r"<task-notification|<tool-use-id|<task-id", re.IGNORECASE)


def _is_extraction_noise(content: str, knowledge_type: str) -> bool:
    """Check if extracted content is conversational noise rather than knowledge.

    Returns True if the content should NOT be stored.
    """
    # Strip common prefixes to examine the core content
    stripped = content
    for prefix in ("I decided: ", "I should: ", "I was corrected: "):
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix) :]
            break

    stripped_lower = stripped.lower().strip()

    # System artifacts (XML tags leaked into content)
    if _SYSTEM_ARTIFACT.search(stripped):
        return True

    # Raw user text starting with repeated punctuation (e.g. "??? first off...")
    if re.match(r"^[?!.]{2,}\s", stripped):
        return True

    # Pure affirmation — user just said "yes" with some extra words
    # e.g. "yes lets commit and push" or "yes :) but make sure..."
    affirmation_core = re.sub(r"[^a-z\s]", "", stripped_lower).strip()
    affirmation_words = affirmation_core.split()
    if affirmation_words and affirmation_words[0] in (
        "yes",
        "yeah",
        "yep",
        "ok",
        "okay",
        "sure",
        "proceed",
        "go",
        "lets",
        "do",
        "perfect",
        "wonderful",
        "great",
    ):
        # Check for reasoning markers — if they explain WHY, it's real
        has_reasoning = any(w in affirmation_words for w in ("because", "since", "reason"))
        if not has_reasoning:
            # If the meaningful content after the affirmation is short, it's noise
            non_affirmation = [
                w
                for w in affirmation_words[1:]
                if w
                not in (
                    "it",
                    "do",
                    "lets",
                    "go",
                    "ahead",
                    "please",
                    "lol",
                    "the",
                    "and",
                    "but",
                    "so",
                    "then",
                    "we",
                    "can",
                    "this",
                    "that",
                    "its",
                    "im",
                    "you",
                    "keep",
                    "going",
                    "now",
                    "make",
                    "sure",
                    "what",
                    "just",
                    "first",
                    "also",
                    "get",
                    "got",
                    "need",
                    "needs",
                    "want",
                    "have",
                    "has",
                    "done",
                    "think",
                    "know",
                    "like",
                    "look",
                    "see",
                    "try",
                    "continue",
                    "find",
                    "nothing",
                    "wrong",
                    "right",
                    "build",
                    "more",
                    "stuff",
                    "things",
                    "thing",
                    "for",
                    "from",
                    "with",
                    "about",
                    "until",
                    "when",
                    "where",
                    "how",
                    "will",
                    "would",
                    "could",
                    "should",
                    "still",
                    "really",
                    "very",
                    "much",
                    "well",
                    "good",
                    "new",
                    "all",
                    "here",
                    "there",
                    "them",
                    "they",
                    "been",
                    "being",
                    "into",
                    "some",
                    "were",
                    "work",
                    "start",
                    "stop",
                )
            ]
            if len(non_affirmation) <= 8:
                return True

    # Conversational noise pattern match
    if _CONVERSATIONAL_NOISE.match(stripped_lower):
        return True

    # Questions directed at the AI — these are prompts, not knowledge
    # Exclude tag questions ("ok?", "right?", "yes?") which are statements
    if stripped_lower.endswith("?") and knowledge_type in ("DIRECTION", "PRINCIPLE"):
        is_tag_question = stripped_lower.rstrip().endswith(("ok?", "right?", "yes?", "no?"))
        if not is_tag_question:
            question_words = stripped_lower.split()
            if len(question_words) < 15:
                return True

    # Raw user quotes — conversational text stored verbatim
    # These are raw chat messages, not synthesized knowledge.
    if knowledge_type in ("DIRECTION", "PRINCIPLE", "BOUNDARY"):
        # User's typing style: ".." ellipsis — signal of raw quote
        # 3+ occurrences in short text = clearly conversational
        double_dot_count = stripped.count("..")
        if double_dot_count >= 3 and len(stripped.split()) < 30:
            return True
        # Conversational statements about accidents/mistakes in the UI
        if re.search(r"\b(oops|whoops|accidentally|i meant to)\b", stripped_lower):
            return True
        # Third-person quotes and meta-commentary about external input
        if re.match(
            r"(this is what (he|she|they) said|i got a review from|"
            r"here is what|someone said|he said|she said|"
            r"my friend (said|wanted|sent|asked))",
            stripped_lower,
        ):
            return True
        # Relayed messages from other AIs or people — not self-knowledge
        if re.search(
            r"(here is the reply|hey claude|your move|ready when you are)",
            stripped_lower,
        ):
            return True
        # Short declarative chat — under 10 words ending with ".."
        if stripped.rstrip().endswith("..") and len(stripped.split()) < 10:
            return True
        # Addressing the AI directly (not as a rule or correction)
        if stripped_lower.startswith(("you ", "if you ", "now you ", "while you ")):
            # Keep rules (must/always/never) and corrections (fixed/broke/forgot/missed)
            has_weight = any(
                w in stripped_lower
                for w in (
                    "must",
                    "always",
                    "never",
                    "rule",
                    "only fixed",
                    "forgot",
                    "broke",
                    "missed",
                    "didn't",
                    "failed",
                    "wrong",
                )
            )
            if not has_weight:
                return True
        # Short questions directed at the AI — chat, not knowledge
        # Exclude tag questions ("ok?", "right?") which are rhetorical
        if stripped_lower.rstrip().endswith("?") and len(stripped.split()) < 20:
            is_tag = stripped_lower.rstrip().endswith(("ok?", "right?", "yes?", "no?"))
            if not is_tag:
                return True
        # Task-specific instructions without lasting value
        # "lets commit and push", "lets keep going", "lets do X"
        if re.match(r"lets?\s+(commit|push|keep|do|try|fix|run|check|look)\b", stripped_lower):
            return True
        # Conversational filler with no actionable content
        if re.match(
            r"(ill go with|i got|i just|i was just|i tried|i need my|"
            r"we need to (clean|commit|push|fix|run|check)|"
            r"how (does|is|do|are) (it|this|that|everything))",
            stripped_lower,
        ):
            return True
        # GitHub opt-out, tool instructions, UI actions — not knowledge
        if re.search(r"\b(opt out|allow .* to use my data|make sure you opt)\b", stripped_lower):
            return True

    return False


def _decide_operation(
    content: str,
    knowledge_type: str,
    best_match: dict[str, Any] | None,
    best_overlap: float,
) -> tuple[str, str | None]:
    """Decide what to do with incoming knowledge.

    Returns (operation, existing_id):
        - ("NOOP", id)   — exact or very close match, just bump access count
        - ("UPDATE", id) — high overlap but enough new info to supersede old
        - ("ADD", None)  — no close match, insert fresh
        - ("SKIP", None) — too short or pure subset, not worth storing
    """
    # Skip: content too short to be useful
    content_words = set(_normalize_text(content).split()) - _STOPWORDS
    meaningful_words = {w for w in content_words if len(w) > 2}
    if len(meaningful_words) < _MIN_CONTENT_WORDS:
        return ("SKIP", None)

    # Skip: conversational noise (raw user quotes, affirmations, questions)
    if _is_extraction_noise(content, knowledge_type):
        return ("SKIP", None)

    if best_match is None or best_overlap < 0.4:
        return ("ADD", None)

    # NOOP: near-identical (current dedup behavior)
    if best_overlap > 0.6:
        # Check if there's enough genuinely new info to warrant an UPDATE
        existing_words = set(_normalize_text(best_match["content"]).split()) - _STOPWORDS
        new_words = meaningful_words - existing_words
        new_ratio = len(new_words) / max(1, len(meaningful_words))
        if new_ratio > 0.2:
            # 20%+ genuinely new words → supersede old with new
            return ("UPDATE", best_match["knowledge_id"])
        return ("NOOP", best_match["knowledge_id"])

    # Medium overlap (0.4-0.6): different enough to add
    return ("ADD", None)


def store_knowledge_smart(
    knowledge_type: str,
    content: str,
    confidence: float = 1.0,
    source_events: list[str] | None = None,
    tags: list[str] | None = None,
    source: str = "STATED",
    maturity: str = "RAW",
) -> str:
    """Store knowledge with smart operation selection.

    Decides between ADD, UPDATE, SKIP, or NOOP based on content analysis:
    - NOOP: exact or near-duplicate, bump access count
    - UPDATE: high overlap but 20%+ new info, supersede old entry
    - ADD: no close match, insert fresh
    - SKIP: too short or pure noise, return empty string

    Also scans for contradictions against existing same-type entries
    and resolves them automatically.
    """
    # First: try exact hash dedup (fast path)
    content_hash = compute_hash(content)
    conn = _get_connection()
    try:
        # Check ALL entries with this hash (active AND superseded)
        all_with_hash = conn.execute(
            "SELECT knowledge_id, knowledge_type, superseded_by FROM knowledge WHERE content_hash = ?",
            (content_hash,),
        ).fetchall()

        for kid, ktype, superseded_by in all_with_hash:
            if ktype != knowledge_type:
                continue
            if superseded_by is not None:
                # This exact content was previously superseded — don't resurrect it
                logger.debug(f"Skipping superseded duplicate: {content[:60]}")
                return ""
            # Active exact match — bump access count
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (time.time(), kid),
            )
            conn.commit()
            # Exact match = corroboration
            try:
                from divineos.core.knowledge_maturity import (
                    increment_corroboration,
                    promote_maturity,
                )

                increment_corroboration(str(kid))
                promote_maturity(str(kid))
            except Exception as e:
                logger.debug(f"Maturity check failed: {e}", exc_info=True)
            return str(kid)

        # Find best fuzzy match via FTS5
        best_match: dict[str, Any] | None = None
        best_overlap = 0.0
        # nosec B608 - column names are hardcoded constants, query parameters passed separately
        fts_query = f"""SELECT {_KNOWLEDGE_COLS_K}
                       FROM knowledge_fts fts
                       JOIN knowledge k ON k.rowid = fts.rowid
                       WHERE knowledge_fts MATCH ?
                         AND k.superseded_by IS NULL
                       ORDER BY bm25(knowledge_fts, 10.0, 5.0, 1.0)
                       LIMIT 10"""
        key_terms = _extract_key_terms(content)
        if key_terms:
            try:
                rows = conn.execute(fts_query, (key_terms,)).fetchall()
                for row in rows:
                    entry = _row_to_dict(row)
                    if entry["knowledge_type"] == knowledge_type:
                        overlap = _compute_overlap(content, entry["content"])
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_match = entry
            except Exception as e:
                logger.warning(f"FTS5 search failed, dedup may miss matches: {e}")

        # Decide operation
        operation, existing_id = _decide_operation(
            content, knowledge_type, best_match, best_overlap
        )
        logger.debug(f"Knowledge operation: {operation} (overlap={best_overlap:.2f})")

        if operation == "SKIP":
            logger.info(f"Skipped noise knowledge: {content[:60]}")
            return ""

        if operation == "NOOP":
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (time.time(), existing_id),
            )
            conn.commit()
            # Corroboration: re-encountering knowledge strengthens trust
            try:
                from divineos.core.knowledge_maturity import (
                    increment_corroboration,
                    promote_maturity,
                )

                increment_corroboration(cast("str", existing_id))
                promote_maturity(cast("str", existing_id))
            except Exception as e:
                logger.debug(f"Maturity check failed: {e}", exc_info=True)
            return cast("str", existing_id)

        # For ADD and UPDATE, we insert a new entry
        now = time.time()
        sources_json = json.dumps(source_events or [])
        tags_json = json.dumps(tags or [])
        kid = str(uuid.uuid4())

        # Check for same-type hash match (race condition guard)
        hash_match = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE content_hash = ? AND knowledge_type = ? AND superseded_by IS NULL",
            (content_hash, knowledge_type),
        ).fetchone()
        if hash_match:
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (now, hash_match[0]),
            )
            conn.commit()
            return str(hash_match[0])

        # Insert new entry
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, created_at, updated_at, knowledge_type, content, confidence, source_events, tags, access_count, content_hash, source, maturity, corroboration_count, contradiction_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0, 0)",
            (
                kid,
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
            ),
        )
        conn.commit()

        # UPDATE: supersede the old entry
        if operation == "UPDATE" and existing_id:
            supersede_knowledge(existing_id, reason=f"Updated by {kid[:12]}")
            logger.info(f"Updated knowledge: {existing_id[:12]} → {kid[:12]}")

        # Scan for contradictions against same-type entries
        try:
            from divineos.core.knowledge_contradiction import (
                resolve_contradiction,
                scan_for_contradictions,
            )

            same_type = get_knowledge(knowledge_type=knowledge_type, limit=100)
            # Exclude the entry we just created
            same_type = [e for e in same_type if e["knowledge_id"] != kid]
            contradictions = scan_for_contradictions(content, knowledge_type, same_type)
            for match in contradictions:
                resolve_contradiction(kid, match)
        except Exception as e:
            logger.debug(f"Contradiction scan failed: {e}", exc_info=True)

        # Post-insert dedup guard: check if FTS finds a pre-existing near-match
        # that we missed (handles race conditions with concurrent inserts)
        if key_terms and operation == "ADD":
            try:
                rows = conn.execute(fts_query, (key_terms,)).fetchall()
                for row in rows:
                    entry = _row_to_dict(row)
                    if entry["knowledge_id"] == kid:
                        continue
                    if entry["knowledge_type"] == knowledge_type:
                        overlap = _compute_overlap(content, entry["content"])
                        if overlap > 0.6:
                            conn.execute(
                                "UPDATE knowledge SET superseded_by = ?, updated_at = ? WHERE knowledge_id = ?",
                                (entry["knowledge_id"], time.time(), kid),
                            )
                            conn.execute(
                                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                                (time.time(), entry["knowledge_id"]),
                            )
                            conn.commit()
                            return cast("str", entry["knowledge_id"])
            except Exception as e:
                logger.debug(f"Post-insert FTS5 search failed: {e}", exc_info=True)

        return kid
    finally:
        conn.close()


# ─── Deep Session Extraction ─────────────────────────────────────────

# Patterns for extracting reasoning context from messages
_REASON_PATTERNS = (
    re.compile(r"\bbecause\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bsince\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bso that\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bthe reason\b\s+(.{10,120})", re.IGNORECASE),
)

_ALTERNATIVE_PATTERNS = (
    re.compile(r"\binstead of\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\brather than\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\bnot\b\s+(\w+.{5,60})", re.IGNORECASE),
)


def _extract_assistant_summary(record: dict[str, Any]) -> str:
    """Extract a short summary of what the assistant was doing in a record."""
    msg = record.get("message", {})
    content = msg.get("content", [])
    if not isinstance(content, list):
        return ""

    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = block.get("text", "")
            # Take first meaningful sentence
            sentences = re.split(r"[.!?\n]", text)
            for s in sentences:
                s = s.strip()
                if len(s) > 15:
                    parts.append(s[:150])
                    break
        elif block.get("type") == "tool_use":
            name = block.get("name", "unknown")
            inp = block.get("input", {})
            if name in ("Read", "Edit", "Write"):
                fp = inp.get("file_path", "")
                parts.append(f"{name} {fp}")
            elif name == "Bash":
                cmd = inp.get("command", "")[:60]
                parts.append(f"Bash: {cmd}")
            else:
                parts.append(f"Tool: {name}")

    return "; ".join(parts[:3])


def _find_reason_in_text(text: str) -> str:
    """Try to extract a reason/justification from text."""
    for pattern in _REASON_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".")
    return ""


def _find_alternative_in_text(text: str) -> str:
    """Try to extract what was rejected/compared against."""
    for pattern in _ALTERNATIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".")
    return ""


def _distill_correction(raw_text: str) -> str:
    """Transform a raw correction quote into a first-person insight.

    Instead of: "no when i say you.. you say i or me.."
    Produce:    "I was told: when the user says 'you' referring to me, I should respond with 'I' or 'me'."
    """
    text = raw_text.strip()[:300]
    # Strip common prefixes that add noise
    for prefix in ("no ", "no, ", "wrong ", "wrong, ", "stop ", "don't "):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    # Clean up
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    # Remove trailing fragments
    if text and text[-1] not in ".!?":
        text = text.rstrip(". ") + "."
    return f"I was corrected: {text}"


def _distill_preference(raw_text: str) -> str:
    """Transform a raw preference quote into a first-person direction."""
    text = raw_text.strip()[:300]
    # Strip "I want", "I prefer", "I like" prefixes — rephrase as what I should do
    for prefix in ("i want ", "i prefer ", "i like ", "i need ", "please "):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text = text.rstrip(". ") + "."
    return f"I should: {text}"


def deep_extract_knowledge(
    analysis: "Any",  # SessionAnalysis — avoid circular import
    records: list[dict[str, Any]],
) -> list[str]:
    """Extract rich, structured knowledge from a session analysis + raw records.

    Goes beyond simple signal detection to extract:
    - Correction pairs (what AI did wrong → what user wanted)
    - User preferences with context
    - Decisions with reasoning and alternatives
    - Session topics

    Returns list of stored knowledge IDs.
    """
    stored_ids: list[str] = []
    session_id = analysis.session_id
    short_id = session_id[:12]

    # Build a map of record index → record for context lookups
    user_indices: list[int] = []
    for i, rec in enumerate(records):
        if rec.get("type") == "user":
            user_indices.append(i)

    # Session topics are extracted but only used as tags on other knowledge,
    # not stored as standalone facts (word frequency alone produces keyword soup).
    topics = extract_session_topics(analysis.user_message_texts)
    topic_tags = [f"topic-{t}" for t in topics[:5]]

    # --- Correction pairs → PRINCIPLE or BOUNDARY with insight content ---
    for correction in analysis.corrections:
        correction_text = correction.content

        # Skip venting/frustration that matched correction patterns but isn't
        # actionable guidance. Real corrections tell the AI what to do differently;
        # frustrations just express displeasure.
        lower_text = correction_text.lower().strip()
        # Too short to be a real instruction (e.g. "no", "wrong")
        if len(lower_text.split()) < 5:
            continue
        # Frustration indicators without actionable content
        frustration_only = any(
            marker in lower_text
            for marker in (
                "i dont even know",
                "i don't even know",
                "what is going on",
                "fml",
                "im lost",
                "i'm lost",
                "utterly lost",
                "i have no idea",
                "this is a mess",
                "a nightmare",
            )
        )
        if frustration_only:
            continue
        # Find this correction in the raw records and get the assistant message before it
        ai_before = ""
        for i, rec in enumerate(records):
            if rec.get("type") != "user":
                continue
            user_text = _extract_user_text_from_record(rec)
            if not user_text:
                continue
            if user_text[:100] == correction_text[:100]:
                for j in range(i - 1, max(i - 5, -1), -1):
                    if records[j].get("type") == "assistant":
                        ai_before = _extract_assistant_summary(records[j])
                        break
                break

        # Classify: hard constraint words → BOUNDARY, otherwise → PRINCIPLE
        lower = correction_text.lower()
        is_boundary = any(
            w in lower for w in ("never", "always", "must", "don't", "do not", "cannot")
        )
        ktype = "BOUNDARY" if is_boundary else "PRINCIPLE"

        # Store insight in first person — future me needs to inhabit this, not parse it
        if ai_before:
            content = f"I was {ai_before.lower()}, but got corrected — {correction_text[:200]}"
        else:
            content = _distill_correction(correction_text)

        kid = store_knowledge_smart(
            knowledge_type=ktype,
            content=content,
            confidence=0.85,
            source="CORRECTED",
            maturity="HYPOTHESIS",
            source_events=[session_id],
            tags=["auto-extracted", "correction-pair", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Preferences → DIRECTION ---
    for pref in getattr(analysis, "preferences", []):
        kid = store_knowledge_smart(
            knowledge_type="DIRECTION",
            content=_distill_preference(pref.content),
            confidence=0.9,
            source="STATED",
            maturity="CONFIRMED",
            source_events=[session_id],
            tags=["auto-extracted", "direction", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Decisions with context ---
    for decision in analysis.decisions:
        decision_text = decision.content
        # Skip short affirmations that aren't real decisions
        if len(decision_text.split()) < 8:
            continue
        # Skip if the noise filter catches it
        if _is_extraction_noise(f"I decided: {decision_text}", "PRINCIPLE"):
            continue
        reason = _find_reason_in_text(decision_text)
        alternative = _find_alternative_in_text(decision_text)

        # Also check the next user message for reasoning
        if not reason:
            for i, rec in enumerate(records):
                if rec.get("type") != "user":
                    continue
                user_text = _extract_user_text_from_record(rec)
                if user_text and user_text[:80] == decision_text[:80]:
                    # Check next user message for reasoning
                    for j in range(i + 1, min(i + 4, len(records))):
                        if records[j].get("type") == "user":
                            next_text = _extract_user_text_from_record(records[j])
                            reason = _find_reason_in_text(next_text)
                            break
                    break

        parts = [f"I decided: {decision_text[:200]}"]
        if alternative:
            parts.append(f"I considered but rejected: {alternative}")
        if reason:
            parts.append(f"Because: {reason}")

        kid = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content=". ".join(parts),
            confidence=0.9,
            source="DEMONSTRATED",
            maturity="HYPOTHESIS",
            source_events=[session_id],
            tags=["auto-extracted", "decision", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Encouragements as positive patterns ---
    for enc in analysis.encouragements:
        # Find what the AI did right (assistant message before encouragement)
        ai_before = ""
        for i, rec in enumerate(records):
            if rec.get("type") != "user":
                continue
            user_text = _extract_user_text_from_record(rec)
            if user_text and user_text[:80] == enc.content[:80]:
                for j in range(i - 1, max(i - 5, -1), -1):
                    if records[j].get("type") == "assistant":
                        ai_before = _extract_assistant_summary(records[j])
                        break
                break

        if not ai_before:
            # Without knowing what the AI did right, the encouragement is just
            # a raw user quote with no actionable insight. Skip it.
            continue

        content = f"I {ai_before.lower()} and it worked well — user affirmed: {enc.content[:150]}"

        kid = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content=content,
            confidence=0.9,
            source="DEMONSTRATED",
            maturity="TESTED",
            source_events=[session_id],
            tags=["auto-extracted", "encouragement", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    return stored_ids


def _extract_user_text_from_record(record: dict[str, Any]) -> str:
    """Extract clean user text from a record (duplicate of session_analyzer helper)."""
    msg = record.get("message", {})
    content = msg.get("content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        content = " ".join(parts)
    if not isinstance(content, str):
        content = str(content)
    if "<system-reminder>" in content:
        content = content[: content.index("<system-reminder>")]
    return content.strip()


# ─── Knowledge Consolidation ─────────────────────────────────────────


def consolidate_related(min_cluster_size: int = 3) -> list[dict[str, Any]]:
    """Find and merge clusters of related knowledge entries.

    Groups entries by type, finds clusters with >50% word overlap,
    and merges clusters of min_cluster_size or more into single entries.

    Returns list of dicts describing what was merged:
        [{"type": "MISTAKE", "merged_count": 4, "new_id": "abc...", "content": "..."}]
    """
    merges: list[dict[str, Any]] = []

    for ktype in KNOWLEDGE_TYPES:
        entries = get_knowledge(knowledge_type=ktype, limit=500)
        if len(entries) < min_cluster_size:
            continue

        # Build clusters using word overlap
        clustered: set[str] = set()  # knowledge_ids already in a cluster
        clusters: list[list[dict[str, Any]]] = []

        for i, entry in enumerate(entries):
            if entry["knowledge_id"] in clustered:
                continue

            cluster = [entry]
            clustered.add(entry["knowledge_id"])

            for j in range(i + 1, len(entries)):
                other = entries[j]
                if other["knowledge_id"] in clustered:
                    continue
                overlap = _compute_overlap(entry["content"], other["content"])
                if overlap > 0.5:
                    cluster.append(other)
                    clustered.add(other["knowledge_id"])

            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)

        # Merge each cluster
        for cluster in clusters:
            # Pick the longest content as the base (most informative)
            cluster.sort(key=lambda e: len(e["content"]), reverse=True)
            best = cluster[0]

            # Combine sources and tags
            all_sources: list[str] = []
            all_tags: set[str] = set()
            max_confidence = 0.0
            for entry in cluster:
                all_sources.extend(entry["source_events"])
                all_tags.update(entry["tags"])
                max_confidence = max(max_confidence, entry["confidence"])

            all_tags.add("consolidated")
            all_tags.discard("")

            # Create the merged entry with unique content to avoid hash dedup
            merged_content = best["content"]
            source_count = len(cluster)
            # Append consolidation note to make content unique
            merged_content = f"{merged_content} [consolidated from {source_count} entries]"
            new_id = store_knowledge(
                knowledge_type=ktype,
                content=merged_content,
                confidence=max_confidence,
                source_events=list(set(all_sources)),
                tags=sorted(all_tags),
            )

            # Supersede the individual entries
            conn = _get_connection()
            try:
                for entry in cluster:
                    if entry["knowledge_id"] != new_id:
                        conn.execute(
                            "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                            (new_id, entry["knowledge_id"]),
                        )
                conn.commit()
            finally:
                conn.close()

            merges.append(
                {
                    "type": ktype,
                    "merged_count": len(cluster),
                    "new_id": new_id,
                    "content": merged_content[:100],
                },
            )

    return merges


# ─── Feedback Loop ────────────────────────────────────────────────────


def _adjust_confidence(
    knowledge_id: str,
    delta: float,
    floor: float = 0.1,
    cap: float = 1.0,
) -> float | None:
    """Adjust confidence on a knowledge entry in-place.

    This is metadata (belief strength), not content — so in-place update
    is appropriate (same pattern as record_access updating access_count).

    Returns the new confidence, or None if the entry doesn't exist.
    """
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT confidence FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
            (knowledge_id,),
        ).fetchone()
        if not row:
            return None

        new_conf = max(floor, min(cap, cast("float", row[0]) + delta))
        conn.execute(
            "UPDATE knowledge SET confidence = ?, updated_at = ? WHERE knowledge_id = ?",
            (new_conf, time.time(), knowledge_id),
        )
        conn.commit()
        return new_conf
    finally:
        conn.close()


def _resolve_lesson(lesson_id: str) -> None:
    """Mark a lesson as resolved."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE lesson_tracking SET status = 'resolved' WHERE lesson_id = ?",
            (lesson_id,),
        )
        conn.commit()
    finally:
        conn.close()


def compute_effectiveness(entry: dict[str, Any]) -> dict[str, Any]:
    """Compute effectiveness status for a knowledge entry.

    Returns {"status": "...", "detail": "..."} based on the entry's type
    and how it connects to lesson tracking and access patterns.
    """
    ktype = entry.get("knowledge_type", "")
    access = entry.get("access_count", 0)

    if ktype in ("MISTAKE", "BOUNDARY", "PRINCIPLE"):
        # Check if a lesson tracks this knowledge
        lessons = get_lessons()
        for lesson in lessons:
            overlap = _compute_overlap(entry.get("content", ""), lesson["description"])
            if overlap > 0.4:
                if lesson["status"] in ("improving", "resolved"):
                    return {
                        "status": "effective",
                        "detail": f"Lesson {lesson['status']} ({lesson['occurrences']} past occurrences)",
                    }
                if lesson["status"] == "active" and lesson["occurrences"] >= 3:
                    return {
                        "status": "recurring",
                        "detail": f"Still recurring ({lesson['occurrences']} occurrences)",
                    }
                if lesson["status"] == "active":
                    return {
                        "status": "active",
                        "detail": f"Tracked ({lesson['occurrences']} occurrences)",
                    }
        # No matching lesson — classify by usage instead of "unknown"
        if access > 3:
            return {"status": "stable", "detail": f"No lesson match but accessed {access} times"}
        if access > 0:
            return {"status": "used", "detail": f"Accessed {access} times, no lesson match"}
        return {"status": "unknown", "detail": "No lesson tracking data and never accessed"}

    if ktype in ("PATTERN", "PROCEDURE", "OBSERVATION"):
        if access > 3:
            return {"status": "reinforced", "detail": f"Confirmed {access} times"}
        if access > 0:
            return {"status": "used", "detail": f"Accessed {access} times"}
        return {"status": "unused", "detail": "Never accessed"}

    if ktype in ("PREFERENCE", "DIRECTION", "DIRECTIVE"):
        return {"status": "stable", "detail": "Directions and directives are always active"}

    if ktype == "FACT":
        if access > 0:
            return {"status": "used", "detail": f"Accessed {access} times"}
        return {"status": "unused", "detail": "Never accessed"}

    # EPISODE or unknown
    return {"status": "stable", "detail": "Record entry"}


def health_check() -> dict[str, Any]:
    """Review the knowledge store and adjust confidence scores.

    Knowledge does NOT decay just because time passed. A lesson that's
    true on day 1 is still true on day 100. Confidence only changes when:

    1. Confirmed: knowledge keeps coming up across sessions → trust more
    2. Recurring: a lesson happened 3+ times → it's clearly a real problem
    3. Resolved: an improving lesson hasn't come back in 30+ days → probably fixed
    4. Contradicted: a superseded entry already gets marked by update_knowledge
    """
    now = time.time()
    result = {
        "confirmed_boosted": 0,
        "recurring_escalated": 0,
        "resolved_lessons": 0,
        "total_checked": 0,
    }

    health_limit = 1000
    all_entries = get_knowledge(limit=health_limit)
    result["total_checked"] = len(all_entries)
    if len(all_entries) >= health_limit:
        logger.warning(
            f"Health check limited to {health_limit} entries — some entries may not be checked"
        )

    # 1. Confirmed boost — if something keeps coming up, it's clearly useful
    # Skip entries that are extraction noise — inflated access counts from
    # the old feedback loop should not keep boosting garbage.
    for entry in all_entries:
        if entry["access_count"] > 5 and entry["confidence"] < 1.0:
            if _is_extraction_noise(entry["content"], entry["knowledge_type"]):
                continue
            new_conf = _adjust_confidence(entry["knowledge_id"], 0.05, cap=1.0)
            if new_conf is not None:
                result["confirmed_boosted"] += 1

    # 2. Recurring lesson escalation — same mistake 3+ times = serious problem
    active_lessons = get_lessons(status="active")
    mistakes = [
        e for e in all_entries if e["knowledge_type"] in ("MISTAKE", "BOUNDARY", "PRINCIPLE")
    ]
    for lesson in active_lessons:
        if lesson["occurrences"] >= 3:
            for mistake in mistakes:
                overlap = _compute_overlap(lesson["description"], mistake["content"])
                if overlap > 0.4:
                    current = mistake["confidence"]
                    if current < 0.95:
                        _adjust_confidence(mistake["knowledge_id"], 0.95 - current)
                        result["recurring_escalated"] += 1
                    break

    # 3. Resolve old improving lessons — hasn't come back in 30 days = fixed
    improving_lessons = get_lessons(status="improving")
    for lesson in improving_lessons:
        age_days = (now - lesson["last_seen"]) / 86400
        if age_days > 30:
            _resolve_lesson(lesson["lesson_id"])
            result["resolved_lessons"] += 1
            # Gently lower the associated MISTAKE — the problem went away,
            # but the knowledge is still worth keeping in case it comes back
            for mistake in mistakes:
                overlap = _compute_overlap(lesson["description"], mistake["content"])
                if overlap > 0.4:
                    _adjust_confidence(mistake["knowledge_id"], -0.05, floor=0.5)
                    break

    # 4. Stale knowledge — unused entries lose confidence over time
    stale_count = 0
    temporal_decay_count = 0
    for entry in all_entries:
        # DIRECTIVE is permanent by design — immune to staleness
        if entry["knowledge_type"] == "DIRECTIVE":
            continue

        age_days = (now - entry["created_at"]) / 86400

        # Zero-access entries older than 30 days decay
        if age_days > 30 and entry["access_count"] == 0:
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.1, floor=0.2)
            if new_conf is not None:
                stale_count += 1

        # Time-sensitive language older than 14 days decays faster
        elif age_days > 14 and _has_temporal_markers(entry["content"]):
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.05, floor=0.3)
            if new_conf is not None:
                temporal_decay_count += 1

    # 5. High contradiction count — entries contradicted 3+ times are suspect
    contradiction_flagged = 0
    for entry in all_entries:
        if entry.get("contradiction_count", 0) >= 3 and entry["confidence"] > 0.4:
            _adjust_confidence(entry["knowledge_id"], -0.2, floor=0.3)
            contradiction_flagged += 1

    # 6. Abandoned knowledge — accessed but then left untouched for 14+ days
    abandoned_count = 0
    for entry in all_entries:
        if entry["knowledge_type"] == "DIRECTIVE":
            continue
        # Must have been accessed at least once (distinguishes from "never used")
        if entry["access_count"] < 1:
            continue
        # Check time since last update (proxy for last meaningful interaction)
        days_since_update = (now - entry["updated_at"]) / 86400
        if days_since_update > 14 and entry["confidence"] > 0.3:
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.02, floor=0.3)
            if new_conf is not None:
                abandoned_count += 1

    result["stale_decayed"] = stale_count
    result["temporal_decayed"] = temporal_decay_count
    result["contradiction_flagged"] = contradiction_flagged
    result["abandoned_decayed"] = abandoned_count

    # 7. Retroactive noise sweep — re-evaluate existing entries against
    # the current noise filter. Entries that slipped in before the filter
    # was improved get their confidence penalized (not deleted — append-only).
    noise_penalized = 0
    for entry in all_entries:
        # Already low confidence — no point penalizing further
        if entry["confidence"] <= 0.2:
            continue
        # Already superseded — leave it alone
        if entry.get("superseded_by"):
            continue
        if _is_extraction_noise(entry["content"], entry["knowledge_type"]):
            new_conf = _adjust_confidence(entry["knowledge_id"], -0.3, floor=0.1)
            if new_conf is not None:
                noise_penalized += 1
    result["noise_penalized"] = noise_penalized

    # 8. Maturity demotion — entries that reached high maturity through
    # inflated counts but now have low confidence should be demoted.
    # A CONFIRMED entry at 0.3 or below is not confirmed by any honest measure.
    demoted = 0
    conn = _get_connection()
    try:
        high_maturity = conn.execute(
            "SELECT knowledge_id, maturity, confidence FROM knowledge "
            "WHERE superseded_by IS NULL AND maturity IN ('CONFIRMED', 'TESTED', 'HYPOTHESIS')"
        ).fetchall()
        for kid, maturity, confidence in high_maturity:
            new_maturity = None
            if maturity == "CONFIRMED" and confidence < 0.8:
                new_maturity = "RAW"
            elif maturity == "TESTED" and confidence < 0.5:
                new_maturity = "RAW"
            elif maturity == "HYPOTHESIS" and confidence < 0.4:
                new_maturity = "RAW"
            if new_maturity:
                conn.execute(
                    "UPDATE knowledge SET maturity = ? WHERE knowledge_id = ?",
                    (new_maturity, kid),
                )
                demoted += 1
        if demoted:
            conn.commit()
    finally:
        conn.close()
    result["maturity_demoted"] = demoted

    return result


# Temporal markers that indicate time-sensitive content
_TEMPORAL_CONTENT_MARKERS = {
    "currently",
    "right now",
    "at the moment",
    "is broken",
    "is failing",
    "is down",
    "today",
    "this week",
    "this sprint",
    "in progress",
    "work in progress",
    "wip",
    "blocked on",
    "waiting for",
    "temporarily",
}


def _has_temporal_markers(content: str) -> bool:
    """Check if content has time-sensitive language that may become stale."""
    content_lower = content.lower()
    return any(marker in content_lower for marker in _TEMPORAL_CONTENT_MARKERS)


# ─── Knowledge Type Migration ────────────────────────────────────────


# How old types map to new types
_MIGRATION_RULES: dict[str, dict[str, Any]] = {
    "MISTAKE": {
        # Keywords that indicate a hard constraint → BOUNDARY
        "boundary_keywords": re.compile(
            r"\b(never|always|must|don't|do not|cannot|forbidden|prohibited)\b",
            re.IGNORECASE,
        ),
        "default": "PRINCIPLE",  # teaching/direction
        "boundary": "BOUNDARY",  # hard constraint
        "source": "CORRECTED",
        "default_maturity": "HYPOTHESIS",
        "boundary_maturity": "TESTED",
    },
    "PREFERENCE": {
        "new_type": "DIRECTION",
        "source": "STATED",
        "maturity": "CONFIRMED",
    },
    "PATTERN": {
        # Keywords indicating how-to → PROCEDURE
        "procedure_keywords": re.compile(
            r"\b(step|how to|process|workflow|first.*then|procedure)\b",
            re.IGNORECASE,
        ),
        "default": "PRINCIPLE",
        "procedure": "PROCEDURE",
        "source": "DEMONSTRATED",
        "maturity": "HYPOTHESIS",
    },
}


def migrate_knowledge_types(dry_run: bool = True) -> list[dict[str, Any]]:
    """Reclassify old-type entries (MISTAKE, PATTERN, PREFERENCE) to new types.

    Uses the supersede pattern: old entry gets superseded_by pointing to new entry.
    In dry_run mode, returns planned changes without writing anything.

    Returns list of {"old_id", "old_type", "new_type", "source", "maturity", "content"}.
    """
    planned: list[dict[str, Any]] = []

    for old_type, rules in _MIGRATION_RULES.items():
        entries = get_knowledge(knowledge_type=old_type, limit=1000)
        for entry in entries:
            content = entry["content"]

            # Skip noise and session-specific entries — don't promote them
            if _is_extraction_noise(content, old_type):
                continue
            from divineos.core.memory import _is_session_specific

            if _is_session_specific(content):
                continue

            if old_type == "MISTAKE":
                if rules["boundary_keywords"].search(content):
                    new_type = rules["boundary"]
                    maturity = rules["boundary_maturity"]
                else:
                    new_type = rules["default"]
                    maturity = rules["default_maturity"]
                source = rules["source"]

            elif old_type == "PREFERENCE":
                new_type = rules["new_type"]
                source = rules["source"]
                maturity = rules["maturity"]

            elif old_type == "PATTERN":
                if rules["procedure_keywords"].search(content):
                    new_type = rules["procedure"]
                else:
                    new_type = rules["default"]
                source = rules["source"]
                maturity = rules["maturity"]

            else:
                continue

            change = {
                "old_id": entry["knowledge_id"],
                "old_type": old_type,
                "new_type": new_type,
                "source": source,
                "maturity": maturity,
                "content": content[:200],
            }
            planned.append(change)

            if not dry_run:
                # Mark old entry as superseded FIRST (so store_knowledge
                # doesn't dedup against it via content_hash)
                placeholder = "migrating"
                conn = _get_connection()
                try:
                    conn.execute(
                        "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                        (placeholder, entry["knowledge_id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()

                try:
                    # Create new entry with new type
                    new_kid = store_knowledge(
                        knowledge_type=new_type,
                        content=content,
                        confidence=entry["confidence"],
                        source_events=entry.get("source_events", []),
                        tags=entry.get("tags", []),
                        source=source,
                        maturity=maturity,
                    )
                except Exception:
                    # Rollback: clear the placeholder so old entry isn't orphaned
                    conn = _get_connection()
                    try:
                        conn.execute(
                            "UPDATE knowledge SET superseded_by = NULL WHERE knowledge_id = ?",
                            (entry["knowledge_id"],),
                        )
                        conn.commit()
                    finally:
                        conn.close()
                    raise

                # Update superseded_by to point to actual new ID
                conn = _get_connection()
                try:
                    conn.execute(
                        "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                        (new_kid, entry["knowledge_id"]),
                    )
                    conn.commit()
                finally:
                    conn.close()
                change["new_id"] = new_kid

    return planned


# ─── Lesson Categorization ────────────────────────────────────────────

# Semantic lesson categories — corrections get mapped to these buckets
# based on keyword matching, instead of using raw word fragments.
_LESSON_CATEGORIES = (
    (
        "blind_coding",
        re.compile(
            r"\bblind|without reading|without checking|without looking|study.+first|"
            r"understand.+before|research.+first|don.t just|not blindly",
            re.IGNORECASE,
        ),
    ),
    (
        "incomplete_fix",
        re.compile(
            r"\bonly fixed one|didn.t fix|still broken|still fail|also fail|"
            r"missed.+other|forgot.+other|the rest",
            re.IGNORECASE,
        ),
    ),
    (
        "ignored_instruction",
        re.compile(
            r"\bdid you not see|did you not read|i already said|i told you|"
            r"i just said|not listening|ignoring what",
            re.IGNORECASE,
        ),
    ),
    (
        "wrong_scope",
        re.compile(
            r"\bi mean.+(?:in|the|this)|not that.+(?:this|the)|wrong (?:file|place|thing)|"
            r"\binstead of\b.+\d|folder.+instead",
            re.IGNORECASE,
        ),
    ),
    (
        "overreach",
        re.compile(
            r"\bnot supposed to|isnt supposed|shouldn.t (?:make|decide|choose)|"
            r"don.t (?:make|decide).+decision|"
            r"\btoo (?:much|far|complex)|over.?engineer|rabbit hole|scope",
            re.IGNORECASE,
        ),
    ),
    (
        "jargon_usage",
        re.compile(
            r"\bjargon|plain english|like.+(?:dumb|stupid|5|new)|break it down|"
            r"\bsimpl(?:e|ify|er)|not a coder|don.t speak",
            re.IGNORECASE,
        ),
    ),
    (
        "shallow_output",
        re.compile(
            r"\bdoesn.t feel|don.t feel|still feel|not.+(?:like people|real|alive|genuine)|"
            r"\bembody|more (?:life|depth|soul)|concise.+not.+concern|token limit",
            re.IGNORECASE,
        ),
    ),
    (
        "perspective_error",
        re.compile(
            r"\bpronoun|when i say you|say i or me|possessive|first person|"
            r"\bperspective|point of view",
            re.IGNORECASE,
        ),
    ),
    (
        "misunderstood",
        re.compile(
            r"\bno i mean|that.s not what|misunderst|wrong idea|confused about|"
            r"\bwhat i meant|trying to stop you|wasn.t denying",
            re.IGNORECASE,
        ),
    ),
)


def _categorize_correction(text: str) -> str | None:
    """Map a correction's text to a semantic lesson category.

    Returns None if no category matches (the correction is probably noise).
    """
    for category, pattern in _LESSON_CATEGORIES:
        if pattern.search(text):
            return category
    return None


def _is_noise_correction(text: str) -> bool:
    """Return True if a correction is noise — not a real lesson.

    Filters: too short, file path dumps, task notifications, forwarded
    messages that are instructions rather than corrections.
    """
    stripped = text.strip()

    # Too short to be meaningful
    if len(stripped) < 20:
        return True

    # Task notification XML
    if "<task-notification>" in stripped or "<task-id>" in stripped:
        return True

    # File path dump (starts with @ and a path)
    if stripped.startswith("@") and ("\\" in stripped[:60] or "/" in stripped[:60]):
        return True

    # Mostly file paths
    path_chars = stripped.count("\\") + stripped.count("/")
    return bool(path_chars > 5 and path_chars > len(stripped) / 20)


def clear_lessons() -> int:
    """Delete ALL lessons from lesson_tracking. Returns count deleted.

    Used to wipe garbage data and re-extract cleanly.
    """
    conn = _get_connection()
    try:
        count = cast("int", conn.execute("SELECT COUNT(*) FROM lesson_tracking").fetchone()[0])
        conn.execute("DELETE FROM lesson_tracking")
        conn.commit()
        return count
    finally:
        conn.close()


def apply_session_feedback(
    analysis: "Any",  # SessionAnalysis
    session_id: str,
) -> dict[str, Any]:
    """Compare new session findings against existing knowledge.

    Called after scan --store. Checks if corrections match existing MISTAKEs
    (recurrences), if encouragements confirm PATTERNs, and marks lessons
    as improving when no matching correction is found.

    Corrections are filtered for noise and categorized into semantic buckets
    before recording lessons.
    """
    result = {
        "recurrences_found": 0,
        "patterns_reinforced": 0,
        "lessons_improving": 0,
        "noise_skipped": 0,
    }

    corrections = getattr(analysis, "corrections", [])
    encouragements = getattr(analysis, "encouragements", [])

    # Step A: Check corrections against existing mistakes/boundaries/principles
    existing_corrections = []
    for ktype in ("MISTAKE", "BOUNDARY", "PRINCIPLE"):
        existing_corrections.extend(get_knowledge(knowledge_type=ktype, limit=200))

    for correction in corrections:
        # Skip noise
        if _is_noise_correction(correction.content):
            result["noise_skipped"] += 1
            continue

        for entry in existing_corrections:
            overlap = _compute_overlap(correction.content, entry["content"])
            if overlap > 0.4:
                _adjust_confidence(entry["knowledge_id"], 0.05, cap=1.0)
                result["recurrences_found"] += 1
                # Record in lesson tracking with semantic category
                category = _categorize_correction(correction.content)
                if category:
                    record_lesson(category, correction.content[:200], session_id)
                break

    # Step B: Check encouragements against existing patterns/principles
    existing_positives = []
    for ktype in ("PATTERN", "PRINCIPLE"):
        existing_positives.extend(get_knowledge(knowledge_type=ktype, limit=200))
    for enc in encouragements:
        for entry in existing_positives:
            overlap = _compute_overlap(enc.content, entry["content"])
            if overlap > 0.4:
                _adjust_confidence(entry["knowledge_id"], 0.05, cap=1.0)
                record_access(entry["knowledge_id"])
                result["patterns_reinforced"] += 1
                break

    # Step C: Mark lessons improving when no matching correction
    active_lessons = get_lessons(status="active")
    for lesson in active_lessons:
        recurred = False
        for correction in corrections:
            if _is_noise_correction(correction.content):
                continue
            overlap = _compute_overlap(correction.content, lesson["description"])
            if overlap > 0.4:
                recurred = True
                break
        if not recurred:
            mark_lesson_improving(lesson["category"], session_id)
            result["lessons_improving"] += 1

    return result


def knowledge_health_report() -> dict[str, Any]:
    """Aggregate effectiveness stats across all active knowledge."""
    entries = get_knowledge(limit=1000)
    by_status: dict[str, int] = {}
    by_type: dict[str, dict[str, int]] = {}

    for entry in entries:
        eff = compute_effectiveness(entry)
        status = eff["status"]
        ktype = entry["knowledge_type"]

        by_status[status] = by_status.get(status, 0) + 1
        if ktype not in by_type:
            by_type[ktype] = {}
        by_type[ktype][status] = by_type[ktype].get(status, 0) + 1

    return {
        "total": len(entries),
        "by_status": by_status,
        "by_type": by_type,
    }
