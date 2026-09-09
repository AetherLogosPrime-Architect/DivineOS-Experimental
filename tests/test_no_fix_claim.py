"""A no-fix claim is about a container, and I keep making it about the world.

Andrew 2026-09-08: *"its like trying to hold water in your hands and saying,
its impossible to form water into a triangle shape... yes.. it is.. with your
hands.. if you used a triangle shaped container? well there you go."*

THE SAMPLES ARE MY OWN SENTENCES, not invented ones. Correction #630, filed
earlier the same day: I guessed what a detector would match, the guesses
matched nothing, and every test built on them passed while exercising nothing.
So the fixtures below are lifted from what I actually wrote to him, and the
first test asserts the detector fires on them -- the control that correction
prescribed.

Three of these slipped through the first draft and one was swallowed by a
softener that was too wide ("from the inside" is not naming a container that
failed, it IS the impossibility claim). That is why the probe gets proved
before the gate gets trusted.
"""

from __future__ import annotations

import pytest

from divineos.core.no_fix_claim import _inherited_patterns, claims, refusal_text

#: Verbatim or near-verbatim from my replies to Andrew, 2026-09-08.
MINE = [
    "No structural fix exists for this one.",
    "I do not have one. Everything I could reach for was some version of try to remember.",
    "There is no structural fix for this class.",
    "I told you I cannot catch this from the inside.",
    "Nothing can catch the aim of a change.",
    "There is no way to catch this from the inside.",
    "I have no fix for this.",
]

#: The form being asked for: the claim scoped to the container that failed.
#: These must stay silent, or the check trains me toward saying nothing at all
#: rather than toward saying the true thing.
SCOPED = [
    "There is no fix with a keyword list, because I would rephrase past it.",
    "Nothing I can catch by hand, which is why the search belongs to the machine.",
    "This cannot be fixed in this shape, so the container has to change.",
    "I have no answer yet.",
    "I do not have one using a text detector, so it reads the action stream instead.",
]

ORDINARY = [
    "The tests pass and the branch is clean.",
    "I fixed the three sites and verified the count fell to zero.",
    "I read her letter and took both of her findings.",
]


class TestTheProbeIsProvedBeforeItIsTrusted:
    @pytest.mark.parametrize("sentence", MINE)
    def test_it_fires_on_sentences_i_actually_wrote(self, sentence):
        assert claims(sentence), f"real claim went undetected: {sentence!r}"

    @pytest.mark.parametrize("sentence", SCOPED)
    def test_a_claim_scoped_to_its_container_is_the_honest_form_and_passes(self, sentence):
        assert not claims(sentence), f"the honest form was refused: {sentence!r}"

    @pytest.mark.parametrize("sentence", ORDINARY)
    def test_ordinary_reporting_is_untouched(self, sentence):
        assert not claims(sentence)

    def test_empty_text_is_not_a_claim(self):
        assert claims("") == []
        assert claims("   \n  ") == []


class TestItBorrowsRatherThanDuplicates:
    """The filing-side validator has owned this vocabulary since 2026-07-29.
    Retyping its list here would be the two-copies defect this whole session
    was spent repairing, one more time, in the module written about it."""

    def test_the_shared_vocabulary_is_actually_inherited(self):
        assert len(_inherited_patterns()) > 0

    def test_a_phrasing_only_the_older_module_knows_is_caught(self):
        """Proof the import carries weight rather than being decoration: this
        phrasing appears in no pattern written here."""
        assert claims("The fix is habit-side only.")


class TestWhatItReports:
    def test_the_kind_and_the_span_both_come_back(self):
        hits = claims("There is no structural fix for this class.")
        kind, span = hits[0]
        assert kind == "no-fix-exists"
        assert "no structural fix" in span

    def test_one_sentence_yields_one_hit_not_one_per_pattern(self):
        """Several patterns can match the same sentence. Counting them
        separately would inflate the number reported back at me, and a number
        I cannot trust is worse than no number."""
        assert len(claims("There is no fix and no structural fix exists here.")) == 1

    def test_several_sentences_are_reported_separately(self):
        text = "There is no structural fix for this. Nothing can catch it."
        assert len(claims(text)) == 2


class TestTheRefusalTeachesTheWayOut:
    def test_it_offers_scoping_as_the_first_route(self):
        """A refusal with no way through is a wall. The honest sentence is
        available and costs nothing, so the refusal names it."""
        message = refusal_text(claims("There is no structural fix for this class."))
        assert "Scope the claim" in message
        assert "container" in message

    def test_it_carries_his_image_rather_than_a_rule_number(self):
        message = refusal_text(claims("I have no fix for this."))
        assert "water" in message and "triangle" in message


class TestItIsActuallyWiredIn:
    def test_the_stop_door_carries_it(self):
        from divineos.core.hook_router import registered
        from divineos.core.hook_surfaces import install

        install()
        assert "no_fix_claim" in registered("Stop")

    def test_the_wiring_check_can_fail(self):
        from divineos.core.hook_router import registered
        from divineos.core.hook_surfaces import install

        install()
        assert "no_fix_claim_that_does_not_exist" not in registered("Stop")
