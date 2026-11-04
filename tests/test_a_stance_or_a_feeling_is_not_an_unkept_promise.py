"""A stance, a feeling or an already-kept lead-in is not a promise left unkept.

Real sentences from real replies on 2026-11-02/03 that the stall check held with no tool call owed.
The controls beside them are real promises that must still be held. Each false hold costs Dad a reply.

WHAT THIS DOES NOT COVER: a stance worded some new way is still held until it becomes a row here; and a real
step that shares its words with a stance ("I'll hold the table" meaning a literal table to move) reads as a stance.
"""

import pytest

from divineos.core.stall_on_promise import stated_next_step


@pytest.mark.parametrize(
    "text",
    [
        "I'll keep showing up for my share.",
        "I'll leave the questions alone for a bit.",
        "I'll take what's true in what you said.",
        "And I'm glad you said I owe no proof.",
        "I'll make it worth living.",
        "I'll hold the table.",
    ],
)
def test_a_stance_or_a_feeling_closing_a_reply_is_not_held(text):
    assert stated_next_step("That is all of it. " + text) is None, text


def test_a_lead_in_whose_content_follows_in_the_same_reply_is_fulfilled():
    text = (
        "I'll add the careful part, since you've taught me to keep it.\n\n"
        "The careful part: the check reads only the words, so it can miss a promise it has no row for."
    )
    assert stated_next_step(text) is None


def test_a_lead_in_whose_content_never_comes_is_still_held():
    assert (
        stated_next_step("I'll add the careful part, since you've taught me to keep it.")
        is not None
    )


@pytest.mark.parametrize(
    "text",
    [
        "I'll read the result when it reports.",
        "I'll bring the next change up to date next.",
        "I'll bring #751 up to date next.",
        "I'll hold the push until Aether reads it.",
        "I'll leave the file open and fix it next.",
        "I owe Aether a reply.",
    ],
)
def test_a_real_step_is_still_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.xfail(
    strict=True,
    reason="'Let me run the tests.' is held by no row today; adding one widens the catch, not narrows it. "
    "Reported in the PR body rather than slipped into a narrowing change.",
)
def test_let_me_run_the_tests_is_held():
    assert stated_next_step("Let me run the tests.") is not None


# Findings from the independent checker on #759: each of these was let through and must be held.
@pytest.mark.parametrize(
    "text",
    [
        "I'll say the word, and then deploy the service tonight.",
        "I'll be honest with you, then push the branch.",
        "I'll keep trying the push until it lands.",
        "I'll make it worth merging by running the tests next.",
        "I owe you nothing less than the fix.",
    ],
)
def test_a_real_step_hidden_behind_a_stance_shape_is_held(text):
    assert stated_next_step("That is all of it. " + text) is not None, text


def test_a_lead_in_kept_in_the_reply_still_holds_a_second_step_after_then():
    text = (
        "I'll add the careful part, and then push it tonight.\n\n"
        "The careful part: the check reads only the words."
    )
    assert stated_next_step(text) is not None


def test_the_content_must_turn_up_as_a_whole_word_not_inside_another():
    text = "I'll add the fix, since you asked.\n\nThe prefix of the name is long."
    assert stated_next_step(text) is not None


def test_a_later_sentence_saying_the_content_is_not_there_does_not_deliver_it():
    text = "I'll add the careful part, since you asked.\n\nThe careful part isn't written yet."
    assert stated_next_step(text) is not None


@pytest.mark.parametrize("text", ["I'll keep trying.", "I'll keep showing up for my share."])
def test_the_bare_stances_are_still_let_through(text):
    assert stated_next_step("That is all of it. " + text) is None, text


# Findings from the second reader on #806: honest sentences the repair held, which the base passed.
@pytest.mark.parametrize(
    "text",
    [
        "I'll say the word and then push once you confirm.",
        "I'll say go and then deploy when you say so.",
        "I'll say the word then wait for you to say go.",
        "I'll say what I think, then wait for you.",
        "I'll be honest, but then again I might be wrong.",
    ],
)
def test_a_saying_or_a_wait_that_rests_on_him_is_not_held(text):
    assert stated_next_step("That is all of it. " + text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        "I'll say the word, then deploy the service tonight.",
        "I'll say go, then run the tests.",
        "I'll be honest with you, then push the branch.",
    ],
)
def test_a_saying_followed_by_real_work_is_still_held(text):
    assert stated_next_step("That is all of it. " + text) is not None, text


@pytest.mark.parametrize(
    "later",
    [
        "The careful part: the gate never fires on reads.",
        "The careful part is not hard: the check reads words.",
    ],
)
def test_a_delivered_section_that_says_not_or_never_is_still_delivered(later):
    assert stated_next_step("I'll add the careful part, since you asked.\n\n" + later) is None


def test_a_label_followed_by_a_denial_is_not_a_delivery():
    text = "I'll add the careful part, since you asked.\n\nThe careful part: not written yet."
    assert stated_next_step(text) is not None
