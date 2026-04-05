"""Tests for Signal Trust Tiers — the foundation of honest self-assessment."""

from divineos.core.trust_tiers import (
    SignalTier,
    apply_tier_weight,
    classify_signal,
    classify_source,
    compute_trust_profile,
    tier_weight,
    weighted_confidence_delta,
    weighted_source_bonus,
)


class TestSignalTier:
    """The enum should be usable as both string and enum."""

    def test_tier_values(self) -> None:
        assert SignalTier.MEASURED == "MEASURED"
        assert SignalTier.BEHAVIORAL == "BEHAVIORAL"
        assert SignalTier.SELF_REPORTED == "SELF_REPORTED"

    def test_tier_is_string(self) -> None:
        assert isinstance(SignalTier.MEASURED, str)


class TestTierWeights:
    """MEASURED > BEHAVIORAL > SELF_REPORTED. Always."""

    def test_measured_is_full_weight(self) -> None:
        assert tier_weight(SignalTier.MEASURED) == 1.0

    def test_behavioral_is_middle(self) -> None:
        assert tier_weight(SignalTier.BEHAVIORAL) == 0.7

    def test_self_reported_is_lowest(self) -> None:
        assert tier_weight(SignalTier.SELF_REPORTED) == 0.4

    def test_hierarchy_preserved(self) -> None:
        m = tier_weight(SignalTier.MEASURED)
        b = tier_weight(SignalTier.BEHAVIORAL)
        s = tier_weight(SignalTier.SELF_REPORTED)
        assert m > b > s > 0


class TestClassifySource:
    """Knowledge sources map to the right tiers."""

    def test_corrected_is_measured(self) -> None:
        """User corrections are objective evidence."""
        assert classify_source("CORRECTED") == SignalTier.MEASURED

    def test_demonstrated_is_behavioral(self) -> None:
        """Actions speak louder than words."""
        assert classify_source("DEMONSTRATED") == SignalTier.BEHAVIORAL

    def test_stated_is_self_reported(self) -> None:
        """Someone said it. Could be right, could be wrong."""
        assert classify_source("STATED") == SignalTier.SELF_REPORTED

    def test_synthesized_is_self_reported(self) -> None:
        """I derived it. Only as good as my reasoning."""
        assert classify_source("SYNTHESIZED") == SignalTier.SELF_REPORTED

    def test_inherited_is_behavioral(self) -> None:
        """Seed data is curated, not self-reported."""
        assert classify_source("INHERITED") == SignalTier.BEHAVIORAL

    def test_unknown_defaults_to_self_reported(self) -> None:
        """When in doubt, trust least."""
        assert classify_source("UNKNOWN") == SignalTier.SELF_REPORTED
        assert classify_source("") == SignalTier.SELF_REPORTED


class TestClassifySignal:
    """Named signals map to tiers based on how gameable they are."""

    def test_test_results_are_measured(self) -> None:
        assert classify_signal("test_result") == SignalTier.MEASURED
        assert classify_signal("correction_count") == SignalTier.MEASURED
        assert classify_signal("error_count") == SignalTier.MEASURED

    def test_quality_checks_are_measured(self) -> None:
        assert classify_signal("completeness_score") == SignalTier.MEASURED
        assert classify_signal("correctness_score") == SignalTier.MEASURED
        assert classify_signal("safety_score") == SignalTier.MEASURED

    def test_patterns_are_behavioral(self) -> None:
        assert classify_signal("access_count") == SignalTier.BEHAVIORAL
        assert classify_signal("corroboration_count") == SignalTier.BEHAVIORAL
        assert classify_signal("lesson_occurrence") == SignalTier.BEHAVIORAL

    def test_affect_is_self_reported(self) -> None:
        assert classify_signal("affect_valence") == SignalTier.SELF_REPORTED
        assert classify_signal("affect_arousal") == SignalTier.SELF_REPORTED
        assert classify_signal("self_assessment") == SignalTier.SELF_REPORTED

    def test_unknown_signal_defaults_to_self_reported(self) -> None:
        assert classify_signal("made_up_signal") == SignalTier.SELF_REPORTED


class TestApplyTierWeight:
    """Tier weighting scales scores by trustworthiness."""

    def test_measured_preserves_score(self) -> None:
        assert apply_tier_weight(0.8, SignalTier.MEASURED) == 0.8

    def test_behavioral_reduces_score(self) -> None:
        result = apply_tier_weight(0.8, SignalTier.BEHAVIORAL)
        assert abs(result - 0.56) < 0.001

    def test_self_reported_reduces_most(self) -> None:
        result = apply_tier_weight(0.8, SignalTier.SELF_REPORTED)
        assert abs(result - 0.32) < 0.001

    def test_zero_stays_zero(self) -> None:
        assert apply_tier_weight(0.0, SignalTier.MEASURED) == 0.0
        assert apply_tier_weight(0.0, SignalTier.SELF_REPORTED) == 0.0


