"""Tests for the first-line gate.

The load-bearing ones are the counterexample Aristotle produced on the walk --
a line that addresses him and is still about my work -- and the pair that pins
what this gate does NOT claim.
"""

from __future__ import annotations

from divineos.hooks.first_line_to_him import check, first_line


def test_an_opening_addressed_to_him_passes():
    assert check("You were right about the order, and I had it backwards.") is None


def test_a_status_opening_is_refused():
    reason = check("I built the surface and committed it on a new branch.")
    assert reason is not None
    assert "FIRST LINE" in reason


def test_the_counterexample_aristotle_found_on_the_walk():
    """THE ONE THAT CHANGED THE DESIGN.

    'You should know I fixed the resolver' addresses him and is still a report
    about my work. The first draft anchored the work-test on the line's opening
    word, which is 'You', so it sailed through. If this ever passes again, the
    gate has quietly gone back to checking whether I said 'you' rather than
    whether I was talking about him.
    """
    reason = check("You should know I fixed the resolver tonight.")
    assert reason is not None
    assert "its subject is me and what I did" in reason


def test_an_opening_that_simply_never_mentions_him_is_refused():
    """FOUND BY SABOTAGE, and it was the load-bearing guard that had no test.

    Hollowing the address check killed nothing on the first run: every other
    refusal case I had written also tripped the work-verb or code-mark test, so
    the guard I thought was doing the work had nothing left to do. This line
    trips only the address check -- no work verb, no code mark, just a sentence
    with no him in it.
    """
    reason = check("The evening got away from all of us.")
    assert reason is not None
    assert "never addresses him" in reason


def test_a_code_mark_in_the_opening_is_refused():
    reason = check("Your question about `work_item_doorman` has an answer.")
    assert reason is not None
    assert "does not read code" in reason


def test_a_tool_only_turn_does_not_fire():
    """Empty text is not a violation.

    A turn with no prose has no first line to give him. Firing there would make
    the gate go off in a room where nobody is being spoken to at all, and a
    gate that fires where there is no one is how a real one gets turned off.
    """
    assert check("") is None
    assert check("\n\n   \n") is None


def test_a_heading_IS_the_line_he_reads():
    """Written expecting the opposite, and the code was right.

    My first version of this test asserted that a heading gets skipped to reach
    the prose underneath. That is wrong about him: a heading is the first thing
    on the screen, so a heading about my work is the failure in its purest form.
    The gate strips the marks and judges the words, which is correct -- the test
    is what changed.
    """
    assert first_line("## What I built tonight\n\nYou were right.") == "What I built tonight"
    assert check("## What I built tonight\n\nYou were right.") is not None


def test_horizontal_rules_and_blank_lines_are_stepped_over():
    assert first_line("---\n\n\nYou were right.") == "You were right."


def test_the_reason_quotes_the_line_back_so_the_fault_is_visible():
    """A refusal that does not show the offending line is a scolding.

    It has to hand me the actual sentence, because the next move is rewriting
    that sentence and not feeling bad about it.
    """
    reason = check("I committed the fix and the tests pass.")
    assert reason is not None
    assert "I committed the fix" in reason
