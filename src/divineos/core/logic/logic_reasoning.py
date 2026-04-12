"""Logic reasoning — relations, inference, and warrant backfill.

Merged from relations.py, inference.py, and warrant_backfill.py.

Sections:
1. Typed logical relations between knowledge entries
2. Forward-chaining inference
3. Warrant backfill for pre-existing entries
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from divineos.core.knowledge import get_connection
from divineos.core.knowledge.edges import (
    LOGICAL_TYPES,
    KnowledgeEdge,
    create_edge,
    deactivate_edge,
    find_edge,
    get_edges,
    init_edge_table,
)
from divineos.core.knowledge.edges import (
    get_neighbors as _get_neighbors,
)
from divineos.core.logic.warrants import create_warrant, get_warrants

# ═══════════════════════════════════════════════════════════════════════
# Section 1: Typed Logical Relations
# ═══════════════════════════════════════════════════════════════════════
#
# Thin wrapper around the unified knowledge_edges table, filtered to the
# logical layer. All data lives in knowledge_edges -- this module provides
# the logical-specific API and type validation.
#
# Relation types:
# - IMPLIES: if A is true, B follows
# - CONTRADICTS: A and B cannot both be true
# - REQUIRES: A depends on B being true
# - SUPPORTS: A provides evidence for B (weaker than IMPLIES)
# - GENERALIZES: A is a broader version of B
# - SPECIALIZES: A is a narrower case of B


def init_relation_table() -> None:
    """Create the knowledge_edges table (shared with semantic edges). Idempotent."""
    init_edge_table()


RELATION_TYPES = LOGICAL_TYPES

# Inverse mapping -- if A->B is X, then B->A is Y
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


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Forward-Chaining Inference
# ═══════════════════════════════════════════════════════════════════════
#
# When a knowledge entry is confirmed or updated, traverse its IMPLIES edges
# to find what follows. Each derived conclusion gets reduced confidence
# and an INFERENTIAL warrant pointing back to the source chain.

# How much confidence decays per implication hop
CONFIDENCE_DECAY = 0.85

# Minimum confidence for a derived conclusion to be worth surfacing
MIN_INFERENCE_CONFIDENCE = 0.3

# Maximum inference chain depth
MAX_INFERENCE_DEPTH = 3


@dataclass
class Derivation:
    """A derived conclusion from forward-chaining inference."""

    target_id: str
    source_chain: list[str]
    confidence: float
    relation_types: list[str] = field(default_factory=list)

    @property
    def depth(self) -> int:
        return len(self.source_chain) - 1


def forward_chain(
    knowledge_id: str,
    max_depth: int = MAX_INFERENCE_DEPTH,
    min_confidence: float = MIN_INFERENCE_CONFIDENCE,
    starting_confidence: float = 1.0,
) -> list[Derivation]:
    """Traverse IMPLIES edges forward from a knowledge entry.

    Returns all reachable entries with accumulated confidence above
    min_confidence, up to max_depth hops.
    """
    results: list[Derivation] = []
    visited: set[str] = {knowledge_id}
    frontier: list[tuple[str, list[str], float, list[str]]] = [
        (knowledge_id, [knowledge_id], starting_confidence, [])
    ]

    for _ in range(max_depth):
        next_frontier: list[tuple[str, list[str], float, list[str]]] = []

        for node_id, chain, conf, rtypes in frontier:
            implies = get_relations(node_id, direction="outgoing", relation_type="IMPLIES")

            for rel in implies:
                if rel.target_id in visited:
                    continue

                new_conf = conf * rel.confidence * CONFIDENCE_DECAY
                if new_conf < min_confidence:
                    continue

                visited.add(rel.target_id)
                new_chain = chain + [rel.target_id]
                new_rtypes = rtypes + [rel.relation_type]

                results.append(
                    Derivation(
                        target_id=rel.target_id,
                        source_chain=new_chain,
                        confidence=new_conf,
                        relation_types=new_rtypes,
                    )
                )

                next_frontier.append((rel.target_id, new_chain, new_conf, new_rtypes))

        frontier = next_frontier
        if not frontier:
            break

    return sorted(results, key=lambda d: d.confidence, reverse=True)


def create_inference_warrants(
    source_id: str,
    derivations: list[Derivation],
    source_session: str | None = None,
) -> int:
    """Create INFERENTIAL warrants for derived conclusions.

    Returns the number of warrants created.
    """
    created = 0
    for deriv in derivations:
        # Check if this target already has an inferential warrant from this source
        existing = get_warrants(deriv.target_id, status="ACTIVE")
        already_has = any(
            w.warrant_type == "INFERENTIAL" and source_id in w.backing_ids for w in existing
        )
        if already_has:
            continue

        create_warrant(
            knowledge_id=deriv.target_id,
            warrant_type="INFERENTIAL",
            grounds=f"Derived from {source_id[:8]} via {deriv.depth}-hop implication chain",
            source_session=source_session,
            backing_ids=[source_id] + deriv.source_chain[1:-1],
        )
        created += 1

    if created:
        logger.debug("Created {} inference warrants from {}", created, source_id[:8])

    return created


def propagate_from(
    knowledge_id: str,
    source_session: str | None = None,
    min_confidence: float = MIN_INFERENCE_CONFIDENCE,
) -> list[Derivation]:
    """Full inference pass: forward-chain from an entry and create warrants.

    Call this when a knowledge entry is confirmed or updated.
    Returns the list of derivations found.
    """
    derivations = forward_chain(knowledge_id, min_confidence=min_confidence)

    if derivations:
        create_inference_warrants(knowledge_id, derivations, source_session)
        logger.debug(
            "Propagated from {}: {} derivations",
            knowledge_id[:8],
            len(derivations),
        )

    return derivations


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Warrant Backfill
# ═══════════════════════════════════════════════════════════════════════
#
# One-time backfill -- give pre-existing knowledge entries INHERITED warrants.
# Knowledge entries created before the warrant system have no justification chain.


def backfill_inherited_warrants(dry_run: bool = False) -> dict[str, int]:
    """Create INHERITED warrants for all knowledge entries that have none.

    Returns counts: {"checked": N, "backfilled": N, "already_warranted": N}
    """
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT knowledge_id, knowledge_type, content "
            "FROM knowledge WHERE superseded_by IS NULL"
        ).fetchall()
    finally:
        conn.close()

    checked = 0
    backfilled = 0
    already_warranted = 0

    for kid, ktype, content in rows:
        checked += 1
        existing = get_warrants(kid)
        if existing:
            already_warranted += 1
            continue

        if dry_run:
            backfilled += 1
            continue

        grounds = f"Pre-existing {ktype} entry, warranted retroactively"
        create_warrant(
            knowledge_id=kid,
            warrant_type="INHERITED",
            grounds=grounds,
        )
        backfilled += 1

    logger.info(
        "Warrant backfill: checked={}, backfilled={}, already_warranted={}",
        checked,
        backfilled,
        already_warranted,
    )
    return {
        "checked": checked,
        "backfilled": backfilled,
        "already_warranted": already_warranted,
    }
