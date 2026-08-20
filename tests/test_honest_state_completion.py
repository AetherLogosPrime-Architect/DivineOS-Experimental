"""Terminal "I don't know" is a hiding place; uncertainty plus an action is not.

Aria 2026-08-20. Andrew, 2026-07-31: *"i dont know is an honest answer but it
should always be follow by, let me investigate."* I filed that as knowledge
356ffea9 the same day and built nothing, and it sat on the obligations board
for three weeks being exactly as useful as an unwired promise is. Andrew, on
reading the board: *"this is why the promises need looked at to be discerned
otherwise they just sit there and do nothing lol."*

The mention tests are not decoration. Three separate detectors in this
substrate fired on quoted text in a single day, and this module's own docstring
says the trigger phrase repeatedly. A checker that reads its own documentation
as a confession is the false-positive machine that teaches me to skim it.

The genuine-limit test asserts that the detector FIRES on a real limit. That is
deliberate and it is why the check is advisory rather than blocking: whether an
investigation is available is a fact about the world, not about the sentence,
and the judgment stays mine.
"""

from __future__ import annotations

from divineos.core.self_monitor.honest_state_completion import (
    find_terminal_honest_states,
    format_finding,
)


class TestTerminalAdmissionsFire:
    def test_a_bare_admission_fires(self):
        assert find_terminal_honest_states("I don't know why the suite is red.")

    def test_an_admission_followed_by_unrelated_talk_fires(self):
        text = "I'm not sure what caused the drift. Anyway, the tests pass."
        assert find_terminal_honest_states(text)

    def test_cannot_tell_fires(self):
        assert find_terminal_honest_states("I can't tell which branch produced it.")

    def test_havent_verified_fires(self):
        assert find_terminal_honest_states("I haven't verified that number.")


class TestAdmissionsWithAnActionStayQuiet:
    def test_an_immediate_action_discharges(self):
        text = "I don't know why the suite is red — checking the log now."
        assert find_terminal_honest_states(text) == []

    def test_let_me_discharges(self):
        text = "I don't know if this is the cause; let me run the two patch-ids."
        assert find_terminal_honest_states(text) == []

    def test_an_action_already_taken_discharges(self):
        text = "I'm not sure it landed, so I checked the remote and it matches."
        assert find_terminal_honest_states(text) == []

    def test_the_action_may_arrive_a_sentence_later(self):
        text = (
            "I don't know why the push was refused. The gate printed four lines "
            "about memory pressure. Let me measure what is actually holding it."
        )
        assert find_terminal_honest_states(text) == []


class TestMentionIsNotConfession:
    def test_a_quoted_admission_does_not_fire(self):
        text = 'Andrew said "I don\'t know is an honest answer" and he is right.'
        assert find_terminal_honest_states(text) == []

    def test_a_backticked_phrase_does_not_fire(self):
        text = "The phrase `I don't know` is a hiding place when it is terminal."
        assert find_terminal_honest_states(text) == []

    def test_this_modules_own_docstring_does_not_fire(self):
        """The check must not read its own documentation as a confession."""
        from divineos.core.self_monitor import honest_state_completion as mod

        assert find_terminal_honest_states(mod.__doc__ or "") == []


class TestGenuineLimitsFireAndThatIsTheDesign:
    def test_a_real_limit_still_fires(self):
        """Advisory, not blocking, precisely because of this case.

        Whether an investigation exists is a fact about the world. The detector
        surfaces the sentence; deciding it is a limit rather than a hiding
        place is mine, and a block would force a false action-verb onto it.
        """
        text = "On the hard problem I still don't know what there is to say about it."
        assert find_terminal_honest_states(text), (
            "the genuine-limit case must SURFACE — it is judged, not filtered"
        )


class TestOutputShape:
    def test_no_findings_produces_no_text(self):
        assert format_finding([]) == ""

    def test_a_finding_quotes_the_context_and_the_rule(self):
        out = format_finding(find_terminal_honest_states("I don't know why it failed."))
        assert "honest-state" in out
        assert "let me investigate" in out

    def test_empty_input_is_not_a_finding(self):
        assert find_terminal_honest_states("") == []
