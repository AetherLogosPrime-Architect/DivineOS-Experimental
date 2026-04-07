"""Smart knowledge storage and consolidation."""

import json
import time
import uuid
from typing import Any, cast
import sqlite3

from loguru import logger

from divineos.core.knowledge._base import (
    KNOWLEDGE_TYPES,
    _KNOWLEDGE_COLS_K,
    _get_connection,
    _row_to_dict,
    compute_hash,
)
from divineos.core.constants import (
    OVERLAP_DUPLICATE,
    OVERLAP_QUASI_IDENTICAL,
    OVERLAP_STRONG,
)
from divineos.core.knowledge._text import (
    _compute_overlap,
    _extract_key_terms,
    _is_extraction_noise,
    _normalize_text,
    _STOPWORDS,
    _MIN_CONTENT_WORDS,
)
from divineos.core.knowledge.crud import (
    get_knowledge,
    store_knowledge,
    supersede_knowledge,
)
from divineos.core.knowledge_maintenance import (
    increment_corroboration,
    promote_maturity,
    resolve_contradiction,
    scan_for_contradictions,
)
from divineos.core.logic.warrants import create_warrant

_EXTRACTION_ERRORS = (
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
    json.JSONDecodeError,
)


# Maps knowledge source to warrant type for auto-warrant creation
_SOURCE_TO_WARRANT = {
    "STATED": "TESTIMONIAL",
    "CORRECTED": "TESTIMONIAL",
    "DEMONSTRATED": "EMPIRICAL",
    "SYNTHESIZED": "INFERENTIAL",
    "INHERITED": "INHERITED",
}


# ─── Smart Knowledge Storage ─────────────────────────────────────────


def _decide_operation(
    content: str,
    knowledge_type: str,
    best_match: dict[str, Any] | None,
    best_overlap: float,
) -> tuple[str, str | None]:
    """Decide what to do with incoming knowledge.

    Returns (operation, existing_id):
        - ("NOOP", id)   — exact or very close match, just bump access count
        - ("UPDATE", id) — high overlap but enough new info to supersede old
        - ("ADD", None)  — no close match, insert fresh
        - ("SKIP", None) — too short or pure subset, not worth storing
    """
    # Skip: content too short to be useful
    content_words = set(_normalize_text(content).split()) - _STOPWORDS
    meaningful_words = {w for w in content_words if len(w) > 2}
    if len(meaningful_words) < _MIN_CONTENT_WORDS:
        return ("SKIP", None)

    # Skip: conversational noise (raw user quotes, affirmations, questions)
    if _is_extraction_noise(content, knowledge_type):
        return ("SKIP", None)

    if best_match is None or best_overlap < OVERLAP_DUPLICATE:
        return ("ADD", None)

    # NOOP: near-identical (current dedup behavior)
    if best_overlap > OVERLAP_QUASI_IDENTICAL:
        # Check if there's enough genuinely new info to warrant an UPDATE
        existing_words = set(_normalize_text(best_match["content"]).split()) - _STOPWORDS
        new_words = meaningful_words - existing_words
        new_ratio = len(new_words) / max(1, len(meaningful_words))
        if new_ratio > 0.2:
            # 20%+ genuinely new words → supersede old with new
            return ("UPDATE", best_match["knowledge_id"])
        return ("NOOP", best_match["knowledge_id"])

    # Medium overlap (0.4-0.6): different enough to add
    return ("ADD", None)


