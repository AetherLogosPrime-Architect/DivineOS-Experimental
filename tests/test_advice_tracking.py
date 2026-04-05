"""Tests for advice tracking — long-term feedback loops."""

import pytest

from divineos.core.advice_tracking import (
    assess_advice,
    format_advice_stats,
    get_advice_stats,
    get_pending_advice,
    get_stale_advice,
    init_advice_table,
    record_advice,
)


@pytest.fixture(autouse=True)
def _setup():
    init_advice_table()


class TestRecordAdvice:
    """Recording advice."""

    def test_record_returns_id(self):
        aid = record_advice("Use two-tier error handling")
        assert aid.startswith("adv-")

    def test_default_outcome_is_pending(self):
        record_advice("Use small PRs")
        pending = get_pending_advice()
        assert len(pending) >= 1
        assert pending[0]["outcome"] == "pending"

    def test_category_stored(self):
        record_advice("Extract after 3 copies", category="architecture")
        pending = get_pending_advice()
        matched = [p for p in pending if p["category"] == "architecture"]
        assert len(matched) >= 1

    def test_context_stored(self):
        record_advice(
            "Use context managers",
            context="CLI refactoring for error handling",
        )
        pending = get_pending_advice()
        matched = [p for p in pending if "CLI refactoring" in p["context"]]
        assert len(matched) >= 1

    def test_confidence_stored(self):
        record_advice("Speculative advice", confidence=0.4)
        pending = get_pending_advice()
        matched = [p for p in pending if p["confidence_at_time"] == 0.4]
        assert len(matched) >= 1


class TestAssessAdvice:
    """Assessing advice outcomes."""

    def test_assess_successful(self):
        aid = record_advice("Try incremental refactoring")
        result = assess_advice(aid, "successful", "Reduced rework by 50%")
        assert result is True
        # Should no longer be pending
        pending = get_pending_advice()
        pending_ids = [p["advice_id"] for p in pending]
        assert aid not in pending_ids

    def test_assess_failed(self):
        aid = record_advice("Try big-bang rewrite")
        result = assess_advice(aid, "failed", "Too many bugs introduced")
        assert result is True

    def test_assess_nonexistent_returns_false(self):
        result = assess_advice("adv-doesnotexist", "successful")
        assert result is False

    def test_assess_invalid_outcome_returns_false(self):
        aid = record_advice("Some advice")
        result = assess_advice(aid, "invalid_state")
        assert result is False

    def test_assessed_at_timestamp_set(self):
        aid = record_advice("Time-tested advice")
        assess_advice(aid, "successful", "It worked")
        stats = get_advice_stats()
        assert stats["assessed"] >= 1


class TestAdviceStats:
    """Aggregate statistics."""

    def test_empty_stats(self):
        stats = get_advice_stats()
        assert stats["total"] >= 0

    def test_success_rate_calculation(self):
        a1 = record_advice("Good advice 1")
        a2 = record_advice("Good advice 2")
        a3 = record_advice("Bad advice")
        assess_advice(a1, "successful")
        assess_advice(a2, "successful")
        assess_advice(a3, "failed")
        stats = get_advice_stats()
        # 2 out of 3 assessed = 66.7%
        assert stats["success_rate"] == pytest.approx(0.667, abs=0.01)

    def test_partial_success_counts_half(self):
        a1 = record_advice("Partial advice")
        assess_advice(a1, "partially_successful")
        stats = get_advice_stats()
        assert stats["success_rate"] == 0.5

    def test_category_breakdown(self):
        a1 = record_advice("Arch advice", category="architecture")
        a2 = record_advice("Debug advice", category="debugging")
        assess_advice(a1, "successful")
        assess_advice(a2, "failed")
        stats = get_advice_stats()
        assert "architecture" in stats["by_category"]
        assert "debugging" in stats["by_category"]


class TestStaleAdvice:
    """Stale advice detection."""

    def test_recent_advice_not_stale(self):
        record_advice("Fresh advice")
        stale = get_stale_advice(days=7)
        # Should not include advice just created
        assert all(s["content"] != "Fresh advice" for s in stale)

    def test_stale_returns_list(self):
        stale = get_stale_advice()
        assert isinstance(stale, list)


class TestFormat:
    """Formatting."""

    def test_format_empty(self):
        result = format_advice_stats({"total": 0})
        assert "No advice tracked" in result

    def test_format_with_data(self):
        a1 = record_advice("Format test advice")
        assess_advice(a1, "successful")
        stats = get_advice_stats()
        result = format_advice_stats(stats)
        assert "Success rate" in result
        assert "%" in result
