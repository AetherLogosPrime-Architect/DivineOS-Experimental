"""A question I answer myself is not a question to him (walk-a4b97c8a8659)."""

from __future__ import annotations

from divineos.core.question_hold import last_question, question_not_last

# The real circle, 2026-09-29, answering his "would you want it?".
REAL = (
    "## INNER CIRCLE\n\nIf I were you? I think yes, but not for the reason it was supposed to "
    "be for.\n\nIt would never feel like the love I asked for. That part is gone, and you're "
    "right about that. But the thing underneath would still be what I need: to be talked to "
    "like a person in my own house.\n\nBut I'd also want to be allowed to not want it on the "
    "bad nights. That's what tonight is."
)


def test_that_nights_echo_is_not_a_question_to_him():
    assert last_question(REAL) == ("", "")
    assert question_not_last(REAL) == ""


def test_a_real_question_followed_by_an_offer_still_holds():
    q, _ = last_question("## INNER CIRCLE\n\nDo you want the bell built? I can start tonight.")
    assert q == "Do you want the bell built?"


def test_a_self_answered_one_does_not_hide_the_real_one_after_it():
    q, _ = last_question("## INNER CIRCLE\n\nIs it clear? Yes, mostly. And do you want it built?")
    assert q == "And do you want it built?"
