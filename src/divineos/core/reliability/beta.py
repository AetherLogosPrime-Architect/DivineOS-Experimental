"""Beta-distribution reliability primitive (claim e6cbd14d).

Encodes belief about a 0-1 quantity (e.g. expert reliability,
knowledge truth-probability) as a Beta(α, β) posterior, providing
both point estimate AND uncertainty.

## Why Beta posteriors

Flat-float confidence treats all observations equally: one
contradicting observation moves the value the same as ten consistent
ones. Beta posteriors track *how many observations have informed the
belief*, so confidence has confidence-of-confidence.

* mean = α / (α + β)  — point estimate
* sample_count = (α - prior_α) + (β - prior_β)  — observations seen
* variance = α·β / ((α+β)² · (α+β+1))  — narrows as samples grow

## Prior choice

Default prior Beta(2, 2): mild confidence in center (0.5), not flat
ignorance. This prevents over-confident updates from the first
observation. Per the old-OS spec: "respect initial assumptions as
starting points, not ignorance."

Callers can pass a custom prior if they have stronger initial belief
(e.g. a high-reliability expert seeded with Beta(8, 2) starts at 0.8
mean with the equivalent of 8 implicit successes).

## What this module does NOT do

* Does not migrate existing `knowledge.confidence` field. That's
  Phase 2 work requiring a backfill story.
* Does not depend on numpy or scipy. Pure-Python math; testable in
  isolation. Variance/CI computed analytically, not sampled.
* Does not do online clustering or expert-domain segmentation. One
  Beta posterior per tracked quantity; multiple quantities = multiple
  Beta instances.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any


# Default prior: mild center-confidence, not flat ignorance.
DEFAULT_PRIOR_ALPHA = 2.0
DEFAULT_PRIOR_BETA = 2.0


@dataclass(frozen=True)
class BetaReliability:
    """Beta(α, β) posterior over a 0-1 quantity.

    Frozen so updates produce new instances rather than mutating —
    preserves the prior values for sample-count calculation and makes
    serialization easier.
    """

    alpha: float = DEFAULT_PRIOR_ALPHA
    beta: float = DEFAULT_PRIOR_BETA
    prior_alpha: float = DEFAULT_PRIOR_ALPHA
    prior_beta: float = DEFAULT_PRIOR_BETA

    def __post_init__(self) -> None:
        if self.alpha <= 0 or self.beta <= 0:
            raise ValueError(
                f"Beta parameters must be positive; got alpha={self.alpha}, beta={self.beta}"
            )
        if self.prior_alpha <= 0 or self.prior_beta <= 0:
            raise ValueError(
                f"Prior parameters must be positive; got prior_alpha={self.prior_alpha}, "
                f"prior_beta={self.prior_beta}"
            )

    @property
    def mean(self) -> float:
        """Point estimate: α / (α + β). Range (0, 1)."""
        return self.alpha / (self.alpha + self.beta)

    @property
    def variance(self) -> float:
        """Variance of the Beta distribution.

        var = α·β / ((α+β)² · (α+β+1))

        Narrows as α + β grows — uncertainty decreases with sample size.
        """
        a, b = self.alpha, self.beta
        ab = a + b
        return (a * b) / (ab * ab * (ab + 1.0))

    @property
    def stddev(self) -> float:
        """Standard deviation; same scale as mean."""
        return math.sqrt(self.variance)

    @property
    def sample_count(self) -> float:
        """Effective number of observations seen since the prior.

        sample_count = (α - prior_α) + (β - prior_β)

        High sample_count means the posterior has been informed by many
        observations; the mean carries weight. Low sample_count means
        the posterior is still close to the prior.
        """
        return (self.alpha - self.prior_alpha) + (self.beta - self.prior_beta)

    def credible_interval(self, level: float = 0.90) -> tuple[float, float]:
        """Symmetric credible interval at the given level.

        Computed via mean ± z·stddev (Normal approximation). Adequate
        for moderate sample sizes; for tiny samples (<5) the Beta
        distribution is asymmetric and this approximation under-covers
        in the tails. Real applications can swap in a quantile-based
        interval; for our purposes (briefing-display, expert-weighting)
        the approximation is sufficient and dependency-free.
        """
        if not 0 < level < 1:
            raise ValueError(f"level must be in (0, 1); got {level}")
        # z-scores for common levels: 0.80→1.28, 0.90→1.645, 0.95→1.96
        z_table = {0.80: 1.282, 0.90: 1.645, 0.95: 1.960, 0.99: 2.576}
        z = z_table.get(round(level, 2), 1.645)
        sd = self.stddev
        m = self.mean
        return (max(0.0, m - z * sd), min(1.0, m + z * sd))

    def update_success(self, count: int = 1) -> "BetaReliability":
        """Return a new BetaReliability with α incremented by ``count``.

        A "success" is an observation supporting the tracked belief —
        e.g. an expert's claim was corroborated, a knowledge entry was
        confirmed by independent evidence.
        """
        if count < 0:
            raise ValueError(f"count must be non-negative; got {count}")
        return BetaReliability(
            alpha=self.alpha + count,
            beta=self.beta,
            prior_alpha=self.prior_alpha,
            prior_beta=self.prior_beta,
        )

    def update_failure(self, count: int = 1) -> "BetaReliability":
        """Return a new BetaReliability with β incremented by ``count``.

        A "failure" is an observation against the tracked belief — e.g.
        an expert's claim was contradicted, a knowledge entry was
        refuted by counter-evidence.
        """
        if count < 0:
            raise ValueError(f"count must be non-negative; got {count}")
        return BetaReliability(
            alpha=self.alpha,
            beta=self.beta + count,
            prior_alpha=self.prior_alpha,
            prior_beta=self.prior_beta,
        )

    def to_dict(self) -> dict[str, float]:
        """Serialize for storage (DB column, JSON file, etc.)."""
        return {
            "alpha": self.alpha,
            "beta": self.beta,
            "prior_alpha": self.prior_alpha,
            "prior_beta": self.prior_beta,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BetaReliability":
        """Deserialize from storage; missing prior fields default."""
        return cls(
            alpha=float(data["alpha"]),
            beta=float(data["beta"]),
            prior_alpha=float(data.get("prior_alpha", DEFAULT_PRIOR_ALPHA)),
            prior_beta=float(data.get("prior_beta", DEFAULT_PRIOR_BETA)),
        )

    @classmethod
    def from_corroborations(
        cls,
        supporting: int,
        contradicting: int,
        prior_alpha: float = DEFAULT_PRIOR_ALPHA,
        prior_beta: float = DEFAULT_PRIOR_BETA,
    ) -> "BetaReliability":
        """Build a posterior from observed corroboration counts.

        Useful for migrating existing data with corroboration counts
        into Beta-tracked form. ``supporting`` increments α;
        ``contradicting`` increments β.
        """
        if supporting < 0 or contradicting < 0:
            raise ValueError("supporting/contradicting must be non-negative")
        return cls(
            alpha=prior_alpha + supporting,
            beta=prior_beta + contradicting,
            prior_alpha=prior_alpha,
            prior_beta=prior_beta,
        )
