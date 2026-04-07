"""Knowledge Relationships — typed edges between knowledge entries.

Knowledge doesn't exist in isolation. A MISTAKE might be CAUSED_BY a
PROCEDURE. A PRINCIPLE might be SUPPORTED_BY multiple OBSERVATIONs.
This module tracks those connections so I can navigate my own knowledge
graph rather than treating it as a flat list.

All data lives in the unified knowledge_edges table. This module provides
the semantic-layer API and auto-detection heuristics.
"""

import re
from typing import Any
import sqlite3

from loguru import logger

from divineos.core.knowledge import get_connection
from divineos.core.knowledge._text import _compute_overlap, _extract_key_terms
from divineos.core.knowledge.crud import search_knowledge
from divineos.core.knowledge.edges import (
    SEMANTIC_TYPES,
    create_edge,
    get_edge_summary,
    get_edges,
    init_edge_table,
    remove_edge,
)

_RELATIONSHIPS_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
)

# Valid relationship types — semantic layer
RELATIONSHIP_TYPES = SEMANTIC_TYPES


def init_relationship_table() -> None:
    """Create the knowledge_edges table (shared with logical edges). Idempotent."""
    init_edge_table()


def add_relationship(
    source_id: str,
    target_id: str,
    relationship: str,
    notes: str = "",
) -> str:
    """Add a typed relationship between two knowledge entries. Returns the edge ID."""
    if relationship not in RELATIONSHIP_TYPES:
        raise ValueError(
            f"Unknown relationship '{relationship}'. Valid: {', '.join(sorted(RELATIONSHIP_TYPES))}"
        )

    edge = create_edge(
        source_id=source_id,
        target_id=target_id,
        edge_type=relationship,
        layer="semantic",
        notes=notes,
    )
    return edge.edge_id


def get_relationships(
    knowledge_id: str,
    direction: str = "both",
) -> list[dict[str, Any]]:
    """Get all semantic relationships for a knowledge entry.

    direction: "outgoing" (source), "incoming" (target), or "both".
    """
    edges = get_edges(knowledge_id, direction=direction, layer="semantic")
    results: list[dict[str, Any]] = []
    for edge in edges:
        d = "outgoing" if edge.source_id == knowledge_id else "incoming"
        results.append(
            {
                "relationship_id": edge.edge_id,
                "source_id": edge.source_id,
                "target_id": edge.target_id,
                "relationship": edge.edge_type,
                "created_at": edge.created_at,
                "notes": edge.notes,
                "direction": d,
            }
        )
    return results


def remove_relationship(relationship_id: str) -> bool:
    """Remove a relationship by its ID. Returns True if it existed."""
    return remove_edge(relationship_id)


