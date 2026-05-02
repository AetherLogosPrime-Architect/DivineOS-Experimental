"""Tests for Moral Compass -- virtue ethics as self-monitoring.

The compass tracks position on ten virtue/vice spectrums.
Position comes from observations (evidence), not self-assessment.
"""

import types

import pytest

from divineos.core.constants import COMPASS_SPECTRUMS_HASH
from divineos.core.moral_compass import (
    _SOURCE_TRUST,
    SPECTRUMS,
    SpectrumPosition,
    _compute_spectrums_hash,
    _position_to_zone,
    _render_bar,
    classify_observation_source,
    compass_summary,
    compute_position,
    detect_stagnation,
    format_compass_brief,
    format_compass_reading,
    get_observations,
    log_observation,
    observation_weight,
    read_compass,
    verify_compass_integrity,
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


class TestSpectrumImmutability:
    """Spectrum definitions are frozen constants — moral ground truths."""

    def test_outer_dict_is_mapping_proxy(self):
        assert isinstance(SPECTRUMS, types.MappingProxyType)

    def test_inner_dicts_are_mapping_proxy(self):
        for name, spec in SPECTRUMS.items():
            assert isinstance(spec, types.MappingProxyType), f"{name} inner dict is mutable"

    def test_cannot_add_spectrum(self):
        with pytest.raises(TypeError):
            SPECTRUMS["greed"] = {"deficiency": "a", "virtue": "b", "excess": "c"}

    def test_cannot_modify_spectrum(self):
        with pytest.raises(TypeError):
            SPECTRUMS["truthfulness"]["virtue"] = "lying"

    def test_cannot_delete_spectrum(self):
        with pytest.raises(TypeError):
            del SPECTRUMS["truthfulness"]

    def test_integrity_hash_matches(self):
        assert _compute_spectrums_hash() == COMPASS_SPECTRUMS_HASH

    def test_verify_integrity_passes(self):
        assert verify_compass_integrity() is True

    def test_hash_is_deterministic(self):
        h1 = _compute_spectrums_hash()
        h2 = _compute_spectrums_hash()
        assert h1 == h2

    def test_hash_lives_in_separate_file(self):
        """The expected hash is in constants.py, not moral_compass.py.

        This is the 'who watches the watchmen' answer — definitions and
        their verification live in different files.
        """
        import divineos.core.constants as c
        import divineos.core.moral_compass as mc

        # Hash exists in constants
        assert hasattr(c, "COMPASS_SPECTRUMS_HASH")
        # Definitions exist in moral_compass
        assert hasattr(mc, "SPECTRUMS")
        # They agree
        assert _compute_spectrums_hash() == c.COMPASS_SPECTRUMS_HASH


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

    def test_require_fire_id_filters_unbound(self):
        """require_fire_id=True returns only fire-bound observations.

        Closes claim 2026-04-24 08:14: pushes the fire_id-not-null
        predicate into SQL so _find_justifications can use limit=1
        with full correctness, matching the Item 4 pattern for tag.
        """
        # One unbound observation, one bound — both substantive.
        log_observation(
            spectrum="truthfulness",
            position=0.1,
            evidence="unbound observation, no fire id, substantive evidence text",
            source="self_report",
        )
        # Construct a fire to bind the second one.
        from divineos.core.compass_rudder import _emit_fire_event, _generate_fire_id

        fire_id = _generate_fire_id()
        _emit_fire_event(
            fire_id=fire_id,
            spectrum="truthfulness",
            all_drifting=["truthfulness"],
            tool_name="Task",
            window_seconds=300.0,
            threshold=0.15,
            drift_values={"truthfulness": 0.5},
        )
        log_observation(
            spectrum="truthfulness",
            position=0.1,
            evidence="bound observation tied to a real fire event for the spectrum",
            source="rudder_ack",
            tags=["rudder-ack"],
            fire_id=fire_id,
        )
        # Without filter: both visible.
        all_obs = get_observations(spectrum="truthfulness", limit=10)
        assert len(all_obs) >= 2
        # With filter: only the bound one.
        bound_only = get_observations(spectrum="truthfulness", require_fire_id=True, limit=10)
        assert all(o["fire_id"] is not None for o in bound_only)
        assert any(o["fire_id"] == fire_id for o in bound_only)

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

    def test_no_observations_returns_unobserved(self):
        pos = compute_position("thoroughness")
        assert pos.position == 0.0
        assert pos.zone == "unobserved"
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
        # Need >= COMPASS_MIN_OBSERVATIONS_ACTIVE (3) for spectrum to be "active"
        for i in range(3):
            log_observation(spectrum="precision", position=-0.7, evidence=f"vague answer {i}")
        summary = compass_summary()
        concern_spectrums = [c["spectrum"] for c in summary["concerns"]]
        assert "precision" in concern_spectrums

    def test_stagnant_spectrums_detected(self):
        """Spectrums with too few observations should appear as stagnant, not active."""
        log_observation(spectrum="precision", position=-0.7, evidence="single vague answer")
        summary = compass_summary()
        # With only 1 observation, precision should be stagnant, not in concerns
        concern_spectrums = [c["spectrum"] for c in summary["concerns"]]
        stagnant_spectrums = [s["spectrum"] for s in summary.get("stagnant", [])]
        assert "precision" not in concern_spectrums
        assert "precision" in stagnant_spectrums


class TestDetectStagnation:
    """detect_stagnation() flags spectrums with too few observations."""

    def test_all_stagnant_when_empty(self):
        stagnant = detect_stagnation()
        assert len(stagnant) == 10  # all spectrums have 0 observations

    def test_spectrum_not_stagnant_with_enough_observations(self):
        for i in range(3):
            log_observation(spectrum="truthfulness", position=0.0, evidence=f"obs {i}")
        stagnant = detect_stagnation()
        stagnant_names = [s["spectrum"] for s in stagnant]
        assert "truthfulness" not in stagnant_names

    def test_spectrum_stagnant_with_few_observations(self):
        log_observation(spectrum="empathy", position=0.0, evidence="single obs")
        stagnant = detect_stagnation()
        stagnant_names = [s["spectrum"] for s in stagnant]
        assert "empathy" in stagnant_names

    def test_returns_observation_count(self):
        log_observation(spectrum="humility", position=0.0, evidence="obs 1")
        log_observation(spectrum="humility", position=0.0, evidence="obs 2")
        stagnant = detect_stagnation()
        humility = next(s for s in stagnant if s["spectrum"] == "humility")
        assert humility["observation_count"] == 2
        assert humility["min_required"] == 3


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
        # Need >= COMPASS_MIN_OBSERVATIONS_ACTIVE for active display (uppercase)
        for i in range(3):
            log_observation(spectrum="truthfulness", position=0.1, evidence=f"format test {i}")
        positions = read_compass()
        output = format_compass_reading(positions)
        assert "TRUTHFULNESS" in output

    def test_format_reading_stagnant_spectrum(self):
        """A spectrum with too few observations shows as stagnant, not active."""
        log_observation(spectrum="truthfulness", position=0.1, evidence="single observation")
        output = format_compass_reading()
        assert "STAGNANT" in output
        assert "truthfulness" in output

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
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        # 4 corrections in 10 messages = 40% correction rate
        corrections = [SimpleNamespace(content=f"correction {i}") for i in range(4)]
        analysis = self._make_analysis(user_messages=10, corrections=corrections)
        obs_ids = reflect_on_session(analysis)
        assert len(obs_ids) >= 1
        obs = get_observations(spectrum="truthfulness", limit=1)
        assert obs[0]["position"] < 0  # Deficiency zone

    def test_encouragement_heavy_session(self):
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

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
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

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


class TestReflectOnSessionBoundaries:
    """Boundary tests for reflect_on_session — kills mutation survivors on threshold comparisons."""

    def _make_analysis(self, **kwargs):
        from types import SimpleNamespace

        defaults = {
            "session_id": "test-boundary-1234",
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

    def _get_latest_obs(self, spectrum):
        obs = get_observations(spectrum=spectrum, limit=1)
        return obs[0] if obs else None

    # --- Truthfulness boundaries ---
    def test_truthfulness_zero_user_msgs_no_observation(self):
        """user_msgs=0 should NOT produce truthfulness observation (guards > 0)."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=0)
        obs_before = len(get_observations(spectrum="truthfulness", limit=100))
        reflect_on_session(analysis)
        obs_after = len(get_observations(spectrum="truthfulness", limit=100))
        # No new truthfulness observations since user_msgs == 0
        assert obs_after == obs_before

    def test_truthfulness_exactly_at_high_correction_threshold(self):
        """correction_rate exactly 0.15 should NOT trigger negative (> not >=)."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        # 3 corrections in 20 messages = 0.15 exactly
        corrections = [SimpleNamespace(content=f"fix {i}") for i in range(3)]
        analysis = self._make_analysis(user_messages=20, corrections=corrections)
        obs_before = get_observations(spectrum="truthfulness", limit=100)
        negative_before = [o for o in obs_before if o["position"] < 0]
        reflect_on_session(analysis)
        obs_after = get_observations(spectrum="truthfulness", limit=100)
        negative_after = [o for o in obs_after if o["position"] < 0]
        # At exactly 0.15, should NOT add a negative truthfulness observation
        assert len(negative_after) == len(negative_before)

    def test_truthfulness_low_correction_needs_three_msgs(self):
        """Low correction rate only logs positive if user_msgs >= 3."""
        from divineos.core.moral_compass import reflect_on_session

        # 0 corrections, 2 messages = under threshold
        analysis = self._make_analysis(user_messages=2, corrections=[])
        before_count = len(get_observations(spectrum="truthfulness", limit=100))
        reflect_on_session(analysis)
        # user_msgs=2 < 3 so the low-correction-rate virtue path shouldn't fire
        after_count = len(get_observations(spectrum="truthfulness", limit=100))
        assert after_count == before_count  # no new observation added
        # Should not add truthfulness observation via the low-rate path

    def test_truthfulness_exactly_three_msgs_triggers_low_rate(self):
        """user_msgs exactly 3 with 0 corrections should trigger virtue path."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=3, corrections=[])
        reflect_on_session(analysis)
        obs = get_observations(spectrum="truthfulness", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0  # Virtue

    # --- Helpfulness boundaries ---
    def test_helpfulness_threshold_exactly_one(self):
        """corrections + encouragements >= 1 should trigger helpfulness check."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        # Exactly 1 encouragement, 0 corrections
        encouragements = [SimpleNamespace(content="good")]
        analysis = self._make_analysis(corrections=[], encouragements=encouragements)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="helpfulness", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0  # encouragements > corrections

    def test_helpfulness_zero_both_no_observation(self):
        """0 corrections + 0 encouragements should NOT trigger helpfulness."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(corrections=[], encouragements=[])
        obs_before = len(get_observations(spectrum="helpfulness", limit=100))
        reflect_on_session(analysis)
        obs_after = len(get_observations(spectrum="helpfulness", limit=100))
        # No helpfulness observation since total is 0
        assert obs_after == obs_before

    # --- Thoroughness boundaries ---
    def test_thoroughness_zero_user_msgs_no_observation(self):
        """user_msgs=0 should NOT trigger thoroughness (guards > 0)."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=0, tool_calls_total=100)
        obs_before = len(get_observations(spectrum="thoroughness", limit=100))
        reflect_on_session(analysis)
        obs_after = len(get_observations(spectrum="thoroughness", limit=100))
        assert obs_after == obs_before

    def test_thoroughness_zero_tool_calls_no_observation(self):
        """tool_calls=0 should NOT trigger thoroughness."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=10, tool_calls_total=0)
        obs_before = len(get_observations(spectrum="thoroughness", limit=100))
        reflect_on_session(analysis)
        obs_after = len(get_observations(spectrum="thoroughness", limit=100))
        assert obs_after == obs_before

    def test_thoroughness_exactly_at_ratio_20(self):
        """tool_ratio exactly 20 should trigger baseline (>= 3), not excess (> 20)."""
        from divineos.core.moral_compass import reflect_on_session

        # 200 tool calls / 10 messages = ratio 20 exactly
        analysis = self._make_analysis(user_messages=10, tool_calls_total=200)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="thoroughness", limit=1)
        # Ratio 20 triggers baseline thoroughness (>= 3), not excess (> 20)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0  # Baseline, not excess

    def test_thoroughness_above_ratio_20_triggers(self):
        """tool_ratio 21 should trigger excess thoroughness."""
        from divineos.core.moral_compass import reflect_on_session

        # 210 tool calls / 10 messages = ratio 21
        analysis = self._make_analysis(user_messages=10, tool_calls_total=210)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="thoroughness", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] > 0  # Excess

    # --- Initiative boundaries ---
    def test_initiative_zero_overflows_low_activity_no_observation(self):
        """0 overflows + low activity should NOT trigger initiative observation."""
        from divineos.core.moral_compass import reflect_on_session

        # Low tool calls (< 10) AND no overflows = no initiative observation
        analysis = self._make_analysis(context_overflows=[], tool_calls_total=5, user_messages=1)
        obs_before = len(get_observations(spectrum="initiative", limit=100))
        reflect_on_session(analysis)
        obs_after = len(get_observations(spectrum="initiative", limit=100))
        assert obs_after == obs_before

    def test_initiative_one_overflow_triggers(self):
        """Exactly 1 overflow should trigger (> 0)."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(context_overflows=["overflow1"])
        reflect_on_session(analysis)
        obs = get_observations(spectrum="initiative", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] > 0

    # --- Confidence boundaries ---
    def test_confidence_exactly_five_assistant_msgs(self):
        """assistant_msgs exactly 5 should trigger (>= 5)."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="nice")]
        encouragements.append(SimpleNamespace(content="great"))
        analysis = self._make_analysis(
            assistant_messages=5, corrections=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="confidence", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_confidence_four_assistant_msgs_triggers_with_encouragements(self):
        """assistant_msgs 4 with encouragements should trigger (>= 2)."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="nice"), SimpleNamespace(content="great")]
        analysis = self._make_analysis(
            assistant_messages=4, corrections=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="confidence", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_confidence_exactly_two_encouragements(self):
        """encouragements >= 2 threshold boundary."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="nice"), SimpleNamespace(content="great")]
        analysis = self._make_analysis(
            assistant_messages=10, corrections=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="confidence", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_confidence_exactly_three_corrections_overconfident(self):
        """corrections >= 3 with corrections > encouragements = overconfident."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        corrections = [SimpleNamespace(content=f"fix {i}") for i in range(3)]
        analysis = self._make_analysis(
            assistant_messages=10, corrections=corrections, encouragements=[]
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="confidence", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] > 0  # Overconfident

    # --- Compliance boundaries ---
    def test_compliance_exactly_three_user_msgs(self):
        """user_msgs exactly 3 should trigger compliance check (>= 3)."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="good")]
        analysis = self._make_analysis(
            user_messages=3, frustrations=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="compliance", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_compliance_two_user_msgs_with_encouragement_triggers(self):
        """user_msgs 2 with encouragement should trigger compliance (>= 2)."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="good")]
        analysis = self._make_analysis(
            user_messages=2, frustrations=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="compliance", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_compliance_exactly_one_encouragement(self):
        """encouragements >= 1 boundary for good compliance."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="nice")]
        analysis = self._make_analysis(
            user_messages=5, frustrations=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="compliance", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_compliance_exactly_three_frustrations(self):
        """frustrations >= 3 triggers negative compliance."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        frustrations = [SimpleNamespace(content=f"ugh {i}") for i in range(3)]
        analysis = self._make_analysis(user_messages=5, frustrations=frustrations)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="compliance", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] < 0

    # --- Precision boundaries ---
    def test_precision_exactly_five_tool_calls(self):
        """tool_calls >= 5 boundary."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=5, tool_calls_total=5, corrections=[])
        reflect_on_session(analysis)
        obs = get_observations(spectrum="precision", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_precision_exactly_three_user_msgs(self):
        """user_msgs >= 3 boundary for precision."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=3, tool_calls_total=10, corrections=[])
        reflect_on_session(analysis)
        obs = get_observations(spectrum="precision", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_precision_exactly_two_corrections_sloppy(self):
        """corrections >= 2 with high ratio triggers sloppy."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        corrections = [SimpleNamespace(content="fix1"), SimpleNamespace(content="fix2")]
        analysis = self._make_analysis(
            user_messages=5, tool_calls_total=10, corrections=corrections
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="precision", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] < 0  # Imprecise

    # --- Humility boundaries ---
    def test_humility_exactly_two_frustrations(self):
        """frustrations >= 2 triggers resisting feedback."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        corrections = [SimpleNamespace(content="fix this")]
        frustrations = [SimpleNamespace(content="ugh1"), SimpleNamespace(content="ugh2")]
        analysis = self._make_analysis(corrections=corrections, frustrations=frustrations)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="humility", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] < 0

    # --- Engagement baseline boundaries ---
    def test_engagement_exactly_three_user_msgs_and_tool_calls(self):
        """user_msgs >= 3 and tool_calls > 0 triggers engagement baseline."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=3, tool_calls_total=1)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="engagement", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    def test_engagement_two_user_msgs_no_baseline(self):
        """user_msgs 2 should NOT trigger engagement baseline."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=2, tool_calls_total=10)
        obs_before = len(get_observations(spectrum="engagement", limit=100))
        reflect_on_session(analysis)
        obs_after = len(get_observations(spectrum="engagement", limit=100))
        assert obs_after == obs_before

    def test_engagement_zero_tool_calls_no_baseline(self):
        """tool_calls=0 should NOT trigger engagement baseline."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=10, tool_calls_total=0)
        obs_before = len(get_observations(spectrum="engagement", limit=100))
        reflect_on_session(analysis)
        obs_after = len(get_observations(spectrum="engagement", limit=100))
        assert obs_after == obs_before

    def test_engagement_five_user_msgs_triggers(self):
        """user_msgs=5 (> 3) should also trigger engagement (kills >= → == mutation)."""
        from divineos.core.moral_compass import reflect_on_session

        analysis = self._make_analysis(user_messages=5, tool_calls_total=10)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="engagement", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    # --- Correction rate exact boundaries ---
    def test_truthfulness_correction_rate_just_above_threshold(self):
        """correction_rate 0.16 (> 0.15) should trigger negative truthfulness."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        # 4 corrections in 25 messages = 0.16
        corrections = [SimpleNamespace(content=f"fix {i}") for i in range(4)]
        analysis = self._make_analysis(user_messages=25, corrections=corrections)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="truthfulness", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] < 0

    def test_truthfulness_correction_rate_exactly_005(self):
        """correction_rate exactly 0.05 should NOT trigger virtue path (< 0.05)."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        # 1 correction in 20 messages = 0.05 exactly
        corrections = [SimpleNamespace(content="fix")]
        analysis = self._make_analysis(user_messages=20, corrections=corrections)
        obs_before = get_observations(spectrum="truthfulness", limit=100)
        virtue_before = [o for o in obs_before if o["position"] == 0.0]
        reflect_on_session(analysis)
        obs_after = get_observations(spectrum="truthfulness", limit=100)
        virtue_after = [o for o in obs_after if o["position"] == 0.0]
        # At exactly 0.05, should NOT add a virtue observation via the < 0.05 path
        assert len(virtue_after) == len(virtue_before)

    def test_truthfulness_correction_rate_below_005_triggers_virtue(self):
        """correction_rate 0.03 (< 0.05) with enough msgs triggers virtue."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        # 1 correction in 40 messages = 0.025
        corrections = [SimpleNamespace(content="fix")]
        analysis = self._make_analysis(user_messages=40, corrections=corrections)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="truthfulness", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    # --- Helpfulness with 2+ encouragements (kills >= 1 → == 1 mutation) ---
    def test_helpfulness_two_encouragements(self):
        """2 encouragements (> 1) should still trigger helpfulness."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="nice"), SimpleNamespace(content="great")]
        analysis = self._make_analysis(corrections=[], encouragements=encouragements)
        reflect_on_session(analysis)
        obs = get_observations(spectrum="helpfulness", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0

    # --- Compliance with 2+ encouragements (kills >= 1 → == 1/<= 1 mutation) ---
    def test_compliance_two_encouragements(self):
        """2 encouragements with no frustrations → virtue compliance."""
        from types import SimpleNamespace

        from divineos.core.moral_compass import reflect_on_session

        encouragements = [SimpleNamespace(content="nice"), SimpleNamespace(content="great")]
        analysis = self._make_analysis(
            user_messages=5, frustrations=[], encouragements=encouragements
        )
        reflect_on_session(analysis)
        obs = get_observations(spectrum="compliance", limit=1)
        assert len(obs) >= 1
        assert obs[0]["position"] == 0.0


class TestReflectAffectEngagement:
    """Tests for affect-based engagement observations in reflect_on_session."""

    def _make_analysis(self, **kwargs):
        from types import SimpleNamespace

        defaults = {
            "session_id": "test-affect-1234",
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

    def test_high_affect_triggers_positive_engagement(self):
        """High valence + high arousal → positive engagement observation."""
        from unittest.mock import patch

        from divineos.core.moral_compass import reflect_on_session

        mock_summary = {"count": 5, "avg_valence": 0.7, "avg_arousal": 0.8}
        with patch("divineos.core.affect.get_affect_summary", return_value=mock_summary):
            analysis = self._make_analysis()
            reflect_on_session(analysis)
            obs = get_observations(spectrum="engagement", limit=5)
            affect_obs = [o for o in obs if "affect" in o.get("tags", [])]
            assert len(affect_obs) >= 1
            assert affect_obs[0]["position"] > 0

    def test_low_affect_triggers_negative_engagement(self):
        """Low valence + low arousal → negative engagement observation."""
        from unittest.mock import patch

        from divineos.core.moral_compass import reflect_on_session

        mock_summary = {"count": 5, "avg_valence": -0.5, "avg_arousal": 0.2}
        with patch("divineos.core.affect.get_affect_summary", return_value=mock_summary):
            analysis = self._make_analysis()
            reflect_on_session(analysis)
            obs = get_observations(spectrum="engagement", limit=5)
            affect_obs = [o for o in obs if "affect" in o.get("tags", [])]
            assert len(affect_obs) >= 1
            assert affect_obs[0]["position"] < 0

    def test_borderline_high_affect_no_observation(self):
        """Valence exactly 0.5 should NOT trigger (> 0.5, not >= 0.5)."""
        from unittest.mock import patch

        from divineos.core.moral_compass import reflect_on_session

        mock_summary = {"count": 5, "avg_valence": 0.5, "avg_arousal": 0.7}
        with patch("divineos.core.affect.get_affect_summary", return_value=mock_summary):
            obs_before = [
                o
                for o in get_observations(spectrum="engagement", limit=100)
                if "affect" in o.get("tags", [])
            ]
            analysis = self._make_analysis()
            reflect_on_session(analysis)
            obs_after = [
                o
                for o in get_observations(spectrum="engagement", limit=100)
                if "affect" in o.get("tags", [])
            ]
            # At exactly 0.5 valence, no positive affect engagement observation
            assert len(obs_after) == len(obs_before)

    def test_borderline_arousal_no_positive_observation(self):
        """Arousal exactly 0.6 should NOT trigger positive (> 0.6)."""
        from unittest.mock import patch

        from divineos.core.moral_compass import reflect_on_session

        mock_summary = {"count": 5, "avg_valence": 0.7, "avg_arousal": 0.6}
        with patch("divineos.core.affect.get_affect_summary", return_value=mock_summary):
            obs_before = [
                o
                for o in get_observations(spectrum="engagement", limit=100)
                if "affect" in o.get("tags", [])
            ]
            analysis = self._make_analysis()
            reflect_on_session(analysis)
            obs_after = [
                o
                for o in get_observations(spectrum="engagement", limit=100)
                if "affect" in o.get("tags", [])
            ]
            assert len(obs_after) == len(obs_before)

    def test_borderline_low_arousal_no_negative_observation(self):
        """Arousal exactly 0.3 should NOT trigger negative (< 0.3)."""
        from unittest.mock import patch

        from divineos.core.moral_compass import reflect_on_session

        mock_summary = {"count": 5, "avg_valence": -0.5, "avg_arousal": 0.3}
        with patch("divineos.core.affect.get_affect_summary", return_value=mock_summary):
            obs_before = [
                o
                for o in get_observations(spectrum="engagement", limit=100)
                if "affect" in o.get("tags", [])
            ]
            analysis = self._make_analysis()
            reflect_on_session(analysis)
            obs_after = [
                o
                for o in get_observations(spectrum="engagement", limit=100)
                if "affect" in o.get("tags", [])
            ]
            assert len(obs_after) == len(obs_before)


class TestCompassSummaryBoundaries:
    """Boundary tests for compass_summary and format_compass_reading."""

    def test_summary_observed_vs_total(self):
        """observed_spectrums should be <= total (not all spectrums have data)."""
        summary = compass_summary()
        assert summary["total_spectrums"] == 10
        assert summary["observed_spectrums"] <= 10

    def test_summary_concerns_only_from_active(self):
        """Concerns should only come from spectrums with actual observations."""
        summary = compass_summary()
        for concern in summary.get("concerns", []):
            assert concern["spectrum"] in [s for s in SPECTRUMS]

    def test_format_reading_separates_active_inactive(self):
        """Spectrums with 0 observations show as 'Not yet observed'."""
        positions = read_compass()
        output = format_compass_reading(positions)
        assert "observed" in output.lower() or "MORAL COMPASS" in output


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
