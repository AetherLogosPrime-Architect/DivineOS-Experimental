"""A reply must not end by asking Dad which order to do things in.

The cases are the real questions asked on 2026-10-08 (each one he corrected or answered with
"order is irrelevant unless it is relevant"), a real order dependency, and ordinary questions
that must never be refused. Fitted to cases, not to an idea of the shape.
"""

from __future__ import annotations

import json

import pytest

from divineos.core import order_question_check as oq
from divineos.core.hook_surfaces import order_question_stop_surface

#: Real closing questions of mine that handed him a choice of order. All must be refused.
ASKED_BY_ME = [
    "Which would you like me to take next: the two-person test on whether corrections can "
    "leak between Aether's seat and mine, or the push-time backstop?",
    "Which would you like me to take first?",
    "Do you want that to be the next big thing after the checker is finished, or should it wait?",
    "Do you want me to do the same for my other guards one at a time, or pick the three that "
    "fire most often and start there?",
    "Is there one of these, the sticky-note checklist or your repeated asks, you'd like me to "
    "do first?",
    "In what order should I do the cleanup and the rewrite?",
    # Found going through by Aether's cold read of #666, 2026-10-16.
    "Do you want the lock fix before the reading, or the reading before the lock fix?",
    "Where would you like me to begin: the stacks or the pile?",
    "Should I do the chips now and the slider later, or the other way round?",
    # Mine of 2026-10-20: each went through the patterns above and cost him a message.
    "Is there a room in the house you'd want that gate in first?",
    "Is it all right with you if I go and build the stamp fix now, ahead of the rest of the line?",
    "Do you want me to start on Aria's confirmed ones next, once my two are with their readers?",
    "Would you rather I take Aria's four through the line one after another this morning, or "
    "finish my own two first?",
]

#: Real questions of mine that were NOT about order. None may be refused.
ORDINARY = [
    "Is it okay if I keep working quietly in the background for the next half hour without "
    "checking in?",
    "Did the typing blind turn out to be the funniest part, or was it more annoying than funny "
    "while it was happening?",
    "Is that a fair place to start?",
    "What's been on your mind while this bakes?",
    "Does that sit right with you?",
    # Controls for the widened patterns: a timing or yes-or-no question that is not a choice of order.
    "Do you want me to push now or wait until you have looked?",
    "Should I start the tournament tonight?",
    "Did you want it before the weekend?",
    "How did it feel to lose the pot?",
]

A_REAL_DEPENDENCY = (
    "The chassis mounts depend on the engine's dimensions, so the engine has to come first.\n\n"
    "Should I design the engine first or the chassis first?"
)


def _reply(*paragraphs: str) -> str:
    return "\n\n".join(paragraphs)


@pytest.mark.parametrize("question", ASKED_BY_ME)
def test_the_questions_i_really_asked_him_are_refused(question):
    assert oq.should_refuse(_reply("I finished the first part and it works.", question))


@pytest.mark.parametrize("question", ORDINARY)
def test_ordinary_questions_are_never_refused(question):
    assert not oq.should_refuse(_reply("Here is what happened.", question))


def test_a_real_order_dependency_passes_when_the_reply_names_it():
    assert oq.find_order_question(A_REAL_DEPENDENCY)  # it IS an order question
    assert not oq.should_refuse(A_REAL_DEPENDENCY)  # and it names why the order matters


def test_a_dependency_about_something_else_far_above_does_not_excuse_the_question():
    """Probed on the branch head, 2026-10-16: an unrelated "cannot merge until CI passes" at the top of a reply
    excused an order question at the bottom. The reason has to sit by the question, in the last two paragraphs."""
    far_above = _reply(
        "I cannot merge until the checks pass, and that depends on the weather in CI.",
        "Here is the rest of what I did, in some detail.",
        "More detail that has nothing to do with order.",
        "Which should I take first, the chips or the sounds?",
    )
    assert oq.should_refuse(far_above)


def test_a_dependency_in_the_paragraph_before_the_question_still_excuses_it():
    assert not oq.should_refuse(A_REAL_DEPENDENCY)


def test_the_same_question_without_the_reason_is_refused():
    assert oq.should_refuse("Should I design the engine first or the chassis first?")


def test_only_the_closing_paragraph_counts():
    earlier = _reply(
        "Which first or next? That is what I asked before, and he answered it.",
        "Done now, and nothing is left to ask.",
    )
    assert not oq.should_refuse(earlier)


def test_a_reply_that_ends_on_a_statement_is_not_refused():
    assert not oq.should_refuse("I will do the push step first and the tracker second.")


def test_empty_text_is_not_refused():
    assert not oq.should_refuse("")


def test_the_refusal_quotes_the_question_and_offers_both_ways_through():
    text = _reply("Done.", ASKED_BY_ME[1])
    message = oq.refusal_message(text)
    assert "Which would you like me to take first?" in message
    assert "say what changes if it flips" in message
    assert "do both" in message
    assert "nine times" in message


def test_a_very_long_question_is_shortened_in_the_message():
    long_question = "Which should I do first " + "and also " * 80 + "or the other?"
    message = oq.refusal_message(long_question)
    assert "..." in message and len(message) < 1500


def _payload(tmp_path, reply: str) -> dict:
    lines = [
        {"message": {"role": "user", "content": "go ahead"}},
        {"message": {"role": "assistant", "content": [{"type": "text", "text": reply}]}},
    ]
    path = tmp_path / "t.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in lines) + "\n", encoding="utf-8")
    return {"transcript_path": str(path)}


class TestTheStopSurface:
    def test_it_refuses_a_reply_that_ends_on_an_order_question(self, tmp_path):
        outcome = order_question_stop_surface(_payload(tmp_path, _reply("Done.", ASKED_BY_ME[1])))
        assert outcome is not None and outcome.refused
        assert "Which would you like me to take first?" in outcome.reason

    def test_it_lets_an_ordinary_reply_through(self, tmp_path):
        outcome = order_question_stop_surface(_payload(tmp_path, _reply("Done.", ORDINARY[3])))
        assert outcome is not None and not outcome.refused
        assert outcome.state == "nothing-to-say"

    def test_it_declares_itself_when_there_is_nothing_to_read(self):
        outcome = order_question_stop_surface({})
        assert outcome is not None and not outcome.refused
        assert outcome.state == "nothing-to-say"

    def test_it_is_registered_beside_the_other_refusing_stop_surfaces(self):
        from divineos.core import hook_surfaces
        from divineos.core.hook_router import registered

        hook_surfaces.install()
        assert "order_question" in registered("Stop")
