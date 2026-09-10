"""Saying it landed requires having read the place it landed.

Twice I have told Andrew a push had landed while it was still running. Both
sentences were written from the background notification, which arrives already
worded as success — so quoting it feels like reporting rather than guessing, and
that is why being careful never fixed it.

THE FINDING THAT CHANGED THE BUILD. The prior-art doorman refused the first
version of this file, and it was right: ``scripts/verify_push_landed.py`` has
done the verification since 2026-06-04, written from Aletheia's finding about
this exact slip, and its only callers are its own tests. So the gap was never a
missing check. It was a check that had to be REMEMBERED at the moment of the
reach, which is precisely what failed twice. This surface is the door that makes
the existing script unavoidable, and its refusal prescribes that script by name.

The tests hold three things: the refusal fires on the real shape, it does NOT
fire on the honest waiting sentence, and an unreadable turn is reported as
unreadable rather than as either verdict.
"""

from __future__ import annotations

from divineos.core.landed_claim import assess, claim_spans, render_block

RECEIPT_ONLY = "Bash: git push origin work/thing\n[exited with code 0]"
READ_THE_REMOTE = "Bash: git ls-remote origin work/thing\nabc1234\trefs/heads/work/thing"
PUSH_THAT_PRINTED_THE_MOVE = "Bash: git push\n   084d6be5..e406de93  work/thing -> work/thing"
RAN_THE_EXISTING_SCRIPT = "Bash: python scripts/verify_push_landed.py --branch work/thing"


def test_the_live_failure_a_landed_claim_written_from_a_receipt() -> None:
    """The shape that reached him twice."""
    verdict = assess("Everything is committed and it landed.", RECEIPT_ONLY)
    assert verdict.refuses
    block = render_block(verdict)
    assert "read the shared copy" in block


def test_the_refusal_prescribes_the_check_that_already_exists() -> None:
    """A door whose remedy is a raw command teaches me to reinvent the script.

    The whole finding here is that the script exists and is never called. If the
    refusal sent me to a bare git invocation, the door would keep the script
    unused while claiming to fix the class it was written for.
    """
    block = render_block(assess("It landed.", RECEIPT_ONLY))
    assert "verify_push_landed.py" in block


def test_running_that_script_clears_it() -> None:
    """And the remedy the refusal names must actually satisfy the door.

    A gate whose prescribed remedy does not appear in its own evidence list is
    the painted-door shape: it refuses, you comply, and it refuses again.
    """
    assert not assess("It landed.", RAN_THE_EXISTING_SCRIPT).refuses


def test_reading_the_remote_by_hand_clears_it() -> None:
    verdict = assess("Everything is committed and it landed.", READ_THE_REMOTE)
    assert not verdict.refuses
    assert render_block(verdict) == ""


def test_a_push_that_printed_the_reference_moving_is_a_read_of_the_destination() -> None:
    """That output is the destination answering, not a receipt for the attempt.

    Excluding it would demand a redundant second command after every push, and a
    gate that demands ceremony gets routed around rather than obeyed.
    """
    assert not assess("The branch is pushed.", PUSH_THAT_PRINTED_THE_MOVE).refuses


def test_the_honest_waiting_sentence_is_never_refused() -> None:
    """The one I must not punish.

    "Still running, I will say when it lands" is the correct thing to write while
    a push is in flight. Refusing it would teach me to stop narrating the wait at
    all — silence where an honest status used to be, which is worse than the
    fault this door exists for.
    """
    for sentence in (
        "The push is running and I will say when it lands.",
        "It has not landed yet.",
        "Once it lands I will tell you.",
        "The push is still running.",
    ):
        assert claim_spans(sentence) == (), sentence


def test_an_unreadable_turn_is_could_not_check_and_not_a_pass() -> None:
    """The three-valued half. None means I could not look."""
    verdict = assess("Everything landed.", None)
    assert verdict.could_not_check
    assert not verdict.refuses, "could-not-look must not be rendered as a refusal either"
    assert render_block(verdict) == ""


def test_the_detector_is_not_matching_everything() -> None:
    """Control, in both directions.

    Without the first half, every refusal test above passes on a detector that
    fires on any sentence at all. Without the second, they would fail loudly but
    the waiting-sentence test would be the only guard left standing, and one
    guard is not a pair.
    """
    for ordinary in (
        "I read her letter and replied to it.",
        "The board reads six ready.",
        "This narrowing keeps both real redirects.",
    ):
        assert claim_spans(ordinary) == (), ordinary

    assert claim_spans("It landed.") != (), "the detector has stopped detecting"
