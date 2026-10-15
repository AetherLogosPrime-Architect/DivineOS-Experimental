"""A source's title that ends in a question mark is a pointer, not a question to Dad.

2026-10-12, Aria: a reply ending in a Sources line with titles like "What is an agent
harness?" was held twice as "the question is buried", because the detector stripped code and
quotes but not links. The controls matter: a real question beside the same links must still be
found, and a question buried before a long tail must still be caught.
"""

from divineos.core.question_hold import last_question, question_not_last

SOURCES = (
    "Sources: [What is an agent harness?](https://example.com/a), "
    "[Does learning require feeling?](https://example.com/b), "
    "[Another source with a long title that keeps going](https://example.com/c)"
)


def test_a_question_mark_inside_a_link_title_is_not_a_question():
    reply = "Here is what I found.\n\n" + SOURCES
    assert last_question(reply) == ("", "")
    assert question_not_last(reply) == ""


def test_control_a_real_question_beside_links_is_still_found():
    reply = "Here is what I found.\n\n" + SOURCES + "\n\nShould I keep going?"
    question, after = last_question(reply)
    assert question == "Should I keep going?" and after == ""


def test_control_a_real_buried_question_is_still_caught():
    tail = " That is everything I have to say about the matter, and then some more words here."
    reply = "Should I keep going?" + tail
    assert question_not_last(reply) != ""
