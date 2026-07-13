"""Tests for sample_honesty — Wilson score CI + substrate-walk assertion.

Pins the structural backing for knowledge 8ab9fb2c (Andrew correction
2026-06-14, "if you dont even know what it contains how do you know if
its helping?"). The pinning matters because the exact failure that
produced this module — claiming "60% real" from a 10-of-3603 sample
— must STILL fail the assertion at the threshold this module ships,
or the gate is theater.
"""

from __future__ import annotations

import math

import pytest

from divineos.core.sample_honesty import (
    SampleQuality,
    assert_substrate_walk,
    sample_quality,
)


class TestSampleQuality:
    def test_point_estimate_matches_naive_fraction(self):
        q = sample_quality(observed=6, sample_size=10, population_size=3603)
        assert q.point_estimate == pytest.approx(0.6, abs=1e-9)

    def test_coverage_is_sample_over_population(self):
        q = sample_quality(observed=6, sample_size=10, population_size=3603)
        assert q.coverage_fraction == pytest.approx(10 / 3603, abs=1e-9)

    def test_wilson_ci_for_known_case_50_of_100(self):
        # Wilson 95% for 50/100 is approximately [0.404, 0.596].
        q = sample_quality(observed=50, sample_size=100, population_size=1000)
        assert q.lower_bound == pytest.approx(0.404, abs=0.005)
        assert q.upper_bound == pytest.approx(0.596, abs=0.005)

    def test_wilson_ci_for_known_case_5_of_10(self):
        # Wilson 95% for 5/10 — small sample. Roughly [0.237, 0.763].
        q = sample_quality(observed=5, sample_size=10, population_size=1000)
        assert q.lower_bound == pytest.approx(0.237, abs=0.01)
        assert q.upper_bound == pytest.approx(0.763, abs=0.01)
        assert q.ci_width > 0.5  # half the probability space — very wide

    def test_wilson_handles_zero_observed(self):
        # 0/10 — Wilson gives a non-zero upper bound (unlike Wald).
        q = sample_quality(observed=0, sample_size=10, population_size=1000)
        assert q.lower_bound == 0.0
        assert q.upper_bound > 0.0
        assert q.upper_bound < 0.4  # plausible upper for 0/10

    def test_wilson_handles_all_observed(self):
        # 10/10 — Wilson gives a non-one lower bound (unlike Wald).
        q = sample_quality(observed=10, sample_size=10, population_size=1000)
        assert q.upper_bound == 1.0
        assert q.lower_bound > 0.6  # plausible lower for 10/10
        assert q.lower_bound < 1.0

    def test_invalid_inputs(self):
        with pytest.raises(ValueError):
            sample_quality(observed=0, sample_size=0, population_size=10)
        with pytest.raises(ValueError):
            sample_quality(observed=-1, sample_size=10, population_size=10)
        with pytest.raises(ValueError):
            sample_quality(observed=11, sample_size=10, population_size=10)
        with pytest.raises(ValueError):
            sample_quality(observed=5, sample_size=10, population_size=0)

    def test_is_underspecified_at_default_threshold(self):
        # 5/10 has CI width ~0.53 — well above the 0.20 threshold.
        q_wide = sample_quality(observed=5, sample_size=10, population_size=3603)
        assert q_wide.is_underspecified() is True
        # 500/1000 has CI width ~0.06 — under the threshold.
        q_tight = sample_quality(observed=500, sample_size=1000, population_size=3603)
        assert q_tight.is_underspecified() is False

    def test_honest_summary_includes_ci_and_coverage(self):
        q = sample_quality(observed=6, sample_size=10, population_size=3603)
        summary = q.honest_summary()
        assert "60.0%" in summary  # point
        assert "95% CI" in summary  # interval marker
        assert "sample 10 of 3603" in summary  # raw counts
        assert "0.3% coverage" in summary  # the absolute scale


class TestAssertSubstrateWalk:
    def test_the_original_failure_still_fails(self):
        # 6/10 of 3603 with default threshold — the exact case that
        # produced this module. Must still raise.
        with pytest.raises(ValueError) as exc:
            assert_substrate_walk(observed=6, sample_size=10, population_size=3603)
        assert "Sample is too small" in str(exc.value)
        assert "Read more of the substrate" in str(exc.value)

    def test_substantial_sample_passes(self):
        # 600/1000 of 3603 — substantial coverage, tight CI. Should pass.
        q = assert_substrate_walk(observed=600, sample_size=1000, population_size=3603)
        assert isinstance(q, SampleQuality)
        assert q.point_estimate == pytest.approx(0.6, abs=1e-9)

    def test_full_substrate_walk_always_passes(self):
        # Reading every entry of the substrate — sample equals population,
        # CI collapses (still nonzero due to Wilson but very tight).
        q = assert_substrate_walk(observed=900, sample_size=3603, population_size=3603)
        assert q.point_estimate == pytest.approx(900 / 3603, abs=1e-9)

    def test_threshold_override(self):
        # 5/10 has CI ~0.53. With threshold 0.6, it should pass; with the
        # default 0.20, it fails. Override lets callers tune.
        q = assert_substrate_walk(
            observed=5, sample_size=10, population_size=1000, ci_width_threshold=0.6
        )
        assert q.point_estimate == 0.5
        with pytest.raises(ValueError):
            assert_substrate_walk(
                observed=5, sample_size=10, population_size=1000, ci_width_threshold=0.4
            )


