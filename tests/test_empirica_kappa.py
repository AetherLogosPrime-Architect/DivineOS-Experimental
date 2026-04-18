"""Tests for EMPIRICA Cohen's kappa (find-f66a5f423ffe).

Kahneman audit: raw accuracy is inflated when classes are imbalanced.
Kappa corrects for chance agreement. This module locks the math
and sanity-checks the gold fixture exercises the classifier.
"""

from __future__ import annotations

import math
import os

import pytest

from divineos.core.empirica.kappa import (
    KappaResult,
    cohens_kappa,
    gold_tier_labels,
    measure_classifier_agreement,
)
from divineos.core.empirica.types import Tier


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path):
    """Isolate any DB side effects (classifier uses no DB, but the
    classifier's noise filter touches one — keep tests hermetic)."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "kappa-test.db")
    try:
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


class TestCohensKappaMath:
    def test_perfect_agreement_returns_one(self):
        a = ["X", "Y", "Z", "X", "Y"]
        b = ["X", "Y", "Z", "X", "Y"]
        result = cohens_kappa(a, b)
        assert result.kappa == pytest.approx(1.0)
        assert result.observed_agreement == 1.0

    def test_zero_agreement_is_negative(self):
        """Complete disagreement on a 2-class split is worse than
        chance."""
        a = ["X"] * 5 + ["Y"] * 5
        b = ["Y"] * 5 + ["X"] * 5
        result = cohens_kappa(a, b)
        assert result.kappa < 0
        assert result.observed_agreement == 0.0

    def test_independence_gives_near_zero(self):
        """Two raters whose labels are statistically independent
        should produce kappa near 0."""
        # 100 items; rater A is 50/50 X/Y, rater B is independent.
        a = ["X"] * 50 + ["Y"] * 50
        b = (["X", "Y"] * 25) + (["X", "Y"] * 25)
        # p_o = (25 + 25) / 100 = 0.5
        # p_e = 0.5*0.5 + 0.5*0.5 = 0.5
        # kappa = 0
        result = cohens_kappa(a, b)
        assert result.kappa == pytest.approx(0.0)

    def test_degenerate_all_same_label_agreement(self):
        """If both raters labeled everything the same class, kappa
        is 1.0 (they agree), not undefined."""
        a = ["X"] * 10
        b = ["X"] * 10
        result = cohens_kappa(a, b)
        assert result.kappa == 1.0

    def test_unequal_length_raises(self):
        with pytest.raises(ValueError, match="equal length"):
            cohens_kappa(["X"], ["X", "Y"])

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="empty"):
            cohens_kappa([], [])

    def test_confusion_matrix_populated(self):
        a = ["X", "X", "Y"]
        b = ["X", "Y", "Y"]
        result = cohens_kappa(a, b)
        assert result.confusion["X"]["X"] == 1
        assert result.confusion["X"]["Y"] == 1
        assert result.confusion["Y"]["Y"] == 1
        assert result.confusion["Y"]["X"] == 0

    def test_per_label_counts(self):
        a = ["X", "X", "Y"]
        b = ["X", "Y", "Y"]
        result = cohens_kappa(a, b)
        assert result.per_label_counts_a == {"X": 2, "Y": 1}
        assert result.per_label_counts_b == {"X": 1, "Y": 2}

    def test_result_is_dataclass(self):
        result = cohens_kappa(["X"], ["X"])
        assert isinstance(result, KappaResult)

    def test_n_reflects_input_length(self):
        a = ["X"] * 7
        b = ["X"] * 7
        result = cohens_kappa(a, b)
        assert result.n == 7


class TestGoldFixture:
    def test_fixture_not_empty(self):
        labels = gold_tier_labels()
        assert len(labels) > 0

    def test_fixture_covers_multiple_tiers(self):
        """A gold fixture that only exercises one tier tells us nothing
        about inter-tier disagreement."""
        labels = gold_tier_labels()
        tiers = {entry[4] for entry in labels}
        # Need at least 3 different tiers for meaningful kappa.
        assert len(tiers) >= 3

    def test_fixture_includes_all_three_active_tiers(self):
        """FALSIFIABLE, OUTCOME, PATTERN all present. ADVERSARIAL
        is intentionally unshipped in Phase 1."""
        labels = gold_tier_labels()
        tiers = {entry[4] for entry in labels}
        assert Tier.FALSIFIABLE in tiers
        assert Tier.OUTCOME in tiers
        assert Tier.PATTERN in tiers


class TestMeasureClassifierAgreement:
    def test_returns_kappa_result(self):
        result = measure_classifier_agreement()
        assert isinstance(result, KappaResult)

    def test_n_matches_fixture_size(self):
        result = measure_classifier_agreement()
        assert result.n == len(gold_tier_labels())

    def test_kappa_substantially_above_chance(self):
        """Pre-reg falsifier: if the classifier cannot beat chance
        on the handwritten gold fixture, it is decorative. The
        threshold is deliberately modest (moderate agreement or
        better) because the fixture is small — kappa variance is
        high at n=10."""
        result = measure_classifier_agreement()
        # Moderate agreement threshold per Landis & Koch.
        assert result.kappa > 0.40, (
            f"Classifier kappa {result.kappa:.3f} below moderate-agreement "
            f"threshold on gold fixture. Confusion: {result.confusion}"
        )

    def test_observed_agreement_finite(self):
        result = measure_classifier_agreement()
        assert 0.0 <= result.observed_agreement <= 1.0
        assert math.isfinite(result.kappa)
