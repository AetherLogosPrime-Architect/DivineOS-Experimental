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


class TestTheMarkerArmsButDoesNotFileOurOwnText:
    """The second door. The Stop gate calls set_marker directly with its own
    diagnostic, and set_marker used to file that string into his corrections as if
    he had said it (rows 216, 220 and 381; the state glance showed #381 as "newest
    from him"). The marker must still arm, because the advertised clear path needs
    it; only the filing is skipped. Collaborators are recorded, not mocked away: the
    assertion is on what reaches them."""

    def _run(self, text, tmp_path):
        from unittest.mock import patch

        from divineos.core import correction_marker

        filed: list[str] = []
        logged: list[str] = []
        with (
            patch.object(correction_marker, "marker_path", return_value=tmp_path / "m.json"),
            patch(
                "divineos.core.andrew_correction_tracker.file_correction",
                side_effect=lambda t: filed.append(t) or 1,
            ),
            patch(
                "divineos.core.corrections.log_correction",
                side_effect=lambda t, session_id=None: logged.append(t) or {},
            ),
        ):
            correction_marker.set_marker(text)
            armed = correction_marker.read_marker()
        return armed, filed, logged

    def test_our_own_diagnostic_arms_the_marker_and_files_nothing(self, tmp_path):
        fire = "[correction-shape-v2 stop-gate] USE clause matched (1 hits); conf=1.00"
        armed, filed, logged = self._run(fire, tmp_path)
        assert armed is not None and armed["trigger"] == fire
        assert filed == [] and logged == []

    def test_a_real_correction_is_still_filed_both_places(self, tmp_path):
        """The control: the guard must not have switched filing off altogether."""
        armed, filed, logged = self._run("no, that is wrong, you did not check it", tmp_path)
        assert armed is not None
        assert filed == ["no, that is wrong, you did not check it"]
        assert logged == ["no, that is wrong, you did not check it"]

    def test_his_words_after_our_tag_are_still_his(self, tmp_path):
        text = "[correction-shape-v2 stop-gate] USE clause matched\nno, that is wrong"
        _, filed, _ = self._run(text, tmp_path)
        assert filed == [text]


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
            "[reach-check-doorman]",
        )

    def test_every_tag_is_bracketed_so_prose_cannot_match_one(self):
        for tag in _MACHINE_ORIGIN_MARKERS:
            assert tag.startswith("[") and tag.endswith("]")
