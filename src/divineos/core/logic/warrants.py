"""Warrant storage — structured justification for knowledge entries.

Every piece of knowledge should have a warrant: why do I believe this?
A warrant records the evidence (grounds), source session, backing chain,
and conditions under which the warrant could be defeated.

Warrant types:
- EMPIRICAL: observed directly in a session (tool output, test result)
- TESTIMONIAL: user stated it (corrections, preferences, directives)
- INFERENTIAL: derived from other knowledge via logical relations
- INHERITED: came from seed data, no session evidence

A warrant can be ACTIVE, DEFEATED (contradicted), or WITHDRAWN (manually).
"""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.knowledge import get_connection

_WARRANTS_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


# ─── Schema ──────────────────────────────────────────────────────────


def init_warrant_table() -> None:
    """Create the warrants table. Idempotent."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS warrants (
                warrant_id     TEXT PRIMARY KEY,
                knowledge_id   TEXT NOT NULL,
                warrant_type   TEXT NOT NULL,
                grounds        TEXT NOT NULL DEFAULT '',
                source_session TEXT DEFAULT NULL,
                source_events  TEXT NOT NULL DEFAULT '[]',
                backing_ids    TEXT NOT NULL DEFAULT '[]',
                defeaters      TEXT NOT NULL DEFAULT '[]',
                created_at     REAL NOT NULL,
                status         TEXT NOT NULL DEFAULT 'ACTIVE',
                FOREIGN KEY (knowledge_id) REFERENCES knowledge(knowledge_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_warrants_knowledge
            ON warrants(knowledge_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_warrants_status
            ON warrants(status)
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Types ───────────────────────────────────────────────────────────

WARRANT_TYPES = {"EMPIRICAL", "TESTIMONIAL", "INFERENTIAL", "INHERITED"}
WARRANT_STATUSES = {"ACTIVE", "DEFEATED", "WITHDRAWN"}


@dataclass
class Warrant:
    """Structured justification for a knowledge entry."""

    warrant_id: str
    knowledge_id: str
    warrant_type: str
    grounds: str
    source_session: str | None = None
    source_events: list[str] = field(default_factory=list)
    backing_ids: list[str] = field(default_factory=list)
    defeaters: list[str] = field(default_factory=list)
    created_at: float = 0.0
    status: str = "ACTIVE"

    def is_valid(self) -> bool:
        """A warrant is valid when active with non-empty grounds."""
        return self.status == "ACTIVE" and bool(self.grounds.strip())


# ─── CRUD ────────────────────────────────────────────────────────────


def create_warrant(
    knowledge_id: str,
    warrant_type: str,
    grounds: str,
    source_session: str | None = None,
    source_events: list[str] | None = None,
    backing_ids: list[str] | None = None,
) -> Warrant:
    """Create and store a new warrant for a knowledge entry."""
    if warrant_type not in WARRANT_TYPES:
        raise ValueError(f"Invalid warrant type: {warrant_type}. Must be one of {WARRANT_TYPES}")

    warrant = Warrant(
        warrant_id=str(uuid.uuid4()),
        knowledge_id=knowledge_id,
        warrant_type=warrant_type,
        grounds=grounds,
        source_session=source_session,
        source_events=source_events or [],
        backing_ids=backing_ids or [],
        created_at=time.time(),
    )

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO warrants
                (warrant_id, knowledge_id, warrant_type, grounds, source_session,
                 source_events, backing_ids, defeaters, created_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                warrant.warrant_id,
                warrant.knowledge_id,
                warrant.warrant_type,
                warrant.grounds,
                warrant.source_session,
                json.dumps(warrant.source_events),
                json.dumps(warrant.backing_ids),
                json.dumps(warrant.defeaters),
                warrant.created_at,
                warrant.status,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug(
        "Created {} warrant {} for knowledge {}",
        warrant_type,
        warrant.warrant_id[:8],
        knowledge_id[:8],
    )
    return warrant


def get_warrants(knowledge_id: str, status: str | None = None) -> list[Warrant]:
    """Get all warrants for a knowledge entry, optionally filtered by status."""
    conn = get_connection()
    try:
        if status:
            rows = conn.execute(
                "SELECT * FROM warrants WHERE knowledge_id = ? AND status = ? ORDER BY created_at",
                (knowledge_id, status),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM warrants WHERE knowledge_id = ? ORDER BY created_at",
                (knowledge_id,),
            ).fetchall()
    finally:
        conn.close()

    return [_row_to_warrant(row) for row in rows]


def get_warrant_by_id(warrant_id: str) -> Warrant | None:
    """Get a single warrant by ID."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM warrants WHERE warrant_id = ?", (warrant_id,)).fetchone()
    finally:
        conn.close()

    return _row_to_warrant(row) if row else None


def defeat_warrant(warrant_id: str, reason: str) -> bool:
    """Mark a warrant as defeated, recording the defeating reason."""
    conn = get_connection()
    try:
        warrant_row = conn.execute(
            "SELECT defeaters FROM warrants WHERE warrant_id = ?", (warrant_id,)
        ).fetchone()
        if not warrant_row:
            return False

        defeaters = json.loads(warrant_row[0])
        defeaters.append(reason)

        conn.execute(
            "UPDATE warrants SET status = 'DEFEATED', defeaters = ? WHERE warrant_id = ?",
            (json.dumps(defeaters), warrant_id),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug("Defeated warrant {}: {}", warrant_id[:8], reason)

    # Check if this defeat creates a recurring pattern worth learning from
    try:
        warrant = get_warrant_by_id(warrant_id)
        if warrant:
            from divineos.core.logic.defeat_lessons import check_defeat_pattern

            check_defeat_pattern(
                knowledge_id=warrant.knowledge_id,
                defeated_warrant_type=warrant.warrant_type,
            )
    except _WARRANTS_ERRORS as e:
        logger.debug("Defeat lesson check failed (non-fatal): {}", e)

    return True


def withdraw_warrant(warrant_id: str) -> bool:
    """Manually withdraw a warrant."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE warrants SET status = 'WITHDRAWN' WHERE warrant_id = ?",
            (warrant_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def has_valid_warrant(knowledge_id: str) -> bool:
    """Check if a knowledge entry has at least one active warrant with grounds."""
    warrants = get_warrants(knowledge_id, status="ACTIVE")
    return any(w.is_valid() for w in warrants)


def count_valid_warrants(knowledge_id: str) -> int:
    """Count the number of valid (active + grounded) warrants."""
    warrants = get_warrants(knowledge_id, status="ACTIVE")
    return sum(1 for w in warrants if w.is_valid())


# ─── Row Helpers ─────────────────────────────────────────────────────


def _row_to_warrant(row: tuple[Any, ...]) -> Warrant:
    """Convert a database row to a Warrant."""
    return Warrant(
        warrant_id=row[0],
        knowledge_id=row[1],
        warrant_type=row[2],
        grounds=row[3],
        source_session=row[4],
        source_events=json.loads(row[5]) if row[5] else [],
        backing_ids=json.loads(row[6]) if row[6] else [],
        defeaters=json.loads(row[7]) if row[7] else [],
        created_at=row[8],
        status=row[9],
    )
