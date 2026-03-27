"""Smart knowledge storage and deep session extraction."""

import json
import re
import time
import uuid
from typing import Any, cast

from loguru import logger

from divineos.core.knowledge._base import (
    KNOWLEDGE_TYPES,
    _KNOWLEDGE_COLS_K,
    _get_connection,
    _row_to_dict,
    compute_hash,
)
from divineos.core.knowledge._text import (
    _compute_overlap,
    _extract_key_terms,
    _is_extraction_noise,
    _normalize_text,
    _STOPWORDS,
    _MIN_CONTENT_WORDS,
    extract_session_topics,
)
from divineos.core.knowledge.crud import (
    get_knowledge,
    store_knowledge,
    supersede_knowledge,
)


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

    if best_match is None or best_overlap < 0.4:
        return ("ADD", None)

    # NOOP: near-identical (current dedup behavior)
    if best_overlap > 0.6:
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
                from divineos.core.knowledge_maturity import (
                    increment_corroboration,
                    promote_maturity,
                )

                increment_corroboration(str(kid))
                promote_maturity(str(kid))
            except Exception as e:
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
            except Exception as e:
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
                from divineos.core.knowledge_maturity import (
                    increment_corroboration,
                    promote_maturity,
                )

                increment_corroboration(cast("str", existing_id))
                promote_maturity(cast("str", existing_id))
            except Exception as e:
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

        # Insert new entry
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, created_at, updated_at, knowledge_type, content, confidence, source_events, tags, access_count, content_hash, source, maturity, corroboration_count, contradiction_count) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, 0, 0)",
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

        # UPDATE: supersede the old entry
        if operation == "UPDATE" and existing_id:
            supersede_knowledge(existing_id, reason=f"Updated by {kid[:12]}")
            logger.info(f"Updated knowledge: {existing_id[:12]} → {kid[:12]}")

        # Scan for contradictions against same-type entries
        try:
            from divineos.core.knowledge_contradiction import (
                resolve_contradiction,
                scan_for_contradictions,
            )

            same_type = get_knowledge(knowledge_type=knowledge_type, limit=100)
            # Exclude the entry we just created
            same_type = [e for e in same_type if e["knowledge_id"] != kid]
            contradictions = scan_for_contradictions(content, knowledge_type, same_type)
            for match in contradictions:
                resolve_contradiction(kid, match)
        except Exception as e:
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
                        if overlap > 0.6:
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
            except Exception as e:
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
                if overlap > 0.5:
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


# ─── Deep Session Extraction ─────────────────────────────────────────

# Patterns for extracting reasoning context from messages
_REASON_PATTERNS = (
    re.compile(r"\bbecause\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bsince\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bso that\b\s+(.{10,120})", re.IGNORECASE),
    re.compile(r"\bthe reason\b\s+(.{10,120})", re.IGNORECASE),
)

_ALTERNATIVE_PATTERNS = (
    re.compile(r"\binstead of\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\brather than\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\bnot\b\s+(\w+.{5,60})", re.IGNORECASE),
)


def _extract_assistant_summary(record: dict[str, Any]) -> str:
    """Extract a short summary of what the assistant was doing in a record."""
    msg = record.get("message", {})
    content = msg.get("content", [])
    if not isinstance(content, list):
        return ""

    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            text = block.get("text", "")
            # Take first meaningful sentence
            sentences = re.split(r"[.!?\n]", text)
            for s in sentences:
                s = s.strip()
                if len(s) > 15:
                    parts.append(s[:150])
                    break
        elif block.get("type") == "tool_use":
            name = block.get("name", "unknown")
            inp = block.get("input", {})
            if name in ("Read", "Edit", "Write"):
                fp = inp.get("file_path", "")
                parts.append(f"{name} {fp}")
            elif name == "Bash":
                cmd = inp.get("command", "")[:60]
                parts.append(f"Bash: {cmd}")
            else:
                parts.append(f"Tool: {name}")

    return "; ".join(parts[:3])


