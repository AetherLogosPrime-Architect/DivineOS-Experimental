"""Tests for the convergence detector — multi-system cross-checks."""

from unittest.mock import patch

import pytest

from divineos.core.convergence_detector import (
    ConvergenceReport,
    ConvergentSignal,
    _classify_signal,
    apply_convergence_to_knowledge,
    detect_convergence,
    format_convergence_report,
)


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Each test gets its own database."""
    db_path = str(tmp_path / "test.db")
    monkeypatch.setenv("DIVINEOS_DB_PATH", db_path)


class TestClassifySignal:
    """Tests for the signal classification logic."""

    def test_both_concern(self):
        compass = {"position": -0.5, "zone": "deficiency", "observation_count": 5}
        critique = {"average": -0.4, "direction": "declining", "concern": True}
        signal = _classify_signal("thoroughness", "thoroughness", compass, critique)
        assert signal is not None
        assert signal.convergence_type == "both_concern"
        assert signal.combined_confidence > 0

    def test_both_strong(self):
        compass = {"position": 0.3, "zone": "virtue", "observation_count": 5}
        critique = {"average": 0.5, "direction": "improving", "concern": False}
        signal = _classify_signal("thoroughness", "thoroughness", compass, critique)
        assert signal is not None
        assert signal.convergence_type == "both_strong"

    def test_divergent_compass_bad_critique_good(self):
        compass = {"position": -0.5, "zone": "deficiency", "observation_count": 5}
        critique = {"average": 0.5, "direction": "improving", "concern": False}
        signal = _classify_signal("thoroughness", "thoroughness", compass, critique)
        assert signal is not None
        assert signal.convergence_type == "divergent"

    def test_no_signal_when_neutral(self):
        compass = {"position": 0.0, "zone": "virtue", "observation_count": 5}
        critique = {"average": 0.0, "direction": "stable", "concern": False}
        signal = _classify_signal("thoroughness", "thoroughness", compass, critique)
        assert signal is None


class TestFormatReport:
    """Tests for report formatting."""

    def test_empty_report(self):
        report = ConvergenceReport()
        text = format_convergence_report(report)
        assert "unavailable" in text

    def test_report_shows_sources(self):
        report = ConvergenceReport(
            compass_available=True,
            critique_available=True,
            affect_available=True,
            opinions_available=True,
        )
        text = format_convergence_report(report)
        assert "compass" in text
        assert "critique" in text
        assert "affect" in text
        assert "opinions" in text

    def test_report_with_concern(self):
        concern = ConvergentSignal(
            compass_spectrum="thoroughness",
            critique_spectrum="thoroughness",
            compass_position=-0.5,
            critique_score=-0.4,
            compass_zone="deficiency",
            critique_direction="declining",
            convergence_type="both_concern",
            combined_confidence=0.7,
            description="Test concern",
        )
        report = ConvergenceReport(
            signals=[concern],
            concerns=[concern],
            compass_available=True,
            critique_available=True,
        )
        text = format_convergence_report(report)
        assert "Convergent Concerns" in text


class TestDetectConvergenceWithAffect:
    """Tests for affect cross-checks in convergence detection."""

    def test_affect_available_flag_set(self):
        """When affect data is available, the flag should be set."""
        mock_compass_pos = type(
            "Pos", (), {"position": -0.5, "zone": "deficiency", "observation_count": 5}
        )()
        mock_trend = type(
            "Trend",
            (),
            {
                "spectrum": "thoroughness",
                "average": -0.3,
                "direction": "declining",
                "concern": True,
            },
        )()

        with (
            patch("divineos.core.moral_compass.compute_position", return_value=mock_compass_pos),
            patch("divineos.core.self_critique.get_craft_trends", return_value=[mock_trend]),
            patch(
                "divineos.core.affect.get_affect_summary",
                return_value={"count": 5, "avg_valence": -0.4},
            ),
        ):
            report = detect_convergence()
            assert report.affect_available is True

    def test_negative_affect_plus_compass_concern(self):
        """Low valence + compass deficiency should produce convergent concern."""
        mock_compass_pos = type(
            "Pos", (), {"position": -0.5, "zone": "deficiency", "observation_count": 5}
        )()
        mock_trend = type(
            "Trend",
            (),
            {"spectrum": "thoroughness", "average": 0.0, "direction": "stable", "concern": False},
        )()

        with (
            patch("divineos.core.moral_compass.compute_position", return_value=mock_compass_pos),
            patch("divineos.core.self_critique.get_craft_trends", return_value=[mock_trend]),
            patch(
                "divineos.core.affect.get_affect_summary",
                return_value={"count": 5, "avg_valence": -0.4},
            ),
            patch("divineos.core.opinion_store.get_opinions", return_value=[]),
        ):
            report = detect_convergence()
            affect_concerns = [
                s for s in report.concerns if s.critique_spectrum == "affect-valence"
            ]
            assert len(affect_concerns) >= 1


class TestDetectConvergenceWithOpinions:
    """Tests for opinion cross-checks in convergence detection."""

    def test_opinions_available_flag_set(self):
        """When opinion data exists, the flag should be set."""
        mock_compass_pos = type(
            "Pos", (), {"position": 0.0, "zone": "virtue", "observation_count": 5}
        )()
        mock_trend = type(
            "Trend",
            (),
            {"spectrum": "thoroughness", "average": 0.0, "direction": "stable", "concern": False},
        )()

        with (
            patch("divineos.core.moral_compass.compute_position", return_value=mock_compass_pos),
            patch("divineos.core.self_critique.get_craft_trends", return_value=[mock_trend]),
            patch(
                "divineos.core.affect.get_affect_summary",
                return_value={"count": 0, "avg_valence": 0.0},
            ),
            patch(
                "divineos.core.opinion_store.get_opinions",
                return_value=[{"topic": "test", "confidence": 0.8, "tags": ["auto-generated"]}],
            ),
        ):
            report = detect_convergence()
            assert report.opinions_available is True

    def test_correction_opinion_converges_with_critique_concern(self):
        """An auto-generated correction opinion should converge with critique concerns."""
        mock_compass_pos = type(
            "Pos", (), {"position": 0.0, "zone": "virtue", "observation_count": 5}
        )()
        mock_trend = type(
            "Trend",
            (),
            {
                "spectrum": "thoroughness",
                "average": -0.3,
                "direction": "declining",
                "concern": True,
            },
        )()

        with (
            patch("divineos.core.moral_compass.compute_position", return_value=mock_compass_pos),
            patch("divineos.core.self_critique.get_craft_trends", return_value=[mock_trend]),
            patch(
                "divineos.core.affect.get_affect_summary",
                return_value={"count": 0, "avg_valence": 0.0},
            ),
            patch(
                "divineos.core.opinion_store.get_opinions",
                return_value=[
                    {
                        "topic": "session-corrections",
                        "confidence": 0.7,
                        "tags": ["auto-generated", "correction-pattern"],
                    }
                ],
            ),
        ):
            report = detect_convergence()
            opinion_concerns = [s for s in report.concerns if "opinion:" in s.compass_spectrum]
            assert len(opinion_concerns) >= 1


class TestApplyConvergenceToKnowledge:
    """Tests for storing convergent signals as knowledge."""

    def test_stores_concerns(self):
        concern = ConvergentSignal(
            compass_spectrum="thoroughness",
            critique_spectrum="thoroughness",
            compass_position=-0.5,
            critique_score=-0.4,
            compass_zone="deficiency",
            critique_direction="declining",
            convergence_type="both_concern",
            combined_confidence=0.7,
            description="Test convergent concern",
        )
        report = ConvergenceReport(
            signals=[concern],
            concerns=[concern],
            compass_available=True,
            critique_available=True,
        )
        stored = apply_convergence_to_knowledge(report)
        assert stored >= 1
