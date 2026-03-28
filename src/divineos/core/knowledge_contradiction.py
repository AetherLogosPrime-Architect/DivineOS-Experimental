"""Knowledge Contradiction Detection — finds and resolves conflicting knowledge.

When new knowledge is stored, this module scans existing same-type entries
for contradictions. A contradiction is detected when two entries share high
word overlap but contain negation markers suggesting opposite claims.

Types:
- TEMPORAL: old fact superseded by new reality ("was broken" → "was fixed")
- DIRECT: same topic, opposite claim
- SUPERSESSION: evolved version of the same information
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Any

from loguru import logger


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

_STOPWORDS = {
    "the",
    "a",
    "an",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "have",
    "has",
    "had",
    "do",
    "does",
    "did",
    "will",
    "would",
    "could",
    "should",
    "may",
    "might",
    "shall",
    "can",
    "to",
    "of",
    "in",
    "for",
    "on",
    "with",
    "at",
    "by",
    "from",
    "as",
    "into",
    "through",
    "during",
    "it",
    "its",
    "this",
    "that",
    "and",
    "but",
    "or",
    "if",
    "then",
    "so",
    "i",
    "my",
    "me",
}


def _normalize(text: str) -> str:
    """Lowercase and strip punctuation for comparison."""
    return re.sub(r"[^\w\s]", " ", text.lower())


def _stem(word: str) -> str:
    """Minimal suffix stripping so 'sessions'/'session' and 'checked'/'checks' match."""
    # Order matters — strip longest suffixes first
    for suffix in (
        "ation",
        "ting",
        "ing",
        "ness",
        "ment",
        "ble",
        "ous",
        "ive",
        "ful",
        "ied",
        "ies",
        "ed",
        "ly",
        "er",
        "es",
        "s",
    ):
        if len(word) > len(suffix) + 2 and word.endswith(suffix):
            return word[: -len(suffix)]
    return word


def _word_set(text: str) -> set[str]:
    """Extract meaningful stemmed words from text."""
    return {_stem(w) for w in _normalize(text).split()} - _STOPWORDS


def _compute_overlap(words_a: set[str], words_b: set[str]) -> float:
    """Word set overlap ratio (0.0-1.0)."""
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    smaller = min(len(words_a), len(words_b))
    return len(intersection) / smaller


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
    if overlap >= 0.5:
        # Temporal: one references past state, other references current
        if new_temporal or existing_temporal:
            return "TEMPORAL"

        # Direct: same topic but opposing claims (one negated, other not)
        if new_has_negation != existing_has_negation:
            return "DIRECT"

        # Very high overlap = likely supersession (updated version)
        if overlap >= 0.8:
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
    new_words = _word_set(new_content)

    for entry in existing_entries:
        # Only compare same-type entries
        if entry.get("knowledge_type") != new_type:
            continue

        # Skip superseded entries
        if entry.get("superseded_by"):
            continue

        existing_words = _word_set(entry.get("content", ""))
        overlap = _compute_overlap(new_words, existing_words)

        if overlap < 0.4:
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
    from divineos.core.knowledge import _get_connection

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
    from divineos.core.knowledge import supersede_knowledge

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
        from divineos.core.knowledge import _get_connection

        conn = _get_connection()
        try:
            conn.execute(
                "UPDATE knowledge SET confidence = MAX(0.3, confidence - 0.15), updated_at = ? WHERE knowledge_id = ?",
                (time.time(), match.existing_id),
            )
            conn.commit()
        finally:
            conn.close()
        logger.info(
            f"Resolved DIRECT contradiction: lowered confidence on {match.existing_id[:12]}"
        )
