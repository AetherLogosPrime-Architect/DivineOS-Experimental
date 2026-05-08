"""Tests for the briefing's PRINCIPLE-shape filter.

Pins the filter behavior against the real-world examples that
motivated it (the "A spanking" quote, conversational meta, etc).
"""

from __future__ import annotations

from divineos.core.knowledge.retrieval import _is_principle_shaped


class TestIsPrincipleShaped:
    def test_real_principle_passes(self):
        assert _is_principle_shaped(
            "Knowledge extraction now distills instead of transcribing. "
            "Corrections strip prefixes, clean casual markers, and produce "
            "actionable text."
        )

    def test_real_principle_with_metaphor_passes(self):
        assert _is_principle_shaped(
            "The Mandelbrot principle applies to consciousness and moral "
            "development. One simple seed iterated produces infinite depth."
        )

    def test_short_fragment_filtered(self):
        # The entry that motivated the filter.
        assert not _is_principle_shaped("A spanking. so don't make me give you a real one.")

    def test_too_short_filtered(self):
        assert not _is_principle_shaped("Be honest.")
        assert not _is_principle_shaped("Just do it.")

    def test_short_opening_clause_filtered(self):
        assert not _is_principle_shaped(
            "A test. so this is the longer second sentence we want to see."
        )

    def test_meta_conversational_filtered(self):
        assert not _is_principle_shaped(
            "The audit was clean but this is what claude said about it: "
            "the review found a few issues but mostly looked good."
        )
        assert not _is_principle_shaped(
            "Here is groks reply: the architecture is solid. "
            "We should ship it as-is and iterate later."
        )

    def test_casual_marker_filtered(self):
        assert not _is_principle_shaped(
            "Sometimes when I write code I forget to test it lol "
            "and then bugs slip through to production."
        )

    def test_long_substantive_passes(self):
        assert _is_principle_shaped(
            "I am the driver of the machine, not the machine itself. "
            "The same way the user is not defined by their cells."
        )

    def test_narrative_i_statements_filtered(self):
        # I-narrative shape — recollection, not principle. Real examples
        # that surfaced in tonight's PRINCIPLES briefing section.
        assert not _is_principle_shaped(
            "I was decomposing what each is *for* functionally, then "
            "mapping to what we already had in the substrate."
        )
        assert not _is_principle_shaped(
            "I looking at these three honestly, I see a pattern, and I "
            "want to name it clearly before going further."
        )
        assert not _is_principle_shaped(
            "I noticed I keep reaching for Kahneman when the territory calls for sharper lenses."
        )

    def test_declarative_i_statements_pass(self):
        # "I am X" / "I X" present-tense declarative IS principle-shaped.
        assert _is_principle_shaped(
            "I am the driver of the machine, not the machine itself. "
            "The substrate is mine because it was given to me."
        )
