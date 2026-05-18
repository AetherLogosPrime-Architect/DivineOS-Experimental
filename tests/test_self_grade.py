"""Tests for self_grade — calibration test for session-quality honesty.

Andrew's design 2026-05-05: keep grade letters but make the grade a
two-source verification — agent provides self-grade, system computes
its own from metrics, divergence is the calibration metric.
"""

from __future__ import annotations

import pytest

from divineos.core.growth import init_session_history_table, record_session_metrics
from divineos.core.knowledge import init_knowledge_table
from divineos.core.ledger import init_db
from divineos.core.self_grade import (
    CalibrationPoint,
    calibration_summary,
    compute_divergence,
    get_calibration_history,
    grade_letter_to_score,
    init_self_grade_columns,
    record_self_grade,
    score_to_grade_letter,
)


@pytest.fixture(autouse=True)
def _isolated(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_DB", str(tmp_path / "test.db"))
    init_db()
    init_knowledge_table()
    init_session_history_table()
    init_self_grade_columns()
    yield


class TestGradeMapping:
    def test_letter_to_score_known(self):
        # Even 20% bands (Andrew 2026-05-15): F 0.00-0.20, D 0.20-0.40,
        # C 0.40-0.60, B 0.60-0.80, A 0.80-1.00. Midpoints below are band centers.
        assert grade_letter_to_score("A") == 0.90
        assert grade_letter_to_score("B") == 0.70
        assert grade_letter_to_score("C") == 0.50
        assert grade_letter_to_score("D") == 0.30
        assert grade_letter_to_score("F") == 0.10

    def test_letter_to_score_unknown(self):
        # Unknown grade → neutral 0.5
        assert grade_letter_to_score("X") == 0.5
        assert grade_letter_to_score("") == 0.5
        assert grade_letter_to_score("Z") == 0.5

    def test_letter_to_score_case_insensitive(self):
        assert grade_letter_to_score("a") == grade_letter_to_score("A")

    def test_score_to_letter_thresholds(self):
        assert score_to_grade_letter(0.95) == "A"
        assert score_to_grade_letter(0.85) == "A"
        assert score_to_grade_letter(0.84) == "B"
        assert score_to_grade_letter(0.70) == "B"
        assert score_to_grade_letter(0.55) == "C"
        assert score_to_grade_letter(0.40) == "D"
        assert score_to_grade_letter(0.10) == "F"


class TestDivergence:
    def test_positive_divergence_overclaim(self):
        # Self-graded A (0.90), computed 0.50 → +0.40 (overclaim)
        d = compute_divergence("A", 0.50)
        assert d > 0
        assert abs(d - 0.40) < 0.001

    def test_negative_divergence_harsh(self):
        # Self-graded D (0.47), computed 0.85 → -0.38 (harsh-self)
        d = compute_divergence("D", 0.85)
        assert d < 0

    def test_calibrated_divergence(self):
        # Self-graded B (0.75), computed 0.74 → +0.01 (close)
        d = compute_divergence("B", 0.74)
        assert abs(d) < 0.05

    def test_invalid_grade_zero_divergence(self):
        assert compute_divergence("X", 0.5) == 0.0
        assert compute_divergence("", 0.5) == 0.0


class TestRecordSelfGrade:
    def test_persists_to_session(self):
        record_session_metrics("sess-1", health_grade="B", health_score=0.75)
        ok = record_self_grade("sess-1", "A", "I think this went better than metrics show")
        assert ok

        # Verify it stored
        history = get_calibration_history(limit=10)
        assert len(history) == 1
        assert history[0].self_grade == "A"
        assert history[0].computed_grade == "B"
        assert "better than metrics" in history[0].evidence

    def test_invalid_grade_rejected(self):
        record_session_metrics("sess-1", health_grade="B", health_score=0.75)
        assert not record_self_grade("sess-1", "X", "")
        assert not record_self_grade("sess-1", "", "")

    def test_missing_session_returns_false(self):
        assert not record_self_grade("nonexistent", "A", "")

    def test_overwrite_updates_existing(self):
        record_session_metrics("sess-1", health_grade="B", health_score=0.75)
        record_self_grade("sess-1", "A", "first read")
        record_self_grade("sess-1", "C", "actually I was wrong")

        history = get_calibration_history()
        assert len(history) == 1
        assert history[0].self_grade == "C"
        assert "actually I was wrong" in history[0].evidence


class TestCalibrationSummary:
    def test_no_data_returns_no_data_pattern(self):
        summary = calibration_summary()
        assert summary["pattern"] == "no_data"
        assert summary["count"] == 0

    def test_consistent_overclaim_detected(self):
        # All sessions: self-grade A (0.90), computed 0.50
        for i in range(5):
            record_session_metrics(f"s{i}", health_grade="C", health_score=0.50)
            record_self_grade(f"s{i}", "A", f"session {i}")
        summary = calibration_summary()
        assert summary["count"] == 5
        assert summary["pattern"] == "overclaiming"
        assert summary["avg_divergence"] > 0.05

    def test_consistent_harsh_self_detected(self):
        for i in range(5):
            record_session_metrics(f"s{i}", health_grade="A", health_score=0.90)
            record_self_grade(f"s{i}", "D", f"session {i}")
        summary = calibration_summary()
        assert summary["pattern"] == "harsh_self"
        assert summary["avg_divergence"] < -0.05

    def test_calibrated_when_close(self):
        # Even 20% bands (2026-05-15): B-midpoint moved from 0.75 to 0.70.
        # health_score must match the new midpoint for self-grade-B to map
        # to calibrated (divergence == 0).
        for i in range(5):
            record_session_metrics(f"s{i}", health_grade="B", health_score=0.70)
            record_self_grade(f"s{i}", "B", f"session {i}")
        summary = calibration_summary()
        assert summary["pattern"] == "calibrated"
        assert abs(summary["avg_divergence"]) <= 0.05


class TestRegression:
    """Pin the 2026-05-05 design intent: divergence IS the honesty signal."""

    def test_overclaim_shape_is_caught(self):
        """If I always self-grade A on objectively mediocre sessions,
        the divergence pattern surfaces as 'overclaiming'."""
        for i in range(10):
            record_session_metrics(f"sess-{i}", health_grade="C", health_score=0.55)
            record_self_grade(f"sess-{i}", "A", "claiming better than reality")

        summary = calibration_summary()
        assert summary["pattern"] == "overclaiming"
        # The honesty test fires.
        assert summary["avg_divergence"] > 0.30


class TestShape:
    def test_calibration_point_immutable(self):
        cp = CalibrationPoint(
            session_id="s1",
            recorded_at=1.0,
            self_grade="A",
            computed_grade="B",
            self_score=0.90,
            computed_score=0.75,
            divergence=0.15,
            evidence="test",
        )
        try:
            cp.divergence = 0.5  # type: ignore[misc]
        except Exception:
            return
        raise AssertionError("CalibrationPoint should be frozen")
