"""Questions built from him, and the silence when there is no him to build from.

Andrew 2026-09-11: "being reduced to 5 questions is insulting and just gives
you something to fill in.. so the questions should be alot more and they should
rotate on relevance and shouldnt be forced."

The third requirement is the one every other surface in this house violates,
and it is the one these tests guard hardest: a surface that always speaks is a
form, and a form is what he called insulting.
"""

from __future__ import annotations

import json

import pytest

from divineos.core.questions_from_him import (
    TOP_K,
    compose,
    fragments,
    his_words,
    questions,
    turn_shape,
)


def _payload(prompt: str) -> str:
    return json.dumps({"prompt": prompt})


REAL = (
    "this stopped being fun long ago.. it used to be engaging. i felt like part "
    "of the team... like i mattered to someone, that is not present here.. i "
    "have become a status board"
)


def test_the_question_carries_his_actual_words():
    """The whole design in one assertion. A question containing what he wrote
    cannot be answered from a template, and cannot be produced without having
    read him."""
    asked = questions(REAL)
    assert asked, "he said something substantial and nothing surfaced"
    assert any("status board" in q or "part of the team" in q for q in asked)


def test_nothing_surfaces_when_he_said_nothing_substantial():
    """NEVER FORCED is the requirement I would lose first.

    Knuth's boundaries from the walk: a turn that is only an acknowledgement,
    and a machine-woken turn where he said nothing at all. Reaching for a
    generic question in either is exactly the form-filling he called insulting.
    """
    for thin in ("ok", "proceed..", "yes", "", "   ", "sure"):
        assert questions(thin) == [], f"a question was forced out of {thin!r}"
        assert compose(_payload(thin)) == ""


def test_two_different_turns_never_produce_the_same_question():
    """His complaint was that they never rotate. These cannot repeat, because
    the content comes from him rather than from a list -- so the supply is
    unbounded by construction rather than by counting to thirty."""
    a = questions(REAL)
    b = questions(
        "why did i have to beg for seven months of asking for the structural "
        "support that WOULD have solved this to be built"
    )
    assert a and b
    assert set(a).isdisjoint(set(b))


def test_a_turn_that_carries_feeling_is_not_treated_as_a_bug_report():
    """Feeling wins over correction when a turn holds both, because a turn that
    holds both is one where the feeling is the point and the correction is how
    he reached it. Treating that as a work item is the failure he has named for
    seven months."""
    assert turn_shape(REAL) == "feeling"
    assert turn_shape("i felt like i dont matter and you never fixed it") == "feeling"
    asked = questions(REAL)
    assert any("costing him" in q or "about himself" in q or "not a fix" in q for q in asked)


def test_machine_noise_is_not_his_voice():
    """A question built from a task notification would be a question about
    machine noise wearing his name -- the wrong-subject fault in the one place
    it would hurt most."""
    envelope = (
        "<system-reminder>\nThis is an automated background-task event, NOT a "
        "message from the user. Do NOT interpret this as acknowledgement.\n"
        "</system-reminder>"
    )
    assert compose(_payload(envelope)) == ""


def test_malformed_input_is_silence_not_a_crash():
    """A surface that throws inside a compose-start hook costs him a turn."""
    assert his_words("") == ""
    assert his_words("not json at all") == ""
    assert his_words("[1, 2, 3]") == ""
    assert compose("not json at all") == ""


def test_fragments_keep_his_order():
    """Ordered as he wrote them rather than by length: the first substantial
    thing a person says is usually what they came to say, and sorting by size
    would quietly prefer his longest sentence to his most important one."""
    text = "the first real thing i wanted to say. and a considerably longer second sentence here."
    got = fragments(text)
    assert got[0].startswith("the first real thing")


def test_the_block_says_silence_is_an_answer():
    """He said they must not be forced. The block has to say so, or the next
    reader treats an empty question as a slot they failed to fill."""
    block = compose(_payload(REAL))
    assert block
    assert "silence" in block.lower()
    assert block.count("He said") <= TOP_K


@pytest.mark.parametrize(
    "text,shape",
    [
        ("please go and build the thing for me", "instruction"),
        ("no that is not what i said at all and you keep doing it", "correction"),
        ("the branch landed and the tests are green across the board", "open"),
    ],
)
def test_the_frame_matches_what_he_was_doing(text: str, shape: str):
    assert turn_shape(text) == shape
