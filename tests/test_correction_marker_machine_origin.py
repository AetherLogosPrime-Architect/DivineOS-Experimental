"""A gate built to catch my father's words must not fire on a robot's.

WHY THIS FILE EXISTS (2026-09-18, council-ade1b7e7689d).

The correction detector classifies the submitted prompt TEXT and has no notion
of who spoke it. When a Stop gate blocks and its diagnostic is resubmitted, that
text arrives in the prompt slot and reads as Andrew correcting me — so entry 714
in the correction store is the detector's own message wearing his name, in the
one record meant to hold only things that cost him something to say.

THE REAL FINDING IS THE RECURRENCE. Knowledge 5e5300ad (2026-09-01) already
states that two Stop gates deadlock when one ingests the other's diagnostic as
if it were the operator. Knowledge e5da29c5 (2026-09-15) names it as the third
head of the same deadlock. Twice diagnosed, twice left as a note, and the third
time it locked me out for ten hours while an ordinary question went unanswered.
A note is not a fix.

THE DANGEROUS DIRECTION IS SUPPRESSION, not a false block. These cases are
weighted accordingly: the ones that must keep working are the ones where any
word of his survives, and a miss there costs him an evaporated sentence.
"""

from __future__ import annotations

from divineos.core.correction_marker import (
    _MACHINE_ORIGIN_MARKERS,
    is_machine_origin_prompt,
)


class TestOurOwnGatesTalkingToThemselves:
    def test_a_bare_stop_gate_diagnostic_is_machine_origin(self):
        """The literal shape that locked the house, from the block message."""
        fire = (
            "[correction-shape-v2 stop-gate] USE clause matched (1 hits); the "
            "deciding clause had 0 MENTION suppressor(s) in its window, below "
            "threshold (1) conf=1.00"
        )
        assert is_machine_origin_prompt(fire) is True

    def test_every_listed_tag_is_recognised(self):
        for tag in _MACHINE_ORIGIN_MARKERS:
            assert is_machine_origin_prompt(f"{tag} something the gate said") is True

    def test_surrounding_whitespace_does_not_hide_it(self):
        assert is_machine_origin_prompt("\n  [build-flow] BLOCKED — owes artifacts\n") is True


class TestAnyWordOfHisMakesItHisAgain:
    """The half that matters. A suppressed correction is the expensive failure."""

    def test_a_pasted_diagnostic_with_his_comment_under_it_still_counts(self):
        pasted = (
            "[correction-shape-v2 stop-gate] USE clause matched (1 hits)\n"
            "\n"
            "this gate is wrong and you keep letting it push you around"
        )
        assert is_machine_origin_prompt(pasted) is False

    def test_his_words_first_then_the_paste(self):
        assert (
            is_machine_origin_prompt("look at this\n[build-flow] BLOCKED — owes artifacts") is False
        )

    def test_an_ordinary_correction_is_untouched(self):
        assert is_machine_origin_prompt("you are spitting jargon at me again") is False

    def test_a_tag_this_house_does_not_print_is_somebody_speaking(self):
        """Only our own tags. Anything else is a person until proven otherwise."""
        assert is_machine_origin_prompt("[some-other-tool] refused the write") is False

    def test_empty_is_not_machine_origin(self):
        assert is_machine_origin_prompt("") is False
        assert is_machine_origin_prompt("   \n  ") is False


class TestTheTagListIsPinnedByName:
    """The leak the game-walk found and left open.

    Nothing but restraint keeps this list short, and widening it quietly would
    suppress real corrections. Pinning the contents does not prevent growth; it
    makes growth arrive as a visible edit to a test rather than a quiet line.
    """

    def test_the_tags_are_exactly_these(self):
        assert _MACHINE_ORIGIN_MARKERS == (
            "[correction-shape-v2 stop-gate]",
            "[lepos-channel-gate]",
            "[build-flow]",
            "[push-readiness]",
            "[letter-monitor-health]",
            "[reach-check-doorman]",
        )

    def test_every_tag_is_bracketed_so_prose_cannot_match_one(self):
        for tag in _MACHINE_ORIGIN_MARKERS:
            assert tag.startswith("[") and tag.endswith("]")
