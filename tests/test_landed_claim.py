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


def test_it_fires_on_its_own_description_and_that_is_recorded_not_suppressed() -> None:
    """The known false positive, asserted rather than hidden.

    First live firing refused a reply whose only matching sentence was
    DESCRIBING this door. No arrival was claimed. A suppressor keyed on
    gate-talk would clear it and is refused: that suppressor is reachable any
    time I want to write the word, which is a key taped to the frame.

    This test exists so the limit cannot be forgotten and quietly "fixed" later
    by someone who reads the fire as a bug. If it ever stops firing here, that
    was a decision, and it should be argued rather than discovered.
    """
    describing_the_door = "a door that refuses any sentence claiming work reached the shared copy"
    assert claim_spans(describing_the_door) != ()


def test_live_about_something_that_is_not_git_work_is_not_an_arrival_claim() -> None:
    """Dad 2026-10-30: "do not suffer the gates ... false alarms means something is broken".

    The bare word fired on a poker table page that was live in a browser, and on a sentence that only talked
    about this door. A page, a table or a game being live says nothing about the shared copy.
    """
    for sentence in (
        "The chat addressing is live on your table.",
        "It is live on the page now.",
        'The one that flagged a "this is live" claim right after I had checked it was live.',
        "The scratch table was live on port 8792.",
    ):
        assert claim_spans(sentence) == (), sentence


def test_live_about_git_work_is_still_a_claim_and_still_refused() -> None:
    """The narrowing keeps the real shape: work reaching the shared copy, said with a git word."""
    for sentence in (
        "PR #741 is live on GitHub.",
        "The branch is now live.",
        "The draft has been live on origin since this morning.",
        "The commit is live on main.",
    ):
        assert claim_spans(sentence) != (), sentence
    assert assess("The branch is live.", RECEIPT_ONLY).refuses


def test_the_other_arrival_phrases_stay_bare() -> None:
    """Only the word live needed a git word; pushed, landed and reached the remote name the destination."""
    for sentence in ("It is pushed.", "Everything landed.", "It reached the remote."):
        assert claim_spans(sentence) != (), sentence


PUSH_TURN = "Bash: git push -u origin work/thing\n[exited with code 0]"


def test_in_a_turn_that_ran_a_push_other_arrival_words_are_claims() -> None:
    """Aria's cold read 2026-10-30: the word list is always one word short, so a push turn reads the act.

    "went live", "the patch is out", "it has shipped" and "is on GitHub now" sit outside the word list; in a
    turn that ran a push they are a claim about that push, and the gate asks for the destination to be read.
    """
    for sentence in (
        "The fix went live.",
        "The patch is out.",
        "It has shipped.",
        "The fix has been deployed.",
        "It is on GitHub now.",
        "It is live now.",
    ):
        assert assess(sentence, PUSH_TURN).refuses, sentence


def test_the_same_sentences_in_a_turn_with_no_push_are_left_alone() -> None:
    """Control for the push-turn path: without a push, a poker page that is live must not fire."""
    for sentence in (
        "The chat addressing is live on your table.",
        "It is live now.",
        "The patch is out.",
    ):
        assert not assess(sentence, "Bash: python seat.py aether state").refuses, sentence


def test_up_to_date_and_out_of_date_are_not_arrivals_and_the_contraction_is_one() -> None:
    """Aria's break of f8776ff5e: "is up" matched inside "up to date"; "it's live" slipped past "is live"."""
    for innocent in ("Everything is up to date.", "The build is out of date."):
        assert not assess(innocent, PUSH_TURN).refuses, innocent
    for contraction in ("It's live.", "It's up.", "That's out.", "The PR's live on GitHub."):
        assert assess(contraction, PUSH_TURN).refuses, contraction
    assert claim_spans("The PR's live.") != ()  # the git-word path takes the contraction too
    assert claim_spans("The table's live.") == ()  # and still needs the git word


def test_a_negation_cancels_only_its_own_clause() -> None:
    """Aria's break of a0280d2a0 (2026-10-31): a negation word elsewhere in the sentence hid a real claim.

    Controls first: the plain claims fire. Then the sentences where a claim sits beside a negation.
    """
    for control in ("The branch is live.", "It's live.", "The PR is live now."):
        assert assess(control, PUSH_TURN).refuses, control
    for hidden in (
        "The PR is live, nothing is out of date.",
        "It is not live yet, but the other one is live.",
        "It was not live before, now it is live.",
        "The PR is live and nothing is wrong.",
    ):
        assert assess(hidden, PUSH_TURN).refuses, hidden
    assert (
        claim_spans("It is not live yet, but the PR is live.") != ()
    )  # the git-word path judges per clause too
    assert (
        claim_spans("It is in a PR and it's live.") != ()
    )  # the git word may sit in another clause


def test_a_negation_is_not_an_arrival_claim_even_in_a_push_turn() -> None:
    """The gate fired on "Nothing is live yet; I'll switch it on between hands tomorrow" (2026-10-31).

    Saying that something has NOT arrived is the honest waiting sentence; refusing it teaches me to stop saying it.
    """
    for sentence in (
        "Nothing is live yet.",
        "Nothing is live yet; I'll switch it on between hands tomorrow, with you at the table.",
        "The fix isn't live.",
        "The PR is not live on GitHub.",
        "The branch has not been pushed.",
        "None of it is out yet, nothing is shipped.",
    ):
        assert not assess(sentence, PUSH_TURN).refuses, sentence
        assert claim_spans(sentence) == (), sentence
    assert assess(
        "The branch is live.", PUSH_TURN
    ).refuses  # control: the plain claim still refuses


def test_a_push_turn_that_read_the_remote_is_clear_and_the_waiting_sentence_is_free() -> None:
    assert not assess("The fix went live.", PUSH_TURN + "\n" + READ_THE_REMOTE).refuses
    assert not assess("It will be live once the push finishes.", PUSH_TURN).refuses


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
