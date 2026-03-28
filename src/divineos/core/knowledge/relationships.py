"""Knowledge Relationships — typed edges between knowledge entries.

Knowledge doesn't exist in isolation. A MISTAKE might be CAUSED_BY a
PROCEDURE. A PRINCIPLE might be SUPPORTED_BY multiple OBSERVATIONs.
This module tracks those connections so I can navigate my own knowledge
graph rather than treating it as a flat list.
"""

import re
import time
import uuid
from typing import Any

from loguru import logger

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

# Negation patterns — word-boundary-aware to avoid false positives (e.g. "not" in "noticed")
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
    Only fires when there's meaningful overlap (>0.3) — we don't want
    to link everything to everything.
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

    # Type-based affinities (e.g. OBSERVATION naturally supports PRINCIPLE)
    pair = (new_type, existing_type)
    if pair in _TYPE_AFFINITIES and overlap >= 0.35:
        return _TYPE_AFFINITIES[pair]

    # Moderate overlap between same types = RELATED_TO (catch-all, conservative)
    if overlap >= 0.5 and new_type == existing_type:
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

    Returns a list of {source_id, target_id, relationship} dicts for what was created.
    """
    if not new_ids:
        return []

    from divineos.core.knowledge._text import _compute_overlap, _extract_key_terms
    from divineos.core.knowledge.crud import search_knowledge

    init_relationship_table()

    # Load the new entries
    conn = _get_connection()
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
        # Find candidates via FTS
        key_terms = _extract_key_terms(entry["content"])
        if not key_terms:
            continue

        try:
            candidates = search_knowledge(key_terms, limit=max_candidates)
        except Exception:
            continue

        for candidate in candidates:
            cid = candidate["knowledge_id"]
            # Don't relate to self or to other new entries from same batch
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
                except (ValueError, Exception):
                    pass  # duplicate or other issue — skip silently

        # Also relate new entries to each other
        for other_kid, other_entry in new_entries.items():
            if other_kid <= kid:  # avoid duplicates and self
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
                except (ValueError, Exception):
                    pass

    if created:
        logger.debug(f"Auto-detected {len(created)} relationships for {len(new_ids)} new entries")

    return created
