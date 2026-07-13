"""Lesson deduplication — fuzzy matching to prevent duplicate lesson entries.

The lesson store had 5 groups of exact duplicates and 3 groups of
semantic duplicates (e.g. "retried 2x", "retried 11x", "retried
without investigating" — same failure, different text). The extraction
pipeline's content_hash dedup only catches exact matches.

This module adds fuzzy matching so semantically-equivalent lessons
merge instead of multiplying.

## Algorithm

1. Normalize: lowercase, strip numbers, strip session IDs, collapse
   whitespace.
2. Compute word-level Jaccard similarity between the normalized
   candidate and each existing active/improving lesson.
3. If similarity >= MERGE_THRESHOLD (0.6), return the existing lesson
   for merging instead of creating a new one.

## Why Jaccard and not embeddings

- No external dependencies (no torch, no API calls).
- Fast enough to run in the extraction pipeline hot path.
- The failure mode we're catching (same behavioral pattern, different
  wording) has high word overlap by construction — the agent describes
  the same mistake with mostly the same words each time.
- 0.6 threshold catches "retried 2x" ≈ "retried 11x" (high overlap)
  while separating genuinely different lessons (low overlap).
"""

from __future__ import annotations

import re
from typing import Any

# Similarity threshold for merging. 0.6 = 60% word overlap.
# Tuned empirically against the 5 known duplicate groups:
#   "retried 2x" vs "retried 11x" → ~0.75 (caught)
#   "edited without reading" vs "broke tests" → ~0.15 (not caught)
MERGE_THRESHOLD = 0.6

# Patterns to strip during normalization
_SESSION_ID_RE = re.compile(r"[0-9a-f]{8}(-[0-9a-f]{4}){3}-[0-9a-f]{12}")
_NUMBERS_RE = re.compile(r"\b\d+\w*\b")
_MULTI_SPACE = re.compile(r"\s+")
_PUNCTUATION = re.compile(r"[^\w\s]")


def _normalize(text: str) -> set[str]:
    """Normalize lesson text to a word set for comparison."""
    t = text.lower()
    # Strip session IDs — they make otherwise-identical lessons look different
    t = _SESSION_ID_RE.sub("", t)
    # Strip bare numbers — "2x" vs "11x" shouldn't differentiate
    t = _NUMBERS_RE.sub("", t)
    # Strip punctuation — "errors," and "errors" should match
    t = _PUNCTUATION.sub("", t)
    # Collapse whitespace
    t = _MULTI_SPACE.sub(" ", t).strip()
    # Split into word set, filter short words
    words = {w for w in t.split() if len(w) > 2}
    return words


def _jaccard(a: set[str], b: set[str]) -> float:
    """Jaccard similarity between two word sets."""
    if not a or not b:
        return 0.0
    intersection = len(a & b)
    union = len(a | b)
    return intersection / union if union > 0 else 0.0


def find_duplicate(
    candidate: str,
    existing_lessons: list[dict[str, Any]],
    threshold: float = MERGE_THRESHOLD,
) -> dict[str, Any] | None:
    """Find an existing lesson that is a fuzzy match for the candidate.

    Args:
        candidate: The text of the new lesson being considered.
        existing_lessons: List of lesson dicts with at least 'description'
            and 'lesson_id' keys.
        threshold: Jaccard similarity threshold for merging.

    Returns:
        The best-matching existing lesson dict if similarity >= threshold,
        or None if no match found.
    """
    if not candidate or not existing_lessons:
        return None

    candidate_words = _normalize(candidate)
    if len(candidate_words) < 3:
        # Too short to meaningfully compare
        return None

    best_match = None
    best_score = 0.0

    for lesson in existing_lessons:
        desc = lesson.get("description", "")
        if not desc:
            continue
        lesson_words = _normalize(desc)
        score = _jaccard(candidate_words, lesson_words)
        if score > best_score:
            best_score = score
            best_match = lesson

    if best_score >= threshold and best_match is not None:
        return best_match
    return None
