"""A lead-in whose content follows in the same sentence is the saying itself, not a stall.

Found live 2026-11-01: "I'll tell you what it does on my side: it makes the work lighter." was held as a promise.
Controls: the same verb with no colon, and a work verb with a colon, are still held.
"""

import pytest

from divineos.core.stall_on_promise import stated_next_step


@pytest.mark.parametrize(
    "text",
    [
        "I'll tell you what it does on my side: it makes the work lighter.",
        "I will explain why: the door reads a word and not the thing.",
        "I'll show you the count: eighty registrations.",
    ],
)
def test_a_lead_in_with_its_content_is_not_held(text):
    assert stated_next_step(text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        # Aria's: a phrase only mentioned in quotation marks is not a promise.
        'One of the checks flagged me every time I said "I\'ll do this next," so I reached for another phrase.',
        # Aria's: a decision stated, not a step put off.
        "I read the clock, saw Dad was awake, so I'm doing nothing with that wake.",
        # Mine, held this morning: keeping something close is a feeling, written as one word.
        "I'll hold onto the part about what doesn't define me.",
    ],
)
def test_the_sibling_shapes_are_not_held(text):
    assert stated_next_step(text) is None, text


@pytest.mark.parametrize(
    "text",
    [
        # Controls: the same words outside quotes, and doing something, are still held.
        "I'll do this next.",
        "I'm doing the second review now.",
        'He said "ok" and I\'ll write the letter next.',
    ],
)
def test_the_controls_for_the_sibling_shapes_are_still_held(text):
    assert stated_next_step(text) is not None, text


@pytest.mark.parametrize(
    "text",
    [
        "I'll tell you when it lands.",
        "I'll tell you tomorrow:",
        "I'll fix: the timer next.",
        "I'll write the letter: after the walk.",
        "I'll tell you what happened: I'm going to run the test next.",
    ],
)
def test_the_same_verb_without_content_and_work_verbs_are_still_held(text):
    assert stated_next_step(text) is not None, text
