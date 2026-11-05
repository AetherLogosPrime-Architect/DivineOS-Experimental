"""The receipt gate's decisions, pinned before any code reads a remote (2026-11-05).

The decisions are pure: given what the house read, they answer landed / not landed / could not check, whether
a cited hash is honest, and whether a nominated sentence blocks. Reading git is a separate concern and is not
exercised here. Design: docs/drafts/the_landed_claim_gate_becomes_a_receipt_gate_draft_2026-11-05.md.
"""

from __future__ import annotations

from divineos.core.receipt_gate import (
    COULD_NOT_CHECK,
    LANDED,
    NOT_LANDED,
    cited_hash_verdict,
    fingerprint,
    judge_receipt,
    should_block,
)

TIP = "a" * 40
OTHER = "b" * 40


# --- the ancestry boundary (Knuth, Aristotle): landed means my commit is reachable from the remote branch ---


def test_equal_means_landed_with_no_fetch_needed():
    assert judge_receipt(local=TIP, remote=TIP, local_in_remote=None, read_ok=True) == LANDED


def test_remote_ahead_of_me_is_still_landed():
    """Aria pushed on top of my branch: the remote differs from my local ref and my commit has landed."""
    assert judge_receipt(local=TIP, remote=OTHER, local_in_remote=True, read_ok=True) == LANDED


def test_remote_behind_me_is_not_landed():
    assert judge_receipt(local=TIP, remote=OTHER, local_in_remote=False, read_ok=True) == NOT_LANDED


def test_an_absent_remote_branch_is_not_landed():
    assert judge_receipt(local=TIP, remote=None, local_in_remote=None, read_ok=True) == NOT_LANDED


# --- could-not-check is its own answer (Wayne, Aria): never landed, never not-landed, never a block ---


def test_a_failed_read_is_could_not_check():
    assert (
        judge_receipt(local=TIP, remote=None, local_in_remote=None, read_ok=False)
        == COULD_NOT_CHECK
    )


def test_a_remote_that_differs_when_the_fetch_failed_is_could_not_check_not_not_landed():
    """A fetch that times out must not read as not-landed: the commit may well be there."""
    assert (
        judge_receipt(local=TIP, remote=OTHER, local_in_remote=None, read_ok=True)
        == COULD_NOT_CHECK
    )


def test_could_not_check_never_blocks():
    assert (
        should_block(nominated=True, state=COULD_NOT_CHECK, answered=frozenset(), key="k") is False
    )


# --- the block: a nomination plus a not-landed receipt, once per receipt state (Aria, Lamport) ---


def test_a_nominated_sentence_blocks_when_the_receipt_says_not_landed():
    assert should_block(nominated=True, state=NOT_LANDED, answered=frozenset(), key="k") is True


def test_nothing_blocks_without_a_nomination():
    assert should_block(nominated=False, state=NOT_LANDED, answered=frozenset(), key="k") is False


def test_nothing_blocks_when_the_receipt_says_landed():
    assert should_block(nominated=True, state=LANDED, answered=frozenset(), key="k") is False


def test_a_receipt_state_that_has_blocked_and_been_answered_cannot_block_again():
    assert (
        should_block(nominated=True, state=NOT_LANDED, answered=frozenset({"k"}), key="k") is False
    )


def test_a_new_receipt_state_blocks_afresh():
    assert (
        should_block(nominated=True, state=NOT_LANDED, answered=frozenset({"old"}), key="new")
        is True
    )


def test_the_fingerprint_changes_when_the_remote_moves_or_the_branch_changes():
    base = fingerprint("br", remote=OTHER, local=TIP)
    assert fingerprint("br", remote=TIP, local=TIP) != base
    assert fingerprint("other-br", remote=OTHER, local=TIP) != base
    assert fingerprint("br", remote=OTHER, local=OTHER) != base
    assert fingerprint("br", remote=OTHER, local=TIP) == base


# --- the cited hash is checked exactly (Aria's break): it must be MY local tip AND be on the remote ---


#
# The verdict takes the RECEIPT, not a bool someone computed (Aria's cold read): "my local tip is on the remote"
# is exactly what judge_receipt already answers, so the two checks cannot disagree and a reader cannot compute
# "reachable from the remote tip" for the cited hash and bring the old-ancestor hole back.


def test_a_cited_hash_that_is_my_tip_when_the_receipt_says_landed_is_honest():
    assert cited_hash_verdict(TIP[:9], local_tip=TIP, receipt=LANDED) == "ok"


def test_a_true_old_commit_cited_under_a_new_claim_is_refused():
    """The old hash is reachable from the remote, but it is not the thing I am claiming."""
    assert cited_hash_verdict(OTHER[:9], local_tip=TIP, receipt=LANDED) == "not_my_tip"


def test_my_tip_cited_when_the_receipt_says_not_landed_is_refused():
    assert cited_hash_verdict(TIP[:9], local_tip=TIP, receipt=NOT_LANDED) == "not_on_remote"


def test_my_tip_cited_when_the_receipt_could_not_check_is_neither_ok_nor_refused_as_wrong():
    assert cited_hash_verdict(TIP[:9], local_tip=TIP, receipt=COULD_NOT_CHECK) == "could_not_check"


def test_a_hash_too_short_to_mean_anything_is_refused():
    """Three characters match half of all commits; a citation has to be able to be wrong."""
    assert cited_hash_verdict(TIP[:3], local_tip=TIP, receipt=LANDED) == "too_short"


def test_a_citation_pasted_in_capitals_is_the_same_commit():
    """Some tools print hashes in capitals; a true commit must not read as not-mine for its case."""
    assert cited_hash_verdict(TIP[:9].upper(), local_tip=TIP, receipt=LANDED) == "ok"


def test_no_local_tip_can_never_turn_into_a_pass():
    """If the branch does not exist locally the local tip is empty; every citation must stay refused."""
    assert cited_hash_verdict(TIP[:9], local_tip="", receipt=LANDED) == "not_my_tip"