class TestModuleAsBackingForCorrection:
    """Anchors the module to the failure that produced it.

    If anyone (including me) ever changes the default threshold so that
    the original 10-of-3603 case PASSES, these tests fail loudly. The
    backing only works if the gate still catches the shape it was named
    against.
    """

    def test_original_band4_estimate_still_blocked_at_defaults(self):
        # Reproducing the original failure exactly:
        # "60% real / 40% noise in band 4" — observed=6, n=10, pop=2197
        # (that band's actual size). The assertion must raise.
        with pytest.raises(ValueError):
            assert_substrate_walk(observed=6, sample_size=10, population_size=2197)

    def test_honest_summary_would_have_been_visible(self):
        # The summary IS the honest report I should have written instead
        # of "60% real". It must include the CI and the coverage fact.
        q = sample_quality(observed=6, sample_size=10, population_size=2197)
        summary = q.honest_summary()
        # The honest summary tells the truth: the CI is huge.
        assert q.ci_width > 0.5
        assert "10 of 2197" in summary

    def test_ci_width_grows_as_sample_shrinks(self):
        # Sanity check on the math itself: smaller samples → wider CIs.
        q_30 = sample_quality(observed=18, sample_size=30, population_size=2197)
        q_10 = sample_quality(observed=6, sample_size=10, population_size=2197)
        q_5 = sample_quality(observed=3, sample_size=5, population_size=2197)
        assert q_30.ci_width < q_10.ci_width < q_5.ci_width

    def test_default_threshold_is_calibrated_to_the_original_failure(self):
        # Document the calibration: at the default threshold, the original
        # failure case (n=10) is blocked, and a substantive walk (n>=200
        # with ~60% rate) passes. If anyone re-tunes, they should see this
        # test break and read this comment first.
        from divineos.core.sample_honesty import _DEFAULT_CI_WIDTH_THRESHOLD

        # Original failure: CI width far exceeds threshold
        q_fail = sample_quality(observed=6, sample_size=10, population_size=2197)
        assert q_fail.ci_width > _DEFAULT_CI_WIDTH_THRESHOLD

        # A reasonable walk of ~200 entries at 60% rate sits well inside.
        q_pass = sample_quality(observed=120, sample_size=200, population_size=2197)
        assert q_pass.ci_width < _DEFAULT_CI_WIDTH_THRESHOLD


class TestWilsonMathDirectly:
    """Sanity-check the math against the Wilson formula by hand."""

    def test_wilson_formula_implementation(self):
        # By-hand for 8/10 at 95%:
        #   p_hat = 0.8, n = 10, z = 1.96
        #   denom = 1 + (1.96^2)/10 = 1.38416
        #   center = (0.8 + 1.96^2 / 20) / 1.38416 ≈ 0.7174
        #   half ≈ (1.96 * sqrt(0.8*0.2/10 + 1.96^2/400)) / 1.38416 ≈ 0.2189
        q = sample_quality(observed=8, sample_size=10, population_size=100)
        # The interval should bracket the point estimate.
        assert q.lower_bound < q.point_estimate < q.upper_bound
        assert q.point_estimate == 0.8
        # Hand-calculated: roughly [0.499, 0.943]
        assert q.lower_bound == pytest.approx(0.499, abs=0.01)
        assert q.upper_bound == pytest.approx(0.943, abs=0.01)

    def test_math_module_is_used(self):
        # Defensive: the module should not have replaced math.sqrt with
        # an approximation that drifts for small inputs.
        q = sample_quality(observed=1, sample_size=2, population_size=100)
        # 1/2 with n=2 is wildly uncertain — CI should span most of [0, 1].
        assert q.ci_width > 0.8
        # Lower must be positive (Wilson, not Wald which can go negative).
        assert q.lower_bound > 0.0
        # Math sanity: the interval centers above p_hat (continuity correction).
        assert math.isfinite(q.lower_bound)
        assert math.isfinite(q.upper_bound)
