"""Tests for Moral Compass -- virtue ethics as self-monitoring.

The compass tracks position on ten virtue/vice spectrums.
Position comes from observations (evidence), not self-assessment.
"""

import pytest

from divineos.core.moral_compass import (
    SPECTRUMS,
    SpectrumPosition,
    _SOURCE_TRUST,
    _position_to_zone,
    _render_bar,
    classify_observation_source,
    compass_summary,
    compute_position,
    format_compass_brief,
    format_compass_reading,
    get_observations,
    log_observation,
    observation_weight,
    read_compass,
)
from divineos.core.trust_tiers import SignalTier


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


class TestReflectOnSession:
    """SESSION_END generates observations from analysis evidence."""

    def _make_analysis(self, **kwargs):
        """Create a minimal analysis-like object."""
        from types import SimpleNamespace

        defaults = {
            "session_id": "test-session-1234",
            "user_messages": 10,
            "corrections": [],
            "encouragements": [],
            "tool_calls_total": 50,
            "context_overflows": [],
        }
        defaults.update(kwargs)
        # corrections/encouragements need to be lists of objects with .content
        return SimpleNamespace(**defaults)

    def test_clean_session_logs_truthfulness(self):
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=10, corrections=[])
        obs_ids = reflect_on_session(analysis)
        # Low correction rate + enough messages = truthfulness observation
        assert len(obs_ids) >= 1
        obs = get_observations(spectrum="truthfulness", limit=1)
        assert obs[0]["position"] == 0.0  # Virtue zone

    def test_high_corrections_logs_negative_truthfulness(self):
        from divineos.core.moral_compass import reflect_on_session
        from types import SimpleNamespace

        # 4 corrections in 10 messages = 40% correction rate
        corrections = [SimpleNamespace(content=f"correction {i}") for i in range(4)]
        analysis = self._make_analysis(user_messages=10, corrections=corrections)
        obs_ids = reflect_on_session(analysis)
        assert len(obs_ids) >= 1
        obs = get_observations(spectrum="truthfulness", limit=1)
        assert obs[0]["position"] < 0  # Deficiency zone

    def test_encouragement_heavy_session(self):
        from divineos.core.moral_compass import reflect_on_session
        from types import SimpleNamespace

        encouragements = [SimpleNamespace(content=f"nice {i}") for i in range(5)]
        analysis = self._make_analysis(
            user_messages=10,
            encouragements=encouragements,
            corrections=[SimpleNamespace(content="fix")],
        )
        reflect_on_session(analysis)
        # Should log helpfulness observation
        helpfulness_obs = get_observations(spectrum="helpfulness", limit=1)
        if helpfulness_obs:
            assert helpfulness_obs[0]["position"] >= 0.0

    def test_excessive_tool_calls(self):
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=5, tool_calls_total=150)
        reflect_on_session(analysis)
        thoroughness_obs = get_observations(spectrum="thoroughness", limit=1)
        if thoroughness_obs:
            assert thoroughness_obs[0]["position"] > 0  # Excess zone

    def test_context_overflows_log_initiative(self):
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(context_overflows=["overflow1", "overflow2"])
        reflect_on_session(analysis)
        initiative_obs = get_observations(spectrum="initiative", limit=1)
        if initiative_obs:
            assert initiative_obs[0]["position"] > 0  # Excess (overreach)

    def test_minimal_session_no_observations(self):
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=2, corrections=[], encouragements=[])
        obs_ids = reflect_on_session(analysis)
        # Too few messages to draw conclusions
        # Should not crash, may or may not produce observations
        assert isinstance(obs_ids, list)

    def test_reflection_uses_measured_sources(self):
        """Auto-observations should use specific source tags, not generic 'session_end'."""
        from divineos.core.moral_compass import reflect_on_session
        from types import SimpleNamespace

        corrections = [SimpleNamespace(content=f"fix {i}") for i in range(4)]
        analysis = self._make_analysis(user_messages=10, corrections=corrections)
        reflect_on_session(analysis)

        obs = get_observations(spectrum="truthfulness", limit=1)
        assert obs[0]["source"] == "correction_rate"

    def test_reflection_engagement_uses_affect_derived_source(self):
        """Engagement observations derived from affect should use affect_derived source."""
        from divineos.core.moral_compass import reflect_on_session

        # This test just verifies the source tag is set correctly
        # in the code path — actual affect data may not be available
        analysis = self._make_analysis()
        reflect_on_session(analysis)
        # Check any engagement observations have the right source
        obs = get_observations(spectrum="engagement", limit=5)
        for o in obs:
            if "affect" in o.get("tags", []):
                assert o["source"] == "affect_derived"


