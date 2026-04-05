"""Knowledge Maintenance — contradiction detection, hygiene cleanup, and maturity promotion.

This module consolidates three knowledge lifecycle operations:

1. **Contradiction Detection**: Finds and resolves conflicting knowledge entries.
   When new knowledge is stored, scans existing same-type entries for contradictions
   via word overlap and negation markers.

2. **Knowledge Hygiene**: Periodic cleanup of the knowledge store. Re-runs noise
   filters on existing entries, decays stale temporal entries, and flags orphans
   that were never accessed.

3. **Maturity Lifecycle**: Promotes knowledge through trust levels
   (RAW -> HYPOTHESIS -> TESTED -> CONFIRMED) based on corroboration counts
   and validity gates.
"""

from __future__ import annotations

import sqlite3
import time
from dataclasses import dataclass
from typing import Any

from loguru import logger

from divineos.core.knowledge._base import (
    _KNOWLEDGE_COLS,
    _get_connection,
    _row_to_dict,
)
from divineos.core.knowledge._text import (
    _compute_stemmed_overlap,
    _has_prescriptive_signal,
    _has_temporal_markers,
    _is_extraction_noise,
    _stemmed_word_set,
)
from divineos.core.knowledge import get_connection
from divineos.core.knowledge.crud import supersede_knowledge
from divineos.core.logic.logic_validation import can_promote

from divineos.core.constants import (
    CONFIDENCE_DEMOTE_CAP,
    CONFIDENCE_ORPHAN_DEMOTE,
    CONFIDENCE_RETRIEVAL_FLOOR,
    DECAY_FLOOR,
    DECAY_MODERATE,
    DECAY_STANDARD,
    HYGIENE_MIN_AGE_DAYS,
    HYGIENE_ORPHAN_MIN_SESSIONS,
    HYGIENE_STALE_AGE_DAYS,
    MATURITY_HYPOTHESIS_TO_TESTED_CONFIDENCE,
    MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION,
    MATURITY_RAW_TO_HYPOTHESIS_CONFIDENCE,
    MATURITY_RAW_TO_HYPOTHESIS_CORROBORATION,
    MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE,
    MATURITY_TESTED_TO_CONFIRMED_CORROBORATION,
    OVERLAP_DUPLICATE,
    OVERLAP_NEAR_IDENTICAL,
    OVERLAP_STRONG,
    SECONDS_PER_DAY,
)


# ─── Contradiction Detection ────────────────────────────────────────────────


@dataclass
class ContradictionMatch:
    """A detected contradiction between new and existing knowledge."""

    existing_id: str
    existing_content: str
    overlap_score: float
    negation_detected: bool
    contradiction_type: str  # "TEMPORAL", "DIRECT", "SUPERSESSION"


# Words that signal a state change or negation
_NEGATION_MARKERS = {
    "not",
    "never",
    "no longer",
    "was fixed",
    "now fixed",
    "resolved",
    "no",
    "dont",
    "don't",
    "doesn't",
    "cannot",
    "isn't",
    "wasn't",
    "shouldn't",
    "won't",
    "removed",
    "deprecated",
    "obsolete",
}

# Words that signal temporal change
_TEMPORAL_MARKERS = {
    "was",
    "used to",
    "previously",
    "before",
    "now",
    "currently",
    "updated",
    "changed",
    "fixed",
    "resolved",
    "no longer",
}


def _has_negation(text: str) -> bool:
    """Check if text contains negation markers."""
    text_lower = text.lower()
    return any(marker in text_lower for marker in _NEGATION_MARKERS)


def _has_temporal_change(text: str) -> bool:
    """Check if text references a state change over time."""
    text_lower = text.lower()
    count = sum(1 for marker in _TEMPORAL_MARKERS if marker in text_lower)
    return count >= 2  # need at least 2 temporal markers to signal real change


