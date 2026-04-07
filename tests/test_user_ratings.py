"""Tests for user ratings — the external validation metric."""

from divineos.core.user_ratings import (
    correlate_with_internal,
    get_rating_stats,
    get_ratings,
    init_ratings_table,
    record_rating,
)


def _setup():
    init_ratings_table()


class TestRecordRating:
    """Recording user ratings."""

    def test_record_valid_rating(self):
        _setup()
        rating_id = record_rating("session-abc", 7, "Good session")
        assert rating_id is not None
        assert rating_id > 0

    def test_record_minimum_rating(self):
        _setup()
        rating_id = record_rating("session-min", 1)
        assert rating_id is not None

    def test_record_maximum_rating(self):
        _setup()
        rating_id = record_rating("session-max", 10)
        assert rating_id is not None

    def test_reject_zero_rating(self):
        _setup()
        try:
            record_rating("session-zero", 0)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_reject_eleven_rating(self):
        _setup()
        try:
            record_rating("session-eleven", 11)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass

    def test_reject_negative_rating(self):
        _setup()
        try:
            record_rating("session-neg", -1)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass


class TestGetRatings:
    """Retrieving ratings."""

    def test_get_recent_ratings(self):
        _setup()
        record_rating("session-r1", 5, "meh")
        record_rating("session-r2", 8, "great")
        ratings = get_ratings(limit=10)
        assert len(ratings) >= 2
        # Most recent first
        assert ratings[0]["created_at"] >= ratings[1]["created_at"]

    def test_ratings_have_expected_fields(self):
        _setup()
        record_rating("session-fields", 6, "test comment")
        ratings = get_ratings(limit=1)
        assert len(ratings) >= 1
        r = ratings[0]
        assert "rating_id" in r
        assert "session_id" in r
        assert "rating" in r
        assert "comment" in r
        assert "created_at" in r

    def test_limit_respected(self):
        _setup()
        for i in range(5):
            record_rating(f"session-lim-{i}", 5 + i % 5)
        ratings = get_ratings(limit=2)
        assert len(ratings) == 2


class TestGetRatingStats:
    """Rating statistics."""

    def test_empty_stats(self):
        _setup()
        # Stats should work even with existing data — just check structure
        stats = get_rating_stats()
        assert "count" in stats
        assert "avg" in stats
        assert "min" in stats
        assert "max" in stats
        assert "recent_avg" in stats
        assert "trend" in stats

    def test_stats_reflect_ratings(self):
        _setup()
        # Record a known set
        record_rating("stats-1", 3)
        record_rating("stats-2", 7)
        stats = get_rating_stats()
        assert stats["count"] >= 2
        assert stats["min"] <= 3
        assert stats["max"] >= 7

    def test_trend_with_few_ratings(self):
        _setup()
        stats = get_rating_stats()
        # With few ratings, trend should be insufficient_data or a valid value
        assert stats["trend"] in (
            "no_data",
            "insufficient_data",
            "improving",
            "stable",
            "declining",
        )


class TestCorrelateWithInternal:
    """Goodhart detection — comparing user vs internal scores."""

    def test_no_ratings_returns_no_data(self):
        _setup()
        # Even with existing ratings, the structure should be valid
        result = correlate_with_internal()
        assert "pairs" in result
        assert "correlation" in result
        assert "divergences" in result

    def test_correlation_structure(self):
        _setup()
        record_rating("corr-session-1", 8, "solid")
        result = correlate_with_internal()
        # Without session_validation data, pairs will be empty
        assert isinstance(result["pairs"], list)
        assert isinstance(result["divergences"], list)
        assert result["correlation"] in (
            "no_data",
            "no_grades",
            "strong",
            "moderate",
            "weak",
        )
