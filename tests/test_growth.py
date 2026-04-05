"""Tests for the growth awareness system."""

from divineos.core.growth import (
    compute_growth_map,
    format_growth_map,
    get_session_history,
    init_session_history_table,
    record_session_metrics,
)
from divineos.core.knowledge._base import init_knowledge_table


def _setup():
    init_knowledge_table()
    init_session_history_table()


class TestSessionHistory:
    def test_record_and_retrieve(self):
        _setup()
        record_session_metrics(
            session_id="test-session-1",
            corrections=2,
            encouragements=3,
            tool_calls=50,
            user_messages=10,
            knowledge_stored=5,
            health_grade="B",
            health_score=0.75,
            engaged=True,
        )
        history = get_session_history()
        assert len(history) == 1
        assert history[0]["session_id"] == "test-session-1"
        assert history[0]["corrections"] == 2
        assert history[0]["encouragements"] == 3
        assert history[0]["health_grade"] == "B"
        assert history[0]["engaged"] == 1

    def test_multiple_sessions_ordered(self):
        _setup()
        record_session_metrics(session_id="s1", corrections=1, health_score=0.5)
        record_session_metrics(session_id="s2", corrections=0, health_score=0.9)
        history = get_session_history()
        assert len(history) == 2
        # Newest first
        assert history[0]["session_id"] == "s2"

    def test_empty_history(self):
        _setup()
        assert get_session_history() == []

    def test_upsert_same_session(self):
        _setup()
        record_session_metrics(session_id="s1", corrections=1)
        record_session_metrics(session_id="s1", corrections=5)
        history = get_session_history()
        assert len(history) == 1
        assert history[0]["corrections"] == 5


class TestGrowthMap:
    def test_no_sessions(self):
        _setup()
        growth = compute_growth_map()
        assert growth["sessions"] == 0

    def test_single_session(self):
        _setup()
        record_session_metrics(
            session_id="s1",
            corrections=1,
            encouragements=2,
            health_grade="B",
            health_score=0.75,
            engaged=True,
        )
        growth = compute_growth_map()
        assert growth["sessions"] == 1
        assert growth["avg_corrections"] == 1.0
        assert growth["engagement_rate"] == 1.0

    def test_improving_trend(self):
        _setup()
        # Older sessions: more corrections, lower scores
        for i in range(3):
            record_session_metrics(
                session_id=f"old-{i}",
                corrections=4,
                health_score=0.4,
                health_grade="D",
            )
        # Newer sessions: fewer corrections, higher scores
        for i in range(3):
            record_session_metrics(
                session_id=f"new-{i}",
                corrections=0,
                health_score=0.9,
                health_grade="A",
            )

        growth = compute_growth_map()
        assert growth["sessions"] == 6
        assert growth["trend"] == "improving"

    def test_grade_distribution(self):
        _setup()
        record_session_metrics(session_id="s1", health_grade="A", health_score=0.9)
        record_session_metrics(session_id="s2", health_grade="A", health_score=0.85)
        record_session_metrics(session_id="s3", health_grade="B", health_score=0.75)

        growth = compute_growth_map()
        assert growth["grade_distribution"]["A"] == 2
        assert growth["grade_distribution"]["B"] == 1

    def test_engagement_tracking(self):
        _setup()
        record_session_metrics(session_id="s1", engaged=True)
        record_session_metrics(session_id="s2", engaged=False)
        record_session_metrics(session_id="s3", engaged=True)
        record_session_metrics(session_id="s4", engaged=False)

        growth = compute_growth_map()
        assert growth["engagement_rate"] == 0.5
        assert growth["blind_sessions"] == 2


class TestFormatGrowthMap:
    def test_empty(self):
        result = format_growth_map({"sessions": 0, "summary": "No data."})
        assert "No data" in result

    def test_formats_full_map(self):
        _setup()
        for i in range(5):
            record_session_metrics(
                session_id=f"s{i}",
                corrections=1,
                encouragements=2,
                health_grade="B",
                health_score=0.75,
                engaged=True,
            )
        growth = compute_growth_map()
        text = format_growth_map(growth)
        assert "Growth Map" in text
        assert "Trajectory" in text
        assert "Health" in text
        assert "Knowledge" in text
        assert "Lessons" in text
        assert "Engagement" in text
