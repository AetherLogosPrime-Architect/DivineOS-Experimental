"""Personal Memory — The AI's Mind.

Two tiers on top of the knowledge store:

1. Core Memory: 8 fixed slots (identity, purpose, style, etc.)
   Always loaded. Rarely changes. ~200 words total.

2. Active Memory: Ranked view into the knowledge store.
   Everything that passes an importance threshold. No hard cap.
   Ranked by importance so the most critical stuff surfaces first.

The knowledge store is the archive. Personal memory is what matters.
"""

import sqlite3
import time

from divineos.core.ledger import get_connection, compute_hash

# ─── Core Memory Slots ───────────────────────────────────────────────

CORE_SLOTS = (
    "user_identity",
    "project_purpose",
    "communication_style",
    "current_priorities",
    "active_constraints",
    "known_strengths",
    "known_weaknesses",
    "relationship_context",
)


_get_connection = get_connection


def init_memory_tables() -> None:
    """Create core_memory and active_memory tables if they don't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS core_memory (
                slot_id      TEXT PRIMARY KEY,
                content      TEXT NOT NULL,
                updated_at   REAL NOT NULL,
                content_hash TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS active_memory (
                memory_id     TEXT PRIMARY KEY,
                knowledge_id  TEXT NOT NULL,
                importance    REAL NOT NULL DEFAULT 0.5,
                reason        TEXT NOT NULL,
                promoted_at   REAL NOT NULL,
                surface_count INTEGER NOT NULL DEFAULT 0,
                pinned        INTEGER NOT NULL DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_active_importance
            ON active_memory(importance DESC)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_active_knowledge
            ON active_memory(knowledge_id)
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS personal_journal (
                entry_id    TEXT PRIMARY KEY,
                content     TEXT NOT NULL,
                created_at  REAL NOT NULL,
                context     TEXT NOT NULL DEFAULT ''
            )
        """)
        # Add columns that may not exist on older databases
        for col, defn in [
            ("linked_knowledge_id", "TEXT DEFAULT NULL"),
            ("tags", "TEXT NOT NULL DEFAULT ''"),
        ]:
            try:
                conn.execute(f"ALTER TABLE personal_journal ADD COLUMN {col} {defn}")
            except sqlite3.OperationalError:
                pass  # column already exists
        # FTS5 index for journal full-text search
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS journal_fts
            USING fts5(content, context, tags, content=personal_journal, content_rowid=rowid)
        """)
        # Triggers to keep FTS in sync
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS journal_fts_insert
            AFTER INSERT ON personal_journal BEGIN
                INSERT INTO journal_fts(rowid, content, context, tags)
                VALUES (NEW.rowid, NEW.content, NEW.context, NEW.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS journal_fts_delete
            AFTER DELETE ON personal_journal BEGIN
                INSERT INTO journal_fts(journal_fts, rowid, content, context, tags)
                VALUES ('delete', OLD.rowid, OLD.content, OLD.context, OLD.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS journal_fts_update
            AFTER UPDATE ON personal_journal BEGIN
                INSERT INTO journal_fts(journal_fts, rowid, content, context, tags)
                VALUES ('delete', OLD.rowid, OLD.content, OLD.context, OLD.tags);
                INSERT INTO journal_fts(rowid, content, context, tags)
                VALUES (NEW.rowid, NEW.content, NEW.context, NEW.tags);
            END;
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Core Memory ─────────────────────────────────────────────────────


def set_core(slot_id: str, content: str) -> None:
    """Set a core memory slot. Overwrites if exists."""
    if slot_id not in CORE_SLOTS:
        raise ValueError(f"Unknown slot '{slot_id}'. Valid: {', '.join(CORE_SLOTS)}")
    conn = _get_connection()
    try:
        conn.execute(
            """INSERT INTO core_memory (slot_id, content, updated_at, content_hash)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(slot_id) DO UPDATE SET
                 content = excluded.content,
                 updated_at = excluded.updated_at,
                 content_hash = excluded.content_hash""",
            (slot_id, content, time.time(), compute_hash(content)),
        )
        conn.commit()
    finally:
        conn.close()


def get_core(slot_id: str | None = None) -> dict[str, str]:
    """Get core memory. One slot or all. Returns {slot_id: content}."""
    conn = _get_connection()
    try:
        if slot_id:
            row = conn.execute(
                "SELECT slot_id, content FROM core_memory WHERE slot_id = ?",
                (slot_id,),
            ).fetchone()
            return {row[0]: row[1]} if row else {}
        rows = conn.execute(
            "SELECT slot_id, content FROM core_memory ORDER BY slot_id",
        ).fetchall()
        return {r[0]: r[1] for r in rows}
    finally:
        conn.close()


def clear_core(slot_id: str) -> bool:
    """Clear a core memory slot. Returns True if it existed."""
    if slot_id not in CORE_SLOTS:
        raise ValueError(f"Unknown slot '{slot_id}'. Valid: {', '.join(CORE_SLOTS)}")
    conn = _get_connection()
    try:
        cursor = conn.execute("DELETE FROM core_memory WHERE slot_id = ?", (slot_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def format_core() -> str:
    """Format all core memory as a text block for context injection."""
    slots = get_core()
    if not slots:
        return ""

    slot_labels = {
        "user_identity": "User",
        "project_purpose": "Project",
        "communication_style": "Communication",
        "current_priorities": "Priorities",
        "active_constraints": "Constraints",
        "known_strengths": "Strengths",
        "known_weaknesses": "Watch out for",
        "relationship_context": "Relationship",
    }

    lines = ["## Core Memory\n"]
    for slot_id in CORE_SLOTS:
        if slot_id in slots:
            label = slot_labels.get(slot_id, slot_id)
            lines.append(f"- **{label}:** {slots[slot_id]}")

    return "\n".join(lines)


# ─── Re-exports from active_memory.py ────────────────────────────────
# Active memory operations were extracted to active_memory.py to keep this
# file under 500 lines. Re-export here so existing imports still work.
from divineos.core.active_memory import (  # noqa: F401, E402
    TYPOGRAPHIC_REPLACEMENTS,
    _is_session_specific,
    _safe_text,
    compute_importance,
    demote_from_active,
    format_recall,
    get_active_memory,
    promote_to_active,
    recall,
    refresh_active_memory,
)
