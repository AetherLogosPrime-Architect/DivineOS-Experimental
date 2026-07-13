"""Math tests for Aria's retriever v1 — Aether's half of the split.

Per pass-3 tests-split-C: Aether writes scaffold + math (composite_score,
tier_weight, recency_multiplier, compute_threshold). Aria writes Q2
assertion coverage + adapter tests when back and consulted.

These tests lock the math invariants that the composite-rank sort and
per-source thresholds depend on. If any of the weights, decay half-life,
or per-source floors drift, these tests fail loudly rather than the
retrieval quality silently degrading.

Test structure follows Aletheia's hash-what-drives rule at the test
layer: cover the invariants that DRIVE the behavior (weights sum to 1,
half-life at 180d, per-source ordering), not just the surface (some
score comes back).
"""

from __future__ import annotations

from divineos.core.memory_linkage_retriever import (
    composite_score,
    compute_threshold,
    recency_multiplier,
    tier_weight,
)


# --- tier_weight (§Q4 tier ordering) ---


def test_tier_weight_constraint_is_1():
    assert tier_weight("constraint") == 1.0


def test_tier_weight_topic_is_0_6():
    assert tier_weight("topic") == 0.6


def test_tier_weight_conditional_is_0():
    """Conditional is state-signal driven, handled by separate detector
    hooks — this retriever should not surface it. Zero weight enforces
    that structurally."""
    assert tier_weight("conditional") == 0.0


def test_tier_weight_ordering_constraint_gt_topic_gt_conditional():
    """The ordering itself is load-bearing — a shift would mean constraint
    items compete equally with topic items, defeating §Q4's whole point."""
    assert tier_weight("constraint") > tier_weight("topic") > tier_weight("conditional")


# --- recency_multiplier (§Q1 exponential decay) ---


def test_recency_zero_days_is_1():
    assert recency_multiplier(0) == 1.0


def test_recency_negative_days_treated_as_fresh():
    """Clock-skew or future-dated items should not get anti-boosted."""
    assert recency_multiplier(-5) == 1.0


def test_recency_half_life_at_180_days():
    """The whole decay-curve is anchored at 180d = 0.5. If that anchor
    moves, the docstring's "a 90-day-old correction still competes with
    a fresh one when similarity is high" property changes silently."""
    value = recency_multiplier(180)
    assert abs(value - 0.5) < 0.01, f"expected ~0.5 at 180d, got {value}"


def test_recency_365_days_around_quarter():
    """Full year old should be ~1/4 of fresh — items don't disappear
    entirely with age, they just weight less.

    Note: Aria's docstring says "~0.3 at 365" but the actual math with
    half-life 180 gives exp(-ln(2) * 365/180) ≈ 0.245. This test asserts
    the math, not the docstring. Docstring drift filed as small follow-up.
    """
    value = recency_multiplier(365)
    assert 0.22 < value < 0.28, f"expected ~0.245 at 365d, got {value}"


def test_recency_monotonically_decreasing():
    """Ordering property: older items always weight less than newer."""
    ages = [1, 30, 90, 180, 365, 720]
    values = [recency_multiplier(a) for a in ages]
    for i in range(len(values) - 1):
        assert values[i] > values[i + 1], f"non-monotonic at {ages[i]} vs {ages[i + 1]}"


def test_recency_positive_bounded():
    """Decay never crosses zero — extremely old items still get a tiny
    signal, they don't get anti-boosted."""
    for days in [1000, 5000, 100000]:
        assert 0 < recency_multiplier(days) < 1.0


# --- composite_score (§Q1 weight composition) ---


def test_composite_all_ones_is_1():
    """Weights sum to 1.0, so a perfect item scores exactly 1.0. If this
    changes, the weight invariant is violated."""
    score = composite_score(
        similarity=1.0,
        tier="constraint",  # tier_weight=1.0
        recency_days=0,  # recency=1.0
        importance_score=1.0,
    )
    assert abs(score - 1.0) < 1e-9


def test_composite_all_zeros_is_0():
    score = composite_score(
        similarity=0.0,
        tier="conditional",  # tier_weight=0.0
        recency_days=100000,  # recency ~ 0
        importance_score=0.0,
    )
    # recency isn't quite zero but very small
    assert score < 0.05


def test_composite_similarity_is_dominant_signal():
    """similarity weight (0.60) should dominate the other three combined
    (0.40). A high-similarity/low-everything-else item should still
    outrank a low-similarity/high-everything-else item."""
    high_sim = composite_score(
        similarity=1.0, tier="conditional", recency_days=1000, importance_score=0.0
    )
    high_others = composite_score(
        similarity=0.0, tier="constraint", recency_days=0, importance_score=1.0
    )
    assert high_sim > high_others


def test_composite_weights_sum_to_1():
    """Property test: the weighted sum with all-1 inputs equals 1.0.
    If a weight is edited without also updating the others, this test
    catches it."""
    # similarity=1 → 0.60, tier=constraint → 0.15, recency=fresh → 0.10,
    # importance=1 → 0.15 → total 1.00
    score = composite_score(1.0, "constraint", 0, 1.0)
    assert abs(score - 1.0) < 1e-9