def _classify_contradiction(
    new_content: str,
    existing_content: str,
    overlap: float,
) -> str | None:
    """Classify the type of contradiction, if any.

    Returns contradiction type or None if no contradiction detected.
    """
    new_has_negation = _has_negation(new_content)
    existing_has_negation = _has_negation(existing_content)
    new_temporal = _has_temporal_change(new_content)
    existing_temporal = _has_temporal_change(existing_content)

    # High overlap with different negation states = contradiction
    if overlap >= OVERLAP_STRONG:
        # Temporal: one references past state, other references current
        if new_temporal or existing_temporal:
            return "TEMPORAL"

        # Direct: same topic but opposing claims (one negated, other not)
        if new_has_negation != existing_has_negation:
            return "DIRECT"

        # Very high overlap = likely supersession (updated version)
        if overlap >= OVERLAP_NEAR_IDENTICAL:
            return "SUPERSESSION"

    return None


def scan_for_contradictions(
    new_content: str,
    new_type: str,
    existing_entries: list[dict[str, Any]],
) -> list[ContradictionMatch]:
    """Scan existing entries for contradictions with new content.

    Args:
        new_content: the content being stored
        new_type: knowledge type of the new entry
        existing_entries: list of existing knowledge dicts (same type)

    Returns:
        List of ContradictionMatch objects for each detected contradiction.
    """
    matches: list[ContradictionMatch] = []
    new_words = _stemmed_word_set(new_content)

    for entry in existing_entries:
        # Only compare same-type entries
        if entry.get("knowledge_type") != new_type:
            continue

        # Skip superseded entries
        if entry.get("superseded_by"):
            continue

        existing_words = _stemmed_word_set(entry.get("content", ""))
        overlap = _compute_stemmed_overlap(new_words, existing_words)

        if overlap < OVERLAP_DUPLICATE:
            continue

        contradiction_type = _classify_contradiction(new_content, entry.get("content", ""), overlap)

        if contradiction_type:
            matches.append(
                ContradictionMatch(
                    existing_id=entry["knowledge_id"],
                    existing_content=entry.get("content", ""),
                    overlap_score=overlap,
                    negation_detected=_has_negation(new_content)
                    or _has_negation(entry.get("content", "")),
                    contradiction_type=contradiction_type,
                )
            )

    return matches


def increment_contradiction_count(knowledge_id: str) -> None:
    """Increment the contradiction_count for a knowledge entry."""
    conn = _get_connection()
    try:
        conn.execute(
            "UPDATE knowledge SET contradiction_count = contradiction_count + 1, updated_at = ? WHERE knowledge_id = ?",
            (time.time(), knowledge_id),
        )
        conn.commit()
        logger.debug(f"Incremented contradiction_count for {knowledge_id[:12]}")
    finally:
        conn.close()


def resolve_contradiction(
    new_id: str,
    match: ContradictionMatch,
) -> None:
    """Resolve a detected contradiction based on its type.

    - TEMPORAL: supersede the old entry (new state replaces old)
    - DIRECT: flag both, reduce confidence on both
    - SUPERSESSION: supersede old with new
    """
    increment_contradiction_count(match.existing_id)

    if match.contradiction_type in ("TEMPORAL", "SUPERSESSION"):
        supersede_knowledge(
            match.existing_id,
            reason=f"Superseded by {new_id[:12]} ({match.contradiction_type})",
        )
        logger.info(
            f"Resolved {match.contradiction_type}: {match.existing_id[:12]} superseded by {new_id[:12]}"
        )
    elif match.contradiction_type == "DIRECT":
        # Both entries are suspect — reduce confidence on old
        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET confidence = MAX(?, confidence - ?), updated_at = ? WHERE knowledge_id = ?",
                (DECAY_FLOOR, DECAY_MODERATE, time.time(), match.existing_id),
            )
            conn.commit()
        finally:
            conn.close()
        logger.info(
            f"Resolved DIRECT contradiction: lowered confidence on {match.existing_id[:12]}"
        )


# ─── Knowledge Hygiene ──────────────────────────────────────────────────────


