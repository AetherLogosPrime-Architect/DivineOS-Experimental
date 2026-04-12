"""Knowledge inference — derive new knowledge from existing knowledge.

This is the "inferred" epistemic channel. Instead of learning from user
input (told) or session events (observed), this module looks at what we
already know and draws conclusions.

Three inference types:
1. Repeated mistakes → boundary: if the same category of mistake recurs 3+
   times, infer that we need a boundary/principle to prevent it.
2. Corroborated patterns → principle: if a pattern is CONFIRMED (5+ sessions),
   promote it to a principle about how things work.
3. Lesson clusters → insight: if 3+ lessons share the same category, synthesize
   a higher-level insight about what's going wrong.
"""

import sqlite3
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import _get_connection
from divineos.core.knowledge._text import _compute_overlap
from divineos.core.knowledge.crud import get_knowledge
from divineos.core.knowledge.extraction import store_knowledge_smart

_INFERENCE_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
)


def infer_boundaries_from_mistakes(min_occurrences: int = 3) -> list[str]:
    """If the same type of mistake keeps happening, infer a boundary.

    Looks at active MISTAKE entries. If 3+ share high word overlap,
    synthesize a boundary that captures the recurring failure pattern.

    Returns list of new knowledge IDs created.
    """
    mistakes = get_knowledge(knowledge_type="MISTAKE", limit=50)
    if len(mistakes) < min_occurrences:
        return []

    # Group by overlap clusters
    clusters: list[list[dict[str, Any]]] = []
    used: set[str] = set()

    for i, m in enumerate(mistakes):
        if m["knowledge_id"] in used:
            continue
        cluster = [m]
        used.add(m["knowledge_id"])
        for j in range(i + 1, len(mistakes)):
            other = mistakes[j]
            if other["knowledge_id"] in used:
                continue
            overlap = _compute_overlap(m["content"], other["content"])
            if overlap >= 0.35:
                cluster.append(other)
                used.add(other["knowledge_id"])
        if len(cluster) >= min_occurrences:
            clusters.append(cluster)

    created: list[str] = []
    for cluster in clusters:
        # Check if we already have a boundary for this pattern
        sample = cluster[0]["content"]
        existing_boundaries = get_knowledge(knowledge_type="BOUNDARY", limit=50)
        already_covered = any(
            _compute_overlap(sample, b["content"]) >= 0.4 for b in existing_boundaries
        )
        if already_covered:
            continue

        # Synthesize a boundary from the cluster
        descriptions = [m["content"][:80] for m in cluster[:5]]
        content = (
            f"I keep making a recurring mistake ({len(cluster)} times): "
            f"{descriptions[0]}. This pattern must stop."
        )

        kid = store_knowledge_smart(
            knowledge_type="BOUNDARY",
            content=content,
            confidence=0.7,
            source="SYNTHESIZED",
            maturity="HYPOTHESIS",
            tags=["inferred", "from-mistakes"],
        )
        if kid:
            created.append(kid)
            # Create edges from the boundary to the source mistakes
            try:
                from divineos.core.knowledge.edges import create_edge

                for m in cluster:
                    create_edge(
                        source_id=kid,
                        target_id=m["knowledge_id"],
                        edge_type="DERIVED_FROM",
                        notes="auto: boundary inferred from recurring mistakes",
                    )
            except _INFERENCE_ERRORS:
                pass

    if created:
        logger.info(f"Inferred {len(created)} boundaries from recurring mistakes")
    return created


def promote_confirmed_patterns() -> list[str]:
    """Promote CONFIRMED patterns to principles.

    A pattern that has been confirmed (5+ corroborations) represents
    stable, reliable knowledge about how things work. It deserves
    to be a principle, not just an observation.

    Returns list of new knowledge IDs created.
    """
    conn = _get_connection()
    try:
        rows = conn.execute(
            """SELECT knowledge_id, content, corroboration_count, tags
               FROM knowledge
               WHERE knowledge_type = 'PATTERN'
                 AND maturity = 'CONFIRMED'
                 AND superseded_by IS NULL""",
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        return []

    created: list[str] = []
    for row in rows:
        kid, content, corr_count, tags = row

        # Check if a similar principle already exists
        existing = get_knowledge(knowledge_type="PRINCIPLE", limit=100)
        already_exists = any(_compute_overlap(content, p["content"]) >= 0.5 for p in existing)
        if already_exists:
            continue

        # Promote to principle
        principle_content = content.replace("I consistently show good", "I reliably demonstrate")
        if not principle_content.startswith("I "):
            principle_content = f"I have established: {principle_content}"

        new_id = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content=principle_content,
            confidence=0.85,
            source="SYNTHESIZED",
            maturity="TESTED",
            tags=["inferred", "from-pattern", "promoted"],
        )
        if new_id and new_id != kid:
            created.append(new_id)
            try:
                from divineos.core.knowledge.edges import create_edge

                create_edge(
                    source_id=new_id,
                    target_id=kid,
                    edge_type="DERIVED_FROM",
                    notes="auto: principle inferred from confirmed pattern",
                )
            except _INFERENCE_ERRORS:
                pass

    if created:
        logger.info(f"Promoted {len(created)} confirmed patterns to principles")
    return created


def synthesize_lesson_insights() -> list[str]:
    """Find lesson clusters and synthesize higher-level insights.

    If 3+ active lessons share the same category, there's a systemic
    issue worth capturing as a standalone observation.

    Returns list of new knowledge IDs created.
    """
    conn = _get_connection()
    try:
        # Find categories with 3+ active lessons
        rows = conn.execute(
            """SELECT category, COUNT(*) as cnt, GROUP_CONCAT(description, ' | ')
               FROM lesson_tracking
               WHERE status = 'active'
               GROUP BY category
               HAVING cnt >= 3
               ORDER BY cnt DESC""",
        ).fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        conn.close()

    if not rows:
        return []

    created: list[str] = []
    for category, count, descriptions in rows:
        content = (
            f"I have a systemic issue with {category}: {count} active lessons "
            f"in this area remain unresolved. This suggests a deeper pattern "
            f"that needs structural attention, not just individual fixes."
        )

        kid = store_knowledge_smart(
            knowledge_type="OBSERVATION",
            content=content,
            confidence=0.7,
            source="SYNTHESIZED",
            maturity="HYPOTHESIS",
            tags=["inferred", "lesson-cluster", f"category-{category}"],
        )
        if kid:
            created.append(kid)

    if created:
        logger.info(f"Synthesized {len(created)} insights from lesson clusters")
    return created


def run_inference_cycle() -> dict[str, list[str]]:
    """Run all inference steps. Called during SESSION_END pipeline.

    Returns dict of inference type → list of new knowledge IDs.
    """
    results: dict[str, list[str]] = {}

    try:
        results["boundaries"] = infer_boundaries_from_mistakes()
    except _INFERENCE_ERRORS as e:
        logger.debug(f"Boundary inference failed: {e}")
        results["boundaries"] = []

    try:
        results["principles"] = promote_confirmed_patterns()
    except _INFERENCE_ERRORS as e:
        logger.debug(f"Pattern promotion failed: {e}")
        results["principles"] = []

    try:
        results["insights"] = synthesize_lesson_insights()
    except _INFERENCE_ERRORS as e:
        logger.debug(f"Lesson insight synthesis failed: {e}")
        results["insights"] = []

    total = sum(len(v) for v in results.values())
    if total:
        logger.info(f"Inference cycle produced {total} new entries")
    return results
