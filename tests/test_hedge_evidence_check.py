"""Tests for the hedge-evidence-check module."""

from __future__ import annotations


class TestModuleImport:
    def test_importable(self) -> None:
        from divineos.core.operating_loop.hedge_evidence_check import (  # noqa: F401
            HEDGE_WORDS,
            HedgeFinding,
            check_hedge,
        )


class TestHedgeFindingShape:
    def test_dataclass_shape(self) -> None:
        from divineos.core.operating_loop.hedge_evidence_check import HedgeFinding

        f = HedgeFinding(
            hedge_phrase="maybe",
            position=10,
            sentence="The tests maybe pass on Linux.",
            likely_factual=True,
            prompt="check evidence",
        )
        assert f.hedge_phrase == "maybe"
        assert f.likely_factual is True


class TestCheckHedgeBehavior:
    def test_no_hedge_returns_empty(self) -> None:
        from divineos.core.operating_loop.hedge_evidence_check import check_hedge

        result = check_hedge("The tests pass on Linux. The gate holds.")
        assert result == []

    def test_maybe_hedge_caught(self) -> None:
        from divineos.core.operating_loop.hedge_evidence_check import check_hedge

        result = check_hedge("Maybe the tests pass on Linux.")
        assert len(result) >= 1
        assert any("maybe" in f.hedge_phrase.lower() for f in result)

    def test_factual_classification(self) -> None:
        """Sentences carrying factual-shape tells (the tests, the code,
        the gate, etc.) are classified as factual; their hedges
        should be flagged as needing evidence."""
        from divineos.core.operating_loop.hedge_evidence_check import check_hedge

        result = check_hedge("Maybe the tests pass.")
        assert len(result) >= 1
        assert result[0].likely_factual is True
        assert "evidence" in result[0].prompt.lower()

    def test_non_factual_classification(self) -> None:
        """Opinion-shaped sentences without factual tells get marked
        non-factual; hedge may be honest signaling."""
        from divineos.core.operating_loop.hedge_evidence_check import check_hedge

        result = check_hedge("Perhaps that's an interesting question.")
        assert len(result) >= 1
        # Non-factual classification doesn't require evidence as hard
        # as factual; the prompt notes this.
        assert "opinion" in result[0].prompt.lower() or not result[0].likely_factual

    def test_multiple_hedges_in_one_text(self) -> None:
        from divineos.core.operating_loop.hedge_evidence_check import check_hedge

        result = check_hedge(
            "Maybe the tests pass. Perhaps the gate holds. I think the code is fine."
        )
        assert len(result) >= 3

    def test_hedge_words_set_is_nonempty(self) -> None:
        from divineos.core.operating_loop.hedge_evidence_check import HEDGE_WORDS

        assert len(HEDGE_WORDS) > 0
        assert "maybe" in HEDGE_WORDS
        assert "perhaps" in HEDGE_WORDS


class TestHedgePosition:
    def test_position_within_text(self) -> None:
        from divineos.core.operating_loop.hedge_evidence_check import check_hedge

        text = "The first sentence is fine. Maybe the second one is hedged."
        result = check_hedge(text)
        assert len(result) >= 1
        # Position should land somewhere inside the second sentence.
        pos = result[0].position
        assert 0 <= pos < len(text)