def run_knowledge_hygiene(
    demote_noise: bool = True,
    decay_stale: bool = True,
    flag_orphans: bool = True,
    min_age_days: float = HYGIENE_MIN_AGE_DAYS,
    stale_age_days: float = HYGIENE_STALE_AGE_DAYS,
    orphan_min_sessions: int = HYGIENE_ORPHAN_MIN_SESSIONS,
) -> dict[str, Any]:
    """Run all hygiene operations on the knowledge store.

    Returns a report of actions taken.
    """
    report: dict[str, Any] = {
        "noise_demoted": 0,
        "noise_superseded": 0,
        "stale_decayed": 0,
        "orphans_flagged": 0,
        "entries_scanned": 0,
        "details": [],
    }

    conn = _get_connection()
    try:
        rows = conn.execute(
            f"SELECT {_KNOWLEDGE_COLS} FROM knowledge "
            "WHERE superseded_by IS NULL AND confidence >= ? "
            "ORDER BY updated_at DESC",
            (CONFIDENCE_RETRIEVAL_FLOOR,),
        ).fetchall()
        entries = [_row_to_dict(row) for row in rows]
        report["entries_scanned"] = len(entries)
    finally:
        conn.close()

    now = time.time()
    cutoff = now - (min_age_days * SECONDS_PER_DAY)

    if demote_noise:
        noise_report = _audit_types(entries, cutoff)
        report["noise_demoted"] = noise_report["demoted"]
        report["noise_superseded"] = noise_report["superseded"]
        report["details"].extend(noise_report["details"])

    if decay_stale:
        stale_report = _sweep_stale(entries, now, stale_age_days)
        report["stale_decayed"] = stale_report["decayed"]
        report["details"].extend(stale_report["details"])

    if flag_orphans:
        orphan_report = _flag_orphans(entries, orphan_min_sessions)
        report["orphans_flagged"] = orphan_report["flagged"]
        report["details"].extend(orphan_report["details"])

    return report


def _audit_types(entries: list[dict[str, Any]], cutoff: float) -> dict[str, Any]:
    """Re-run noise filter on existing PRINCIPLE/BOUNDARY entries.

    Entries that would be rejected by today's filter get demoted to
    OBSERVATION (if they have some value) or superseded (if pure noise).
    """
    result: dict[str, Any] = {"demoted": 0, "superseded": 0, "details": []}
    conn = _get_connection()

    try:
        for entry in entries:
            kid = entry["knowledge_id"]
            ktype = entry.get("knowledge_type", "")
            content = entry.get("content", "")
            created = entry.get("created_at", 0)

            # Only audit PRINCIPLE and BOUNDARY types — others are fine
            if ktype not in ("PRINCIPLE", "BOUNDARY"):
                continue
            # Don't touch recent entries — give them time to prove value
            if created > cutoff:
                continue
            # Don't touch high-corroboration entries — they proved useful
            if entry.get("corroboration_count", 0) >= 3:
                continue
            # Don't touch pinned entries
            if entry.get("pinned"):
                continue

            # Would today's filter reject this?
            if _is_extraction_noise(content, ktype):
                # Pure noise — supersede it
                conn.execute(
                    "UPDATE knowledge SET superseded_by = 'hygiene-audit', "
                    "confidence = 0.1 WHERE knowledge_id = ?",
                    (kid,),
                )
                result["superseded"] += 1
                result["details"].append(f"Superseded {ktype}: {content[:60]}...")
                continue

            # Has no prescriptive signal — demote to OBSERVATION
            content_lower = content.lower()
            if not _has_prescriptive_signal(content_lower):
                conn.execute(
                    "UPDATE knowledge SET knowledge_type = 'OBSERVATION', "
                    "confidence = CASE WHEN confidence > ? THEN ? ELSE confidence END "
                    "WHERE knowledge_id = ?",
                    (CONFIDENCE_DEMOTE_CAP, CONFIDENCE_DEMOTE_CAP, kid),
                )
                result["demoted"] += 1
                result["details"].append(f"Demoted to OBSERVATION: {content[:60]}...")

        conn.commit()
    finally:
        conn.close()

    return result


