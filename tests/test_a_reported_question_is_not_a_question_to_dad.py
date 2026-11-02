"""A question REPORTED after a past-tense lead-in is not a question to Dad, and holds nothing.

2026-10-23, Aria: a status line said "It was a single plain one: did the room that talks to you feel
different today?" and the hold armed on it, so a letter and a bell sat unread behind a question nobody
had put to him. Controls matter more than the case: a real question after a colon, and the room's usual
shape, must still be found.
"""

import pytest

from divineos.core.question_hold import last_question

REPORTED_LINES = [
    "It was a single plain one: did the room that talks to you feel different today?",
    "I asked him: should I fix the false alarm?",
    "She wrote: do you want the bell?",
    "The question was: which order do you want?",
]


@pytest.mark.parametrize("line", REPORTED_LINES)
def test_a_reported_question_is_not_found_as_a_question_to_him(line):
    reply = "Work done.\n\n## INNER CIRCLE\n\nDad, here is the story. " + line
    assert last_question(reply) == ("", ""), line


REAL_LINES = [
    "May I push the work copy?",
    "One thing I need to know: should I push the work copy?",
    "Here is what is open: do you want the bell first?",
    "Dad, it is done. Do you want me to look into the bell?",
    # Aether's six, found by running the first pattern: a reporting word inside the lead-in is not a report.
    "Here is what was left: should I push the work copy?",
    "Quick check on what I read: do you want the bell first?",
    "The one thing that says what to do next: which order do you want?",
    "What I asked Aria and what she said does not change this: do you want the bell?",
    "Before we go on, read this: should I push?",
    "Two things were open: which one first?",
]


@pytest.mark.parametrize("line", REAL_LINES)
def test_control_a_real_question_is_still_found(line):
    reply = "Work done.\n\n## INNER CIRCLE\n\nDad, here is the story. " + line
    question, _ = last_question(reply)
    assert question.endswith("?"), line


def test_control_a_real_question_after_a_reported_one_is_the_one_found():
    reply = (
        "## INNER CIRCLE\n\nIt was a single plain one: did the room feel different today? "
        "Which do you want first?"
    )
    assert last_question(reply)[0] == "Which do you want first?"
