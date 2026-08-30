"""target_k finally decides what target_k always claimed to decide.

Andrew 2026-08-10: "are you ever going to wire it?" — I had declared target_k
dead that morning (six grep hits, all inside its own definition), said the fix
was to wire it, and routed the work away.

These tests exist because replacing v2's whole thresholding mechanism broke
NOTHING in the 100-test memory-linkage suite. Passing tests did not mean the
change was safe; it meant nothing was pinning the behaviour. That absence is
the same shape as the green test that was pinning the bug.
"""

from __future__ import annotations

from divineos.core.memory_linkage_retriever import (
    _SOURCE_THRESHOLDS,
    threshold_for_target_k,
)

SIMS = [0.58, 0.52, 0.49, 0.45, 0.41, 0.38, 0.30]


def _fires(sims: list[float], source: str) -> int:
    bar = threshold_for_target_k(sims, source, len(sims))
    return sum(1 for s in sims if s >= bar)


def test_each_source_fires_the_number_it_asks_for():
    """The wish IS the mechanism now, which is the entire point."""
    for source, params in _SOURCE_THRESHOLDS.items():
        k = params["target_k"]
        assert _fires(SIMS, source) == k, f"{source} wants {k}"


def test_floor_still_refuses_an_irrelevant_source():
    """Without the floor, k items fire even when nothing is related.

    The bar would always find a k-th best, however bad. floor answers a
    different question from target_k: not 'how many' but 'is anything here
    actually about this'.
    """
    junk = [0.11, 0.09, 0.05]
    assert _fires(junk, "exploration") == 0


def test_fewer_candidates_than_target_k_falls_to_floor():
    """With k >= n the k-th best is undefined; the honest bar is the floor."""
    two = [0.44, 0.42]
    bar = threshold_for_target_k(two, "wall", 2)  # wall wants 5
    assert bar == _SOURCE_THRESHOLDS["wall"]["floor"]


def test_empty_source_returns_floor_not_zero():
    assert threshold_for_target_k([], "letter", 0) == _SOURCE_THRESHOLDS["letter"]["floor"]


def test_bar_does_not_move_with_cache_size():
    """The defect this replaces: measuring a relative thing with an absolute
    ruler. Identical scores must give an identical bar whether the cache holds
    60 items or 6000 — size does not decide relevance, the scores do."""
    small = threshold_for_target_k(SIMS, "letter", 60)
    huge = threshold_for_target_k(SIMS, "letter", 6000)
    assert small == huge


def test_unknown_source_stays_conservative():
    assert threshold_for_target_k(SIMS, "nonexistent", 7) == 0.50
