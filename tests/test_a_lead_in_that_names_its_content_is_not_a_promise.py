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
        "I'll tell you when it lands.",
        "I'll tell you tomorrow:",
        "I'll fix: the timer next.",
        "I'll write the letter: after the walk.",
        "I'll tell you what happened: I'm going to run the test next.",
    ],
)
def test_the_same_verb_without_content_and_work_verbs_are_still_held(text):
    assert stated_next_step(text) is not None, text
