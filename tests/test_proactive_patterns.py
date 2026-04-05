"""Tests for proactive pattern detection — prescriptive recommendations."""

import pytest

from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.proactive_patterns import (
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


class TestFullContextAdvice:
    """Combined warnings + recommendations."""

    def test_returns_string(self):
        result = get_full_context_advice("refactoring CLI commands")
        assert isinstance(result, str)

    def test_empty_for_empty_context(self):
        result = get_full_context_advice("")
        assert result == ""
