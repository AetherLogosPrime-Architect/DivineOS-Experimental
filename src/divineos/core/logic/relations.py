"""Typed logical relations between knowledge entries.

Edges in a knowledge graph. Each relation says "entry A relates to entry B
in this specific way" with a confidence score and optional warrant.

Relation types:
- IMPLIES: if A is true, B follows
- CONTRADICTS: A and B cannot both be true
- REQUIRES: A depends on B being true
- SUPPORTS: A provides evidence for B (weaker than IMPLIES)
- GENERALIZES: A is a broader version of B
- SPECIALIZES: A is a narrower case of B
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

from loguru import logger

from divineos.core.knowledge import get_connection


# ─── Schema ──────────────────────────────────────────────────────────


def init_relation_table() -> None:
    """Create the logical_relations table. Idempotent."""
    conn = get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS logical_relations (
                relation_id   TEXT PRIMARY KEY,
                source_id     TEXT NOT NULL,
                target_id     TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                confidence    REAL NOT NULL DEFAULT 1.0,
                warrant_id    TEXT DEFAULT NULL,
                created_at    REAL NOT NULL,
                status        TEXT NOT NULL DEFAULT 'ACTIVE',
                notes         TEXT NOT NULL DEFAULT '',
                FOREIGN KEY (source_id) REFERENCES knowledge(knowledge_id),
                FOREIGN KEY (target_id) REFERENCES knowledge(knowledge_id)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relations_source
            ON logical_relations(source_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relations_target
            ON logical_relations(target_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_relations_type
            ON logical_relations(relation_type)
        """)
        conn.commit()
    finally:
        conn.close()


# ─── Types ───────────────────────────────────────────────────────────

RELATION_TYPES = {
    "IMPLIES",
    "CONTRADICTS",
    "REQUIRES",
    "SUPPORTS",
    "GENERALIZES",
    "SPECIALIZES",
}

# Inverse mapping — if A→B is X, then B→A is Y
INVERSE_RELATIONS = {
    "IMPLIES": "REQUIRES",
    "REQUIRES": "IMPLIES",
    "CONTRADICTS": "CONTRADICTS",
    "SUPPORTS": "SUPPORTS",
    "GENERALIZES": "SPECIALIZES",
    "SPECIALIZES": "GENERALIZES",
}


@dataclass
class LogicalRelation:
    """A typed edge between two knowledge entries."""

    relation_id: str
    source_id: str
    target_id: str
    relation_type: str
    confidence: float = 1.0
    warrant_id: str | None = None
    created_at: float = 0.0
    status: str = "ACTIVE"
    notes: str = ""


# ─── CRUD ────────────────────────────────────────────────────────────


def create_relation(
    source_id: str,
    target_id: str,
    relation_type: str,
    confidence: float = 1.0,
    warrant_id: str | None = None,
    notes: str = "",
) -> LogicalRelation:
    """Create a logical relation between two knowledge entries."""
    if relation_type not in RELATION_TYPES:
        raise ValueError(f"Invalid relation type: {relation_type}. Must be one of {RELATION_TYPES}")
    if source_id == target_id:
        raise ValueError("Cannot create a relation from a knowledge entry to itself")
    if not 0.0 <= confidence <= 1.0:
        raise ValueError(f"Confidence must be between 0.0 and 1.0, got {confidence}")

    # Check for duplicate
    existing = find_relation(source_id, target_id, relation_type)
    if existing:
        logger.debug(
            "Relation {} already exists between {} and {}",
            relation_type,
            source_id[:8],
            target_id[:8],
        )
        return existing

    rel = LogicalRelation(
        relation_id=str(uuid.uuid4()),
        source_id=source_id,
        target_id=target_id,
        relation_type=relation_type,
        confidence=confidence,
        warrant_id=warrant_id,
        created_at=time.time(),
        notes=notes,
    )

    conn = get_connection()
    try:
        conn.execute(
            """
            INSERT INTO logical_relations
                (relation_id, source_id, target_id, relation_type, confidence,
                 warrant_id, created_at, status, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                rel.relation_id,
                rel.source_id,
                rel.target_id,
                rel.relation_type,
                rel.confidence,
                rel.warrant_id,
                rel.created_at,
                rel.status,
                rel.notes,
            ),
        )
        conn.commit()
    finally:
        conn.close()

    logger.debug(
        "Created relation {} --{}-> {}",
        source_id[:8],
        relation_type,
        target_id[:8],
    )
    return rel


def find_relation(source_id: str, target_id: str, relation_type: str) -> LogicalRelation | None:
    """Find an existing active relation between two entries of a given type."""
    conn = get_connection()
    try:
        row = conn.execute(
            """
            SELECT * FROM logical_relations
            WHERE source_id = ? AND target_id = ? AND relation_type = ? AND status = 'ACTIVE'
            """,
            (source_id, target_id, relation_type),
        ).fetchone()
    finally:
        conn.close()

    return _row_to_relation(row) if row else None


def get_relations(
    knowledge_id: str,
    direction: str = "both",
    relation_type: str | None = None,
) -> list[LogicalRelation]:
    """Get all active relations for a knowledge entry.

    direction: "outgoing" (source=id), "incoming" (target=id), or "both".
    """
    conn = get_connection()
    try:
        results: list[LogicalRelation] = []

        if direction in ("outgoing", "both"):
            if relation_type:
                rows = conn.execute(
                    "SELECT * FROM logical_relations WHERE source_id = ? AND relation_type = ? AND status = 'ACTIVE'",
                    (knowledge_id, relation_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM logical_relations WHERE source_id = ? AND status = 'ACTIVE'",
                    (knowledge_id,),
                ).fetchall()
            results.extend(_row_to_relation(r) for r in rows)

        if direction in ("incoming", "both"):
            if relation_type:
                rows = conn.execute(
                    "SELECT * FROM logical_relations WHERE target_id = ? AND relation_type = ? AND status = 'ACTIVE'",
                    (knowledge_id, relation_type),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM logical_relations WHERE target_id = ? AND status = 'ACTIVE'",
                    (knowledge_id,),
                ).fetchall()
            results.extend(_row_to_relation(r) for r in rows)

        return results
    finally:
        conn.close()


def deactivate_relation(relation_id: str) -> bool:
    """Deactivate a relation (soft delete)."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE logical_relations SET status = 'INACTIVE' WHERE relation_id = ?",
            (relation_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_neighbors(
    knowledge_id: str, relation_type: str | None = None, max_depth: int = 1
) -> list[str]:
    """Get IDs of knowledge entries connected within max_depth hops.

    Breadth-first traversal. Returns unique IDs excluding the start node.
    """
    visited: set[str] = {knowledge_id}
    frontier: set[str] = {knowledge_id}
    result: list[str] = []

    for _ in range(max_depth):
        next_frontier: set[str] = set()
        for node_id in frontier:
            relations = get_relations(node_id, direction="both", relation_type=relation_type)
            for rel in relations:
                neighbor = rel.target_id if rel.source_id == node_id else rel.source_id
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
                    result.append(neighbor)
        frontier = next_frontier
        if not frontier:
            break

    return result


# ─── Row Helpers ─────────────────────────────────────────────────────


def _row_to_relation(row: tuple[Any, ...]) -> LogicalRelation:
    """Convert a database row to a LogicalRelation."""
    return LogicalRelation(
        relation_id=row[0],
        source_id=row[1],
        target_id=row[2],
        relation_type=row[3],
        confidence=row[4],
        warrant_id=row[5],
        created_at=row[6],
        status=row[7],
        notes=row[8],
    )
