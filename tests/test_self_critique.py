"""Tests for self-critique — craft quality assessment."""

import json

import pytest

from divineos.core.knowledge import _get_connection
from divineos.core.self_critique import (
    CRAFT_SPECTRUMS,
    CraftAssessment,
    assess_session_craft,
    format_craft_assessment,
    format_craft_trends,
    get_craft_trends,
    get_recent_assessments,
    init_critique_table,
)


@pytest.fixture(autouse=True)
def _setup():
    init_critique_table()


class TestAssessSessionCraft:
    """Session craft assessment."""

    def test_returns_assessment(self):
        result = assess_session_craft("test-session-1")
        assert isinstance(result, CraftAssessment)
        assert result.assessment_id.startswith("ca-")

    def test_all_spectrums_scored(self):
        result = assess_session_craft("test-session-2")
        for spectrum in CRAFT_SPECTRUMS:
            assert spectrum in result.scores

    def test_scores_in_range(self):
        result = assess_session_craft("test-session-3")
        for spectrum, score in result.scores.items():
            assert -1.0 <= score <= 1.0, f"{spectrum} score {score} out of range"

    def test_overall_computed(self):
        result = assess_session_craft("test-session-4")
        assert isinstance(result.overall, float)

    def test_stored_in_db(self):
        result = assess_session_craft("test-session-5")
        assessments = get_recent_assessments()
        ids = [a["assessment_id"] for a in assessments]
        assert result.assessment_id in ids

    def test_session_id_stored(self):
        assess_session_craft("unique-session-id")
        assessments = get_recent_assessments()
        sessions = [a["session_id"] for a in assessments]
        assert "unique-session-id" in sessions


class TestCraftTrends:
    """Trend computation."""

    def test_no_trends_with_one_assessment(self):
        assess_session_craft("trend-1")
        trends = get_craft_trends()
        assert trends == []

    def test_trends_with_multiple_assessments(self):
        # Insert multiple assessments directly for control
        conn = _get_connection()
        try:
            import time
            import uuid

            for i in range(5):
                scores = {s: 0.1 * (i + 1) for s in CRAFT_SPECTRUMS}
                conn.execute(
                    "INSERT INTO craft_assessments "
                    "(assessment_id, session_id, scores, overall, notes, assessed_at) "
                    "VALUES (?, ?, ?, ?, '[]', ?)",
                    (
                        f"ca-trend-{uuid.uuid4().hex[:8]}",
                        f"trend-sess-{i}",
                        json.dumps(scores),
                        sum(scores.values()) / len(scores),
                        time.time() - (5 - i) * 3600,
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        trends = get_craft_trends(n=5)
        assert len(trends) > 0
        for trend in trends:
            assert trend.spectrum in CRAFT_SPECTRUMS
            assert trend.direction in ("improving", "declining", "stable")

    def test_trend_detects_direction(self):
        conn = _get_connection()
        try:
            import time
            import uuid

            # Clear previous test data for isolation
            conn.execute("DELETE FROM craft_assessments")
            conn.commit()

            # Create declining pattern: most recent (highest assessed_at) has lowest score
            # i=0 oldest (+0.5), i=1 (+0.2), i=2 (-0.1), i=3 newest (-0.4)
            for i in range(4):
                score_val = 0.5 - (i * 0.3)
                scores = {s: score_val for s in CRAFT_SPECTRUMS}
                conn.execute(
                    "INSERT INTO craft_assessments "
                    "(assessment_id, session_id, scores, overall, notes, assessed_at) "
                    "VALUES (?, ?, ?, ?, '[]', ?)",
                    (
                        f"ca-dir-{uuid.uuid4().hex[:8]}",
                        f"dir-sess-{i}",
                        json.dumps(scores),
                        score_val,
                        time.time() + (i * 100),  # newer = higher timestamp
                    ),
                )
            conn.commit()
        finally:
            conn.close()

        trends = get_craft_trends(n=4)
        # Most recent have lower scores → declining
        assert any(t.direction == "declining" for t in trends)


class TestCraftSpectrums:
    """Spectrum definitions."""

    def test_all_spectrums_have_descriptions(self):
        for name, spec in CRAFT_SPECTRUMS.items():
            assert "description" in spec
            assert "negative" in spec
            assert "positive" in spec

    def test_five_spectrums(self):
        assert len(CRAFT_SPECTRUMS) == 5


class TestFormat:
    """Formatting."""

    def test_format_assessment(self):
        result = assess_session_craft("fmt-session")
        text = format_craft_assessment(result)
        assert "Craft Self-Assessment" in text
        assert "Overall" in text
        assert "elegance" in text

    def test_format_trends_not_enough(self):
        text = format_craft_trends([])
        assert "Not enough" in text

    def test_score_bar_visual(self):
        from divineos.core.self_critique import _score_bar

        bar_high = _score_bar(0.8)
        bar_low = _score_bar(-0.8)
        assert bar_high.count("▓") > bar_low.count("▓")

    def test_score_bar_extremes(self):
        from divineos.core.self_critique import _score_bar

        assert len(_score_bar(1.0)) == 10
        assert len(_score_bar(-1.0)) == 10
        assert _score_bar(1.0) == "▓" * 10
        assert _score_bar(-1.0) == "░" * 10
