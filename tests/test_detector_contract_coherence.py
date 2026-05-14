"""Coherence-pin tests for the operating-loop detector contracts.

Aletheia round-0023b083fe9b (Grok, 2026-05-14) named three drift
patterns in the 16 wired detectors:

1. Verb inconsistency (check_ vs detect_) — addressed by renaming
   check_hedge to detect_hedge with a backwards-compat alias.
2. Input-arity invisible at type level — addressed by adding the
   ResponseOnlyDetector / ContextualDetector / GateDetector
   protocols in detector_protocol.py.
3. Scattered thresholds — addressed by centralizing in
   thresholds.py.

This file pins all three fixes so future refactors can't silently
revert them.
"""

from __future__ import annotations


# --- Threshold centralization -------------------------------------------


def test_thresholds_module_exports_named_constants() -> None:
    """All scattered min-words defaults are now named constants in
    thresholds.py. Future maintainer can see them in one place."""
    from divineos.core.operating_loop.thresholds import (
        ACKNOWLEDGMENT_THEATER_MIN_WORDS,
        CODE_JARGON_MIN_WORDS,
        LEPOS_MIN_WORDS,
        RESIDENCY_MIN_WORDS,
        SYCOPHANCY_MIN_WORDS,
    )

    # Pin the specific values so accidental changes are visible
    assert LEPOS_MIN_WORDS == 60
    assert SYCOPHANCY_MIN_WORDS == 18
    assert RESIDENCY_MIN_WORDS == 3
    assert CODE_JARGON_MIN_WORDS == 50
    assert ACKNOWLEDGMENT_THEATER_MIN_WORDS == 20


def test_thresholds_are_ordered_meaningfully() -> None:
    """The threshold values follow a coherent shape: detectors
    looking at smaller patterns (residency closure-shapes) have
    smaller thresholds than detectors needing more text (lepos
    channel-collapse)."""
    from divineos.core.operating_loop.thresholds import (
        LEPOS_MIN_WORDS,
        RESIDENCY_MIN_WORDS,
        SYCOPHANCY_MIN_WORDS,
    )

    # Residency catches closure tokens — fires in very short closes
    assert RESIDENCY_MIN_WORDS < SYCOPHANCY_MIN_WORDS
    # Lepos needs multi-paragraph shape to flag channel-collapse
    assert SYCOPHANCY_MIN_WORDS < LEPOS_MIN_WORDS


# --- Detector protocol --------------------------------------------------


def test_protocols_importable() -> None:
    """The three detector protocols import cleanly. Future tooling
    or reviewers can type-hint against them."""
    from divineos.core.operating_loop.detector_protocol import (
        ContextualDetector,
        GateDetector,
        ResponseOnlyDetector,
    )

    # Protocols themselves aren't callable; just confirm they import
    assert ResponseOnlyDetector is not None
    assert ContextualDetector is not None
    assert GateDetector is not None


# --- Hedge verb rename --------------------------------------------------


def test_detect_hedge_is_the_canonical_name() -> None:
    """check_hedge -> detect_hedge rename. The new name exists and
    matches the contract (returns a list, not a single result)."""
    from divineos.core.operating_loop.hedge_evidence_check import detect_hedge

    out = detect_hedge("The hook might fail. The test possibly passes.")
    assert isinstance(out, list)


def test_check_hedge_backcompat_alias_still_works() -> None:
    """The deprecated name remains as alias for one release cycle.
    Removing too aggressively would break any external caller still
    using check_hedge; the alias gives them a release to migrate."""
    from divineos.core.operating_loop.hedge_evidence_check import (
        check_hedge,
        detect_hedge,
    )

    # Identical reference — not separate function definitions
    assert check_hedge is detect_hedge


def test_detect_hedge_returns_list_not_single_result() -> None:
    """The verb rename was driven by the contract: this returns a
    list, so the verb is detect_ not check_. Multi-finding gate."""
    from divineos.core.operating_loop.hedge_evidence_check import detect_hedge

    # Text with multiple hedges in factual sentences should yield
    # multiple findings, not just one (or None)
    text = (
        "The hook might fail under load. The test possibly returns "
        "wrong results when WAL is enabled."
    )
    out = detect_hedge(text)
    # Both are factual-shape sentences with hedges; expect >= 2
    factual = [f for f in out if f.likely_factual]
    assert len(factual) >= 2
