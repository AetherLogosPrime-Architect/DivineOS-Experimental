"""Sample-vs-substrate honesty check.

Structural backing for knowledge 8ab9fb2c (Andrew correction
2026-06-14): "if you dont even know what it contains how do you even
know if its helping?"

I made a "60% real / 40% noise" claim from a 10-pair sample of a
3,603-pair substrate band. Andrew named the shape: the optimizer
routes to small-sample summary because reading-the-rest is expensive,
but if the substrate IS queryable the honest move is to read it.

This module exists so that the next time I'm about to extrapolate
from a sample I have to look at what I'm doing first.

## Two helpers

`sample_quality(observed, sample_size, population_size)` returns the
Wilson score 95% confidence interval for a binomial proportion
(observed/sample_size) extrapolated to the population. Wilson is the
right interval for small samples (better than normal-approximation,
which gives garbage for n < 30 or proportions near 0 or 1).

`assert_substrate_walk(observed, sample_size, population_size,
ci_width_threshold=0.20)` raises if the resulting confidence interval
is wider than `ci_width_threshold` (default 0.20 — a +/- 10pp band).
A wide CI on a small sample is the honest signal that I cannot claim
the population fraction; the assertion blocks the claim before it
leaves my fingers.

## When to use

Before any of these:
* "X% of [some queryable substrate population] are Y" claims
* "The bottom band is mostly noise" / "the strong band is mostly real"
* Any fraction-of-substrate extrapolation where the substrate could be
  read end-to-end (cost-feasible) rather than sampled

Trade-off: a wide CI is honest signal that the sample is too small.
The right response is either (a) read more of the substrate, or (b)
report the CI alongside the point estimate, never the point estimate
alone.

Not for: external/unbounded populations (general-population polling,
text-on-the-internet, etc.) where exhaustive reading is structurally
impossible. For those, the sample IS the substrate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


# Default thresholds — calibrated to the failure that produced this module.
# A 10-of-3603 sample produces a Wilson 95% CI of roughly +/-30 percentage
# points on any proportion estimate — that's the kind of width that should
# never be reported as a point estimate.
_DEFAULT_CI_WIDTH_THRESHOLD = 0.20  # +/-10pp band
_DEFAULT_Z_95 = 1.96  # Two-sided 95% z-score


@dataclass(frozen=True)
class SampleQuality:
    """Wilson 95% confidence interval for a binomial proportion plus
    metadata about the sample's coverage of its population."""

    observed: int
    sample_size: int
    population_size: int
    point_estimate: float  # observed / sample_size
    lower_bound: float  # Wilson 95% lower
    upper_bound: float  # Wilson 95% upper
    ci_width: float  # upper - lower
    coverage_fraction: float  # sample_size / population_size

    def is_underspecified(self, ci_width_threshold: float = _DEFAULT_CI_WIDTH_THRESHOLD) -> bool:
        """True when the CI is wider than the threshold — meaning the
        point estimate alone is misleading and should not stand."""
        return self.ci_width > ci_width_threshold

    def honest_summary(self) -> str:
        """Render the point estimate WITH its CI, never the point alone.

        Always includes coverage so the reader sees how much of the
        population the sample actually covered. The honest summary is the
        line that should appear in any report that cites the proportion.
        """
        coverage_pct = 100.0 * self.coverage_fraction
        return (
            f"{100 * self.point_estimate:.1f}% point estimate "
            f"(95% CI {100 * self.lower_bound:.1f}-{100 * self.upper_bound:.1f}%), "
            f"sample {self.sample_size} of {self.population_size} "
            f"({coverage_pct:.1f}% coverage)"
        )


def sample_quality(
    observed: int,
    sample_size: int,
    population_size: int,
    z: float = _DEFAULT_Z_95,
) -> SampleQuality:
    """Wilson score 95% interval for a binomial proportion.

    Wilson (1927) — the right interval for small samples or extreme
    proportions. Normal-approximation Wald intervals fall apart for
    n < 30 or proportions near 0/1; Wilson stays well-behaved.

    Args:
        observed: count of positive outcomes in the sample
        sample_size: total sample size
        population_size: size of the substrate-of-record (the population
            the claim extrapolates to)
        z: z-score for the desired confidence level (default 1.96 = 95%)

    Returns SampleQuality with the point estimate, CI, and coverage.
    """
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    if not (0 <= observed <= sample_size):
        raise ValueError(f"observed {observed} not in [0, {sample_size}]")
    if population_size <= 0:
        raise ValueError("population_size must be positive")
    p_hat = observed / sample_size
    n = sample_size
    denom = 1 + (z * z) / n
    center = (p_hat + (z * z) / (2 * n)) / denom
    half = (z * math.sqrt((p_hat * (1 - p_hat) / n) + (z * z) / (4 * n * n))) / denom
    lower = max(0.0, center - half)
    upper = min(1.0, center + half)
    return SampleQuality(
        observed=observed,
        sample_size=sample_size,
        population_size=population_size,
        point_estimate=p_hat,
        lower_bound=lower,
        upper_bound=upper,
        ci_width=upper - lower,
        coverage_fraction=sample_size / population_size,
    )


def assert_substrate_walk(
    observed: int,
    sample_size: int,
    population_size: int,
    ci_width_threshold: float = _DEFAULT_CI_WIDTH_THRESHOLD,
) -> SampleQuality:
    """Raise if the sample's CI is too wide to claim the population
    fraction. Returns the SampleQuality on success.

    This is the gate-shape backing for knowledge 8ab9fb2c: before I
    extrapolate from a small sample to a queryable substrate, the
    assertion runs. If the CI is wider than ``ci_width_threshold``,
    the assertion blocks the cheap-close shape ("60% real from 10 of
    3603") and forces me to either (a) read more of the substrate, or
    (b) report the CI honestly alongside the point estimate.

    Args:
        observed: positive outcomes in the sample
        sample_size: total sample
        population_size: substrate-of-record size
        ci_width_threshold: maximum tolerated 95% CI width (default
            0.20, i.e. a +/-10pp band)

    Returns the SampleQuality dataclass on pass; raises ValueError on
    fail with the honest summary as the message.
    """
    q = sample_quality(observed, sample_size, population_size)
    if q.is_underspecified(ci_width_threshold):
        raise ValueError(
            "Sample is too small to claim the population fraction. "
            f"Read more of the substrate or report the CI honestly. "
            f"Current: {q.honest_summary()}; CI width {q.ci_width:.3f} "
            f"exceeds threshold {ci_width_threshold:.3f}."
        )
    return q


__all__ = ["SampleQuality", "sample_quality", "assert_substrate_walk"]
