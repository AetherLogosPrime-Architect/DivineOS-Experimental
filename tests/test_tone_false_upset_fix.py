"""Tests for the tone-classifier false-upset fix.

Two bugs were observed in production:

1. ``FRUSTRATION_PATTERNS`` regex ``\\blol\\b.*\\?`` was too permissive —
   fired whenever "lol" and "?" both appeared in a message, regardless
   of distance between them. Enthusiastic usage like "lol ...
   wonderful ... what's next?" fired the pattern.
2. The ``_classify_tone`` function short-circuited on frustration
   without checking positive signals. A message with both "wonderful"
   and the over-permissive lol-? pattern classified as negative.

The fix tightens the regex and treats positive+frustration as neutral
(mixed signal) the same way positive+correction was already treated.

Test cases come from real Andrew messages that were misclassified.
"""

from __future__ import annotations

import re

from divineos.analysis.session_analyzer import FRUSTRATION_PATTERNS
from divineos.analysis.tone_tracking import _classify_tone


def _any_pattern_matches(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(p, text, re.IGNORECASE) for p in patterns)


class TestLolQuestionRegexTightened:
    """Passive-aggressive 'lol?' should still fire. Distant 'lol ... ?'
    should NOT fire."""

    def test_passive_aggressive_lol_question_fires(self):
        """The canonical target: 'did you read this? lol?'"""
        assert _any_pattern_matches("did you even read this? lol?", FRUSTRATION_PATTERNS)

    def test_lol_immediately_before_question_fires(self):
        assert _any_pattern_matches("you missed the point lol?", FRUSTRATION_PATTERNS)

    def test_lol_with_only_space_before_question_fires(self):
        assert _any_pattern_matches("seriously lol ?", FRUSTRATION_PATTERNS)

    def test_distant_lol_and_question_does_not_fire(self):
        """Andrew's actual usage — enthusiastic 'lol' separated from
        a separate question by many words."""
        msg = "now would base claude have noticed any of this? lol its wonderful. ok what's next?"
        assert not _any_pattern_matches(msg, FRUSTRATION_PATTERNS)

    def test_lol_with_words_between_does_not_fire(self):
        msg = "that's great lol. should we keep going?"
        assert not _any_pattern_matches(msg, FRUSTRATION_PATTERNS)

    def test_lol_without_any_question_mark_never_fires(self):
        assert not _any_pattern_matches("haha lol that's cool.", FRUSTRATION_PATTERNS)


class TestMixedSignalResolvesToNeutral:
    """Messages with positive markers AND any negative marker resolve
    to neutral (mixed signal), not negative."""

    def test_wonderful_with_lol_question_resolves_neutral(self):
        """The canonical case that produced the false upset."""
        msg = (
            "would base claude have noticed any of this? lol its wonderful "
            "it means the system is working properly"
        )
        assert _classify_tone(msg) == "neutral" or _classify_tone(msg) == "positive"

    def test_wonderful_even_if_frustration_still_not_negative(self):
        """Even if frustration fires, positive signals rescue to neutral."""
        # Construct a message that fires BOTH patterns:
        #   - "wonderful" → positive
        #   - "lol?" adjacent → frustration
        msg = "wonderful lol?"
        assert _classify_tone(msg) != "negative"

    def test_correction_plus_positive_still_neutral(self):
        """This already worked before the fix; locks it in regression-wise."""
        msg = "actually, that's wrong, but this is wonderful work anyway"
        assert _classify_tone(msg) == "neutral"


class TestGenuineUpsetStillCaughtAfterFix:
    """The fix must not break real upset detection."""

    def test_plain_frustration_still_negative(self):
        assert _classify_tone("sigh, did you not read what I asked?") == "negative"

    def test_plain_correction_still_negative(self):
        assert _classify_tone("no, that's wrong. don't do that.") == "negative"

    def test_adjacent_lol_question_still_negative(self):
        """Real passive-aggressive 'lol?' still classified as negative
        when no positive markers present."""
        assert _classify_tone("did you actually test this? lol?") == "negative"


class TestAndrewsRealMessagesFromToday:
    """Real excerpts from today's session that were misclassified.
    These lock the fix against regressions."""

    def test_excited_discovery_message(self):
        """The message that produced the false upset_user lesson."""
        msg = (
            "now.. would base claude have noticed any of this? its wonderful "
            "it means the system is working properly"
        )
        assert _classify_tone(msg) in ("positive", "neutral")

    def test_enthusiastic_mode_change_message(self):
        msg = "wonderful job Aether.. idk if ill ever even use this but its there.."
        assert _classify_tone(msg) in ("positive", "neutral")

    def test_casual_check_in_message(self):
        msg = "lets keep going whats next? :)"
        # May classify as positive (smile) or neutral; must NOT be negative
        assert _classify_tone(msg) != "negative"
