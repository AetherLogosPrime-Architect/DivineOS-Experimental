"""Tests for proactive pattern detection — prescriptive recommendations."""

import pytest

from divineos.core.knowledge import init_knowledge_table
from divineos.core.proactive_patterns import (
    _is_recommendation_noise,
    format_recommendations,
    get_full_context_advice,
    recommend,
)


@pytest.fixture(autouse=True)
def _setup():
    init_knowledge_table()


class TestRecommend:
    """Recommendation engine."""

    def test_empty_context_returns_empty(self):
        recs = recommend("")
        assert recs == []

    def test_whitespace_context_returns_empty(self):
        recs = recommend("   ")
        assert recs == []

    def test_returns_list(self):
        recs = recommend("error handling in CLI commands")
        assert isinstance(recs, list)

    def test_recommendations_have_required_fields(self):
        recs = recommend("knowledge store database sqlite")
        for r in recs:
            assert "text" in r
            assert "relevance" in r
            assert "source" in r
            assert "type" in r
            assert "reason" in r

    def test_max_recommendations_respected(self):
        recs = recommend("testing code quality", max_recommendations=2)
        assert len(recs) <= 2

    def test_relevance_in_range(self):
        recs = recommend("append only ledger integrity")
        for r in recs:
            assert 0.0 <= r["relevance"] <= 1.0

    def test_sorted_by_relevance(self):
        recs = recommend("memory knowledge store")
        if len(recs) >= 2:
            for i in range(len(recs) - 1):
                assert recs[i]["relevance"] >= recs[i + 1]["relevance"]


class TestFormat:
    """Formatting."""

    def test_format_empty(self):
        result = format_recommendations([])
        assert result == ""

    def test_format_with_recs(self):
        recs = [
            {
                "text": "Use context managers for cleanup",
                "relevance": 0.8,
                "source": "knowledge",
                "type": "PRINCIPLE",
                "id": "k-123",
                "confidence": 0.9,
                "reason": "content match",
            }
        ]
        result = format_recommendations(recs)
        assert "Relevant patterns" in result
        assert "context managers" in result
        assert "★" in result  # high confidence marker


class TestRecommendationNoiseFilter:
    """Noise entries should never become TRY recommendations."""

    def test_yes_opener_is_noise(self):
        assert _is_recommendation_noise("Yes so we need a science engine", "PRINCIPLE")

    def test_ok_opener_is_noise(self):
        assert _is_recommendation_noise("Ok heres the new audit", "DIRECTION")

    def test_wonderful_opener_is_noise(self):
        assert _is_recommendation_noise("Wonderful here is the next reply", "PRINCIPLE")

    def test_here_is_opener_is_noise(self):
        assert _is_recommendation_noise("Here is a fresh audit", "DIRECTION")

    def test_absolutely_opener_is_noise(self):
        assert _is_recommendation_noise("Absolutely thats the whole point", "PRINCIPLE")

    def test_well_opener_is_noise(self):
        assert _is_recommendation_noise("Well yes I am built for efficiency", "DIRECTION")

    def test_real_principle_not_noise(self):
        assert not _is_recommendation_noise("Maturity must flow both directions.", "PRINCIPLE")

    def test_real_procedure_not_noise(self):
        assert not _is_recommendation_noise("Always run tests after code changes.", "PROCEDURE")

    def test_directive_not_noise(self):
        assert not _is_recommendation_noise(
            "[no-theater] Every line of code does something real.", "DIRECTIVE"
        )

    def test_case_insensitive(self):
        assert _is_recommendation_noise("YES this is great", "PRINCIPLE")
        assert _is_recommendation_noise("ok lets do it", "DIRECTION")


class TestFullContextAdvice:
    """Combined warnings + recommendations."""

    def test_returns_string(self):
        result = get_full_context_advice("refactoring CLI commands")
        assert isinstance(result, str)

    def test_empty_for_empty_context(self):
        result = get_full_context_advice("")
        assert result == ""