def find_related_cluster(
    knowledge_id: str,
    max_depth: int = 2,
) -> list[dict[str, Any]]:
    """Walk the semantic edge graph from a starting node up to max_depth hops.

    Returns a flat list of unique related entries with their relationship path.
    """
    visited: set[str] = {knowledge_id}
    cluster: list[dict[str, Any]] = []
    frontier = [knowledge_id]

    for depth in range(max_depth):
        next_frontier: list[str] = []
        for kid in frontier:
            edges = get_edges(kid, direction="both", layer="semantic")
            for edge in edges:
                other = edge.target_id if edge.source_id == kid else edge.source_id
                if other not in visited:
                    visited.add(other)
                    next_frontier.append(other)
                    cluster.append(
                        {
                            "knowledge_id": other,
                            "relationship": edge.edge_type,
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
    return get_edge_summary(knowledge_id, layer="semantic")


# ─── Auto-Detection ─────────────────────────────────────────────────

# Causal language patterns
_CAUSAL_PATTERNS = [
    re.compile(r"\bbecause\b", re.IGNORECASE),
    re.compile(r"\bcaused by\b", re.IGNORECASE),
    re.compile(r"\bdue to\b", re.IGNORECASE),
    re.compile(r"\bresulted? from\b", re.IGNORECASE),
    re.compile(r"\bsince\b.*\b(?:broke|failed|crashed|error)", re.IGNORECASE),
    re.compile(r"\bafter\b.*\b(?:broke|failed|crashed|stopped)", re.IGNORECASE),
]

# Elaboration signals — one entry adds detail to another
_ELABORATION_PATTERNS = [
    re.compile(r"\bspecifically\b", re.IGNORECASE),
    re.compile(r"\bfor example\b", re.IGNORECASE),
    re.compile(r"\bin particular\b", re.IGNORECASE),
    re.compile(r"\bmore precisely\b", re.IGNORECASE),
    re.compile(r"\bnamely\b", re.IGNORECASE),
]

# Negation patterns — word-boundary-aware to avoid false positives
_NEGATION_PATTERNS = [
    re.compile(r"\bnot\b", re.IGNORECASE),
    re.compile(r"\bnever\b", re.IGNORECASE),
    re.compile(r"\bno longer\b", re.IGNORECASE),
    re.compile(r"\bwas fixed\b", re.IGNORECASE),
    re.compile(r"\bnow fixed\b", re.IGNORECASE),
    re.compile(r"\bresolved\b", re.IGNORECASE),
    re.compile(r"\bdon'?t\b", re.IGNORECASE),
    re.compile(r"\bcan'?t\b", re.IGNORECASE),
    re.compile(r"\bwon'?t\b", re.IGNORECASE),
    re.compile(r"\bisn'?t\b", re.IGNORECASE),
]

# Knowledge type pairs where certain relationships are natural
_TYPE_AFFINITIES: dict[tuple[str, str], str] = {
    ("OBSERVATION", "PRINCIPLE"): "SUPPORTS",
    ("OBSERVATION", "BOUNDARY"): "SUPPORTS",
    ("EPISODE", "OBSERVATION"): "DERIVED_FROM",
    ("PROCEDURE", "PRINCIPLE"): "APPLIES_TO",
    ("PROCEDURE", "BOUNDARY"): "APPLIES_TO",
    ("PRINCIPLE", "BOUNDARY"): "SUPPORTS",
    ("PRINCIPLE", "DIRECTIVE"): "SUPPORTS",
    ("BOUNDARY", "DIRECTIVE"): "ELABORATES",
    ("DIRECTION", "PRINCIPLE"): "SUPPORTS",
    ("MISTAKE", "PRINCIPLE"): "CAUSED_BY",
    ("MISTAKE", "BOUNDARY"): "CAUSED_BY",
    ("PATTERN", "PRINCIPLE"): "SUPPORTS",
}


def _has_negation_marker(text: str) -> bool:
    return any(p.search(text) for p in _NEGATION_PATTERNS)


def _has_causal_language(text: str) -> bool:
    return any(p.search(text) for p in _CAUSAL_PATTERNS)


def _has_elaboration_language(text: str) -> bool:
    return any(p.search(text) for p in _ELABORATION_PATTERNS)


def _classify_relationship(
    new_content: str,
    new_type: str,
    existing_content: str,
    existing_type: str,
    overlap: float,
) -> str | None:
    """Determine the relationship type between two knowledge entries.

    Returns a relationship type string or None if no relationship detected.
    Only fires when there's meaningful overlap (>0.3).
    """
    if overlap < 0.3:
        return None

    # High overlap + negation difference = CONTRADICTS
    if overlap >= 0.5:
        new_neg = _has_negation_marker(new_content)
        existing_neg = _has_negation_marker(existing_content)
        if new_neg != existing_neg:
            return "CONTRADICTS"

    # Very high overlap + new is longer = ELABORATES
    if overlap >= 0.6:
        new_words = len(new_content.split())
        existing_words = len(existing_content.split())
        if new_words > existing_words * 1.5:
            return "ELABORATES"
        if _has_elaboration_language(new_content):
            return "ELABORATES"

    # Causal language in the new entry pointing at the existing topic
    if overlap >= 0.35 and _has_causal_language(new_content):
        return "CAUSED_BY"

    # Type-based affinities
    pair = (new_type, existing_type)
    if pair in _TYPE_AFFINITIES and overlap >= 0.35:
        return _TYPE_AFFINITIES[pair]

    # Moderate overlap between same types = RELATED_TO
    if overlap >= 0.5 and new_type == existing_type:
        return "RELATED_TO"

    # Cross-type with decent overlap — different facets of the same topic
    if overlap >= 0.4 and new_type != existing_type:
        return "RELATED_TO"

    return None


def auto_detect_relationships(
    new_ids: list[str],
    max_candidates: int = 20,
) -> list[dict[str, str]]:
    """Scan newly extracted knowledge against existing entries and create relationships.

    For each new entry:
    1. Search existing knowledge via FTS5 for similar content
    2. Compute word overlap
    3. Classify the relationship type using heuristics
    4. Create the edge
    """
    if not new_ids:
        return []

    conn = get_connection()
    try:
        placeholders = ",".join("?" for _ in new_ids)
        new_rows = conn.execute(
            f"SELECT knowledge_id, knowledge_type, content FROM knowledge "  # nosec B608
            f"WHERE knowledge_id IN ({placeholders})",
            new_ids,
        ).fetchall()
    finally:
        conn.close()

    new_entries = {r[0]: {"type": r[1], "content": r[2]} for r in new_rows}
    created: list[dict[str, str]] = []
    new_id_set = set(new_ids)

    for kid, entry in new_entries.items():
        key_terms = _extract_key_terms(entry["content"])
        if not key_terms:
            continue

        try:
            candidates = search_knowledge(key_terms, limit=max_candidates)
        except _RELATIONSHIPS_ERRORS:
            continue

        for candidate in candidates:
            cid = candidate["knowledge_id"]
            if cid == kid or cid in new_id_set:
                continue

            overlap = _compute_overlap(entry["content"], candidate["content"])
            rel_type = _classify_relationship(
                new_content=entry["content"],
                new_type=entry["type"],
                existing_content=candidate["content"],
                existing_type=candidate["knowledge_type"],
                overlap=overlap,
            )

            if rel_type:
                try:
                    add_relationship(kid, cid, rel_type, notes="auto-detected")
                    created.append(
                        {
                            "source_id": kid,
                            "target_id": cid,
                            "relationship": rel_type,
                        }
                    )
                except (ValueError, sqlite3.IntegrityError):
                    pass  # duplicate or invalid relationship type

        # Also relate new entries to each other
        for other_kid, other_entry in new_entries.items():
            if other_kid <= kid:
                continue
            overlap = _compute_overlap(entry["content"], other_entry["content"])
            rel_type = _classify_relationship(
                new_content=entry["content"],
                new_type=entry["type"],
                existing_content=other_entry["content"],
                existing_type=other_entry["type"],
                overlap=overlap,
            )
            if rel_type:
                try:
                    add_relationship(kid, other_kid, rel_type, notes="auto-detected")
                    created.append(
                        {
                            "source_id": kid,
                            "target_id": other_kid,
                            "relationship": rel_type,
                        }
                    )
                except (ValueError, sqlite3.IntegrityError):
                    pass  # duplicate or invalid relationship type

    if created:
        logger.debug(f"Auto-detected {len(created)} relationships for {len(new_ids)} new entries")

    return created