def test_composite_importance_clamped_upper():
    """importance_score gets clamped to [0, 1] so a stale persistence
    write of 1.5 doesn't produce a super-item."""
    normal = composite_score(0.5, "topic", 30, 1.0)
    over = composite_score(0.5, "topic", 30, 1.5)
    assert normal == over


def test_composite_importance_clamped_lower():
    """Negative importance clamped to 0 — a persistence bug shouldn't
    produce negative scores."""
    normal = composite_score(0.5, "topic", 30, 0.0)
    under = composite_score(0.5, "topic", 30, -0.5)
    assert normal == under


def test_composite_tier_flip_shifts_score_by_expected_amount():
    """Structural test: flipping constraint→topic drops the score by
    exactly (tier_weight_delta * 0.15). If the tier weight in
    composite_score gets tuned without also updating tier_weight(), this
    test catches the drift."""
    as_constraint = composite_score(0.5, "constraint", 30, 0.5)
    as_topic = composite_score(0.5, "topic", 30, 0.5)
    expected_delta = (1.0 - 0.6) * 0.15
    assert abs((as_constraint - as_topic) - expected_delta) < 1e-9


# --- compute_threshold (§Q1 per-source curves) ---


def test_threshold_unknown_source_defaults_conservative():
    """Any unfamiliar source gets a high threshold (0.50) so we don't
    accidentally over-surface from an untuned source."""
    assert compute_threshold("nonexistent_source", 100) == 0.50  # type: ignore[arg-type]


def test_threshold_small_cache_returns_floor():
    """Cache ≤ 50 items → threshold at floor. The retriever should surface
    aggressively when the substrate is sparse."""
    assert compute_threshold("correction", 10) == 0.30
    assert compute_threshold("exploration", 30) == 0.35
    assert compute_threshold("letter", 50) == 0.40


def test_threshold_never_exceeds_ceiling():
    """Ceiling at 0.85 must not be crossed even for huge caches — else
    even the strongest signal gets silenced."""
    for source in ["correction", "exploration", "knowledge", "wall", "letter"]:
        assert compute_threshold(source, 1_000_000) <= 0.85


def test_threshold_monotonically_rises_with_cache_size():
    """As substrate grows, threshold should not fall — else large-substrate
    noise wouldn't get filtered."""
    for source in ["correction", "exploration", "knowledge", "wall", "letter"]:
        sizes = [50, 100, 500, 1000, 10000]
        thresholds = [compute_threshold(source, s) for s in sizes]
        for i in range(len(thresholds) - 1):
            assert thresholds[i] <= thresholds[i + 1], (
                f"{source}: threshold fell from {thresholds[i]} to {thresholds[i + 1]} "
                f"between cache_size {sizes[i]} and {sizes[i + 1]}"
            )


def test_threshold_per_source_floors_match_spec():
    """The per-source floors ARE the spec — if they drift, the retriever's
    Q1 tuning is being edited without documentation."""
    assert compute_threshold("correction", 10) == 0.30
    assert compute_threshold("exploration", 10) == 0.35
    assert compute_threshold("knowledge", 10) == 0.30
    assert compute_threshold("wall", 10) == 0.25
    assert compute_threshold("letter", 10) == 0.40


def test_threshold_letter_starts_highest_wall_starts_lowest():
    """letter is highest-threshold (private context, high precision needed);
    wall is lowest (identity notes, we want more of them surfacing).
    This ordering is a design choice in §Q4 — locking it prevents silent
    tuning drift."""
    letter_floor = compute_threshold("letter", 10)
    wall_floor = compute_threshold("wall", 10)
    assert letter_floor > wall_floor


def test_threshold_steepness_visible_in_growth_rate():
    """correction has steepness 0.30, wall has steepness 0.10. So at the
    same large cache_size, correction's threshold has risen more from its
    floor than wall's has from its floor (in relative terms)."""
    correction_delta = compute_threshold("correction", 1000) - 0.30
    wall_delta = compute_threshold("wall", 1000) - 0.25
    assert correction_delta > wall_delta


def test_threshold_ceiling_reached_at_extreme_size():
    """At extremely large cache, high-steepness sources should saturate
    near the ceiling (0.85)."""
    correction_at_scale = compute_threshold("correction", 10_000_000)
    # steepness 0.30, log10(1e7)-1 = 6, 6*0.30 = 1.8 → clamped to 1.0
    # → floor + (ceiling - floor) * 1.0 = ceiling
    assert abs(correction_at_scale - 0.85) < 0.01


# --- Integration: composite + threshold ---


def test_score_can_be_above_or_below_threshold():
    """The retrieval pipeline compares composite_score to per-source
    threshold. This test just proves the two functions produce values in
    the same numeric range and can be compared meaningfully."""
    score = composite_score(0.6, "topic", 30, 0.5)
    threshold = compute_threshold("knowledge", 100)
    # Both are floats in [0, 1] — comparison is meaningful.
    assert isinstance(score, float) and 0 <= score <= 1
    assert isinstance(threshold, float) and 0 <= threshold <= 1
