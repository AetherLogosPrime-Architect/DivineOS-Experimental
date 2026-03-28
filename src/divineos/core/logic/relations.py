"""Typed logical relations between knowledge entries.

Thin wrapper around the unified knowledge_edges table, filtered to the
logical layer. All data lives in knowledge_edges — this module provides
the logical-specific API and type validation.

Relation types:
- IMPLIES: if A is true, B follows
- CONTRADICTS: A and B cannot both be true
- REQUIRES: A depends on B being true
- SUPPORTS: A provides evidence for B (weaker than IMPLIES)
- GENERALIZES: A is a broader version of B
- SPECIALIZES: A is a narrower case of B
"""

from __future__ import annotations

from dataclasses import dataclass

from divineos.core.knowledge.edges import (
    LOGICAL_TYPES,
    KnowledgeEdge,
    create_edge,
    deactivate_edge,
    find_edge,
    get_edges,
    get_neighbors as _get_neighbors,
    init_edge_table,
)

# ─── Schema ──────────────────────────────────────────────────────────


def init_relation_table() -> None:
    """Create the knowledge_edges table (shared with semantic edges). Idempotent."""
    init_edge_table()


# ─── Types ───────────────────────────────────────────────────────────

RELATION_TYPES = LOGICAL_TYPES

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
    """A typed logical edge between two knowledge entries."""

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

    edge = create_edge(
        source_id=source_id,
        target_id=target_id,
        edge_type=relation_type,
        layer="logical",
        confidence=confidence,
        warrant_id=warrant_id,
        notes=notes,
    )
    return _edge_to_relation(edge)


def find_relation(source_id: str, target_id: str, relation_type: str) -> LogicalRelation | None:
    """Find an existing active logical relation between two entries."""
    edge = find_edge(source_id, target_id, relation_type)
    return _edge_to_relation(edge) if edge else None


def get_relations(
    knowledge_id: str,
    direction: str = "both",
    relation_type: str | None = None,
) -> list[LogicalRelation]:
    """Get all active logical relations for a knowledge entry."""
    edges = get_edges(
        knowledge_id,
        direction=direction,
        edge_type=relation_type,
        layer="logical",
    )
    return [_edge_to_relation(e) for e in edges]


def deactivate_relation(relation_id: str) -> bool:
    """Deactivate a logical relation (soft delete)."""
    return deactivate_edge(relation_id)


def get_neighbors(
    knowledge_id: str, relation_type: str | None = None, max_depth: int = 1
) -> list[str]:
    """Get IDs of knowledge entries connected via logical edges within max_depth hops."""
    return _get_neighbors(
        knowledge_id,
        edge_type=relation_type,
        layer="logical",
        max_depth=max_depth,
    )


# ─── Helpers ─────────────────────────────────────────────────────────


def _edge_to_relation(edge: KnowledgeEdge) -> LogicalRelation:
    """Convert a KnowledgeEdge to a LogicalRelation."""
    return LogicalRelation(
        relation_id=edge.edge_id,
        source_id=edge.source_id,
        target_id=edge.target_id,
        relation_type=edge.edge_type,
        confidence=edge.confidence,
        warrant_id=edge.warrant_id,
        created_at=edge.created_at,
        status=edge.status,
        notes=edge.notes,
    )
