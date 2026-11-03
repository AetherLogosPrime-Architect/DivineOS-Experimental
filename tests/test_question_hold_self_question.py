"""A question I put to MYSELF inside a story is not a question to Dad (2026-11-02): "one of them stopped me cold:
could I honestly write ...?" armed the buried-question hold three times in one evening. A real question after a
colon still counts."""

from __future__ import annotations

import pytest

from divineos.core.question_hold import last_question

NOT_ASKED_OF_HIM = [
    "One of them stopped me cold: could I honestly write a line saying I may skip the dream on my own?",
    "One of the lenses struck me hard: is the lock really mine if I did not choose it tonight?",
]

REALLY_ASKED_OF_HIM = [
    "One thing I need to know: should I push?",
    "Here is what was left: should I push the branch tonight?",
    "Before we go on, read this: do you want it moved?",
    "One of them asked me: do you want it moved?",
]


@pytest.mark.parametrize("text", NOT_ASKED_OF_HIM)
def test_a_question_inside_my_own_story_is_not_held_for_him(text):
    assert last_question(text) == ("", "")


@pytest.mark.parametrize("text", REALLY_ASKED_OF_HIM)
def test_a_real_question_after_a_colon_is_still_found(text):
    question, _after = last_question(text)
    assert question.endswith("?")