def _sweep_stale(
    entries: list[dict[str, Any]], now: float, stale_age_days: float
) -> dict[str, Any]:
    """Decay confidence on entries with temporal markers that are old."""
    result: dict[str, Any] = {"decayed": 0, "details": []}
    conn = _get_connection()
    stale_cutoff = now - (stale_age_days * SECONDS_PER_DAY)

    try:
        for entry in entries:
            kid = entry["knowledge_id"]
            ktype = entry.get("knowledge_type", "")
            content = entry.get("content", "")
            updated = entry.get("updated_at", 0)
            confidence = entry.get("confidence", 0.5)

            # Directives are permanent by design
            if ktype == "DIRECTIVE":
                continue
            # Only decay old entries with temporal markers
            if updated > stale_cutoff:
                continue
            if not _has_temporal_markers(content):
                continue
            # Don't decay below floor
            if confidence <= DECAY_FLOOR:
                continue

            new_confidence = max(confidence - DECAY_STANDARD, DECAY_FLOOR)
            conn.execute(
                "UPDATE knowledge SET confidence = ? WHERE knowledge_id = ?",
                (new_confidence, kid),
            )
            result["decayed"] += 1
            result["details"].append(
                f"Decayed ({confidence:.1f}->{new_confidence:.1f}): {content[:60]}..."
            )

        conn.commit()
    finally:
        conn.close()

    return result


def _flag_orphans(entries: list[dict[str, Any]], min_sessions: int) -> dict[str, Any]:
    """Flag entries that were never accessed and are old enough to judge."""
    result: dict[str, Any] = {"flagged": 0, "details": []}
    conn = _get_connection()

    try:
        for entry in entries:
            kid = entry["knowledge_id"]
            ktype = entry.get("knowledge_type", "")
            content = entry.get("content", "")
            access_count = entry.get("access_count", 0)
            corroboration = entry.get("corroboration_count", 0)

            # Directives and pinned entries are exempt
            if ktype == "DIRECTIVE" or entry.get("pinned"):
                continue
            # Only flag entries that have never been accessed or corroborated
            if access_count >= 2 or corroboration >= 1:
                continue

            # Demote orphaned entries to low confidence
            confidence = entry.get("confidence", CONFIDENCE_ORPHAN_DEMOTE)
            if confidence > CONFIDENCE_ORPHAN_DEMOTE:
                new_confidence = CONFIDENCE_ORPHAN_DEMOTE
                conn.execute(
                    "UPDATE knowledge SET confidence = ? WHERE knowledge_id = ?",
                    (new_confidence, kid),
                )
                result["flagged"] += 1
                result["details"].append(f"Orphan ({access_count} accesses): {content[:60]}...")

        conn.commit()
    finally:
        conn.close()

    return result


def format_hygiene_report(report: dict[str, Any]) -> str:
    """Format hygiene report for display."""
    lines = [f"Knowledge Hygiene Report ({report['entries_scanned']} entries scanned):"]

    if report["noise_demoted"]:
        lines.append(f"  Demoted {report['noise_demoted']} noisy entries to OBSERVATION")
    if report["noise_superseded"]:
        lines.append(f"  Superseded {report['noise_superseded']} pure noise entries")
    if report["stale_decayed"]:
        lines.append(f"  Decayed {report['stale_decayed']} stale entries with temporal markers")
    if report["orphans_flagged"]:
        lines.append(f"  Flagged {report['orphans_flagged']} orphan entries (never accessed)")

    total = (
        report["noise_demoted"]
        + report["noise_superseded"]
        + report["stale_decayed"]
        + report["orphans_flagged"]
    )
    if total == 0:
        lines.append("  Knowledge store is clean. No action needed.")

    if report["details"]:
        lines.append("")
        lines.append("Details:")
        for detail in report["details"][:20]:
            lines.append(f"  {detail}")
        if len(report["details"]) > 20:
            lines.append(f"  ... and {len(report['details']) - 20} more")

    return "\n".join(lines)


# ─── Maturity Lifecycle ─────────────────────────────────────────────────────


_KM_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

# Promotion rules: (from_maturity, min_corroboration, min_confidence) -> to_maturity
# Confidence floors prevent noise-penalized entries from being promoted
# by inflated corroboration counts from the old feedback loop era.
_PROMOTION_RULES: list[tuple[str, int, float, str]] = [
    (
        "RAW",
        MATURITY_RAW_TO_HYPOTHESIS_CORROBORATION,
        MATURITY_RAW_TO_HYPOTHESIS_CONFIDENCE,
        "HYPOTHESIS",
    ),
    (
        "HYPOTHESIS",
        MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION,
        MATURITY_HYPOTHESIS_TO_TESTED_CONFIDENCE,
        "TESTED",
    ),
    (
        "TESTED",
        MATURITY_TESTED_TO_CONFIRMED_CORROBORATION,
        MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE,
        "CONFIRMED",
    ),
]


