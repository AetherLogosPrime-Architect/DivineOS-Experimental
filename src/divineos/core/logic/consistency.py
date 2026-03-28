"""Consistency checking — detect contradictions in the knowledge graph.

Two modes:
1. Local: check a single entry against its direct CONTRADICTS relations
2. Transitive: BFS through IMPLIES/REQUIRES chains to find indirect contradictions

The checker returns a list of inconsistencies, each describing the
contradiction path and the entries involved.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from divineos.core.logic.relations import (
    get_relations,
    create_relation,
)


# ─── Types ───────────────────────────────────────────────────────────


@dataclass
class Inconsistency:
    """A detected contradiction between knowledge entries."""

    entry_a: str
    entry_b: str
    path: list[str] = field(default_factory=list)
    contradiction_type: str = "DIRECT"  # DIRECT or TRANSITIVE
    confidence: float = 1.0
    explanation: str = ""


# ─── Checking ────────────────────────────────────────────────────────


def check_local_consistency(knowledge_id: str) -> list[Inconsistency]:
    """Check for direct CONTRADICTS relations on this entry."""
    contradictions = get_relations(knowledge_id, direction="both", relation_type="CONTRADICTS")

    results: list[Inconsistency] = []
    for rel in contradictions:
        other_id = rel.target_id if rel.source_id == knowledge_id else rel.source_id
        results.append(
            Inconsistency(
                entry_a=knowledge_id,
                entry_b=other_id,
                path=[knowledge_id, other_id],
                contradiction_type="DIRECT",
                confidence=rel.confidence,
                explanation=rel.notes or "Direct contradiction relation",
            )
        )

    return results


def check_transitive_consistency(knowledge_id: str, max_depth: int = 3) -> list[Inconsistency]:
    """BFS through IMPLIES/REQUIRES chains looking for CONTRADICTS at each node.

    If A implies B, and B contradicts C, then A has a transitive
    inconsistency with C (confidence decays with depth).

    max_depth limits how far we search to avoid runaway graph traversal.
    """
    results: list[Inconsistency] = []
    visited: set[str] = {knowledge_id}
    # Each frontier entry: (node_id, path_from_start, accumulated_confidence)
    frontier: list[tuple[str, list[str], float]] = [(knowledge_id, [knowledge_id], 1.0)]

    for depth in range(max_depth):
        next_frontier: list[tuple[str, list[str], float]] = []

        for node_id, path, conf in frontier:
            # At each node, check for CONTRADICTS
            contradictions = get_relations(node_id, direction="both", relation_type="CONTRADICTS")
            for rel in contradictions:
                other_id = rel.target_id if rel.source_id == node_id else rel.source_id
                if other_id == knowledge_id:
                    continue  # skip self-loops
                if other_id in visited:
                    continue

                transitive_conf = conf * rel.confidence * 0.8  # decay per hop
                results.append(
                    Inconsistency(
                        entry_a=knowledge_id,
                        entry_b=other_id,
                        path=path + [other_id],
                        contradiction_type="TRANSITIVE",
                        confidence=transitive_conf,
                        explanation=f"Transitive contradiction via {len(path)} hop(s)",
                    )
                )

            # Traverse IMPLIES and REQUIRES edges for next depth
            for rtype in ("IMPLIES", "REQUIRES", "SUPPORTS"):
                related = get_relations(node_id, direction="outgoing", relation_type=rtype)
                for rel in related:
                    if rel.target_id not in visited:
                        visited.add(rel.target_id)
                        next_frontier.append(
                            (
                                rel.target_id,
                                path + [rel.target_id],
                                conf * rel.confidence * 0.9,
                            )
                        )

        frontier = next_frontier
        if not frontier:
            break

    return results


def check_consistency(knowledge_id: str, max_depth: int = 3) -> list[Inconsistency]:
    """Full consistency check: local + transitive.

    Returns all detected inconsistencies, sorted by confidence (highest first).
    """
    results = check_local_consistency(knowledge_id)
    results.extend(check_transitive_consistency(knowledge_id, max_depth=max_depth))

    # Deduplicate by (entry_a, entry_b) pair, keeping highest confidence
    seen: dict[tuple[str, str], Inconsistency] = {}
    for inc in results:
        key = (min(inc.entry_a, inc.entry_b), max(inc.entry_a, inc.entry_b))
        if key not in seen or inc.confidence > seen[key].confidence:
            seen[key] = inc

    return sorted(seen.values(), key=lambda x: x.confidence, reverse=True)


def register_contradiction(
    entry_a: str,
    entry_b: str,
    confidence: float = 1.0,
    notes: str = "",
) -> None:
    """Register a CONTRADICTS relation between two entries.

    Also increments contradiction_count on both entries.
    """
    create_relation(
        source_id=entry_a,
        target_id=entry_b,
        relation_type="CONTRADICTS",
        confidence=confidence,
        notes=notes,
    )

    # Increment contradiction_count on both entries
    from divineos.core.knowledge import get_connection

    conn = get_connection()
    try:
        for kid in (entry_a, entry_b):
            conn.execute(
                "UPDATE knowledge SET contradiction_count = contradiction_count + 1 WHERE knowledge_id = ?",
                (kid,),
            )
        conn.commit()
    finally:
        conn.close()

    logger.debug("Registered contradiction between {} and {}", entry_a[:8], entry_b[:8])
