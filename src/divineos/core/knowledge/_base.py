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


# Single source of truth for knowledge column names.
# Add a column here + add the ALTER TABLE migration = done.
# _row_to_dict, _KNOWLEDGE_COLS, and _KNOWLEDGE_COLS_K all derive from this list.
_KNOWLEDGE_COL_NAMES: list[str] = [
    "knowledge_id",
    "created_at",
    "updated_at",
    "knowledge_type",
    "content",
    "confidence",
    "source_events",
    "tags",
    "access_count",
    "superseded_by",
    "content_hash",
    "source",
    "maturity",
    "corroboration_count",
    "contradiction_count",
    "valid_from",
    "valid_until",
    "layer",
    "source_entity",
    "related_to",
]

_KNOWLEDGE_COLS = ", ".join(_KNOWLEDGE_COL_NAMES)
_KNOWLEDGE_COLS_K = ", ".join(f"k.{c}" for c in _KNOWLEDGE_COL_NAMES)

# Columns that store JSON and need parsing on read
_JSON_COLS = frozenset({"source_events", "tags"})

# Columns that should be cast to int on read
_INT_COLS = frozenset({"corroboration_count", "contradiction_count"})

# Default values for columns that may be missing in old schemas
_KNOWLEDGE_DEFAULTS: dict[str, Any] = {
    "source": "INHERITED",
    "maturity": "RAW",
    "corroboration_count": 0,
    "contradiction_count": 0,
    "valid_from": None,
    "valid_until": None,
    "layer": "active",
    "source_entity": None,
    "related_to": None,
}


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

        # Layer column (active/archive stratification)
        try:
            conn.execute(
                "ALTER TABLE knowledge ADD COLUMN layer TEXT DEFAULT 'active'",
            )
        except sqlite3.OperationalError as e:
            logger.debug(f"Column layer already exists in knowledge table: {e}")

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
    """Convert a knowledge table row to a dict.

    Column mapping is derived from _KNOWLEDGE_COL_NAMES — no hardcoded
    indices. Adding a column to the list is all that's needed.
    """
    d: dict[str, Any] = {}
    for i, name in enumerate(_KNOWLEDGE_COL_NAMES):
        if i < len(row):
            val = row[i]
            if name in _JSON_COLS:
                val = json.loads(val) if val else []
            elif name in _INT_COLS and val is not None:
                val = int(val)
            d[name] = val
        else:
            # Column not present in this row (old schema) — use default
            d[name] = _KNOWLEDGE_DEFAULTS.get(name)
    return d


_LESSON_COL_NAMES: list[str] = [
    "lesson_id",
    "created_at",
    "category",
    "description",
    "first_session",
    "occurrences",
    "last_seen",
    "sessions",
    "status",
    "content_hash",
    "agent",
]

_LESSON_JSON_COLS = frozenset({"sessions"})

_LESSON_DEFAULTS: dict[str, Any] = {
    "agent": "unknown",
    "regressions": 0,
}


def _lesson_row_to_dict(row: tuple[Any, ...]) -> dict[str, Any]:
    """Convert a lesson_tracking table row to a dict.

    Column mapping derived from _LESSON_COL_NAMES — no hardcoded indices.
    """
    d: dict[str, Any] = {}
    for i, name in enumerate(_LESSON_COL_NAMES):
        if i < len(row):
            val = row[i]
            if name in _LESSON_JSON_COLS:
                val = json.loads(val) if val else []
            d[name] = val
        else:
            d[name] = _LESSON_DEFAULTS.get(name)
    # regressions may be at the end if the column exists
    if len(row) > len(_LESSON_COL_NAMES):
        d["regressions"] = row[len(_LESSON_COL_NAMES)]
    elif "regressions" not in d:
        d["regressions"] = 0
    return d
