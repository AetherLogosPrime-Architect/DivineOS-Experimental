"""Logic validation — consistency checking, validity gates, and defeat lessons.

Merged from consistency.py, validity_gate.py, and defeat_lessons.py.

Sections:
1. Consistency checking (contradiction detection, local + transitive)
2. Validity gate (warrant-aware promotion for maturity lifecycle)
3. Defeat lessons (defeated-warrant-to-lesson pipeline)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from divineos.core.knowledge import get_connection
from divineos.core.logic.warrants import get_warrants

# ═══════════════════════════════════════════════════════════════════════
# Section 1: Consistency Checking
# ═══════════════════════════════════════════════════════════════════════
#
# Two modes:
# 1. Local: check a single entry against its direct CONTRADICTS relations
# 2. Transitive: BFS through IMPLIES/REQUIRES chains to find indirect contradictions


@dataclass
class Inconsistency:
    """A detected contradiction between knowledge entries."""

    entry_a: str
    entry_b: str
    path: list[str] = field(default_factory=list)
    contradiction_type: str = "DIRECT"  # DIRECT or TRANSITIVE
    confidence: float = 1.0
    explanation: str = ""


def check_local_consistency(knowledge_id: str) -> list[Inconsistency]:
    """Check for direct CONTRADICTS relations on this entry."""
    # Late import: logic_validation -> logic_reasoning -> knowledge -> extraction -> knowledge_maintenance -> logic_validation cycle
    from divineos.core.logic.logic_reasoning import get_relations

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
    # Late import: same cycle as check_local_consistency
    from divineos.core.logic.logic_reasoning import get_relations

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
    # Late import: same cycle as check_local_consistency
    from divineos.core.logic.logic_reasoning import create_relation

    create_relation(
        source_id=entry_a,
        target_id=entry_b,
        relation_type="CONTRADICTS",
        confidence=confidence,
        notes=notes,
    )

    # Increment contradiction_count on both entries
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


# ═══════════════════════════════════════════════════════════════════════
# Section 2: Validity Gate
# ═══════════════════════════════════════════════════════════════════════
#
# Warrant-aware promotion for the maturity lifecycle.
#
# Rules:
# - RAW -> HYPOTHESIS: automatic (no warrant needed)
# - HYPOTHESIS -> TESTED: needs at least 1 valid warrant
# - TESTED -> CONFIRMED: needs 2+ valid warrants from different types
# - Any entry with all warrants defeated cannot promote


@dataclass
class ValidityVerdict:
    """Result of a validity gate check."""

    passed: bool
    current_maturity: str
    target_maturity: str | None
    reason: str
    warrant_count: int = 0
    warrant_types: list[str] | None = None


def check_validity_for_promotion(
    knowledge_id: str,
    current_maturity: str,
    target_maturity: str,
    corroboration_count: int = 0,
) -> ValidityVerdict:
    """Check if a knowledge entry's warrants support promotion.

    This is called by the maturity system AFTER the corroboration-based
    check passes. It's a second gate: "yes you've been seen enough times,
    but do you have real justification?"
    """
    warrants = get_warrants(knowledge_id, status="ACTIVE")
    valid_warrants = [w for w in warrants if w.is_valid()]
    warrant_types = list({w.warrant_type for w in valid_warrants})

    # High corroboration (≥10) counts as implicit EMPIRICAL evidence.
    # Being corroborated many times across sessions IS empirical validation —
    # it means the knowledge kept coming up and being confirmed by use.
    if corroboration_count >= 10 and "EMPIRICAL" not in warrant_types:
        warrant_types.append("EMPIRICAL")

    # RAW -> HYPOTHESIS: always allowed (low bar, just needs first encounter)
    if current_maturity == "RAW" and target_maturity == "HYPOTHESIS":
        return ValidityVerdict(
            passed=True,
            current_maturity=current_maturity,
            target_maturity=target_maturity,
            reason="RAW -> HYPOTHESIS requires no warrant",
            warrant_count=len(valid_warrants),
            warrant_types=warrant_types,
        )

    # HYPOTHESIS -> TESTED: needs at least 1 valid warrant
    if current_maturity == "HYPOTHESIS" and target_maturity == "TESTED":
        if len(valid_warrants) >= 1:
            return ValidityVerdict(
                passed=True,
                current_maturity=current_maturity,
                target_maturity=target_maturity,
                reason=f"Has {len(valid_warrants)} valid warrant(s)",
                warrant_count=len(valid_warrants),
                warrant_types=warrant_types,
            )
        return ValidityVerdict(
            passed=False,
            current_maturity=current_maturity,
            target_maturity=target_maturity,
            reason="HYPOTHESIS -> TESTED requires at least 1 valid warrant",
            warrant_count=0,
            warrant_types=[],
        )

    # TESTED -> CONFIRMED: needs 2+ valid warrants from different types
    if current_maturity == "TESTED" and target_maturity == "CONFIRMED":
        if len(valid_warrants) >= 2 and len(warrant_types) >= 2:
            return ValidityVerdict(
                passed=True,
                current_maturity=current_maturity,
                target_maturity=target_maturity,
                reason=f"Has {len(valid_warrants)} warrants across {len(warrant_types)} types",
                warrant_count=len(valid_warrants),
                warrant_types=warrant_types,
            )
        if len(valid_warrants) < 2:
            return ValidityVerdict(
                passed=False,
                current_maturity=current_maturity,
                target_maturity=target_maturity,
                reason=f"TESTED -> CONFIRMED requires 2+ warrants, has {len(valid_warrants)}",
                warrant_count=len(valid_warrants),
                warrant_types=warrant_types,
            )
        return ValidityVerdict(
            passed=False,
            current_maturity=current_maturity,
            target_maturity=target_maturity,
            reason=f"TESTED -> CONFIRMED requires 2+ warrant types, has {len(warrant_types)}: {warrant_types}",
            warrant_count=len(valid_warrants),
            warrant_types=warrant_types,
        )

    # Unknown transition -- allow it (don't block what we don't understand)
    return ValidityVerdict(
        passed=True,
        current_maturity=current_maturity,
        target_maturity=target_maturity,
        reason=f"No validity rule for {current_maturity} -> {target_maturity}",
        warrant_count=len(valid_warrants),
        warrant_types=warrant_types,
    )


def can_promote(
    knowledge_id: str,
    current_maturity: str,
    target_maturity: str,
    corroboration_count: int = 0,
) -> bool:
    """Quick check: can this entry promote? Returns True/False."""
    verdict = check_validity_for_promotion(
        knowledge_id, current_maturity, target_maturity, corroboration_count
    )
    return verdict.passed


# ═══════════════════════════════════════════════════════════════════════
# Section 3: Defeat Lessons
# ═══════════════════════════════════════════════════════════════════════
#
# When warrants get defeated, that's a reasoning failure worth learning from.
# If a warrant type keeps getting defeated on a topic, create a lesson:
# "I keep believing X based on Y evidence but it turns out wrong."


def check_defeat_pattern(
    knowledge_id: str,
    defeated_warrant_type: str,
    session_id: str | None = None,
) -> str | None:
    """Check if this defeat creates a recurring pattern.

    If 2+ warrants of the same type have been defeated on this knowledge entry,
    create a lesson about the reasoning failure.

    Returns lesson_id if created, None otherwise.
    """
    all_warrants = get_warrants(knowledge_id)
    defeated_same_type = [
        w
        for w in all_warrants
        if w.status == "DEFEATED" and w.warrant_type == defeated_warrant_type
    ]

    if len(defeated_same_type) < 2:
        return None

    # Get a topic hint from the knowledge content
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (knowledge_id,)
        ).fetchone()
    finally:
        conn.close()

    topic = row[0][:80] if row else "unknown topic"
    return record_defeat_lesson(
        knowledge_id=knowledge_id,
        warrant_type=defeated_warrant_type,
        defeat_count=len(defeated_same_type),
        topic_hint=topic,
        session_id=session_id,
    )


def record_defeat_lesson(
    knowledge_id: str,
    warrant_type: str,
    defeat_count: int,
    topic_hint: str,
    session_id: str | None = None,
) -> str:
    """Create a lesson from a warrant defeat pattern."""

    description = (
        f"I keep believing claims based on {warrant_type} evidence that turn out wrong. "
        f"Defeated {defeat_count}x on: {topic_hint}"
    )

    # Late import: logic_validation -> lessons -> knowledge_maintenance -> logic_validation cycle
    from divineos.core.knowledge.lessons import record_lesson

    lesson_id = record_lesson(
        category="reasoning_failure",
        description=description,
        session_id=session_id or "unknown",
    )
    logger.info(
        "Created lesson from {} defeat pattern on {}: {}",
        warrant_type,
        knowledge_id[:8],
        lesson_id[:8] if lesson_id else "none",
    )
    return lesson_id or ""


def scan_defeated_only_entries(limit: int = 100) -> list[dict[str, Any]]:
    """Find knowledge entries whose ONLY warrants are all DEFEATED.

    These entries have lost all justification.
    """
    conn = get_connection()
    try:
        # Get all knowledge IDs that have warrants
        rows = conn.execute("SELECT DISTINCT knowledge_id FROM warrants").fetchall()
    finally:
        conn.close()

    results: list[dict[str, Any]] = []
    for (kid,) in rows[:limit]:
        warrants = get_warrants(kid)
        if not warrants:
            continue
        active = [w for w in warrants if w.status == "ACTIVE"]
        if active:
            continue  # Has at least one active warrant
        # All warrants are defeated or withdrawn
        defeat_reasons = []
        for w in warrants:
            if w.status == "DEFEATED":
                defeat_reasons.extend(w.defeaters)

        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT content FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
                (kid,),
            ).fetchone()
        finally:
            conn.close()

        if row:
            results.append(
                {
                    "knowledge_id": kid,
                    "content": row[0],
                    "warrant_count": len(warrants),
                    "defeat_reasons": defeat_reasons,
                }
            )

    return results
