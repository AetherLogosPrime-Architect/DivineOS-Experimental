"""Tests for the semantic-overlap surface added to `divineos claim`.

Built 2026-06-11 alongside find_similar_in_corpus. Parallel pattern to
the learn-dedup surface but for the claims engine: when a new claim is
filed whose statement is semantically close to an existing active claim,
surface the close matches informationally before filing fresh.

Uses on-the-fly encoding (find_similar_in_corpus) rather than a stored
embedding column — the claims table is small enough not to justify the
schema migration yet.
"""

from __future__ import annotations

import pytest


def _semantic_available() -> bool:
    try:
        from divineos.core.semantic_store import embed

        return embed("test sentence to confirm model loads") is not None
    except Exception:
        return False


_skip_no_semantic = pytest.mark.skipif(
    not _semantic_available(),
    reason="semantic-similarity primitive unavailable (ml extras missing)",
)


@_skip_no_semantic
@pytest.mark.timeout(180)
class TestFindSimilarInCorpus:
    """The new generic helper that encodes both query and candidates
    on the fly. Used by the claim CLI; could be reused by other tables
    without stored embeddings."""

    def test_returns_close_match_above_threshold(self):
        from divineos.core.semantic_store import find_similar_in_corpus

        candidates = [
            ("c1", "The cat sat on the mat"),
            ("c2", "Apricot jam tastes wonderful on rye toast"),
            ("c3", "I refactored the verify-claim detector to add source-letter trace"),
        ]
        results = find_similar_in_corpus(
            "Updated the unverified-claim detector to track source letters",
            candidates,
            top_k=5,
            min_similarity=0.3,
        )
        # c3 should appear as the closest match.
        assert results
        assert results[0][0] == "c3"

    def test_empty_candidates_returns_empty(self):
        from divineos.core.semantic_store import find_similar_in_corpus

        assert find_similar_in_corpus("anything", []) == []

    def test_empty_query_returns_empty(self):
        from divineos.core.semantic_store import find_similar_in_corpus

        assert find_similar_in_corpus("", [("c1", "something")]) == []

    def test_respects_min_similarity(self):
        from divineos.core.semantic_store import find_similar_in_corpus

        candidates = [("c1", "the cat sat on the mat")]
        results = find_similar_in_corpus(
            "quantum chromodynamics asymptotic freedom of quarks",
            candidates,
            min_similarity=0.5,
        )
        assert results == []

    def test_caps_results_at_top_k(self):
        from divineos.core.semantic_store import find_similar_in_corpus

        # Many candidates all close in meaning
        base = "I refactored the verify-claim detector"
        candidates = [(f"c{i}", base + f" attempt {i}") for i in range(10)]
        results = find_similar_in_corpus(base, candidates, top_k=3, min_similarity=0.3)
        assert len(results) <= 3

    def test_skips_candidates_with_empty_content(self):
        from divineos.core.semantic_store import find_similar_in_corpus

        candidates = [
            ("c1", ""),  # empty
            ("c2", None),  # None
            ("c3", "the cat sat on the mat"),
        ]
        results = find_similar_in_corpus("the cat sat on the mat", candidates, min_similarity=0.5)
        # Only c3 should be in results — c1 and c2 are filtered.
        assert results
        assert all(r[0] == "c3" for r in results)
