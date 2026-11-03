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
