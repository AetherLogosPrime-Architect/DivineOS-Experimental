"""The merge-review gate must distinguish 'not yet' from 'no'.

THE DEFECT (2026-08-01). The merge-review job failed 17 times and passed 0
times across the recent run history. The sweep attributed this to CI being
asked to read an untracked audit database. That was wrong, and the real CI
output said so plainly:

    [merge-review] FAIL: No APPROVED operator review on head 921ff275.

The job runs on every push. An approval is submitted against a specific
commit SHA, so at the instant a new head is pushed there cannot be an
approval on it — the approval can only arrive afterward. The gate evaluated
that condition at the one moment it was guaranteed to be unmet, on every
single run, forever. A check that has never said yes carries no information,
and a permanently-red check teaches the operator to ignore the whole panel.

The audit-DB problem was real but LATENT: it sat behind the approval wall
and would have fired the first time an approval actually landed. Both are
fixed here, because fixing only the first would have moved the permanent red
one step down the road rather than removing it.

WHAT THESE TESTS PROTECT AGAINST. The obvious wrong way to make a red check
go green is to weaken it. These tests pin both directions: the not-yet cases
must be PENDING, and every genuine defect must still be FAIL.
"""

from __future__ import annotations

from divineos.core.merge_review_gate import (
    MergeReviewConfig,
    Review,
    classify_merge,
    verify_merge,
)

HEAD = "921ff27583cd0000000000000000000000000000"
OLD = "1111111111111111111111111111111111111111"
BODY = "External-Review: round-abc123"
CONFIG = MergeReviewConfig(frozenset({"aetherlogosprime-architect"}))


def _approval(sha: str = HEAD, login: str = "aetherlogosprime-architect") -> Review:
    return Review(author_login=login, state="APPROVED", commit_id=sha)


# --------------------------------------------------------------------------
# PENDING — the states that were wrongly red
# --------------------------------------------------------------------------


def test_freshly_pushed_head_with_no_reviews_is_pending_not_fail():
    """The exact condition behind all 17 failures."""
    verdict, msg = classify_merge([], HEAD, BODY, CONFIG, round_is_logged=True)
    assert verdict == "PENDING"
    assert "Awaiting operator approval" in msg
    assert "not a defect" in msg


def test_pending_message_does_not_read_as_an_accusation():
    """Wording matters: this fires on every healthy PR, so it must not
    describe the normal case in the language of a violation."""
    _, msg = classify_merge([], HEAD, BODY, CONFIG, round_is_logged=True)
    assert "No APPROVED" not in msg


def test_stale_approval_on_an_older_commit_is_pending():
    """A push invalidates the prior approval. That is the SHA-binding working
    as designed — the operator simply needs to re-approve — so it is 'not yet
    approved again', not 'this PR is defective'."""
    verdict, _ = classify_merge([_approval(OLD)], HEAD, BODY, CONFIG, round_is_logged=True)
    assert verdict == "PENDING"


def test_approval_from_a_non_operator_is_pending():
    """Someone outside the roster approving does not authorize the merge, but
    neither is it a defect — the operator's approval is still just absent."""
    verdict, _ = classify_merge(
        [_approval(HEAD, "some-other-user")], HEAD, BODY, CONFIG, round_is_logged=True
    )
    assert verdict == "PENDING"


def test_non_approving_review_states_are_pending():
    """COMMENTED / CHANGES_REQUESTED are review activity, not authorization."""
    for state in ("COMMENTED", "CHANGES_REQUESTED", "DISMISSED"):
        r = Review(author_login="aetherlogosprime-architect", state=state, commit_id=HEAD)
        verdict, _ = classify_merge([r], HEAD, BODY, CONFIG, round_is_logged=True)
        assert verdict == "PENDING", state


# --------------------------------------------------------------------------
# FAIL — nothing that was caught before may stop being caught
# --------------------------------------------------------------------------


