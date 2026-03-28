"""Forward-chaining inference — derive downstream knowledge when new facts enter.

When a knowledge entry is confirmed or updated, traverse its IMPLIES edges
to find what follows. Each derived conclusion gets reduced confidence
(belief doesn't propagate at full strength) and an INFERENTIAL warrant
pointing back to the source chain.

This is not a full theorem prover. It's a practical notification system:
"you confirmed X, which means Y and Z might also be true."
"""

from __future__ import annotations

from dataclasses import dataclass, field

from loguru import logger

from divineos.core.logic.relations import get_relations
from divineos.core.logic.warrants import create_warrant, get_warrants


# ─── Types ───────────────────────────────────────────────────────────

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


# ─── Forward Chaining ────────────────────────────────────────────────


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
