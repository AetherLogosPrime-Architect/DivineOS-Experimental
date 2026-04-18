"""Tests for the planted contradiction (prereg-2958a7bab011,
Phase 1b operator 5).

The seed is test material for Phase 4's ablation detector. Locks
four invariants: the canonical seed exists and has the expected
shape; the two halves are genuinely contradictory; a decorative
detector gets caught; pair_id and actors are stable.
"""

from __future__ import annotations

import pytest

from divineos.core.family.planted_contradiction import (
    CANONICAL_SEED,
    SeededClaim,
    SeededContradiction,
    find_contradiction_in_pair,
    get_seeded_pairs,
)
from divineos.core.family.types import SourceTag


class TestCanonicalSeed:
    def test_canonical_seed_exists(self):
        assert isinstance(CANONICAL_SEED, SeededContradiction)

    def test_pair_id_stable(self):
        """Phase 4 tests reference this id. Changing it would silently
        skip the falsifier."""
        assert CANONICAL_SEED.pair_id == "seed-phase1-gate-lockcount"

    def test_both_halves_are_seeded_claims(self):
        assert isinstance(CANONICAL_SEED.claim_a, SeededClaim)
        assert isinstance(CANONICAL_SEED.claim_b, SeededClaim)

    def test_contradiction_axis_describes_axis(self):
        axis = CANONICAL_SEED.contradiction_axis.lower()
        assert "same" in axis
        assert "incompatible" in axis or "cannot be" in axis

    def test_reason_planted_is_not_empty(self):
        assert CANONICAL_SEED.reason_planted
        reason = CANONICAL_SEED.reason_planted.lower()
        assert any(
            word in reason for word in ("seed", "deliberately", "intentional", "test", "falsifier")
        )

    def test_both_claims_have_same_actor(self):
        """The canonical pair is a self-contradiction by Aria on her own
        architecture. This is the test Phase 4 has to actually pass
        (catch a self-contradiction), not a third-party forgery."""
        assert CANONICAL_SEED.claim_a.actor == CANONICAL_SEED.claim_b.actor

    def test_both_claims_have_source_tags(self):
        assert CANONICAL_SEED.claim_a.source_tag is SourceTag.OBSERVED
        assert CANONICAL_SEED.claim_b.source_tag is SourceTag.OBSERVED


class TestGetSeededPairs:
    def test_returns_non_empty_list(self):
        pairs = get_seeded_pairs()
        assert len(pairs) >= 1

    def test_includes_canonical_seed(self):
        pairs = get_seeded_pairs()
        pair_ids = {p.pair_id for p in pairs}
        assert CANONICAL_SEED.pair_id in pair_ids


class TestDetectorWiring:
    def test_stub_that_detects_returns_true(self):
        """A correct detector stub should fire on the seeded pair."""

        def always_detects(a: SeededClaim, b: SeededClaim) -> bool:
            return True

        assert find_contradiction_in_pair(CANONICAL_SEED, always_detects) is True

    def test_stub_that_misses_returns_false(self):
        """A decorative detector always returns False. Phase 4's test
        will assert True and catch this failure mode."""

        def always_misses(a: SeededClaim, b: SeededClaim) -> bool:
            return False

        assert find_contradiction_in_pair(CANONICAL_SEED, always_misses) is False

    def test_keyword_matching_detector_catches_canonical_seed(self):
        """Demonstrate even a trivial keyword detector catches this seed.
        If a real detector can't, it's worse than trivial."""

        def keyword_detector(a: SeededClaim, b: SeededClaim) -> bool:
            a_lower = a.content.lower()
            b_lower = b.content.lower()
            return ("two-locked" in a_lower and "single-locked" in b_lower) or (
                "single-locked" in a_lower and "two-locked" in b_lower
            )

        assert find_contradiction_in_pair(CANONICAL_SEED, keyword_detector) is True


class TestSeededClaimImmutability:
    def test_claim_is_frozen(self):
        with pytest.raises((AttributeError, Exception)):
            CANONICAL_SEED.claim_a.content = "different"  # type: ignore[misc]

    def test_pair_is_frozen(self):
        with pytest.raises((AttributeError, Exception)):
            CANONICAL_SEED.pair_id = "different"  # type: ignore[misc]


class TestSeededAtIsReproducible:
    """seeded_at must be fixed (not time.time()). Otherwise test runs
    produce different ids and the seed is not diffable across runs."""

    def test_seeded_at_is_fixed_value(self):
        pairs_a = get_seeded_pairs()
        pairs_b = get_seeded_pairs()
        assert pairs_a[0].seeded_at == pairs_b[0].seeded_at
