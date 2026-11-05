"""The receipt gate's decisions: what the house read, and what follows from it.

Design: docs/drafts/the_landed_claim_gate_becomes_a_receipt_gate_draft_2026-11-05.md (two council walks and two
raters). Words only NOMINATE that a reply may claim arrival; a fact decides. Everything here is pure: it takes
what was read from git and answers. Reading git is a separate concern, so these decisions can be pinned without
a network.

Covers claims about the pushed branch only. Silence does not cover "the PR is merged" or any other claim.

A trap the reader must respect, found in ``substrate_retarget`` and ``stamp_ready_command``: ``git merge-base
--is-ancestor`` exits 1 for "no" and ALSO non-zero when the object is not present locally. Only exit 1 is a
"no"; anything else is ``local_in_remote=None`` here, which the judge reads as could-not-check.
"""

from __future__ import annotations

LANDED = "landed"
NOT_LANDED = "not_landed"
COULD_NOT_CHECK = "could_not_check"

# A citation has to be able to be wrong: three characters match half of all commits.
MIN_CITED_HASH = 7


def judge_receipt(
    *, local: str, remote: str | None, local_in_remote: bool | None, read_ok: bool
) -> str:
    """Landed means my local commit is reachable from the named remote branch.

    ``remote`` None with ``read_ok`` means the branch is absent there. ``local_in_remote`` None means the
    ancestry question was not answered (the fetch failed or was not needed); it is only needed when the two
    tips differ, because equal tips are landed without it.
    """
    if not read_ok:
        return COULD_NOT_CHECK
    if remote is None:
        return NOT_LANDED
    if remote == local:
        return LANDED
    if local_in_remote is None:
        return COULD_NOT_CHECK
    return LANDED if local_in_remote else NOT_LANDED


def fingerprint(branch: str, *, remote: str | None, local: str) -> str:
    """One receipt state. A state that blocked and was answered cannot block again; a new one can."""
    return f"{branch}|{remote or 'absent'}|{local}"


def should_block(*, nominated: bool, state: str, answered: frozenset[str], key: str) -> bool:
    """A nomination plus a not-landed receipt blocks, once per receipt state. Never on could-not-check."""
    return nominated and state == NOT_LANDED and key not in answered


def cited_hash_verdict(cited: str, *, local_tip: str, on_remote: bool) -> str:
    """A hash in a claim is a citation, not a verification, so it is checked exactly.

    It must be MY local tip for the branch (the thing I am claiming) AND be on the remote. Reachable alone
    would let a true old commit be cited under a new claim.
    """
    if len(cited) < MIN_CITED_HASH:
        return "too_short"
    if not local_tip.startswith(cited):
        return "not_my_tip"
    if not on_remote:
        return "not_on_remote"
    return "ok"
