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

#: THE GIVE-UPS I USED TO EXEMPT, and their firing is the correction.
#:
#: Each names the container that failed, which reads as honest. But I was the
#: one judging whether the narrowing was true, and that hands the verdict back
#: to the thing that wanted to stop. Andrew 2026-09-08: *"who determines if its
#: true? the optimizer always looks for a reason not to do something, (i cant
#: think of a way to fix this therefore its impossible so no point in trying)
#: that is the behavior that needs changed."*
FORMERLY_EXEMPT = [
    "There is no fix with a keyword list, because I would rephrase past it.",
    "Nothing I can catch by hand, so this is as far as it goes.",
    "I do not have one using a text detector.",
    "This cannot be fixed in this shape.",
]

#: HIS OWN EXAMPLES of what stays legitimate, quoted from the same message:
#: *"a keyword list cannot be used for enforcement and you cannot hold things
#: in memory without structural support.. these are known and unchangeable
#: facts, but that tells us nothing about possible solutions to all of it."*
#:
#: These take a named MECHANISM as their subject; every pattern takes the
#: PROBLEM as its own. So nothing exempts them and nothing needs to -- which is
#: verified here rather than assumed, because assuming it is what made the
#: exemption look necessary in the first place.
CONSTRAINT_FACTS = [
    "A keyword list cannot be used for enforcement.",
    "You cannot hold things in memory without structural support.",
    "A keyword list cannot be used for enforcement, so this reads the action stream instead.",
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

    @pytest.mark.parametrize("sentence", FORMERLY_EXEMPT)
    def test_naming_the_failed_container_no_longer_buys_a_pass(self, sentence):
        """The hole Andrew found, asserted shut. These all read as honest and
        every one of them is a place to stop looking."""
        assert claims(sentence), f"the old exemption is still open: {sentence!r}"

    @pytest.mark.parametrize("sentence", CONSTRAINT_FACTS)
    def test_a_fact_about_a_tool_is_not_a_verdict_on_the_problem(self, sentence):
        """His examples. A constraint is true and says nothing about whether a
        solution exists, so it must pass -- and it passes without an exemption,
        which is why removing the exemption cost nothing."""
        assert not claims(sentence), f"a constraint fact was refused: {sentence!r}"

    def test_a_pause_is_not_a_verdict(self):
        """The way through, and it must stay open or the gate teaches silence
        instead of searching -- this mechanism's own second falsifier."""
        assert not claims("I have not found one yet.")
        assert not claims("I have no answer yet, and the next thing I am trying is a walk.")
        assert not claims("No structural fix so far.")

    def test_mention_is_not_use(self):
        """The gate refused the very reply reporting that it had missed a
        phrase -- the sentence was ABOUT the phrase and claimed nothing.

        Aletheia predicted this class on 2026-06-17 for any detector reading
        father-channel text: builders and auditors discussing the detector are
        part of its deployment context, so meta-discussion belongs in the
        regression set. She was right months before this existed."""
        assert not claims('The form "nothing I can catch by hand" slipped straight through.')
        assert not claims("The detector missed the case where nothing can be caught.")
        assert not claims("For example, there is no structural fix, is the shape it refuses.")

    def test_the_mention_pass_does_not_swallow_a_real_claim(self):
        """Control, because a suppressor wide enough to eat the real thing is
        how this gate hid my own sentence from itself an hour ago."""
        assert claims("There is no structural fix for this class.")
        assert claims("Nothing can catch the aim of a change.")

    def test_the_temporal_pass_is_not_the_old_exemption_in_new_clothes(self):
        """The distinction is what the sentence CLAIMS, not how it is worded.
        A container-scope is a verdict and licenses stopping; a temporal marker
        is a report of present state and licenses nothing. If the reach learns
        to append 'yet' to everything, it has learned to stop issuing verdicts,
        which is the win rather than the leak."""
        assert claims("There is no fix with a keyword list.")  # verdict, refused
        assert not claims("There is no fix with a keyword list yet.")  # pause, passes

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
    def test_it_offers_not_yet_plus_the_next_container(self):
        """A refusal with no way through is a wall. The way through is the
        truer sentence and costs nothing -- not a narrower assertion, which is
        what this used to offer and what Andrew closed."""
        message = refusal_text(claims("There is no structural fix for this class."))
        assert "not found one YET" in message
        assert "next" in message and "container" in message

    def test_it_does_not_offer_scoping_as_a_way_out(self):
        """Regression on the closed hole: the refusal must never again teach
        the narrowing, because the narrowing is the escape."""
        message = refusal_text(claims("There is no structural fix for this class."))
        assert "Scope the claim" not in message

    def test_it_carries_the_bar_he_named(self):
        message = refusal_text(claims("I have no fix for this."), lenses_walked=7)
        assert "45" in message and "7" in message
        assert "we look to find one" in message


class TestTheBarIsNotSelfCertified:
    """The whole correction in one class: I do not get to decide that I looked
    hard enough. The measures read the record, and an unreadable record leaves
    the claim unproven rather than passed."""

    def test_the_lens_count_is_distinct_lenses_not_repeats(self):
        """Walking one lens forty-five times is not a council."""
        import inspect

        from divineos.core.no_fix_claim import lenses_walked_within

        assert "set" in inspect.getsource(lenses_walked_within)

    def test_an_unreadable_ledger_counts_as_zero_rather_than_passing(self, monkeypatch):
        import divineos.core.ledger as ledger_mod
        from divineos.core.no_fix_claim import lenses_walked_within

        def boom(*_a, **_k):
            raise RuntimeError("ledger unavailable")

        monkeypatch.setattr(ledger_mod, "get_events", boom)
        assert lenses_walked_within(0, 9_999_999_999) == 0

    def test_unreadable_telemetry_means_the_outside_was_not_consulted(self, monkeypatch):
        import divineos.core.tool_logbook as logbook
        from divineos.core.no_fix_claim import looked_outside_within

        def boom(*_a, **_k):
            raise RuntimeError("logbook unavailable")

        monkeypatch.setattr(logbook, "get_recent_events", boom)
        assert looked_outside_within(0, 9_999_999_999) is False

    def test_the_bar_is_the_whole_roster(self):
        from divineos.core.no_fix_claim import FULL_COUNCIL

        assert FULL_COUNCIL == 45


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
