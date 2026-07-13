"""Tests for lesson fuzzy deduplication."""

from divineos.core.lesson_dedup import _jaccard, _normalize, find_duplicate


class TestNormalize:
    def test_strips_numbers(self):
        words = _normalize("I retried a failed action 11x without investigating")
        assert "11x" not in words  # number stripped, 'x' too short

    def test_strips_session_ids(self):
        words = _normalize("session 4517c734-1fe1-4ad0-b0e0-4e4e4300953b failed")
        # UUID should be stripped
        assert "4517c734-1fe1-4ad0-b0e0-4e4e4300953b" not in " ".join(words)

    def test_lowercase(self):
        words = _normalize("RETRIED Failed ACTION")
        assert "retried" in words
        assert "failed" in words

    def test_filters_short_words(self):
        words = _normalize("I am a bad AI")
        # 'I', 'am', 'a' are <= 2 chars, filtered
        assert "bad" in words


class TestJaccard:
    def test_identical_sets(self):
        assert _jaccard({"a", "b", "c"}, {"a", "b", "c"}) == 1.0

    def test_disjoint_sets(self):
        assert _jaccard({"a", "b"}, {"c", "d"}) == 0.0

    def test_partial_overlap(self):
        # {a,b,c} & {b,c,d} = {b,c}, union = {a,b,c,d}
        assert _jaccard({"a", "b", "c"}, {"b", "c", "d"}) == 0.5

    def test_empty_set(self):
        assert _jaccard(set(), {"a"}) == 0.0


class TestFindDuplicate:
    def test_catches_retry_variants(self):
        """The core use case: 'retried 2x' and 'retried 11x' are the same lesson."""
        existing = [
            {
                "lesson_id": "abc",
                "description": "I retried a failed action without investigating the cause. Investigate errors, dont blindly retry.",
            },
        ]
        candidate = "I retried a failed action 2x without investigating the cause. I need to investigate errors, not blindly retry"
        match = find_duplicate(candidate, existing)
        assert match is not None
        assert match["lesson_id"] == "abc"

    def test_different_lessons_not_matched(self):
        """Genuinely different lessons should not match."""
        existing = [
            {
                "lesson_id": "abc",
                "description": "I retried a failed action without investigating the cause.",
            },
        ]
        candidate = "I edited files without reading them first. I must read before I edit."
        match = find_duplicate(candidate, existing)
        assert match is None

    def test_empty_existing(self):
        match = find_duplicate("some lesson", [])
        assert match is None

    def test_short_candidate_skipped(self):
        """Very short candidates can't meaningfully compare."""
        existing = [{"lesson_id": "abc", "description": "I retried without investigating."}]
        match = find_duplicate("bad", existing)
        assert match is None

    def test_best_match_returned(self):
        """When multiple lessons match, the best one is returned."""
        existing = [
            {
                "lesson_id": "low",
                "description": "I upset the user by acting without pausing to understand the situation.",
            },
            {
                "lesson_id": "high",
                "description": "I retried a failed action without investigating the cause. Investigate errors, dont blindly retry.",
            },
        ]
        candidate = "I retried a failed action without investigating the cause. I need to investigate errors, not blindly retry."
        match = find_duplicate(candidate, existing)
        assert match is not None
        assert match["lesson_id"] == "high"
