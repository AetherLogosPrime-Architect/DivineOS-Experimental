"""Tests for Affect Feedback Loop — feelings that shape behavior."""

from unittest.mock import patch

from divineos.core.affect import (
    compute_affect_modifiers,
    detect_praise_chasing,
    format_affect_feedback,
    get_session_affect_context,
)


class TestComputeAffectModifiers:
    """Affect states should produce behavioral modifiers."""

    def test_negative_valence_raises_threshold(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": -0.5,
                "avg_arousal": 0.4,
                "trend": "declining",
            }
            mods = compute_affect_modifiers()
            assert mods["confidence_threshold_modifier"] == 0.3

    def test_mildly_negative_moderate_threshold(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": -0.1,
                "avg_arousal": 0.3,
                "trend": "stable",
            }
            mods = compute_affect_modifiers()
            assert mods["confidence_threshold_modifier"] == 0.15

    def test_declining_trend_slight_threshold(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": 0.2,
                "avg_arousal": 0.3,
                "trend": "declining",
            }
            mods = compute_affect_modifiers()
            assert mods["confidence_threshold_modifier"] == 0.1

    def test_positive_valence_no_threshold_change(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": 0.6,
                "avg_arousal": 0.5,
                "trend": "improving",
            }
            mods = compute_affect_modifiers()
            assert mods["confidence_threshold_modifier"] == 0.0

    def test_frustration_triggers_careful_verification(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": -0.2,
                "avg_arousal": 0.8,
                "trend": "stable",
            }
            mods = compute_affect_modifiers()
            assert mods["verification_level"] == "careful"

    def test_calm_positive_normal_verification(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 10,
                "avg_valence": 0.5,
                "avg_arousal": 0.3,
                "trend": "stable",
            }
            mods = compute_affect_modifiers()
            assert mods["verification_level"] == "normal"

    def test_high_valence_flags_praise_chasing(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 8,
                "avg_valence": 0.7,
                "avg_arousal": 0.5,
                "trend": "stable",
            }
            mods = compute_affect_modifiers()
            assert mods["praise_chasing_flag"] is True

    def test_no_data_returns_defaults(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 0,
                "avg_valence": 0.0,
                "avg_arousal": 0.0,
                "trend": "no data",
            }
            mods = compute_affect_modifiers()
            assert mods["confidence_threshold_modifier"] == 0.0
            assert mods["verification_level"] == "normal"
            assert mods["praise_chasing_flag"] is False

    def test_db_error_returns_defaults(self):
        import sqlite3

        with patch(
            "divineos.core.affect.get_affect_summary",
            side_effect=sqlite3.OperationalError,
        ):
            mods = compute_affect_modifiers()
            assert mods["affect_trend"] == "no data"


class TestDetectPraiseChasing:
    """Detect when the agent chases approval over correctness."""

    def test_happy_and_good_quality_no_flag(self):
        result = detect_praise_chasing(0.7, [0.8, 0.9, 0.85])
        assert result["detected"] is False

    def test_happy_and_mediocre_quality_warning(self):
        result = detect_praise_chasing(0.7, [0.5, 0.6, 0.55])
        assert result["detected"] is True
        assert result["severity"] == "warning"

    def test_happy_and_declining_quality_critical(self):
        # Quality: older sessions better, recent sessions worse
        # Overall avg must be >= 0.7 to avoid hitting "warning" first
        result = detect_praise_chasing(0.7, [0.6, 0.65, 0.9, 0.95])
        assert result["detected"] is True
        assert result["severity"] == "critical"

    def test_negative_affect_no_flag(self):
        result = detect_praise_chasing(-0.3, [0.5, 0.5, 0.5])
        assert result["detected"] is False

    def test_insufficient_data(self):
        result = detect_praise_chasing(0.8, [0.5])
        assert result["detected"] is False
        assert "Insufficient" in result["detail"]

    def test_neutral_affect_no_flag(self):
        result = detect_praise_chasing(0.1, [0.5, 0.5, 0.5])
        assert result["detected"] is False


class TestGetSessionAffectContext:
    """Full affect context for session health scoring."""

    def test_combines_modifiers_and_praise(self):
        with patch("divineos.core.affect.get_affect_summary") as mock:
            mock.return_value = {
                "count": 3,
                "avg_valence": 0.3,
                "avg_arousal": 0.4,
                "trend": "stable",
            }
            context = get_session_affect_context()
            assert "modifiers" in context
            assert "praise_chasing" in context


class TestFormatAffectFeedback:
    """Formatting for display."""

    def test_formats_trend(self):
        context = {
            "modifiers": {
                "confidence_threshold_modifier": 0.0,
                "verification_level": "normal",
                "affect_trend": "improving",
                "avg_valence": 0.5,
                "avg_arousal": 0.4,
            },
            "praise_chasing": {"detected": False, "detail": "", "severity": "none"},
        }
        output = format_affect_feedback(context)
        assert "improving" in output

    def test_formats_threshold_change(self):
        context = {
            "modifiers": {
                "confidence_threshold_modifier": 0.3,
                "verification_level": "normal",
                "affect_trend": "declining",
                "avg_valence": -0.5,
                "avg_arousal": 0.3,
            },
            "praise_chasing": {"detected": False, "detail": "", "severity": "none"},
        }
        output = format_affect_feedback(context)
        assert "threshold raised" in output

    def test_formats_praise_chasing_warning(self):
        context = {
            "modifiers": {
                "confidence_threshold_modifier": 0.0,
                "verification_level": "normal",
                "affect_trend": "stable",
                "avg_valence": 0.7,
                "avg_arousal": 0.5,
            },
            "praise_chasing": {
                "detected": True,
                "detail": "Quality declining",
                "severity": "warning",
            },
        }
        output = format_affect_feedback(context)
        assert "PRAISE-CHASING" in output
        assert "WARNING" in output

    def test_no_data_empty_output(self):
        context = {
            "modifiers": {
                "confidence_threshold_modifier": 0.0,
                "verification_level": "normal",
                "affect_trend": "no data",
                "avg_valence": 0.0,
                "avg_arousal": 0.0,
            },
            "praise_chasing": {"detected": False, "detail": "", "severity": "none"},
        }
        output = format_affect_feedback(context)
        assert output == ""