def _find_reason_in_text(text: str) -> str:
    """Try to extract a reason/justification from text."""
    for pattern in _REASON_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".")
    return ""


def _find_alternative_in_text(text: str) -> str:
    """Try to extract what was rejected/compared against."""
    for pattern in _ALTERNATIVE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).strip().rstrip(".")
    return ""


def _distill_correction(raw_text: str) -> str:
    """Transform a raw correction quote into a first-person insight.

    Instead of: "no when i say you.. you say i or me.."
    Produce:    "I was told: when the user says 'you' referring to me, I should respond with 'I' or 'me'."
    """
    text = raw_text.strip()[:300]
    # Strip common prefixes that add noise
    for prefix in ("no ", "no, ", "wrong ", "wrong, ", "stop ", "don't "):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    # Clean up
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    # Remove trailing fragments
    if text and text[-1] not in ".!?":
        text = text.rstrip(". ") + "."
    return f"I was corrected: {text}"


def _distill_preference(raw_text: str) -> str:
    """Transform a raw preference quote into a first-person direction."""
    text = raw_text.strip()[:300]
    # Strip "I want", "I prefer", "I like" prefixes — rephrase as what I should do
    for prefix in ("i want ", "i prefer ", "i like ", "i need ", "please "):
        if text.lower().startswith(prefix):
            text = text[len(prefix) :]
            break
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    if text and text[-1] not in ".!?":
        text = text.rstrip(". ") + "."
    return f"I should: {text}"


def _extract_user_text_from_record(record: dict[str, Any]) -> str:
    """Extract clean user text from a record (duplicate of session_analyzer helper)."""
    msg = record.get("message", {})
    content = msg.get("content", "")
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        content = " ".join(parts)
    if not isinstance(content, str):
        content = str(content)
    if "<system-reminder>" in content:
        content = content[: content.index("<system-reminder>")]
    return content.strip()


