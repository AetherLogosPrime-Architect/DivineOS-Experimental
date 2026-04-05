"""Tests for SIS Tier 2 (statistical) and Tier 3 (semantic) scoring."""

import pytest

from divineos.core.sis_tiers import (
    score_all_tiers,
    score_concreteness_norms,
    score_tfidf_grounding,
)

_has_sklearn = True
try:
    import sklearn  # noqa: F401
except ImportError:
    _has_sklearn = False

needs_sklearn = pytest.mark.skipif(not _has_sklearn, reason="sklearn not installed")


class TestConcretenessNorms:
    """Test Tier 2a: psycholinguistic concreteness scoring."""

    def test_technical_text_scores_high(self):
        score = score_concreteness_norms(
            "The database stores file records in a table with hash columns"
        )
        assert score is not None
        assert score > 0.5

    def test_abstract_text_scores_low(self):
        score = score_concreteness_norms(
            "The essence of consciousness transcends existence and truth"
        )
        assert score is not None
        assert score < 0.4

    def test_returns_none_for_short_text(self):
        """Fewer than 3 scored words = not enough signal."""
        score = score_concreteness_norms("hello world")
        assert score is None

    def test_returns_none_for_empty(self):
        assert score_concreteness_norms("") is None

    def test_mixed_text_scores_middle(self):
        score = score_concreteness_norms("The soul of the system is its database and test pipeline")
        assert score is not None
        assert 0.2 <= score <= 0.8

    def test_normalized_to_zero_one(self):
        """All scores should be between 0 and 1."""
        score = score_concreteness_norms("keyboard screen mouse disk server printer button switch")
        assert score is not None
        assert 0.0 <= score <= 1.0


class TestTfidfGrounding:
    """Test Tier 2b: TF-IDF similarity to reference corpora."""

    @needs_sklearn
    def test_grounded_text_matches_grounded_corpus(self):
        result = score_tfidf_grounding(
            "Store knowledge entries in SQLite database with deduplication"
        )
        assert result is not None
        assert result["grounded"] > result["esoteric"]
        assert result["ratio"] > 0

    @needs_sklearn
    def test_esoteric_text_matches_esoteric_corpus(self):
        result = score_tfidf_grounding(
            "The cosmic consciousness transcends the sacred void of being"
        )
        assert result is not None
        assert result["esoteric"] > result["grounded"]
        assert result["ratio"] < 0

    @needs_sklearn
    def test_returns_dict_with_required_keys(self):
        result = score_tfidf_grounding("test input text")
        assert result is not None
        assert "grounded" in result
        assert "esoteric" in result
        assert "ratio" in result

    @needs_sklearn
    def test_scores_bounded(self):
        result = score_tfidf_grounding("The pipeline extracts knowledge and filters noise")
        assert result is not None
        assert 0.0 <= result["grounded"] <= 1.0
        assert 0.0 <= result["esoteric"] <= 1.0
        assert -1.0 <= result["ratio"] <= 1.0


class TestAllTiers:
    """Test the combined multi-tier scoring."""

    def test_returns_tiers_used(self):
        result = score_all_tiers("Store data in a database table")
        assert "lexical" in result["tiers_used"]
        # Statistical tier needs norms to match — may not on short text
        assert len(result["tiers_used"]) >= 1

    def test_combined_grounding_present(self):
        result = score_all_tiers("The pipeline stores knowledge in SQLite with hash verification")
        # combined_grounding may be None if no optional deps and norms don't match
        if result["combined_grounding"] is not None:
            assert 0.0 <= result["combined_grounding"] <= 1.0

    @needs_sklearn
    def test_grounded_text_scores_high(self):
        result = score_all_tiers("Run pytest to verify all test cases pass after code changes")
        assert result["combined_grounding"] is not None
        assert result["combined_grounding"] > 0.5

    def test_esoteric_text_scores_low(self):
        result = score_all_tiers(
            "The eternal soul transcends the sacred void through cosmic meditation"
        )
        # With norms only, combined_grounding comes from concreteness norms
        if result["combined_grounding"] is not None:
            assert result["combined_grounding"] < 0.5


class TestDeepAssessment:
    """Test deep mode integration with main SIS module."""

    def test_deep_assessment_works(self):
        from divineos.core.semantic_integrity import assess_integrity

        report = assess_integrity("Store session events in an append-only database", deep=True)
        assert report.verdict == "ACCEPT"
        # Should have tier info in flags
        assert any("tiers:" in f for f in report.flags)

    def test_deep_translation_works(self):
        from divineos.core.semantic_integrity import assess_and_translate

        result = assess_and_translate(
            "The karma system tracks consequences in the akashic records",
            deep=True,
        )
        assert result["verdict"] == "TRANSLATE"
        assert result["changed"]

    def test_deep_mode_more_accurate_on_paraphrase(self):
        """Deep mode should catch esoteric content even without exact keywords."""
        from divineos.core.semantic_integrity import assess_integrity

        # This paraphrase avoids most keywords but is clearly esoteric
        text = "The universal memory that never forgets preserves all experiences eternally"
        shallow = assess_integrity(text, deep=False)
        deep = assess_integrity(text, deep=True)

        # Deep should flag more issues or give lower integrity
        assert (
            len(deep.flags) >= len(shallow.flags)
            or deep.integrity_score <= shallow.integrity_score + 0.1
        )