def test_approved_but_no_round_named_still_fails():
    """The receipt requirement. Approval without a named audit round is the
    gate's core catch and must stay red."""
    verdict, msg = classify_merge(
        [_approval()], HEAD, "no trailer anywhere", CONFIG, round_is_logged=True
    )
    assert verdict == "FAIL"
    assert "must be named" in msg


def test_approved_but_round_is_fabricated_still_fails():
    """Store was READABLE and said the round does not exist. That is a real
    finding and the whole reason round_is_logged exists."""
    verdict, msg = classify_merge([_approval()], HEAD, BODY, CONFIG, round_is_logged=False)
    assert verdict == "FAIL"
    assert "not present in the audit store" in msg


def test_empty_operator_roster_still_fails_closed():
    """A misconfigured roster must never become satisfiable."""
    verdict, _ = classify_merge(
        [_approval()], HEAD, BODY, MergeReviewConfig(frozenset()), round_is_logged=True
    )
    assert verdict == "FAIL"


def test_missing_head_sha_still_fails():
    """Without a head there is nothing to bind an approval to."""
    verdict, _ = classify_merge([_approval()], "", BODY, CONFIG, round_is_logged=True)
    assert verdict == "FAIL"


def test_pending_is_not_a_blanket_green():
    """The load-bearing anti-regression test. If someone 'fixes' a future red
    by making everything PENDING, this catches it: a fabricated round must
    never be reachable as PENDING."""
    verdict, _ = classify_merge([_approval()], HEAD, BODY, CONFIG, round_is_logged=False)
    assert verdict != "PENDING"


# --------------------------------------------------------------------------
# UNKNOWN — blindness reports as blindness, not as a finding
# --------------------------------------------------------------------------


def test_unreadable_store_does_not_claim_the_round_is_fabricated():
    """round_is_logged=None means the lookup never ran. Reporting 'no such
    round was logged' on that basis states a fact not in evidence — the same
    defect class as a health surface that reverts to optimism when blind,
    only inverted into pessimism."""
    verdict, msg = classify_merge([_approval()], HEAD, BODY, CONFIG, round_is_logged=None)
    assert verdict == "PASS"
    assert "UNVERIFIABLE" in msg
    assert "Not a clean confirmation" in msg
    assert "not present in the audit store" not in msg


def test_unverifiable_round_still_requires_a_named_round():
    """Being unable to CHECK the round does not excuse not NAMING one. The
    textual requirement is verifiable from the PR alone."""
    verdict, _ = classify_merge([_approval()], HEAD, "nothing here", CONFIG, round_is_logged=None)
    assert verdict == "FAIL"


def test_unverifiable_does_not_bypass_the_approval_requirement():
    """An unreadable audit store must not become a way to skip the keystone."""
    verdict, _ = classify_merge([], HEAD, BODY, CONFIG, round_is_logged=None)
    assert verdict == "PENDING"


# --------------------------------------------------------------------------
# The strict projection must not drift from the classifier
# --------------------------------------------------------------------------


def test_verify_merge_still_treats_pending_as_unauthorized():
    """verify_merge answers 'is this merge authorized right now'. An
    unapproved PR is not authorized, so it stays False there — the softening
    is in how CI REPORTS the state, not in what counts as authorized."""
    ok, _ = verify_merge([], HEAD, BODY, CONFIG, round_is_logged=True)
    assert ok is False


def test_verify_merge_agrees_with_classify_on_every_case():
    """Pins the projection so the two surfaces cannot diverge later."""
    cases = [
        ([], HEAD, BODY, True),
        ([_approval()], HEAD, BODY, True),
        ([_approval()], HEAD, BODY, False),
        ([_approval()], HEAD, BODY, None),
        ([_approval(OLD)], HEAD, BODY, True),
        ([_approval()], HEAD, "no round", True),
        ([], "", BODY, True),
    ]
    for reviews, head, body, logged in cases:
        verdict, _ = classify_merge(reviews, head, body, CONFIG, round_is_logged=logged)
        ok, _ = verify_merge(reviews, head, body, CONFIG, round_is_logged=logged)
        assert ok == (verdict == "PASS"), (reviews, head, body, logged, verdict)