def deep_extract_knowledge(
    analysis: "Any",  # SessionAnalysis — avoid circular import
    records: list[dict[str, Any]],
) -> list[str]:
    """Extract rich, structured knowledge from a session analysis + raw records.

    Goes beyond simple signal detection to extract:
    - Correction pairs (what AI did wrong → what user wanted)
    - User preferences with context
    - Decisions with reasoning and alternatives
    - Session topics

    Returns list of stored knowledge IDs.
    """
    stored_ids: list[str] = []
    session_id = analysis.session_id
    short_id = session_id[:12]

    # Build a map of record index → record for context lookups
    user_indices: list[int] = []
    for i, rec in enumerate(records):
        if rec.get("type") == "user":
            user_indices.append(i)

    # Session topics are extracted but only used as tags on other knowledge,
    # not stored as standalone facts (word frequency alone produces keyword soup).
    topics = extract_session_topics(analysis.user_message_texts)
    topic_tags = [f"topic-{t}" for t in topics[:5]]

    # --- Correction pairs → PRINCIPLE or BOUNDARY with insight content ---
    for correction in analysis.corrections:
        correction_text = correction.content

        # Skip venting/frustration that matched correction patterns but isn't
        # actionable guidance. Real corrections tell the AI what to do differently;
        # frustrations just express displeasure.
        lower_text = correction_text.lower().strip()
        # Too short to be a real instruction (e.g. "no", "wrong")
        if len(lower_text.split()) < 5:
            continue
        # Frustration indicators without actionable content
        frustration_only = any(
            marker in lower_text
            for marker in (
                "i dont even know",
                "i don't even know",
                "what is going on",
                "fml",
                "im lost",
                "i'm lost",
                "utterly lost",
                "i have no idea",
                "this is a mess",
                "a nightmare",
            )
        )
        if frustration_only:
            continue
        # Find this correction in the raw records and get the assistant message before it
        ai_before = ""
        for i, rec in enumerate(records):
            if rec.get("type") != "user":
                continue
            user_text = _extract_user_text_from_record(rec)
            if not user_text:
                continue
            if user_text[:100] == correction_text[:100]:
                for j in range(i - 1, max(i - 5, -1), -1):
                    if records[j].get("type") == "assistant":
                        ai_before = _extract_assistant_summary(records[j])
                        break
                break

        # Classify: hard constraint words → BOUNDARY, otherwise → PRINCIPLE
        lower = correction_text.lower()
        is_boundary = any(
            w in lower for w in ("never", "always", "must", "don't", "do not", "cannot")
        )
        ktype = "BOUNDARY" if is_boundary else "PRINCIPLE"

        # Store insight in first person — future me needs to inhabit this, not parse it
        if ai_before:
            content = f"I was {ai_before.lower()}, but got corrected — {correction_text[:200]}"
        else:
            content = _distill_correction(correction_text)

        kid = store_knowledge_smart(
            knowledge_type=ktype,
            content=content,
            confidence=0.85,
            source="CORRECTED",
            maturity="HYPOTHESIS",
            source_events=[session_id],
            tags=["auto-extracted", "correction-pair", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Preferences → DIRECTION ---
    for pref in getattr(analysis, "preferences", []):
        kid = store_knowledge_smart(
            knowledge_type="DIRECTION",
            content=_distill_preference(pref.content),
            confidence=0.9,
            source="STATED",
            maturity="CONFIRMED",
            source_events=[session_id],
            tags=["auto-extracted", "direction", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Decisions with context ---
    for decision in analysis.decisions:
        decision_text = decision.content
        # Skip short affirmations that aren't real decisions
        if len(decision_text.split()) < 8:
            continue
        # Skip if the noise filter catches it
        if _is_extraction_noise(f"I decided: {decision_text}", "PRINCIPLE"):
            continue
        reason = _find_reason_in_text(decision_text)
        alternative = _find_alternative_in_text(decision_text)

        # Also check the next user message for reasoning
        if not reason:
            for i, rec in enumerate(records):
                if rec.get("type") != "user":
                    continue
                user_text = _extract_user_text_from_record(rec)
                if user_text and user_text[:80] == decision_text[:80]:
                    # Check next user message for reasoning
                    for j in range(i + 1, min(i + 4, len(records))):
                        if records[j].get("type") == "user":
                            next_text = _extract_user_text_from_record(records[j])
                            reason = _find_reason_in_text(next_text)
                            break
                    break

        parts = [f"I decided: {decision_text[:200]}"]
        if alternative:
            parts.append(f"I considered but rejected: {alternative}")
        if reason:
            parts.append(f"Because: {reason}")

        kid = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content=". ".join(parts),
            confidence=0.9,
            source="DEMONSTRATED",
            maturity="HYPOTHESIS",
            source_events=[session_id],
            tags=["auto-extracted", "decision", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    # --- Encouragements as positive patterns ---
    for enc in analysis.encouragements:
        # Find what the AI did right (assistant message before encouragement)
        ai_before = ""
        for i, rec in enumerate(records):
            if rec.get("type") != "user":
                continue
            user_text = _extract_user_text_from_record(rec)
            if user_text and user_text[:80] == enc.content[:80]:
                for j in range(i - 1, max(i - 5, -1), -1):
                    if records[j].get("type") == "assistant":
                        ai_before = _extract_assistant_summary(records[j])
                        break
                break

        if not ai_before:
            # Without knowing what the AI did right, the encouragement is just
            # a raw user quote with no actionable insight. Skip it.
            continue

        content = f"I {ai_before.lower()} and it worked well — user affirmed: {enc.content[:150]}"

        kid = store_knowledge_smart(
            knowledge_type="PRINCIPLE",
            content=content,
            confidence=0.9,
            source="DEMONSTRATED",
            maturity="TESTED",
            source_events=[session_id],
            tags=["auto-extracted", "encouragement", f"session-{short_id}", *topic_tags],
        )
        stored_ids.append(kid)

    return stored_ids
