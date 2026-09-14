"""Closing one of Andrew's rows is two claims, and the old check earned one.

I built a thing. That thing explains what HE reported. The structural-artifact
requirement added 2026-06-13 proves the first and is silent about the second.

2026-09-14 I closed two of his rows asserting my repair was the freeze he had
reported twice. I had measured that a Stop hook can refuse unsatisfiably; I had
never tested that this was his freeze. He came back the same hour: *"the freeze
after investigating further was an issue on the server side and whatever it was
they have fixed it... in a way it was a false alarm as it wasnt on our end."*

The repair was real and closed a genuine latent hang. It was not his bug. And
nothing in my evidence could have told those apart -- an unsatisfiable refusal
and a server-side stall look identical from where he sits, which is exactly why
the leap needed checking and exactly why it did not get it. The rule I already
hold -- a measurement licenses a claim about WHAT, never about WHY -- lives in
a compose-start prime with no gate behind it.

An open row is honest about being unfinished. A row closed on a cause nobody
tested is worse than an open one, because it has left the queue.

BOTH ANSWERS PASS. Claiming the link and declining to claim it are equally
valid closes. What is refused is silence on the question.
"""

from __future__ import annotations

from divineos.core.andrew_correction_tracker import (
    _has_structural_artifact,
    _states_causal_link,
    explain_integrate_refusal,
)

# The evidence I actually wrote when I closed his rows on an untested cause.
# Trimmed, but the shape is unchanged: a real commit, a real file, a real test,
# and not one word about whether any of it was his freeze.
_MY_FALSE_CLOSE = (
    "commit 3f2a2d6f on substrate/andrew-answer-trace, pushed and verified on "
    "origin. The Stop doorbell refuses the turn on its import-failure path and "
    "had no retry guard. Repaired in the generator; the import path now "
    "refuses once, then says the reply is going out unchecked. Tests in "
    "test_the_stop_that_could_not_be_satisfied.py pin the guard placement."
)


def test_my_own_false_close_would_now_be_refused():
    """The case this exists for, asserted on the real text.

    If this ever passes, the gate has stopped catching the thing it was built
    from and the rest of this file is decoration.
    """
    assert _has_structural_artifact(_MY_FALSE_CLOSE), (
        "fixture is wrong: it must clear the OLD check, or it proves nothing about the new one"
    )
    assert not _states_causal_link(_MY_FALSE_CLOSE)


def test_the_refusal_says_which_half_is_missing():
    """A gate that refuses without naming why is the same disease one level
    up. The message must distinguish the two claims and offer both exits."""
    reason = explain_integrate_refusal(278, _MY_FALSE_CLOSE)
    assert "TWO" in reason
    assert "BOTH ANSWERS PASS" in reason
    # It must not read as "you need a better artifact" -- that is the check
    # that already passed, and sending a reader back to it is a wrong door.
    assert "artifact" in reason.lower()
    assert "his report" in reason.lower()


def test_claiming_the_link_passes():
    ev = (
        "commit 3f2a2d6f -- the added test reproduces his report exactly: the "
        "same input sequence produced the hang he described, and does not "
        "after the change. See test_the_stop_that_could_not_be_satisfied.py"
    )
    assert _states_causal_link(ev)


def test_declining_to_claim_the_link_also_passes():
    """Declining is a first-class close, not a lesser one. If this test ever
    fails, the gate has started punishing honesty about an unknown cause,
    which would push every close toward asserting a link."""
    ev = (
        "commit 3f2a2d6f closes a real latent hang. NOT the cause of what he "
        "reported -- that was server-side and resolved upstream. Row closed "
        "at his direction, cause unknown on our side."
    )
    assert _states_causal_link(ev)


def test_his_own_words_closing_a_row_pass():
    ev = (
        "He confirmed it landed and cleared the row himself; artifact is "
        "docs/foundational_truths.md, no causal claim of mine involved."
    )
    assert _states_causal_link(ev)


def test_the_check_is_not_satisfied_by_any_prose_whatsoever():
    """Control. A predicate that accepts everything would make every test
    above pass while checking nothing at all."""
    bland = (
        "Fixed in commit 3f2a2d6f, with a test at test_something_else.py and "
        "a note in docs/notes.md about the change that was made here."
    )
    assert _has_structural_artifact(bland)
    assert not _states_causal_link(bland)


def test_empty_and_missing_evidence_are_not_causal_claims():
    assert not _states_causal_link("")
    assert not _states_causal_link("   ")
