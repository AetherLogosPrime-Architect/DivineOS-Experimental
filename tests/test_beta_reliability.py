"""Tests for Beta-distribution reliability primitive (claim e6cbd14d)."""

from __future__ import annotations

import math

import pytest

from divineos.core.reliability.beta import (
    DEFAULT_PRIOR_ALPHA,
    DEFAULT_PRIOR_BETA,
    BetaReliability,
)


class TestConstruction:
    def test_default_prior(self) -> None:
        b = BetaReliability()
        assert b.alpha == DEFAULT_PRIOR_ALPHA
        assert b.beta == DEFAULT_PRIOR_BETA
        assert b.mean == 0.5

    def test_custom_prior(self) -> None:
        b = BetaReliability(alpha=8, beta=2, prior_alpha=8, prior_beta=2)
        assert b.mean == 0.8

    def test_zero_alpha_rejected(self) -> None:
        with pytest.raises(ValueError):
            BetaReliability(alpha=0, beta=2)

    def test_negative_beta_rejected(self) -> None:
        with pytest.raises(ValueError):
            BetaReliability(alpha=2, beta=-1)


class TestPointEstimate:
    def test_balanced(self) -> None:
        assert BetaReliability(alpha=2, beta=2).mean == 0.5

    def test_skewed_high(self) -> None:
        b = BetaReliability(alpha=8, beta=2)
        assert b.mean == 0.8

    def test_skewed_low(self) -> None:
        b = BetaReliability(alpha=1, beta=9)
        assert b.mean == 0.1


class TestUncertainty:
    def test_variance_narrows_with_sample_size(self) -> None:
        # Both have mean 0.5; the one with more observations has lower variance
        small = BetaReliability(alpha=2, beta=2)
        large = BetaReliability(alpha=200, beta=200)
        assert large.variance < small.variance

    def test_stddev_matches_sqrt_variance(self) -> None:
        b = BetaReliability(alpha=10, beta=5)
        assert math.isclose(b.stddev, math.sqrt(b.variance))

    def test_sample_count_default_is_zero(self) -> None:
        # Default prior means no observations seen yet
        b = BetaReliability()
        assert b.sample_count == 0

    def test_sample_count_grows_with_updates(self) -> None:
        b = BetaReliability().update_success(5).update_failure(3)
        assert b.sample_count == 8


class TestCredibleInterval:
    def test_default_level(self) -> None:
        b = BetaReliability(alpha=20, beta=20)
        low, high = b.credible_interval()
        assert 0 <= low < b.mean < high <= 1

    def test_higher_level_wider_interval(self) -> None:
        b = BetaReliability(alpha=20, beta=20)
        low_90, high_90 = b.credible_interval(0.90)
        low_99, high_99 = b.credible_interval(0.99)
        assert (high_99 - low_99) > (high_90 - low_90)

    def test_invalid_level_rejected(self) -> None:
        b = BetaReliability()
        with pytest.raises(ValueError):
            b.credible_interval(0.0)
        with pytest.raises(ValueError):
            b.credible_interval(1.5)

    def test_more_data_narrower_interval(self) -> None:
        small = BetaReliability(alpha=2, beta=2)
        large = BetaReliability(alpha=100, beta=100)
        small_low, small_high = small.credible_interval()
        large_low, large_high = large.credible_interval()
        assert (large_high - large_low) < (small_high - small_low)


class TestUpdates:
    def test_success_increments_alpha(self) -> None:
        b1 = BetaReliability(alpha=2, beta=2)
        b2 = b1.update_success()
        assert b2.alpha == b1.alpha + 1
        assert b2.beta == b1.beta

    def test_failure_increments_beta(self) -> None:
        b1 = BetaReliability(alpha=2, beta=2)
        b2 = b1.update_failure()
        assert b2.beta == b1.beta + 1
        assert b2.alpha == b1.alpha

    def test_update_count(self) -> None:
        b = BetaReliability(alpha=2, beta=2).update_success(5)
        assert b.alpha == 7

    def test_negative_count_rejected(self) -> None:
        b = BetaReliability()
        with pytest.raises(ValueError):
            b.update_success(-1)
        with pytest.raises(ValueError):
            b.update_failure(-1)

    def test_immutable(self) -> None:
        # Frozen dataclass — assignment raises
        b = BetaReliability()
        with pytest.raises(Exception):
            b.alpha = 100  # type: ignore[misc]

    def test_updates_preserve_prior(self) -> None:
        # Prior values must be preserved across updates so sample_count
        # remains correct.
        b = BetaReliability(alpha=8, beta=2, prior_alpha=8, prior_beta=2)
        b2 = b.update_success(3).update_failure(1)
        assert b2.prior_alpha == 8
        assert b2.prior_beta == 2
        assert b2.sample_count == 4


class TestSerialization:
    def test_round_trip(self) -> None:
        b1 = BetaReliability(alpha=15, beta=5, prior_alpha=2, prior_beta=2)
        d = b1.to_dict()
        b2 = BetaReliability.from_dict(d)
        assert b2 == b1

    def test_from_dict_missing_prior_uses_default(self) -> None:
        b = BetaReliability.from_dict({"alpha": 10, "beta": 5})
        assert b.prior_alpha == DEFAULT_PRIOR_ALPHA
        assert b.prior_beta == DEFAULT_PRIOR_BETA


class TestFromCorroborations:
    def test_supporting_only(self) -> None:
        b = BetaReliability.from_corroborations(supporting=5, contradicting=0)
        assert b.alpha == DEFAULT_PRIOR_ALPHA + 5
        assert b.beta == DEFAULT_PRIOR_BETA

    def test_balanced(self) -> None:
        b = BetaReliability.from_corroborations(supporting=10, contradicting=10)
        assert b.mean == 0.5
        assert b.sample_count == 20

    def test_negative_count_rejected(self) -> None:
        with pytest.raises(ValueError):
            BetaReliability.from_corroborations(supporting=-1, contradicting=0)


class TestEpistemicHonesty:
    """Verifies the substantive epistemic claim: confidence has
    confidence-of-confidence. A high-mean low-sample posterior should
    be visibly less certain than a high-mean high-sample posterior.
    """

    def test_two_obs_vs_two_hundred(self) -> None:
        few = BetaReliability().update_success(2)
        many = BetaReliability().update_success(200)
        # Means similar (both pushed high), but...
        # ... uncertainty should be very different
        assert many.stddev < few.stddev / 5
        assert many.sample_count == 200
        assert few.sample_count == 2

    def test_one_contradiction_doesnt_swing_high_sample(self) -> None:
        # The motivating example from the spec: "one bad finding doesn't
        # swing 15% with 200 data points"
        established = BetaReliability().update_success(200)
        challenged = established.update_failure(1)
        delta = abs(established.mean - challenged.mean)
        assert delta < 0.01  # Less than 1% movement
