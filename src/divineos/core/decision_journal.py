"""Decision Journal — Captures the WHY behind choices.

Not a changelog. Not a log of what happened. This captures moments
that shift understanding — the reasoning behind decisions, the
alternatives rejected, the context that would otherwise evaporate.

Searchable by future sessions so when I face a similar crossroads,
I can find the reasoning, not just the outcome.
"""

import json
import sqlite3
import time
import uuid
from typing import Any, cast

from divineos.core.affect import _affect_row_to_dict, get_recent_affect
from divineos.core.memory import _get_connection


# Weight thresholds for emotional significance
WEIGHT_ROUTINE = 1  # everyday technical choice
WEIGHT_SIGNIFICANT = 2  # architectural decision, trade-off
WEIGHT_PARADIGM = 3  # changes how I understand something


def init_decision_journal() -> None:
    """Create the decision_journal table and FTS index if they don't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decision_journal (
                decision_id     TEXT PRIMARY KEY,
                created_at      REAL NOT NULL,
                content         TEXT NOT NULL,
                reasoning       TEXT NOT NULL DEFAULT '',
                alternatives    TEXT NOT NULL DEFAULT '[]',
                context         TEXT NOT NULL DEFAULT '',
                emotional_weight INTEGER NOT NULL DEFAULT 1,
                tags            TEXT NOT NULL DEFAULT '[]',
                linked_knowledge_ids TEXT NOT NULL DEFAULT '[]',
                session_id      TEXT NOT NULL DEFAULT '',
                tension         TEXT NOT NULL DEFAULT '',
                almost          TEXT NOT NULL DEFAULT ''
            )
        """)
        # Migrate existing tables: add tension/almost columns if missing
        try:
            conn.execute("ALTER TABLE decision_journal ADD COLUMN tension TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
        try:
            conn.execute("ALTER TABLE decision_journal ADD COLUMN almost TEXT NOT NULL DEFAULT ''")
        except sqlite3.OperationalError:
            pass  # column already exists
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS decision_fts
            USING fts5(
                content, reasoning, alternatives, context, tags,
                content=decision_journal, content_rowid=rowid
            )
        """)
        conn.executescript("""
            CREATE TRIGGER IF NOT EXISTS decision_fts_insert
            AFTER INSERT ON decision_journal BEGIN
                INSERT INTO decision_fts(rowid, content, reasoning, alternatives, context, tags)
                VALUES (NEW.rowid, NEW.content, NEW.reasoning, NEW.alternatives, NEW.context, NEW.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS decision_fts_update
            AFTER UPDATE ON decision_journal BEGIN
                INSERT INTO decision_fts(decision_fts, rowid, content, reasoning, alternatives, context, tags)
                VALUES ('delete', OLD.rowid, OLD.content, OLD.reasoning, OLD.alternatives, OLD.context, OLD.tags);
                INSERT INTO decision_fts(rowid, content, reasoning, alternatives, context, tags)
                VALUES (NEW.rowid, NEW.content, NEW.reasoning, NEW.alternatives, NEW.context, NEW.tags);
            END;
            CREATE TRIGGER IF NOT EXISTS decision_fts_delete
            AFTER DELETE ON decision_journal BEGIN
                INSERT INTO decision_fts(decision_fts, rowid, content, reasoning, alternatives, context, tags)
                VALUES ('delete', OLD.rowid, OLD.content, OLD.reasoning, OLD.alternatives, OLD.context, OLD.tags);
            END;
        """)
        conn.commit()
    finally:
        conn.close()


def record_decision(
    content: str,
    reasoning: str = "",
    alternatives: list[str] | None = None,
    context: str = "",
    emotional_weight: int = WEIGHT_ROUTINE,
    tags: list[str] | None = None,
    linked_knowledge_ids: list[str] | None = None,
    session_id: str = "",
    tension: str = "",
    almost: str = "",
) -> str:
    """Record a decision with its full reasoning context. Returns the decision ID.

    This is for moments that matter — choices made, realizations had,
    understanding that shifted. The reasoning field is the heart of it:
    WHY this, not something else.

    Counterfactual fields (optional but valuable):
        tension: The competing principles or values at play.
        almost: What I almost did instead, and why I didn't.
    """
    init_decision_journal()
    decision_id = str(uuid.uuid4())
    weight = max(WEIGHT_ROUTINE, min(WEIGHT_PARADIGM, emotional_weight))

    conn = _get_connection()
    try:
        conn.execute(
            "INSERT INTO decision_journal "
            "(decision_id, created_at, content, reasoning, alternatives, "
            "context, emotional_weight, tags, linked_knowledge_ids, session_id, "
            "tension, almost) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                decision_id,
                time.time(),
                content,
                reasoning,
                json.dumps(alternatives or []),
                context,
                weight,
                json.dumps(tags or []),
                json.dumps(linked_knowledge_ids or []),
                session_id,
                tension,
                almost,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    # Auto-link the most recent affect state if one exists within 5 minutes
    try:
        recent = get_recent_affect(within_seconds=300.0)
        if recent and not recent.get("linked_decision_id"):
            conn = _get_connection()
            try:
                conn.execute(
                    "UPDATE affect_log SET linked_decision_id = ? WHERE entry_id = ?",
                    (decision_id, recent["entry_id"]),
                )
                conn.commit()
            finally:
                conn.close()
    except (ImportError, sqlite3.OperationalError):
        pass  # affect_log table may not exist yet

    return decision_id


def get_affect_at_decision(decision_id: str) -> dict[str, Any] | None:
    """Find the closest affect state to when a decision was made."""
    init_decision_journal()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT created_at FROM decision_journal WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        if not row:
            return None
        decision_time = row[0]

        affect_row = conn.execute(
            "SELECT entry_id, created_at, valence, arousal, dominance, description, trigger, "
            "tags, linked_claim_id, linked_decision_id, linked_knowledge_id, session_id "
            "FROM affect_log "
            "ORDER BY ABS(created_at - ?) LIMIT 1",
            (decision_time,),
        ).fetchone()
    except sqlite3.OperationalError:
        return None  # affect_log table doesn't exist
    finally:
        conn.close()
    if not affect_row:
        return None
    return _affect_row_to_dict(affect_row)


def list_decisions(
    limit: int = 20,
    min_weight: int = 0,
) -> list[dict[str, Any]]:
    """Get decisions, newest first. Optionally filter by minimum emotional weight."""
    init_decision_journal()
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT decision_id, created_at, content, reasoning, alternatives, "
            "context, emotional_weight, tags, linked_knowledge_ids, session_id, "
            "tension, almost "
            "FROM decision_journal "
            "WHERE emotional_weight >= ? "
            "ORDER BY created_at DESC LIMIT ?",
            (min_weight, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def search_decisions(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """Full-text search across all decision fields — content, reasoning, alternatives, context."""
    init_decision_journal()
    safe_query = " ".join(f'"{t}"' for t in query.split() if t)
    if not safe_query:
        return []
    conn = _get_connection()
    try:
        rows = conn.execute(
            "SELECT d.decision_id, d.created_at, d.content, d.reasoning, "
            "d.alternatives, d.context, d.emotional_weight, d.tags, "
            "d.linked_knowledge_ids, d.session_id, d.tension, d.almost "
            "FROM decision_fts f "
            "JOIN decision_journal d ON f.rowid = d.rowid "
            "WHERE decision_fts MATCH ? "
            "ORDER BY rank "
            "LIMIT ?",
            (safe_query, limit),
        ).fetchall()
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]


def get_decision(decision_id: str) -> dict[str, Any] | None:
    """Get a single decision by ID (supports short IDs)."""
    init_decision_journal()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT decision_id, created_at, content, reasoning, alternatives, "
            "context, emotional_weight, tags, linked_knowledge_ids, session_id, "
            "tension, almost "
            "FROM decision_journal WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        if not row:
            row = conn.execute(
                "SELECT decision_id, created_at, content, reasoning, alternatives, "
                "context, emotional_weight, tags, linked_knowledge_ids, session_id, "
                "tension, almost "
                "FROM decision_journal WHERE decision_id LIKE ?",
                (f"{decision_id}%",),
            ).fetchone()
    finally:
        conn.close()
    return _row_to_dict(row) if row else None


def count_decisions() -> int:
    """Count total decisions recorded."""
    init_decision_journal()
    conn = _get_connection()
    try:
        return cast(int, conn.execute("SELECT COUNT(*) FROM decision_journal").fetchone()[0])
    finally:
        conn.close()


def get_paradigm_shifts(limit: int = 10) -> list[dict[str, Any]]:
    """Get only the highest-weight decisions — the ones that changed everything."""
    return list_decisions(limit=limit, min_weight=WEIGHT_PARADIGM)


def link_knowledge(decision_id: str, knowledge_id: str) -> bool:
    """Add a knowledge ID to a decision's linked_knowledge_ids."""
    init_decision_journal()
    conn = _get_connection()
    try:
        row = conn.execute(
            "SELECT linked_knowledge_ids FROM decision_journal WHERE decision_id = ?",
            (decision_id,),
        ).fetchone()
        if not row:
            return False
        existing: list[str] = json.loads(row[0]) if row[0] else []
        if knowledge_id not in existing:
            existing.append(knowledge_id)
            conn.execute(
                "UPDATE decision_journal SET linked_knowledge_ids = ? WHERE decision_id = ?",
                (json.dumps(existing), decision_id),
            )
            conn.commit()
        return True
    finally:
        conn.close()


def _row_to_dict(row: tuple[Any, ...] | sqlite3.Row) -> dict[str, Any]:
    """Convert a DB row to a decision dict."""
    d = {
        "decision_id": row[0],
        "created_at": row[1],
        "content": row[2],
        "reasoning": row[3],
        "alternatives": json.loads(row[4]) if row[4] else [],
        "context": row[5],
        "emotional_weight": row[6],
        "tags": json.loads(row[7]) if row[7] else [],
        "linked_knowledge_ids": json.loads(row[8]) if row[8] else [],
        "session_id": row[9],
        "tension": row[10] if len(row) > 10 else "",
        "almost": row[11] if len(row) > 11 else "",
    }
    return d
