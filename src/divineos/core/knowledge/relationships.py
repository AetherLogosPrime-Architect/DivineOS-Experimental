"""Knowledge Relationships — typed edges between knowledge entries.

Knowledge doesn't exist in isolation. A MISTAKE might be CAUSED_BY a
PROCEDURE. A PRINCIPLE might be SUPPORTED_BY multiple OBSERVATIONs.
This module tracks those connections so I can navigate my own knowledge
graph rather than treating it as a flat list.
"""

import time
import uuid
from typing import Any

from divineos.core.knowledge._base import _get_connection

# Valid relationship types
RELATIONSHIP_TYPES = {
    "CAUSED_BY",  # A was caused by B
    "SUPPORTS",  # A provides evidence for B
    "CONTRADICTS",  # A contradicts B
    "ELABORATES",  # A adds detail to B
    "SUPERSEDES",  # A replaces B (different from superseded_by column — that's linear)
    "RELATED_TO",  # A is related to B (general)
    "DERIVED_FROM",  # A was derived from B
    "APPLIES_TO",  # A applies in context of B
}


def init_relationship_table() -> None:
    """Create the knowledge_relationships table if it doesn't exist."""
    conn = _get_connection()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_relationships (
                relationship_id TEXT PRIMARY KEY,
                source_id       TEXT NOT NULL,
                target_id       TEXT NOT NULL,
                relationship    TEXT NOT NULL,
                created_at      REAL NOT NULL,
                notes           TEXT NOT NULL DEFAULT '',
                UNIQUE(source_id, target_id, relationship)
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rel_source
            ON knowledge_relationships(source_id)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_rel_target
            ON knowledge_relationships(target_id)
        """)
        conn.commit()
    finally:
        conn.close()


def add_relationship(
    source_id: str,
    target_id: str,
    relationship: str,
    notes: str = "",
) -> str:
    """Add a typed relationship between two knowledge entries. Returns the relationship ID."""
    if relationship not in RELATIONSHIP_TYPES:
        raise ValueError(
            f"Unknown relationship '{relationship}'. Valid: {', '.join(sorted(RELATIONSHIP_TYPES))}"
        )
    if source_id == target_id:
        raise ValueError("Cannot relate a knowledge entry to itself.")

    init_relationship_table()
    rel_id = str(uuid.uuid4())
    conn = _get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO knowledge_relationships "
            "(relationship_id, source_id, target_id, relationship, created_at, notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (rel_id, source_id, target_id, relationship, time.time(), notes),
        )
        conn.commit()
    finally:
        conn.close()
    return rel_id


def get_relationships(
    knowledge_id: str,
    direction: str = "both",
) -> list[dict[str, Any]]:
    """Get all relationships for a knowledge entry.

    direction: "outgoing" (source), "incoming" (target), or "both".
    """
    init_relationship_table()
    conn = _get_connection()
    try:
        results: list[dict[str, Any]] = []
        if direction in ("outgoing", "both"):
            rows = conn.execute(
                "SELECT relationship_id, source_id, target_id, relationship, created_at, notes "
                "FROM knowledge_relationships WHERE source_id = ?",
                (knowledge_id,),
            ).fetchall()
            for r in rows:
                results.append(
                    {
                        "relationship_id": r[0],
                        "source_id": r[1],
                        "target_id": r[2],
                        "relationship": r[3],
                        "created_at": r[4],
                        "notes": r[5],
                        "direction": "outgoing",
                    }
                )
        if direction in ("incoming", "both"):
            rows = conn.execute(
                "SELECT relationship_id, source_id, target_id, relationship, created_at, notes "
                "FROM knowledge_relationships WHERE target_id = ?",
                (knowledge_id,),
            ).fetchall()
            for r in rows:
                results.append(
                    {
                        "relationship_id": r[0],
                        "source_id": r[1],
                        "target_id": r[2],
                        "relationship": r[3],
                        "created_at": r[4],
                        "notes": r[5],
                        "direction": "incoming",
                    }
                )
        return results
    finally:
        conn.close()


def remove_relationship(relationship_id: str) -> bool:
    """Remove a relationship by its ID. Returns True if it existed."""
    init_relationship_table()
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "DELETE FROM knowledge_relationships WHERE relationship_id = ?",
            (relationship_id,),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def find_related_cluster(
    knowledge_id: str,
    max_depth: int = 2,
) -> list[dict[str, Any]]:
    """Walk the relationship graph from a starting node up to max_depth hops.

    Returns a flat list of unique related entries with their relationship path.
    """
    init_relationship_table()
    visited: set[str] = {knowledge_id}
    cluster: list[dict[str, Any]] = []
    frontier = [knowledge_id]

    for depth in range(max_depth):
        next_frontier: list[str] = []
        for kid in frontier:
            rels = get_relationships(kid, direction="both")
            for rel in rels:
                other = rel["target_id"] if rel["source_id"] == kid else rel["source_id"]
                if other not in visited:
                    visited.add(other)
                    next_frontier.append(other)
                    cluster.append(
                        {
                            "knowledge_id": other,
                            "relationship": rel["relationship"],
                            "via": kid,
                            "depth": depth + 1,
                        }
                    )
        frontier = next_frontier
        if not frontier:
            break

    return cluster


def get_relationship_summary(knowledge_id: str) -> str:
    """Format a short text summary of relationships for display."""
    rels = get_relationships(knowledge_id)
    if not rels:
        return ""

    lines = []
    for rel in rels:
        if rel["direction"] == "outgoing":
            lines.append(f"  → {rel['relationship']} → {rel['target_id'][:8]}...")
        else:
            lines.append(f"  ← {rel['relationship']} ← {rel['source_id'][:8]}...")
        if rel["notes"]:
            lines.append(f"    ({rel['notes']})")
    return "\n".join(lines)
