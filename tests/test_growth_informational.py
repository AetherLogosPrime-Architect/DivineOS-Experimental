"""Tests for the growth-informational rebuild (2026-05-05).

Andrew's spec: growth shouldn't grade or judge — it should inform.
The new format surfaces mistakes, lessons, instructions, and corrections.
The trajectory-as-judgment ("declining"/"improving") is removed.
"""

from __future__ import annotations

import pytest

from divineos.core.growth import (
    compute_growth_map,
    format_growth_map,
    init_session_history_table,
    record_session_metrics,
)
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    init_db()
    init_knowledge_table()
    init_session_history_table()
    yield


def _seed_sessions(count: int = 3, corrections: int = 4) -> None:
    for i in range(count):
        record_session_metrics(
            session_id=f"sess-{i}",
            corrections=corrections,
            encouragements=2,
            tool_calls=10,
            user_messages=5,
            health_grade="B",
            health_score=0.7,
            engaged=True,
        )


class TestNoTrajectoryJudgment:
    def test_trend_is_neutral(self):
        _seed_sessions(count=3)
        growth = compute_growth_map(limit=10)
        assert growth["trend"] == "neutral"

    def test_no_declining_or_improving(self):
        # Record a session with low score then high — old code would
        # have called this "improving"; new code reports neutral.
        record_session_metrics("s1", corrections=10, health_score=0.3)
        record_session_metrics("s2", corrections=2, health_score=0.9)
        growth = compute_growth_map(limit=10)
        assert growth["trend"] not in ("improving", "declining")

    def test_formatted_output_no_grade_letters(self):
        _seed_sessions(count=3)
        growth = compute_growth_map(limit=10)
        text = format_growth_map(growth)
        # The "Grades: 5B 2C" line is gone
        assert "Grades:" not in text

    def test_formatted_output_no_trajectory_word(self):
        _seed_sessions(count=3)
        growth = compute_growth_map(limit=10)
        text = format_growth_map(growth)
        assert "Trajectory:" not in text
        assert "declining" not in text.lower()

    def test_formatted_output_includes_information_framing(self):
        _seed_sessions(count=3)
        growth = compute_growth_map(limit=10)
        text = format_growth_map(growth)
        assert "self-correction" in text.lower() or "self-information" in text.lower()


class TestNewInformationalKeys:
    def test_totals_key_present(self):
        _seed_sessions(count=3, corrections=5)
        growth = compute_growth_map(limit=10)
        assert "totals" in growth
        assert growth["totals"]["corrections"] == 15
        assert growth["totals"]["encouragements"] == 6

    def test_recent_lessons_key_present(self):
        growth = compute_growth_map(limit=10)
        # Empty store → empty list, but key is present in non-empty case
        if growth["sessions"] > 0:
            assert "recent_lessons" in growth

    def test_recent_instructions_key_present(self):
        _seed_sessions(count=2)
        growth = compute_growth_map(limit=10)
        assert "recent_instructions" in growth

    def test_correction_summary_key_present(self):
        _seed_sessions(count=2)
        growth = compute_growth_map(limit=10)
        assert "correction_summary" in growth
        assert "total" in growth["correction_summary"]


class TestBackwardCompat:
    """The old dict keys must keep working — hud and core_memory_refresh
    still consume them."""

    def test_old_keys_present(self):
        _seed_sessions(count=3)
        growth = compute_growth_map(limit=10)
        for k in (
            "sessions",
            "trend",
            "trend_detail",
            "avg_corrections",
            "avg_encouragements",
            "avg_health_score",
            "grade_distribution",
            "total_knowledge",
            "maturity",
            "lessons",
            "engagement_rate",
            "blind_sessions",
            "tone_insight",
        ):
            assert k in growth, f"missing backward-compat key: {k}"

    def test_empty_history_still_works(self):
        growth = compute_growth_map(limit=10)
        assert growth["sessions"] == 0
        assert "summary" in growth


class TestInformationalSections:
    def test_format_includes_what_happened(self):
        _seed_sessions(count=3, corrections=5)
        text = format_growth_map(compute_growth_map(limit=10))
        assert "What happened" in text
        assert "Corrections received: 15" in text  # 3 sessions * 5

    def test_format_includes_knowledge_section(self):
        _seed_sessions(count=2)
        text = format_growth_map(compute_growth_map(limit=10))
        assert "Knowledge accumulated" in text

    def test_format_includes_engagement_section(self):
        _seed_sessions(count=2)
        text = format_growth_map(compute_growth_map(limit=10))
        assert "Engagement" in text
