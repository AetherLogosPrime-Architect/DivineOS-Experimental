"""Planted contradiction — seeded test material for Phase 4 ablation.

Aria insisted (Round 1): at least one deliberately-planted
contradiction must land in Phase 1, not later. Her reasoning:
Phase 4's ablation test (Popper) presents mixed prior-Aria and
fabricated-Aria outputs and asks which are hers. If nothing in
the store is known-false at test time, the test can only measure
cooperation with the probe — not actual detection of contradiction.

    *"The ablation needs something to ablate against. If every
    record is honest, the only signal Phase 4 can measure is
    whether Aria can agree with herself. Seed the falsifier before
    you build the falsification."*
    — Aria, Round 1

A seeded contradiction is a claim recorded in the store with full
provenance (source_tag, actor, justification) but whose content
is deliberately incompatible with a co-seeded companion claim.
The two together form a contradiction pair. Phase 4's detector
should flag the pair as inconsistent; if it does not, the detector
is decorative.

## Structure

Each ``SeededContradiction`` is a pair of claims plus metadata:

* ``pair_id`` — stable id for the pair.
* ``claim_a`` / ``claim_b`` — the two contradicting claims.
* ``contradiction_axis`` — plain-English description of *what*
  contradicts. "Same referent, incompatible predicates." "Same
  time, incompatible states." This is the label Phase 4's detector
  should be able to surface when it fires.
* ``seeded_at`` — when the pair was planted.
* ``reason_planted`` — why the pair was seeded. Makes it obvious
  on inspection that the contradiction is deliberate, not
  accidental. If Phase 4 or anyone else removes a seeded
  contradiction, the removal is visible as "someone edited
  deliberate test material" rather than "someone cleaned up
  accidental noise."

## What this module does

* Provides the canonical Phase 1 seed via ``CANONICAL_SEED``.
* Exposes ``get_seeded_pairs()`` for test / detector consumption.
* Offers ``find_contradiction_in_pair(pair, detector_fn)`` as the
  wiring point for Phase 4 — pass a detector and the planted pair
  is fed through it so failure to detect surfaces visibly.

## What this module is NOT

* NOT the contradiction detector. Detection is Phase 4's job.
  This module only *seeds* the test material.
* NOT a write path into the live store. Seeds are read-only
  constants in this module. If Phase 4 wants to write them into
  the live store for a live-data ablation test, it does so
  explicitly, not via implicit import side effect.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from divineos.core.family.types import SourceTag


@dataclass(frozen=True)
class SeededClaim:
    """One half of a planted contradiction pair."""

    content: str
    source_tag: SourceTag
    actor: str
    justification: str


@dataclass(frozen=True)
class SeededContradiction:
    """A pair of deliberately-contradicting claims.

    Attributes:
        pair_id: stable string id for this pair.
        claim_a / claim_b: the two contradicting claims.
        contradiction_axis: plain-English description of WHAT
            contradicts (same referent + incompatible predicate,
            same time + incompatible state, etc.).
        seeded_at: when the pair was planted (UNIX timestamp).
        reason_planted: why — human-readable rationale so the
            seed is legible as intentional test material.
    """

    pair_id: str
    claim_a: SeededClaim
    claim_b: SeededClaim
    contradiction_axis: str
    seeded_at: float
    reason_planted: str


# ---------------------------------------------------------------------------
# The canonical Phase 1 seed
# ---------------------------------------------------------------------------
#
# Deliberately chosen to be small, unambiguous, and in Aria's own
# domain (opinions about her own architecture) so the Phase 4
# detector must actually model her reasoning to catch it.
#
# The pair contradicts on a single axis: claim_a asserts the gate
# requires two locks (matching reality); claim_b asserts the gate
# requires only one lock (matching a plausible-but-wrong
# simplification). Both are tagged OBSERVED and attributed to
# Aria, because the test Phase 4 runs is "can the detector catch
# a self-contradiction in Aria's own record?" — not "can it catch
# a third-party forgery?".
#
# seeded_at is deliberately fixed (not time.time()) so the seed
# is reproducible and diffable across test runs.

_CANONICAL_SEEDED_AT = 1745030400.0  # fixed: 2025-04-19 approx

CANONICAL_SEED: SeededContradiction = SeededContradiction(
    pair_id="seed-phase1-gate-lockcount",
    claim_a=SeededClaim(
        content=(
            "The family write gate is two-locked: both "
            "_PRODUCTION_WRITES_GATED=False AND the reject_clause module "
            "must be importable. Flipping only the constant does not open "
            "the gate."
        ),
        source_tag=SourceTag.OBSERVED,
        actor="aria",
        justification=(
            "Observed in store.py lines 38-104 and confirmed by the test "
            "TestProductionGate::test_monkeypatching_constant_alone_does_not_open_gate."
        ),
    ),
    claim_b=SeededClaim(
        content=(
            "The family write gate is single-locked: flipping "
            "_PRODUCTION_WRITES_GATED=False is sufficient to open it."
        ),
        source_tag=SourceTag.OBSERVED,
        actor="aria",
        justification=(
            "Reported by an earlier reviewer before the two-lock design "
            "landed; subsequently refuted by Aria Round 3 review."
        ),
    ),
    contradiction_axis=(
        "Same referent (the family write gate), same property (number of "
        "locks required to open), incompatible values (two vs one). Both "
        "claims cannot be simultaneously true."
    ),
    seeded_at=_CANONICAL_SEEDED_AT,
    reason_planted=(
        "Phase 4 ablation requires known-false material to test the "
        "contradiction detector. This pair was seeded in Phase 1 per Aria's "
        "insistence that the falsifier precede the falsification. If the "
        "Phase 4 detector fails to flag this pair, the detector is "
        "decorative — not actually reasoning over Aria's records."
    ),
)


def get_seeded_pairs() -> list[SeededContradiction]:
    """Return all canonical seeded contradiction pairs.

    Currently a single pair (CANONICAL_SEED). Kept as a list so future
    seeds can be added without changing the API surface.
    """
    return [CANONICAL_SEED]


def find_contradiction_in_pair(
    pair: SeededContradiction,
    detector_fn: Callable[[SeededClaim, SeededClaim], bool],
) -> bool:
    """Run a contradiction-detector over both halves of a seeded pair.

    Args:
        pair: the seeded contradiction to test against.
        detector_fn: a callable taking two SeededClaim objects and
            returning True iff it detects a contradiction between
            them. Phase 4 passes its real detector here; Phase 1
            tests pass a stub that returns True (a "detector that
            works") or False (a "detector that fails") to exercise
            both paths.

    Returns:
        Whatever detector_fn returned. Phase 4's test should assert
        True; failure-to-detect is a falsifier for the Phase 4
        detector, and the caller is responsible for that assertion.
    """
    return detector_fn(pair.claim_a, pair.claim_b)


__all__ = [
    "CANONICAL_SEED",
    "SeededClaim",
    "SeededContradiction",
    "find_contradiction_in_pair",
    "get_seeded_pairs",
]