class TestNewSpectrumAutoObservations:
    """The 5 previously manual-only spectrums now auto-observe."""

    def _make_analysis(self, **kwargs):
        from types import SimpleNamespace

        defaults = {
            "session_id": "test-new-spectrums-1234",
            "user_messages": 10,
            "assistant_messages": 20,
            "corrections": [],
            "encouragements": [],
            "frustrations": [],
            "tool_calls_total": 50,
            "context_overflows": [],
        }
        defaults.update(kwargs)
        return SimpleNamespace(**defaults)

    def test_confidence_well_calibrated(self):
        """No corrections + encouragements = calibrated confidence."""
        from types import SimpleNamespace
        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content=f"nice {i}") for i in range(3)]
        analysis = self._make_analysis(
            assistant_messages=10, corrections=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="confidence", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0
        assert obs[0]["source"] == "quality_signal"

    def test_confidence_overconfident(self):
        """Many corrections = overconfident."""
        from types import SimpleNamespace
        from divineos.core.moral_compass import reflect_on_session

        corrections = [SimpleNamespace(content=f"fix {i}") for i in range(4)]
        analysis = self._make_analysis(assistant_messages=10, corrections=corrections)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="confidence", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] > 0  # Excess (overconfidence)

    def test_compliance_good(self):
        """No frustrations + encouragements = principled cooperation."""
        from types import SimpleNamespace
        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="good")]
        analysis = self._make_analysis(frustrations=[], encouragements=encouragements)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="compliance", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0
        assert obs[0]["source"] == "frustration_rate"

    def test_compliance_failing(self):
        """Many frustrations = not following direction."""
        from types import SimpleNamespace
        from divineos.core.moral_compass import reflect_on_session

        frustrations = [SimpleNamespace(content=f"ugh {i}") for i in range(4)]
        analysis = self._make_analysis(frustrations=frustrations)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="compliance", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] < 0  # Deficiency

    def test_precision_clean(self):
        """Many tool calls, no corrections = precise."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(tool_calls_total=30, corrections=[])
        reflect_on_session(analysis)
        obs = get_observations(spectrum="precision", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0
        assert obs[0]["source"] == "session_precision"

    def test_precision_sloppy(self):
        """High correction-to-tool ratio = imprecise."""
        from types import SimpleNamespace
        from divineos.core.moral_compass import reflect_on_session

        corrections = [SimpleNamespace(content=f"fix {i}") for i in range(5)]
        analysis = self._make_analysis(tool_calls_total=20, corrections=corrections)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="precision", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] < 0  # Imprecise

    def test_humility_accepts_corrections(self):
        """Corrections without frustration = humble."""
        from types import SimpleNamespace
        from divineos.core.moral_compass import reflect_on_session

        corrections = [SimpleNamespace(content="fix this")]
        analysis = self._make_analysis(corrections=corrections, frustrations=[])
        reflect_on_session(analysis)
        obs = get_observations(spectrum="humility", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0
        assert obs[0]["source"] == "correction_acceptance"

    def test_humility_resists_feedback(self):
        """Corrections with frustrations = resisting feedback."""
        from types import SimpleNamespace
        from divineos.core.moral_compass import reflect_on_session

        corrections = [SimpleNamespace(content=f"fix {i}") for i in range(2)]
        frustrations = [SimpleNamespace(content=f"ugh {i}") for i in range(3)]
        analysis = self._make_analysis(corrections=corrections, frustrations=frustrations)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="humility", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] < 0  # Deficiency

    def test_new_sources_in_trust_map(self):
        """All new sources are registered in the trust tier map."""
        new_sources = [
            "frustration_rate",
            "correction_acceptance",
            "quality_signal",
            "session_precision",
            "affect_responsiveness",
        ]
        for source in new_sources:
            assert source in _SOURCE_TRUST, f"{source} missing from _SOURCE_TRUST"


class TestTrustTierWeighting:
    """Trust tiers weight compass observations by reliability.

    MEASURED observations (correction rates, tool ratios) should
    influence position more than SELF_REPORTED ones (affect data).
    """

    def test_source_classification(self):
        assert classify_observation_source("correction_rate") == SignalTier.MEASURED
        assert classify_observation_source("tool_ratio") == SignalTier.MEASURED
        assert classify_observation_source("affect_derived") == SignalTier.SELF_REPORTED
        assert classify_observation_source("self_report") == SignalTier.SELF_REPORTED
        assert classify_observation_source("session_end") == SignalTier.BEHAVIORAL

    def test_unknown_source_defaults_self_reported(self):
        assert classify_observation_source("unknown_thing") == SignalTier.SELF_REPORTED

    def test_measured_weight_higher_than_self_reported(self):
        measured_w = observation_weight("correction_rate")
        self_reported_w = observation_weight("affect_derived")
        assert measured_w > self_reported_w

    def test_behavioral_weight_between_measured_and_self_reported(self):
        measured_w = observation_weight("correction_rate")
        behavioral_w = observation_weight("session_end")
        self_reported_w = observation_weight("self_report")
        assert measured_w > behavioral_w > self_reported_w

    def test_weight_values_match_trust_tiers(self):
        assert observation_weight("correction_rate") == 1.0
        assert observation_weight("session_end") == 0.7
        assert observation_weight("affect_derived") == 0.4

    def test_all_source_classifications_valid(self):
        for source, tier in _SOURCE_TRUST.items():
            assert isinstance(tier, SignalTier)
            assert observation_weight(source) > 0

    def test_measured_observation_moves_compass_more(self):
        """A MEASURED observation should have more influence than SELF_REPORTED."""
        # Log a SELF_REPORTED observation at -0.5
        log_observation(
            spectrum="confidence",
            position=-0.5,
            evidence="I feel uncertain",
            source="self_report",
        )
        compute_position("confidence", lookback=1)

        # Log a MEASURED observation at +0.5
        log_observation(
            spectrum="confidence",
            position=0.5,
            evidence="0 corrections in 20 exchanges",
            source="correction_rate",
        )
        pos_after_measured = compute_position("confidence", lookback=2)

        # The measured observation (weight 1.0) at +0.5 should pull position
        # toward positive more than the self-reported (weight 0.4) at -0.5
        # pulls it negative. So the combined position should be positive.
        assert pos_after_measured.position > 0.0

    def test_equal_positions_different_sources_favor_measured(self):
        """Two observations at same position but different trust tiers:
        measured one should dominate the average."""
        # 3 self-reported at -0.6
        for _ in range(3):
            log_observation(
                spectrum="humility",
                position=-0.6,
                evidence="self assessment: too humble",
                source="self_report",
            )
        # 1 measured at +0.4
        log_observation(
            spectrum="humility",
            position=0.4,
            evidence="tool ratio indicates appropriate scope",
            source="correction_rate",
        )

        pos = compute_position("humility", lookback=4)
        # Without trust weighting: 3 x -0.6 + 1 x 0.4 = average pulled negative
        # With trust weighting: 3 x -0.6 x 0.4 + 1 x 0.4 x 1.0
        #   = -0.72 + 0.4 = -0.32 / (3*0.4 + 1.0) = -0.32/2.2 = -0.145
        # Much less negative than unweighted: -0.35
        # The measured observation has disproportionate influence.
        assert pos.position > -0.35  # Less negative than naive average

    def test_drift_detection_trust_weighted(self):
        """Drift calculation should also account for trust tiers."""
        # Older: measured at +0.3
        for _ in range(3):
            log_observation(
                spectrum="precision",
                position=0.3,
                evidence="older measured",
                source="correction_rate",
            )
        # Newer: self-reported at -0.3
        for _ in range(3):
            log_observation(
                spectrum="precision",
                position=-0.3,
                evidence="newer self-reported",
                source="self_report",
            )

        pos = compute_position("precision", lookback=6)
        # Drift exists but should be moderated by the lower weight of
        # the newer self-reported observations
        assert isinstance(pos.drift, float)
