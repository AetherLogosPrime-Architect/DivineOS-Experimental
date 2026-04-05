"""Knowledge base — constants, schema, DB connection, row helpers."""

import json
import sqlite3
from typing import Any

from loguru import logger

import divineos.core.ledger as _ledger_mod

# ─── Constants ───────────────────────────────────────────────────────

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
    # User style/approach preferences ("use X", "prefer Y", "I like Z")
    "PREFERENCE",
    # User operational instructions ("always X", "never Y", "before X do Y")
    "INSTRUCTION",
    # Legacy types (still accepted, new code should not create these)
    "PATTERN",
    "MISTAKE",
}

KNOWLEDGE_SOURCES = {"STATED", "CORRECTED", "DEMONSTRATED", "SYNTHESIZED", "INHERITED"}

KNOWLEDGE_MATURITY = {"RAW", "HYPOTHESIS", "TESTED", "CONFIRMED", "REVISED"}


_KNOWLEDGE_COLS = (
    "knowledge_id, created_at, updated_at, knowledge_type, content, "
    "confidence, source_events, tags, access_count, superseded_by, content_hash, "
    "source, maturity, corroboration_count, contradiction_count, "
    "valid_from, valid_until, layer, source_entity, related_to"
)

_KNOWLEDGE_COLS_K = (
    "k.knowledge_id, k.created_at, k.updated_at, k.knowledge_type, k.content, "
    "k.confidence, k.source_events, k.tags, k.access_count, k.superseded_by, k.content_hash, "
    "k.source, k.maturity, k.corroboration_count, k.contradiction_count, "
    "k.valid_from, k.valid_until, k.layer, k.source_entity, k.related_to"
)


# ─── DB Connection ───────────────────────────────────────────────────


def compute_hash(content: str) -> str:
    """Delegate to ledger's hash function."""
    return _ledger_mod.compute_hash(content)


def _get_connection() -> sqlite3.Connection:
    """Returns a connection to the ledger database."""
    return _ledger_mod.get_connection()


# Public alias — use this from modules outside core/knowledge/
get_connection = _get_connection


# ─── Schema ──────────────────────────────────────────────────────────


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

        # Provenance columns (cross-entity attribution and manual linking)
        for col, col_type, default in [
            ("source_entity", "TEXT", "NULL"),
            ("related_to", "TEXT", "NULL"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE knowledge ADD COLUMN {col} {col_type} DEFAULT {default}",
                )
            except sqlite3.OperationalError as e:
                logger.debug(f"Column {col} already exists in knowledge table: {e}")

        # Temporal dimension columns (nullable — NULL means unbounded)
        for col, col_type, default in [
            ("valid_from", "REAL", "NULL"),
            ("valid_until", "REAL", "NULL"),
        ]:
            try:
                conn.execute(
                    f"ALTER TABLE knowledge ADD COLUMN {col} {col_type} DEFAULT {default}",
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


# ─── Row Helpers ─────────────────────────────────────────────────────


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
    # Provenance columns (source_entity at 18, related_to at 19)
    if len(row) > 18:
        d["source_entity"] = row[18]
        d["related_to"] = row[19] if len(row) > 19 else None
    else:
        d["source_entity"] = None
        d["related_to"] = None
    return d


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
    if len(row) > 11:
        d["regressions"] = row[11]
    else:
        d["regressions"] = 0
    return d