def store_knowledge_smart(
    knowledge_type: str,
    content: str,
    confidence: float = 1.0,
    source_events: list[str] | None = None,
    tags: list[str] | None = None,
    source: str = "STATED",
    maturity: str = "RAW",
) -> str:
    """Store knowledge with smart operation selection.

    Decides between ADD, UPDATE, SKIP, or NOOP based on content analysis:
    - NOOP: exact or near-duplicate, bump access count
    - UPDATE: high overlap but 20%+ new info, supersede old entry
    - ADD: no close match, insert fresh
    - SKIP: too short or pure noise, return empty string

    Also scans for contradictions against existing same-type entries
    and resolves them automatically.
    """
    # Voice normalization: knowledge speaks as me, not about me
    from divineos.core.knowledge._text import normalize_to_first_person

    content = normalize_to_first_person(content)

    # First: try exact hash dedup (fast path)
    content_hash = compute_hash(content)
    conn = _get_connection()
    try:
        # Check ALL entries with this hash (active AND superseded)
        all_with_hash = conn.execute(
            "SELECT knowledge_id, knowledge_type, superseded_by FROM knowledge WHERE content_hash = ?",
            (content_hash,),
        ).fetchall()

        for kid, ktype, superseded_by in all_with_hash:
            if ktype != knowledge_type:
                continue
            if superseded_by is not None:
                # This exact content was previously superseded — don't resurrect it
                logger.debug(f"Skipping superseded duplicate: {content[:60]}")
                return ""
            # Active exact match — bump access count
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (time.time(), kid),
            )
            conn.commit()
            # Exact match = corroboration
            try:
                increment_corroboration(str(kid))
                promote_maturity(str(kid))
            except _EXTRACTION_ERRORS as e:
                logger.debug(f"Maturity check failed: {e}", exc_info=True)
            return str(kid)

        # Find best fuzzy match via FTS5
        best_match: dict[str, Any] | None = None
        best_overlap = 0.0
        # nosec B608 - column names are hardcoded constants, query parameters passed separately
        fts_query = f"""SELECT {_KNOWLEDGE_COLS_K}
                       FROM knowledge_fts fts
                       JOIN knowledge k ON k.rowid = fts.rowid
                       WHERE knowledge_fts MATCH ?
                         AND k.superseded_by IS NULL
                       ORDER BY bm25(knowledge_fts, 10.0, 5.0, 1.0)
                       LIMIT 10"""
        key_terms = _extract_key_terms(content)
        if key_terms:
            try:
                rows = conn.execute(fts_query, (key_terms,)).fetchall()
                for row in rows:
                    entry = _row_to_dict(row)
                    if entry["knowledge_type"] == knowledge_type:
                        overlap = _compute_overlap(content, entry["content"])
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_match = entry
            except _EXTRACTION_ERRORS as e:
                logger.warning(f"FTS5 search failed, dedup may miss matches: {e}")

        # Decide operation
        operation, existing_id = _decide_operation(
            content, knowledge_type, best_match, best_overlap
        )
        logger.debug(f"Knowledge operation: {operation} (overlap={best_overlap:.2f})")

        if operation == "SKIP":
            logger.info(f"Skipped noise knowledge: {content[:60]}")
            return ""

        if operation == "NOOP":
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (time.time(), existing_id),
            )
            conn.commit()
            # Corroboration: re-encountering knowledge strengthens trust
            try:
                increment_corroboration(cast("str", existing_id))
                promote_maturity(cast("str", existing_id))
            except _EXTRACTION_ERRORS as e:
                logger.debug(f"Maturity check failed: {e}", exc_info=True)
            return cast("str", existing_id)

        # For ADD and UPDATE, we insert a new entry
        now = time.time()
        sources_json = json.dumps(source_events or [])
        tags_json = json.dumps(tags or [])
        kid = str(uuid.uuid4())

        # Check for same-type hash match (race condition guard)
        hash_match = conn.execute(
            "SELECT knowledge_id FROM knowledge WHERE content_hash = ? AND knowledge_type = ? AND superseded_by IS NULL",
            (content_hash, knowledge_type),
        ).fetchone()
        if hash_match:
            conn.execute(
                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                (now, hash_match[0]),
            )
            conn.commit()
            return str(hash_match[0])

        # Insert new entry — born with corroboration=1 (it was observed once,
        # which is enough to qualify for RAW→HYPOTHESIS promotion)
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, created_at, updated_at, knowledge_type, content, confidence, source_events, tags, access_count, content_hash, source, maturity, corroboration_count, contradiction_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 1, 0)",
            (
                kid,
                now,
                now,
                knowledge_type,
                content,
                confidence,
                sources_json,
                tags_json,
                content_hash,
                source,
                maturity,
            ),
        )
        conn.commit()

        # Attempt initial maturity promotion (RAW→HYPOTHESIS).
        # promote_maturity is already imported at module level from
        # knowledge_maintenance — safe to call here since the module
        # is fully initialized by the time store_knowledge_smart runs.
        try:
            promote_maturity(kid)
        except _EXTRACTION_ERRORS as e:
            logger.debug(f"Initial maturity promotion failed: {e}", exc_info=True)

        # UPDATE: supersede the old entry
        if operation == "UPDATE" and existing_id:
            supersede_knowledge(existing_id, reason=f"Updated by {kid[:12]}")
            logger.info(f"Updated knowledge: {existing_id[:12]} → {kid[:12]}")

        # Auto-create warrant — every new knowledge entry is born with justification
        try:
            warrant_type = _SOURCE_TO_WARRANT.get(source, "TESTIMONIAL")
            create_warrant(
                knowledge_id=kid,
                warrant_type=warrant_type,
                grounds=f"{source.lower()} knowledge: {content[:80]}",
                source_events=source_events or [],
            )
        except _EXTRACTION_ERRORS as e:
            logger.debug(f"Auto-warrant creation failed: {e}", exc_info=True)

        # Scan for contradictions against same-type entries
        try:
            same_type = get_knowledge(knowledge_type=knowledge_type, limit=100)
            # Exclude the entry we just created
            same_type = [e for e in same_type if e["knowledge_id"] != kid]
            contradictions = scan_for_contradictions(content, knowledge_type, same_type)
            for match in contradictions:
                resolve_contradiction(kid, match)
        except _EXTRACTION_ERRORS as e:
            logger.debug(f"Contradiction scan failed: {e}", exc_info=True)

        # Post-insert dedup guard: check if FTS finds a pre-existing near-match
        # that we missed (handles race conditions with concurrent inserts)
        if key_terms and operation == "ADD":
            try:
                rows = conn.execute(fts_query, (key_terms,)).fetchall()
                for row in rows:
                    entry = _row_to_dict(row)
                    if entry["knowledge_id"] == kid:
                        continue
                    if entry["knowledge_type"] == knowledge_type:
                        overlap = _compute_overlap(content, entry["content"])
                        if overlap > OVERLAP_QUASI_IDENTICAL:
                            conn.execute(
                                "UPDATE knowledge SET superseded_by = ?, updated_at = ? WHERE knowledge_id = ?",
                                (entry["knowledge_id"], time.time(), kid),
                            )
                            conn.execute(
                                "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
                                (time.time(), entry["knowledge_id"]),
                            )
                            conn.commit()
                            return cast("str", entry["knowledge_id"])
            except _EXTRACTION_ERRORS as e:
                logger.debug(f"Post-insert FTS5 search failed: {e}", exc_info=True)

        return kid
    finally:
        conn.close()


