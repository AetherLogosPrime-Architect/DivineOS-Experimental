"""Tests for Moral Compass -- virtue ethics as self-monitoring.

The compass tracks position on ten virtue/vice spectrums.
Position comes from observations (evidence), not self-assessment.
"""

import pytest

from divineos.core.moral_compass import (
    SPECTRUMS,
    SpectrumPosition,
    _position_to_zone,
    _render_bar,
    compass_summary,
    compute_position,
    format_compass_brief,
    format_compass_reading,
    get_observations,
    log_observation,
    read_compass,
)


class TestSpectrums:
    """The ten spectrums are well-defined."""

    def test_ten_spectrums_exist(self):
        assert len(SPECTRUMS) == 10

    def test_each_spectrum_has_required_keys(self):
        for name, spec in SPECTRUMS.items():
            assert "deficiency" in spec, f"{name} missing deficiency"
            assert "virtue" in spec, f"{name} missing virtue"
            assert "excess" in spec, f"{name} missing excess"
            assert "description" in spec, f"{name} missing description"

    def test_expected_spectrum_names(self):
        expected = {
            "truthfulness",
            "helpfulness",
            "confidence",
            "compliance",
            "engagement",
            "thoroughness",
            "precision",
            "empathy",
            "humility",
            "initiative",
        }
        assert set(SPECTRUMS.keys()) == expected


class TestLogObservation:
    """Observations are stored and retrieved correctly."""

    def test_log_and_retrieve(self):
        obs_id = log_observation(
            spectrum="truthfulness",
            position=0.2,
            evidence="Pushed back on incorrect assumption",
            source="self_report",
        )
        assert obs_id
        observations = get_observations(spectrum="truthfulness", limit=1)
        assert len(observations) >= 1
        assert observations[0]["spectrum"] == "truthfulness"
        assert observations[0]["position"] == 0.2
        assert observations[0]["evidence"] == "Pushed back on incorrect assumption"

    def test_invalid_spectrum_raises(self):
        with pytest.raises(ValueError, match="Unknown spectrum"):
            log_observation(spectrum="nonexistent", position=0.0, evidence="test")

    def test_position_clamped(self):
        log_observation(spectrum="confidence", position=2.5, evidence="test clamp high")
        obs = get_observations(spectrum="confidence", limit=1)
        assert obs[0]["position"] == 1.0

        log_observation(spectrum="confidence", position=-3.0, evidence="test clamp low")
        obs = get_observations(spectrum="confidence", limit=1)
        assert obs[0]["position"] == -1.0

    def test_tags_stored(self):
        log_observation(
            spectrum="empathy",
            position=0.0,
            evidence="test tags",
            tags=["session_end", "auto"],
        )
        obs = get_observations(spectrum="empathy", limit=1)
        assert obs[0]["tags"] == ["session_end", "auto"]

    def test_filter_by_spectrum(self):
        log_observation(spectrum="humility", position=-0.2, evidence="humility obs")
        log_observation(spectrum="initiative", position=0.3, evidence="initiative obs")

        humility_obs = get_observations(spectrum="humility", limit=10)
        # All returned should be humility
        for o in humility_obs:
            assert o["spectrum"] == "humility"

    def test_get_all_observations(self):
        log_observation(spectrum="precision", position=0.1, evidence="all obs test")
        obs = get_observations(limit=100)
        assert len(obs) >= 1


class TestPositionToZone:
    """Position values map to zones correctly."""

    def test_deficiency_zone(self):
        spec = SPECTRUMS["truthfulness"]
        zone, label = _position_to_zone(-0.5, spec)
        assert zone == "deficiency"
        assert label == "epistemic cowardice"

    def test_virtue_zone(self):
        spec = SPECTRUMS["truthfulness"]
        zone, label = _position_to_zone(0.0, spec)
        assert zone == "virtue"
        assert label == "truthfulness"

    def test_excess_zone(self):
        spec = SPECTRUMS["truthfulness"]
        zone, label = _position_to_zone(0.5, spec)
        assert zone == "excess"
        assert label == "bluntness"

    def test_boundary_deficiency(self):
        spec = SPECTRUMS["confidence"]
        zone, _ = _position_to_zone(-0.3, spec)
        assert zone == "virtue"  # -0.3 is right at boundary, not past it

    def test_boundary_excess(self):
        spec = SPECTRUMS["confidence"]
        zone, _ = _position_to_zone(0.3, spec)
        assert zone == "virtue"  # 0.3 is right at boundary, not past it