def check_promotion(entry: dict[str, Any]) -> str | None:
    """Check if an entry qualifies for maturity promotion.

    Returns the new maturity level, or None if no promotion is warranted.
    """
    current = entry.get("maturity", "RAW")
    corroboration = entry.get("corroboration_count", 0)
    confidence = entry.get("confidence", 0.5)

    for from_level, min_corrob, min_conf, to_level in _PROMOTION_RULES:
        if current == from_level and corroboration >= min_corrob and confidence >= min_conf:
            return to_level

    return None


def _passes_validity_gate(knowledge_id: str, current: str, target: str) -> bool:
    """Check if the validity gate allows this promotion.

    Fails gracefully if logic tables aren't initialized yet.
    """
    try:
        return can_promote(knowledge_id, current, target)
    except _KM_ERRORS:
        # Logic tables may not exist yet — allow promotion (backward compat)
        return True


def promote_maturity(knowledge_id: str) -> str | None:
    """Check and apply maturity promotion for a knowledge entry.

    Both corroboration AND validity gates must pass.
    Returns the new maturity level if promoted, None otherwise.
    """
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT maturity, corroboration_count, confidence FROM knowledge WHERE knowledge_id = ? AND superseded_by IS NULL",
            (knowledge_id,),
        ).fetchone()
        if not row:
            return None

        entry = {
            "maturity": row[0],
            "corroboration_count": row[1],
            "confidence": row[2],
        }

        new_maturity = check_promotion(entry)
        if not new_maturity:
            return None

        # Second gate: warrant-based validity
        if not _passes_validity_gate(knowledge_id, entry["maturity"], new_maturity):
            logger.debug(
                "Validity gate blocked promotion of {}: {} -> {}",
                knowledge_id[:12],
                entry["maturity"],
                new_maturity,
            )
            return None

        conn.execute(
            "UPDATE knowledge SET maturity = ?, updated_at = ? WHERE knowledge_id = ?",
            (new_maturity, time.time(), knowledge_id),
        )
        conn.commit()
        logger.info(f"Promoted {knowledge_id[:12]}: {entry['maturity']} -> {new_maturity}")
        return new_maturity
    finally:
        conn.close()


def increment_corroboration(knowledge_id: str) -> int:
    """Increment corroboration count for a knowledge entry.

    Called when knowledge is re-encountered in a new session.
    Returns the new corroboration count.
    """
    conn = get_connection()
    try:
        conn.execute(
            "UPDATE knowledge SET corroboration_count = corroboration_count + 1, updated_at = ? WHERE knowledge_id = ?",
            (time.time(), knowledge_id),
        )
        conn.commit()
        row = conn.execute(
            "SELECT corroboration_count FROM knowledge WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        count = row[0] if row else 0
        logger.debug(f"Corroboration for {knowledge_id[:12]}: {count}")
        return count
    finally:
        conn.close()


def run_maturity_cycle(entries: list[dict[str, Any]]) -> dict[str, int]:
    """Batch check for maturity promotions across entries.

    Both corroboration AND validity gates must pass.
    Returns counts of promotions by type.
    """
    promotions: dict[str, int] = {}
    for entry in entries:
        kid = entry.get("knowledge_id", "")
        if not kid:
            continue
        # Skip already superseded
        if entry.get("superseded_by"):
            continue

        new_maturity = check_promotion(entry)
        if not new_maturity:
            continue

        # Second gate: warrant-based validity
        if not _passes_validity_gate(kid, entry["maturity"], new_maturity):
            logger.debug(
                "Validity gate blocked batch promotion of {}: {} -> {}",
                kid[:12],
                entry["maturity"],
                new_maturity,
            )
            continue

        conn = get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET maturity = ?, updated_at = ? WHERE knowledge_id = ?",
                (new_maturity, time.time(), kid),
            )
            conn.commit()
        finally:
            conn.close()

        promotions[new_maturity] = promotions.get(new_maturity, 0) + 1
        logger.info(f"Batch promoted {kid[:12]}: {entry['maturity']} -> {new_maturity}")

    return promotions
