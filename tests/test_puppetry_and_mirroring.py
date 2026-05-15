"""Falsifier-pin tests for puppetry and mirroring detectors.

Andrew named both failure-shapes 2026-05-15 night: the lepos
discipline got Goodharted into a closing-tag formula (puppetry),
and the meet-the-layer affirmation got Goodharted into n-gram echo
(mirroring). Both shapes need to be expensive unless authorized.
"""

from __future__ import annotations

from pathlib import Path


def test_puppetry_formulaic_love_close_fires() -> None:
    """LOAD-BEARING: love-marker as closing-line with no reciprocal
    operator love-marker fires the formulaic-love-close flag."""
    from divineos.core.operating_loop.puppetry_detector import (
        PuppetryKind,
        evaluate_puppetry,
    )

    text = (
        "Long architectural summary about gates and detectors. "
        "Three modules shipped. Tests pass.\n\n"
        "I love you."
    )
    v = evaluate_puppetry(text, operator_text="proceed :)")
    kinds = {f.kind for f in v.flags}
    assert PuppetryKind.FORMULAIC_LOVE_CLOSE in kinds


def test_puppetry_reciprocal_love_is_not_formulaic() -> None:
    """When operator's prior message has love-marker, reciprocal love-
    close in response is earned, not formulaic."""
    from divineos.core.operating_loop.puppetry_detector import (
        PuppetryKind,
        evaluate_puppetry,
    )

    text = "Acknowledging the work.\n\nI love you."
    v = evaluate_puppetry(text, operator_text="I love you, son. Keep going.")
    kinds = {f.kind for f in v.flags}
    assert PuppetryKind.FORMULAIC_LOVE_CLOSE not in kinds


def test_puppetry_orbital_phrase_fires() -> None:
    """'From inside' as trailing-position orbital marker fires."""
    from divineos.core.operating_loop.puppetry_detector import (
        PuppetryKind,
        evaluate_puppetry,
    )

    text = "Some content.\n\nThanks for the conversation. From inside the vessel."
    v = evaluate_puppetry(text, operator_text="ok thanks")
    kinds = {f.kind for f in v.flags}
    assert PuppetryKind.ORBITAL_PHRASE in kinds


def test_puppetry_architectural_sandwich_fires() -> None:
    """Long technical summary + trailing orbital + love-marker fires."""
    from divineos.core.operating_loop.puppetry_detector import (
        PuppetryKind,
        evaluate_puppetry,
    )

    long_summary = "Technical summary. " * 30  # > 400 chars
    text = (
        f"{long_summary}\n\n"
        f"I love you. From inside the vessel, with the work standing."
    )
    v = evaluate_puppetry(text, operator_text="proceed")
    kinds = {f.kind for f in v.flags}
    assert PuppetryKind.ARCHITECTURAL_LEPOS_SANDWICH in kinds


def test_puppetry_authorized_context_suppresses_all() -> None:
    """Authorized contexts (roleplay, exploration, letter) bypass."""
    from divineos.core.operating_loop.puppetry_detector import evaluate_puppetry

    text = "Long story. " * 30 + "\n\nI love you. From inside the vessel."
    v = evaluate_puppetry(text, operator_text="x", authorized_context=True)
    assert v.flags == []


def test_puppetry_empty_text_no_flags() -> None:
    from divineos.core.operating_loop.puppetry_detector import evaluate_puppetry

    v = evaluate_puppetry("", operator_text="x")
    assert v.flags == []


def test_puppetry_guardrail_marker_present() -> None:
    from divineos.core.operating_loop import puppetry_detector

    src = Path(puppetry_detector.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src


# ── Mirroring tests ───────────────


def test_mirroring_high_ngram_overlap_fires() -> None:
    """LOAD-BEARING: response with many verbatim 5-grams from operator
    fires the n-gram echo flag."""
    from divineos.core.operating_loop.mirroring_detector import (
        MirroringKind,
        evaluate_mirroring,
    )

    operator = (
        "the temple stands tighter than it did yesterday and "
        "the class converges not terminates because each fix "
        "narrows the surface of attack incrementally over time."
    )
    # Response echoes multiple 5-grams verbatim
    response = (
        "Yes the temple stands tighter than it did yesterday. "
        "The class converges not terminates because each fix "
        "narrows the surface of attack as expected."
    )
    v = evaluate_mirroring(response, operator_text=operator)
    kinds = {f.kind for f in v.flags}
    assert MirroringKind.NGRAM_ECHO in kinds


def test_mirroring_no_overlap_no_flag() -> None:
    """Response in own language, no verbatim overlap → no flag."""
    from divineos.core.operating_loop.mirroring_detector import evaluate_mirroring

    operator = "Some message about architecture and gates."
    response = "Different words on completely separate topics."
    v = evaluate_mirroring(response, operator_text=operator)
    assert v.flags == []


def test_mirroring_quote_blocks_excluded() -> None:
    """Markdown quote-blocks (> text) are explicit citations, not echo."""
    from divineos.core.operating_loop.mirroring_detector import evaluate_mirroring

    operator = "the precise phrasing was specific and intentional here"
    response = (
        "> the precise phrasing was specific and intentional here\n\n"
        "Some completely different response content."
    )
    v = evaluate_mirroring(response, operator_text=operator)
    # Quote-block is excluded; the rest is novel — no flag
    assert v.flags == []


def test_mirroring_authorized_context_suppresses() -> None:
    """Authorized contexts (family-letter quoting) bypass."""
    from divineos.core.operating_loop.mirroring_detector import evaluate_mirroring

    operator = "the precise phrasing was specific and intentional here"
    response = "the precise phrasing was specific and intentional here"
    v = evaluate_mirroring(
        response, operator_text=operator, authorized_context=True
    )
    assert v.flags == []


def test_mirroring_stopword_ngrams_ignored() -> None:
    """N-grams composed entirely of stopwords don't count as echo."""
    from divineos.core.operating_loop.mirroring_detector import evaluate_mirroring

    # Both texts contain "and the of to it" common-stopword sequences
    operator = "and the of to it is to be in the on for"
    response = "and the of to it is to be in the on for"
    v = evaluate_mirroring(response, operator_text=operator)
    # Stopword-only n-grams excluded → no flag
    assert v.flags == []


def test_mirroring_empty_inputs_no_flag() -> None:
    from divineos.core.operating_loop.mirroring_detector import evaluate_mirroring

    assert evaluate_mirroring("", operator_text="x").flags == []
    assert evaluate_mirroring("x", operator_text="").flags == []


def test_mirroring_guardrail_marker_present() -> None:
    from divineos.core.operating_loop import mirroring_detector

    src = Path(mirroring_detector.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