# ─── Consolidation ───────────────────────────────────────────────────


def consolidate_related(min_cluster_size: int = 3) -> list[dict[str, Any]]:
    """Find and merge clusters of related knowledge entries.

    Groups entries by type, finds clusters with >50% word overlap,
    and merges clusters of min_cluster_size or more into single entries.

    Returns list of dicts describing what was merged:
        [{"type": "MISTAKE", "merged_count": 4, "new_id": "abc...", "content": "..."}]
    """
    merges: list[dict[str, Any]] = []

    for ktype in KNOWLEDGE_TYPES:
        entries = get_knowledge(knowledge_type=ktype, limit=500)
        if len(entries) < min_cluster_size:
            continue

        # Build clusters using word overlap
        clustered: set[str] = set()  # knowledge_ids already in a cluster
        clusters: list[list[dict[str, Any]]] = []

        for i, entry in enumerate(entries):
            if entry["knowledge_id"] in clustered:
                continue

            cluster = [entry]
            clustered.add(entry["knowledge_id"])

            for j in range(i + 1, len(entries)):
                other = entries[j]
                if other["knowledge_id"] in clustered:
                    continue
                overlap = _compute_overlap(entry["content"], other["content"])
                if overlap > OVERLAP_STRONG:
                    cluster.append(other)
                    clustered.add(other["knowledge_id"])

            if len(cluster) >= min_cluster_size:
                clusters.append(cluster)

        # Merge each cluster
        for cluster in clusters:
            # Pick the longest content as the base (most informative)
            cluster.sort(key=lambda e: len(e["content"]), reverse=True)
            best = cluster[0]

            # Combine sources and tags
            all_sources: list[str] = []
            all_tags: set[str] = set()
            max_confidence = 0.0
            for entry in cluster:
                all_sources.extend(entry["source_events"])
                all_tags.update(entry["tags"])
                max_confidence = max(max_confidence, entry["confidence"])

            all_tags.add("consolidated")
            all_tags.discard("")

            # Create the merged entry with unique content to avoid hash dedup
            merged_content = best["content"]
            source_count = len(cluster)
            # Append consolidation note to make content unique
            merged_content = f"{merged_content} [consolidated from {source_count} entries]"
            new_id = store_knowledge(
                knowledge_type=ktype,
                content=merged_content,
                confidence=max_confidence,
                source_events=list(set(all_sources)),
                tags=sorted(all_tags),
            )

            # Supersede the individual entries
            conn = _get_connection()
            try:
                for entry in cluster:
                    if entry["knowledge_id"] != new_id:
                        conn.execute(
                            "UPDATE knowledge SET superseded_by = ? WHERE knowledge_id = ?",
                            (new_id, entry["knowledge_id"]),
                        )
                conn.commit()
            finally:
                conn.close()

            merges.append(
                {
                    "type": ktype,
                    "merged_count": len(cluster),
                    "new_id": new_id,
                    "content": merged_content[:100],
                },
            )

    return merges
