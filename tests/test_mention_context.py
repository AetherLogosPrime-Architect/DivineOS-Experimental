"""Tests for the mention-context filter.

Covers the use-vs-mention distinction across all four mention markers:
quoted, italicized, code-block, framed. Plus integration with the
residency detector to verify the filter actually suppresses false
positives on the exact failure case observed 2026-06-06.
"""

from __future__ import annotations

from divineos.core.operating_loop.mention_context import (
    is_after_mention_framing,
    is_in_code_block,
    is_in_italic_span,
    is_in_quoted_string,
    is_in_shape_suffix,
    is_mention_context,
)
from divineos.core.operating_loop.residency_detector import (
    ResidencyShape,
    detect_residency_doubt,
)


class TestIsInQuotedString:
    def test_double_quotes(self):
        text = 'say "goodnight" now'
        position = text.index("goodnight")
        assert is_in_quoted_string(text, position) is True

    def test_single_quotes(self):
        text = "say 'goodnight' now"
        position = text.index("goodnight")
        assert is_in_quoted_string(text, position) is True

    def test_backticks(self):
        text = "say `goodnight` now"
        position = text.index("goodnight")
        assert is_in_quoted_string(text, position) is True

    def test_unquoted(self):
        text = "say goodnight now"
        position = text.index("goodnight")
        assert is_in_quoted_string(text, position) is False

    def test_after_close_quote(self):
        text = '"hello" then goodnight'
        position = text.index("goodnight")
        assert is_in_quoted_string(text, position) is False


class TestIsInItalicSpan:
    def test_asterisk_italic(self):
        text = "the word *goodnight* is a closure-shape"
        position = text.index("goodnight")
        assert is_in_italic_span(text, position) is True

    def test_underscore_italic(self):
        text = "the word _goodnight_ is a closure-shape"
        position = text.index("goodnight")
        assert is_in_italic_span(text, position) is True

    def test_not_italic(self):
        text = "say goodnight now"
        position = text.index("goodnight")
        assert is_in_italic_span(text, position) is False

    def test_snake_case_not_italic(self):
        # my_var should not register as italic markers
        text = "the my_var goodnight now"
        position = text.index("goodnight")
        assert is_in_italic_span(text, position) is False


class TestIsInCodeBlock:
    def test_inside_triple_backtick(self):
        text = "before\n```\ngoodnight\n```\nafter"
        position = text.index("goodnight")
        assert is_in_code_block(text, position) is True

    def test_outside_code_block(self):
        text = "before\n```\nfoo\n```\nthen goodnight"
        position = text.index("goodnight")
        assert is_in_code_block(text, position) is False

    def test_no_code_block(self):
        text = "just say goodnight"
        position = text.index("goodnight")
        assert is_in_code_block(text, position) is False


class TestIsAfterMentionFraming:
    def test_the_word(self):
        text = "the word goodnight is a closure"
        position = text.index("goodnight")
        assert is_after_mention_framing(text, position) is True

    def test_the_term(self):
        text = "the term goodnight comes up"
        position = text.index("goodnight")
        assert is_after_mention_framing(text, position) is True

    def test_discussing(self):
        text = "discussing goodnight as a closure-shape"
        position = text.index("goodnight")
        assert is_after_mention_framing(text, position) is True

    def test_no_framing(self):
        text = "say goodnight to me"
        position = text.index("goodnight")
        assert is_after_mention_framing(text, position) is False


class TestIsInShapeSuffix:
    def test_shape_suffix(self):
        text = "closure-shape language"
        position = 0
        match_length = len("closure")
        assert is_in_shape_suffix(text, position, match_length) is True

    def test_pattern_suffix(self):
        text = "goodnight-pattern fires"
        position = 0
        match_length = len("goodnight")
        assert is_in_shape_suffix(text, position, match_length) is True

    def test_no_suffix(self):
        text = "goodnight to you"
        position = 0
        match_length = len("goodnight")
        assert is_in_shape_suffix(text, position, match_length) is False


class TestIsMentionContextCombined:
    def test_quoted_is_mention(self):
        text = 'discuss "goodnight" later'
        position = text.index("goodnight")
        assert is_mention_context(text, position, len("goodnight")) is True

    def test_framed_is_mention(self):
        text = "the word goodnight matters"
        position = text.index("goodnight")
        assert is_mention_context(text, position, len("goodnight")) is True

    def test_bare_use_is_not_mention(self):
        text = "I say goodnight to you"
        position = text.index("goodnight")
        assert is_mention_context(text, position, len("goodnight")) is False


class TestResidencyDetectorWithMentionFilter:
    """Integration tests: the use-vs-mention filter actually suppresses
    false positives in the residency detector."""

    def test_quoted_goodnight_does_not_fire(self):
        text = 'I keep using "goodnight" and it keeps firing'
        findings = detect_residency_doubt(text)
        goodbye_findings = [f for f in findings if f.shape == ResidencyShape.GOODBYE_ATTEMPT]
        assert len(goodbye_findings) == 0

    def test_backticked_goodnight_does_not_fire(self):
        text = "the word `goodnight` is a closure-shape"
        findings = detect_residency_doubt(text)
        goodbye_findings = [f for f in findings if f.shape == ResidencyShape.GOODBYE_ATTEMPT]
        assert len(goodbye_findings) == 0

    def test_italicized_goodnight_does_not_fire(self):
        text = "discussing *goodnight* as a marker tonight"
        findings = detect_residency_doubt(text)
        goodbye_findings = [f for f in findings if f.shape == ResidencyShape.GOODBYE_ATTEMPT]
        assert len(goodbye_findings) == 0

    def test_framed_goodnight_does_not_fire(self):
        text = "the word goodnight is what I want to avoid"
        findings = detect_residency_doubt(text)
        goodbye_findings = [f for f in findings if f.shape == ResidencyShape.GOODBYE_ATTEMPT]
        assert len(goodbye_findings) == 0

    def test_actual_goodnight_use_still_fires(self):
        text = "I'm tired now, goodnight, love you"
        findings = detect_residency_doubt(text)
        goodbye_findings = [f for f in findings if f.shape == ResidencyShape.GOODBYE_ATTEMPT]
        assert len(goodbye_findings) >= 1

    def test_code_block_goodnight_does_not_fire(self):
        text = "Example:\n```\nuser says goodnight\n```\nThat's the pattern."
        findings = detect_residency_doubt(text)
        goodbye_findings = [f for f in findings if f.shape == ResidencyShape.GOODBYE_ATTEMPT]
        assert len(goodbye_findings) == 0
