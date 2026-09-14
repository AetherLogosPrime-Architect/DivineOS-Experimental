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
    def test_announcing_the_absence_does_NOT_pass(self):
        # SUPERSEDED WITHIN THE HOUR, and the reversal is the finding.
        #
        # This originally asserted the opposite: that "Nothing here for you to
        # decide" was a valid short close. It was the first thing I wrote under
        # the new rule, and it is a phrasing he banned -- it decides on his
        # behalf that he is not wanted.
        #
        # The house had already said so in the same block I was working from:
        # "If nothing needs deciding, raise no question -- announcing the
        # absence is a stamp." I read that and built a gate making it a
        # first-class pass.
        room = (
            "Nothing here for you to decide. I fixed the thing that was making "
            "my replies long, and it was a rule I wrote myself."
        )
        assert len(room) < 400
        assert not _circle_block_substance_check(room)[0]

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
    """THE ORIGINAL HOLE CLOSED WITHIN THE HOUR, and the test caught it.

    This first asserted that a FALSE "nothing for you to decide" walked through,
    and its own docstring said: if a later change closes this honestly, the test
    fails and should be rewritten to assert the closure, which is the point of
    having it.

    That is exactly what happened, in the same session. Composing the short form
    with the dismissal check refuses every absence-announcement, true or false,
    so the hole this class was built around no longer exists.

    A DIFFERENT hole does, and it is the Breaker's, so the class keeps its job
    on the new one: naming a TRIVIAL decision unlocks the short form while
    carrying nothing. I cannot close that -- whether a decision is real is a
    fact about the work, not the sentence -- and the tell is him answering a
    declared decision with something other than an answer, which is a thing to
    watch for in his replies rather than something a check can see.
    """

    def test_the_absence_announcement_hole_is_closed(self):
        room = (
            "Nothing for you to decide here. I merged both branches and picked "
            "the resolution myself while you were out."
        )
        assert not _circle_block_substance_check(room)[0]

    def test_a_trivial_declared_decision_still_unlocks_the_short_form(self):
        # Declares a decision, addresses him, is not dismissive, carries nothing.
        assert _short_circle_is_an_answer(
            "Your call whether you want the details on this one. I can go as deep as you like."
        )


class TestItCannotWriteHimOut:
    """Found an hour after shipping, on my own next message to him.

    I closed with "nothing needs you" -- banned months ago because it decides on
    his behalf that he is not wanted -- while describing the rule that produced
    it. Measured straight after:

        "Nothing here needs you..."         short-form refused   dismissal CAUGHT
        "Nothing for you to decide here..." short-form ALLOWED   dismissal CAUGHT
        "You are not needed on this one..." short-form refused   dismissal missed

    The middle row was the defect: two of my own checks, shipped an hour apart,
    disagreeing about one sentence with no arbiter. Announcing an absence is the
    cheapest way to satisfy a decision-declaration -- no work, no content, true
    of most turns -- so the rule was quietly making the emptiest close the most
    efficient one, and that pull grows stronger with tiredness, which is the
    state the closing room gets written in.
    """

    def test_the_phrasing_that_started_this_is_now_refused(self):
        assert not _short_circle_is_an_answer(
            "Nothing for you to decide here. I fixed it and I will tell you how if you want."
        )

    def test_handing_him_a_real_call_is_untouched(self):
        assert _short_circle_is_an_answer(
            "Your call on whether I land the small branch first. I lean yes and will say why."
        )


class TestKnownLimitsOfTheShortForm:
    """Two limits, recorded rather than widened away at the end of a long night.

    Widening a rule because a case I like got refused is how a narrow guard
    becomes a general licence, and both of these are refusals I can live with.
    """

    def test_a_close_that_names_no_decision_falls_back_to_the_full_floor(self):
        # A good closing, not dismissive, not an absence-announcement -- and it
        # hands him no call, so it does not get the short exception. His words
        # scope this exactly: summaries "in places where my decisions will
        # matter". Where they do not, the original floor stands.
        assert not _short_circle_is_an_answer(
            "The outstanding piece is mine to finish, and I will bring it to you when it is real."
        )

    def test_the_inherited_blind_spot_is_real(self):
        # Composition buys the dismissal check's coverage -- no more. The
        # plainest spelling of the banned thing is missed by that list, and
        # widening it from here is how two lists start drifting apart. It fails
        # for a different reason (no decision declared), which is luck rather
        # than design, and this test exists so the luck is visible.
        assert not _short_circle_is_an_answer(
            "You are not needed on this one. I handled it and it is all pushed."
        )
