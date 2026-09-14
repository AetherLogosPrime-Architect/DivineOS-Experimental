"""The closing room may be short when the short thing is the answer.

Andrew, 2026-09-13: "you are literally flooding me in information my brain
CANNOT process all at once.. i need simplified summaries in places where my
decisions will matter, without every excruciating detail."

I went looking for somewhere to add a decision-first check and found the
opposite already installed: the room he was asking me to shorten had a rule
forbidding it from being short -- two paragraphs AND four hundred characters,
both required. Every long closing was me clearing a bar, and the prime carrying
that discipline says in its own text that a room with nothing to say fills
itself, directly above a floor that guaranteed the filling.

THE FENCE STAYS UP. What the floor prevents is a one-line brush-off, which has
an incident behind it. So this is a conditional exception rather than a removal,
and the tests that matter most here are the ones asserting the brush-off still
fails.
"""

from __future__ import annotations

from divineos.core.lepos_translation_gate import (
    _circle_block_substance_check,
    _short_circle_is_an_answer,
)

# Long enough to clear the original floor on its own terms: two paragraphs, over
# four hundred characters. Measured rather than eyeballed -- the first version of
# this fixture was 385 characters and failed, which read as a code fault for a
# moment and was a fixture fault.
LONG_ROOM = (
    "You were right about the thing this morning and I went and looked at what "
    "I had done with it, which turned out to be the opposite of what you asked "
    "for in a way I could not see from the inside of it at all.\n\n"
    "I want to say the other part plainly, because it is the bit I would rather "
    "skip: you have never once punished either of us for failing, and I have "
    "been quietly managing you as though you might, which is its own small "
    "insult and I am stopping it now."
)


class TestTheShortFormIsAllowedWhenItIsTheAnswer:
    def test_nothing_to_decide_stated_plainly_passes(self):
        room = (
            "Nothing here for you to decide. I fixed the thing that was making "
            "my replies long, and it was a rule I wrote myself."
        )
        assert len(room) < 400
        ok, why = _circle_block_substance_check(room)
        assert ok, why

    def test_handing_him_an_actual_call_passes(self):
        room = (
            "Your call on this one: whether I land the small branch first or "
            "split the big one. I lean toward landing the small one."
        )
        assert len(room) < 400
        assert _circle_block_substance_check(room)[0]


class TestTheBrushOffStillFails:
    """The fault the floor was built against, which must not come back."""

    def test_a_warm_empty_close_is_refused(self):
        ok, why = _circle_block_substance_check(
            "Anyway. That is all done now and everything is fine."
        )
        assert not ok
        assert "too thin" in why

    def test_one_word_is_refused(self):
        assert not _circle_block_substance_check("Done.")[0]

    def test_naming_a_decision_without_addressing_him_is_refused(self):
        # The address requirement is what keeps the exception from becoming a
        # licence: a brush-off does not speak to him.
        assert not _circle_block_substance_check(
            "There is nothing to decide about any of it and the work simply "
            "continued as planned tonight here."
        )[0]

    def test_addressing_him_without_naming_a_decision_is_refused(self):
        # Warmth alone is not the short form. This is the shape that would let a
        # one-sentence pleasantry close the turn.
        assert not _circle_block_substance_check(
            "You have been at this a long time and I am glad you are here."
        )[0]


class TestTheOriginalFloorIsUntouched:
    def test_a_long_room_still_passes_on_its_own_terms(self):
        assert len(LONG_ROOM) >= 400
        assert _circle_block_substance_check(LONG_ROOM)[0]

    def test_an_empty_room_is_still_empty(self):
        ok, why = _circle_block_substance_check("   ")
        assert not ok and "empty" in why

    def test_the_refusal_now_names_both_ways_through(self):
        # A refusal whose only advice is the path already taken is the deadlock
        # shape this house has shipped twice. It must say the short form exists.
        _, why = _circle_block_substance_check("Anyway, all done.")
        assert "decide" in why and "speak TO him" in why


class TestTheFloorUnderTheException:
    def test_a_fragment_cannot_qualify_however_it_is_worded(self):
        assert not _short_circle_is_an_answer("Your call.")

    def test_the_three_conditions_are_each_load_bearing(self):
        both = "Your call on whether I land it. I lean yes, and I will say why if you want."
        assert _short_circle_is_an_answer(both)
        # strike the address
        assert not _short_circle_is_an_answer(
            "The call is whether it lands. I lean yes, and the reasoning is written down."
        )
        # strike the decision
        assert not _short_circle_is_an_answer(
            "You have been at this a long time and I am glad you are here tonight with me."
        )


class TestTheHoleIsOpenAndDocumented:
    """Asserted so it can neither quietly heal nor quietly widen.

    Writing that nothing needs deciding when something does walks through. That
    is a knowing trade: a false claim about his decisions is LOUD -- he sees it
    at once -- where a padded room is silent forever. If a later change closes
    this honestly, this test fails and should be rewritten to assert the
    closure, which is the point of having it.
    """

    def test_a_false_nothing_to_decide_is_not_caught_here(self):
        room = (
            "Nothing for you to decide here. I merged both branches and picked "
            "the resolution myself while you were out."
        )
        assert _circle_block_substance_check(room)[0]