class TestWeightedSourceBonus:
    """Source bonuses reflect both information value and trustworthiness."""

    def test_corrected_highest_bonus(self) -> None:
        """Corrections are high value AND high trust."""
        bonus = weighted_source_bonus("CORRECTED")
        assert bonus == 0.10  # 0.10 * 1.0 (MEASURED)

    def test_demonstrated_moderate_bonus(self) -> None:
        bonus = weighted_source_bonus("DEMONSTRATED")
        assert abs(bonus - 0.056) < 0.001  # 0.08 * 0.7 (BEHAVIORAL)

    def test_stated_low_bonus(self) -> None:
        bonus = weighted_source_bonus("STATED")
        assert abs(bonus - 0.024) < 0.001  # 0.06 * 0.4 (SELF_REPORTED)

    def test_corrected_beats_stated(self) -> None:
        """A correction is worth more than a claim."""
        assert weighted_source_bonus("CORRECTED") > weighted_source_bonus("STATED")

    def test_demonstrated_beats_synthesized(self) -> None:
        """Doing beats theorizing."""
        assert weighted_source_bonus("DEMONSTRATED") > weighted_source_bonus("SYNTHESIZED")

    def test_unknown_source_gets_minimal_bonus(self) -> None:
        bonus = weighted_source_bonus("UNKNOWN")
        assert bonus < weighted_source_bonus("INHERITED")


class TestWeightedConfidenceDelta:
    """Confidence adjustments scale by signal trustworthiness."""

    def test_measured_signal_full_delta(self) -> None:
        delta = weighted_confidence_delta(0.1, "test_result")
        assert delta == 0.1

    def test_self_reported_signal_reduced_delta(self) -> None:
        delta = weighted_confidence_delta(0.1, "affect_valence")
        assert abs(delta - 0.04) < 0.001

    def test_negative_delta_also_scaled(self) -> None:
        delta = weighted_confidence_delta(-0.2, "self_assessment")
        assert abs(delta - (-0.08)) < 0.001

    def test_behavioral_signal_middle_delta(self) -> None:
        delta = weighted_confidence_delta(0.1, "lesson_occurrence")
        assert abs(delta - 0.07) < 0.001


class TestComputeTrustProfile:
    """Trust profile reveals how much of the knowledge store is trustworthy."""

    def test_empty_entries(self) -> None:
        profile = compute_trust_profile([])
        assert profile["total"] == 0
        assert profile["trust_score"] == 0.0

    def test_all_measured(self) -> None:
        entries = [{"source": "CORRECTED"} for _ in range(10)]
        profile = compute_trust_profile(entries)
        assert profile["measured_pct"] == 100
        assert profile["trust_score"] == 1.0

    def test_all_self_reported(self) -> None:
        entries = [{"source": "STATED"} for _ in range(10)]
        profile = compute_trust_profile(entries)
        assert profile["self_reported_pct"] == 100
        assert profile["trust_score"] == 0.4

    def test_mixed_profile(self) -> None:
        entries = [
            {"source": "CORRECTED"},  # MEASURED
            {"source": "DEMONSTRATED"},  # BEHAVIORAL
            {"source": "STATED"},  # SELF_REPORTED
        ]
        profile = compute_trust_profile(entries)
        assert profile["total"] == 3
        assert profile["measured_pct"] == 33
        assert profile["behavioral_pct"] == 33
        assert profile["self_reported_pct"] == 33
        # (1.0 + 0.7 + 0.4) / 3 = 0.7
        assert profile["trust_score"] == 0.7

    def test_missing_source_defaults_to_behavioral(self) -> None:
        """Entries without source field default to INHERITED -> BEHAVIORAL."""
        entries = [{"content": "something"}]
        profile = compute_trust_profile(entries)
        assert profile["behavioral_pct"] == 100

    def test_trust_score_reflects_composition(self) -> None:
        """More measured knowledge = higher trust score."""
        mostly_measured = [{"source": "CORRECTED"}] * 8 + [{"source": "STATED"}] * 2
        mostly_stated = [{"source": "CORRECTED"}] * 2 + [{"source": "STATED"}] * 8
        p1 = compute_trust_profile(mostly_measured)
        p2 = compute_trust_profile(mostly_stated)
        assert p1["trust_score"] > p2["trust_score"]
