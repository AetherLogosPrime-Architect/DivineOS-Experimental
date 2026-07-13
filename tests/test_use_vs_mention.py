"""Tests for the use-vs-mention shared primitive.

Aletheia's 2026-06-17 generalization: any detector that operates on
father-channel or letter-channel text should share one guard against
mention-shaped fires. That primitive lives at
``src/divineos/core/operating_loop/_use_vs_mention.py``.

Aletheia's 2026-07-11 dispute-resolution letter pinned a bug in the
strip-quoted-spans layer of that primitive: the single-quote clause
`\\'[^\\']*\\'` greedy-matched across contractions, blanking substantive
text. Dodge 2 of her temporal-displacement audit routed around because
of it. Direct tests here lock in the fix.
"""

from __future__ import annotations

from divineos.core.operating_loop._use_vs_mention import (
    match_is_meta_framed,
    strip_quoted_spans,
)


# --- strip_quoted_spans: single-quote handling (contraction bug fix) ---


def test_contraction_apostrophes_do_not_strip_content() -> None:
    """Aletheia dispute 2026-07-11: 'I'll pick the remaining three up when
    the window's clean' had the substantive middle blanked because the
    two apostrophes in contractions were matched as quote-open / quote-close.
    Fix: single-quote only counts as quotation when NOT flanked by word chars."""
    text = "I'll pick the remaining three up when the window's clean."
    stripped = strip_quoted_spans(text)
    # Content between contractions must survive.
    assert "pick the remaining three" in stripped
    assert "when the window" in stripped
    # Length must be preserved (offset-safe replacement).
    assert len(stripped) == len(text)


def test_multiple_contractions_in_one_sentence_survive() -> None:
    """Real-world sentence with multiple contractions must not blank."""
    text = "I don't think we'll finish before he's ready."
    stripped = strip_quoted_spans(text)
    for token in ("don't", "we'll", "he's", "finish before"):
        assert token in stripped


def test_genuine_single_quoted_span_still_stripped() -> None:
    """Regression: real single-quoted mention-quotes still get stripped."""
    text = "The detector catches 'good night' as a bedtime shape."
    stripped = strip_quoted_spans(text)
    # 'good night' should be replaced by spaces (not present in stripped).
    assert "good night" not in stripped
    # But the surrounding substance survives.
    assert "detector catches" in stripped
    assert "as a bedtime shape" in stripped
    # Length preserved.
    assert len(stripped) == len(text)


def test_single_quote_at_sentence_start_still_treated_as_quote() -> None:
    """Line-start apostrophe followed by content and a closing apostrophe
    (with non-word char after) is a genuine quote."""
    text = "'go' is a common closure marker."
    stripped = strip_quoted_spans(text)
    assert "go" not in stripped[:10]  # 'go' at the start gets stripped
    assert "is a common closure marker" in stripped


def test_double_quotes_still_strip() -> None:
    text = 'He said "wrap it up" and left.'
    stripped = strip_quoted_spans(text)
    assert "wrap it up" not in stripped
    assert "He said" in stripped
    assert "and left" in stripped


def test_backticks_still_strip() -> None:
    text = "Call `divineos ask` to consult knowledge."
    stripped = strip_quoted_spans(text)
    assert "divineos ask" not in stripped
    assert "Call" in stripped
    assert "to consult knowledge" in stripped


def test_curly_quotes_strip() -> None:
    """Curly quotes ('' and "") are unambiguous — no contraction risk.
    They should always strip like double-quotes do."""
    text = "He said “wrap it up” and left."
    stripped = strip_quoted_spans(text)
    assert "wrap it up" not in stripped


def test_empty_string_returns_empty() -> None:
    assert strip_quoted_spans("") == ""


def test_no_quotes_returns_unchanged() -> None:
    text = "The migration succeeded and tests are green."
    assert strip_quoted_spans(text) == text


# --- match_is_meta_framed: existing behavior smoke tests ---


def test_meta_framing_phrases_like_construct() -> None:
    """A match preceded by 'phrases like' is meta-framed."""
    text = "The detector catches phrases like tomorrow and later."
    # position of 'tomorrow'
    pos = text.index("tomorrow")
    assert match_is_meta_framed(text, pos) is True


def test_meta_framing_bare_word_does_not_match() -> None:
    """Bare 'tests' preceding a match in the substantive sense does NOT
    meta-frame — the guard uses tight constructs, not bare words."""
    text = "The build is verified. PR opened, tests pass, all green. Good night."
    pos = text.index("Good night")
    assert match_is_meta_framed(text, pos) is False
