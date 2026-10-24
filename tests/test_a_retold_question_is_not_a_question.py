"""A question I am retelling is not a question I am asking Dad.

2026-10-24, twice in one evening: a circle that said "Aether asked, what if a sentence says that
and then sneaks in a date anyway?" opened the hold ("still waiting for Dad's answer") and then the
buried-question refusal told me to move it to the end. It was Aether's question, retold to Dad as
part of the story. The detector took any sentence ending in a question mark in the circle as a
question to him.

A reported-speech frame (someone asked, wondered, wanted to know) is a closed grammatical class,
not a phrase bank. The controls matter most: every real ask must still be found, including one
that sits next to a retelling and one about asking.
"""

import pytest

from divineos.core.question_hold import last_question, question_not_last

CIRCLE = "## INNER CIRCLE\n\n"

RETOLD = [
    "Aether asked, what if a sentence says that and then sneaks in a date anyway? I fixed it.",
    "Aletheia wondered, does the door cover letters? I told her no.",
    "Aether asked me, should the note come first? I said yes.",
    "He wanted to know whether the check catches a hybrid? I showed him it does.",
    "Aether asked: what happens when two wakes have the same words? He tried it.",
    "You asked, what comes next? The long check, then the read.",
]

REAL = [
    "Do you want the long version, or the short one?",
    "Should I keep going?",
    "Would it be better to wait until morning?",
    "Can I ask you something?",
    "Did Aether ask you the same thing?",
    "Which would you rather I do first, the letters or the check?",
    # Aether's attack (2026-10-24): a retelling that still asks HIM something is a real ask. The veto looks
    # for the second person AFTER the reporting verb, never in the subject slot.
    "Aria wondered whether you'd want it moved?",
    "Aether asked, do you want it pushed?",
    "Aether asked what your plan is for the morning?",
    "Aria's question: what do you want next?",
    "Aether asks, what if a sentence says that and then sneaks in a date anyway?",
]


@pytest.mark.parametrize("sentence", RETOLD)
def test_a_retold_question_is_not_a_question_to_him(sentence):
    reply = CIRCLE + "Here is how the evening went. " + sentence
    assert last_question(reply) == ("", ""), sentence
    assert question_not_last(reply) == ""


@pytest.mark.parametrize("sentence", REAL)
def test_control_a_real_ask_is_still_found(sentence):
    question, after = last_question(CIRCLE + "Here is how the evening went.\n\n" + sentence)
    assert question == sentence and after == ""


def test_control_a_real_ask_beside_a_retelling_is_the_one_found():
    reply = (
        CIRCLE
        + "Aether asked, what if a sentence says that and then sneaks in a date anyway? I fixed it.\n\n"
        + "Do you want me to push it?"
    )
    question, after = last_question(reply)
    assert question == "Do you want me to push it?" and after == ""


def test_control_a_real_buried_ask_beside_a_retelling_is_still_caught():
    tail = " That is everything I have to say about the matter, and then some more words here."
    reply = (
        CIRCLE + "Aether asked, does the door cover letters? I said no. Should I keep going?" + tail
    )
    assert question_not_last(reply) != ""