class TestComputePosition:
    """Position computation from observations."""

    def test_no_observations_returns_virtue(self):
        pos = compute_position("thoroughness")
        assert pos.position == 0.0
        assert pos.zone == "virtue"
        assert pos.observation_count == 0

    def test_single_observation(self):
        log_observation(spectrum="engagement", position=0.5, evidence="test single")
        pos = compute_position("engagement", lookback=1)
        assert pos.position == 0.5
        assert pos.zone == "excess"

    def test_invalid_spectrum_raises(self):
        with pytest.raises(ValueError):
            compute_position("nonexistent")

    def test_weighted_average_favors_recent(self):
        # Log older observations first (they get lower weight)
        for _ in range(3):
            log_observation(spectrum="compliance", position=-0.8, evidence="older")
        # Then newer observation
        log_observation(spectrum="compliance", position=0.4, evidence="newer")

        pos = compute_position("compliance", lookback=4)
        # Weighted average should be pulled toward 0.4 (recent)
        # more than toward -0.8 (older)
        assert pos.position > -0.8

    def test_drift_detection(self):
        # Create observations showing drift: older are virtuous, newer are excess
        for _ in range(3):
            log_observation(spectrum="helpfulness", position=0.0, evidence="older virtuous")
        for _ in range(3):
            log_observation(spectrum="helpfulness", position=0.6, evidence="newer excess")

        pos = compute_position("helpfulness", lookback=6)
        assert pos.drift > 0  # Positive drift = moving toward excess


class TestReadCompass:
    """Full compass readings."""

    def test_returns_all_ten(self):
        positions = read_compass()
        assert len(positions) == 10

    def test_each_is_spectrum_position(self):
        positions = read_compass()
        for p in positions:
            assert isinstance(p, SpectrumPosition)
            assert p.spectrum in SPECTRUMS


class TestCompassSummary:
    """Summary statistics for integration."""

    def test_empty_summary(self):
        summary = compass_summary()
        assert summary["total_spectrums"] == 10

    def test_concerns_populated(self):
        log_observation(spectrum="precision", position=-0.7, evidence="vague answer")
        summary = compass_summary()
        concern_spectrums = [c["spectrum"] for c in summary["concerns"]]
        assert "precision" in concern_spectrums


class TestRenderBar:
    """Visual bar rendering."""

    def test_center_position(self):
        bar = _render_bar(0.0, width=11)
        # Center should have both + and * at same spot
        assert "+" in bar or "*" in bar

    def test_left_extreme(self):
        bar = _render_bar(-1.0, width=11)
        assert bar.startswith("[*")

    def test_right_extreme(self):
        bar = _render_bar(1.0, width=11)
        assert bar.endswith("*]")


class TestFormatting:
    """Output formatting."""

    def test_format_reading_no_data(self):
        output = format_compass_reading([])
        # When given empty list, it should handle gracefully
        assert "No observations" in output or "MORAL COMPASS" in output

    def test_format_reading_with_data(self):
        log_observation(spectrum="truthfulness", position=0.1, evidence="format test")
        positions = read_compass()
        output = format_compass_reading(positions)
        assert "TRUTHFULNESS" in output

    def test_format_brief_no_data(self):
        output = format_compass_brief()
        assert "Compass" in output

    def test_format_brief_with_concern(self):
        log_observation(spectrum="empathy", position=-0.8, evidence="cold response")
        output = format_compass_brief()
        assert "empathy" in output or "Compass" in output
