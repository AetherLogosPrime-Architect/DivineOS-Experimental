"""The board called a branch READY while another request existed to replace it.

Found 2026-09-14, one command before I sent it to Aletheia as fact. #504 read
READY -- every checked station proven -- and #515 existed for exactly one
reason: she had refused to read #504's ratio of letters to code and asked for a
rebuild. #515's own first sentence says it supersedes #504.

Four stations answered four questions honestly. None of them was the question.
Every station until this one asks about the request in front of it, so a
request standing OVER it was invisible by construction -- the week's disease in
one more place: a check covering what it covers, read as covering what you
needed.

The second half of these tests is about the first repair being wrong. Prose
ambiguity is a property of the request making the claim; I attached it to every
OTHER request, and two vague bodies turned five proven branches into
could-not-check. Four ready went to zero. A board that noisy gets switched off,
which costs more than the hole. So: the claim is a footnote about the claimant,
never a verdict on the innocent.
"""

from __future__ import annotations

from divineos.core.build_flow import (
    Status,
    check_supersession_station,
    unresolved_supersession_claims,
)

# The live shape that produced the false READY, in the form the board reads it.
_R504 = (504, "substrate/andrew-answer-trace", "The five build-flow stations nothing watches.")
_R515 = (
    515,
    "substrate/andrew-answer-trace-code",
    "Supersedes: #504\n\nSame work, writing left where it belongs.",
)


def test_the_replaced_branch_is_not_clean() -> None:
    result = check_supersession_station(504, _R504[1], (_R504, _R515))
    assert result.status is Status.MISSING
    assert "#515" in result.detail


def test_the_replacement_itself_is_clean() -> None:
    result = check_supersession_station(515, _R515[1], (_R504, _R515))
    assert result.status is Status.SATISFIED


def test_a_branch_named_by_nobody_is_clean() -> None:
    other = (459, "fix/mixed-scope-publish-gate", "A publish gate for mixed-scope branches.")
    result = check_supersession_station(459, other[1], (_R504, _R515, other))
    assert result.status is Status.SATISFIED


def test_the_declaration_may_name_the_branch_instead_of_the_number() -> None:
    """Audit-before-PR is the correct order, so the name is often all there is."""
    claimant = (515, "b-code", "Supersedes: substrate/andrew-answer-trace\n")
    result = check_supersession_station(504, _R504[1], (_R504, claimant))
    assert result.status is Status.MISSING


def test_the_colon_is_optional() -> None:
    """Both requests already open here that declare one wrote it without a colon.

    A trailer format nobody uses is a format that reports nothing.
    """
    claimant = (513, "gate/quiet-checks-clean", "Supersedes #504, which carried 193 files.")
    result = check_supersession_station(504, _R504[1], (_R504, claimant))
    assert result.status is Status.MISSING


def test_an_unreadable_body_is_not_an_absent_claim() -> None:
    result = check_supersession_station(504, _R504[1], (_R504, (515, "b", None)))
    assert result.status is Status.CANNOT_CHECK
    assert "#515" in result.detail


def test_prose_alone_never_marks_a_branch_dead() -> None:
    """A word-match holding a verdict is a language detector; the composer
    rephrases past those. Only a declaration naming this request decides."""
    vague = (515, "b", "This supersedes earlier attempts at the same idea.")
    result = check_supersession_station(504, _R504[1], (_R504, vague))
    assert result.status is Status.SATISFIED


def test_one_vague_body_does_not_cloud_the_innocent() -> None:
    """THE REGRESSION THAT MATTERS. This is what the first repair did wrong."""
    vague = (514, "build/doorman", "This supersedes the two doorman branches.")
    clean = (459, "fix/mixed-scope-publish-gate", "A publish gate.")
    roster = (vague, clean, _R504, _R515)
    assert check_supersession_station(459, clean[1], roster).status is Status.SATISFIED
    assert check_supersession_station(504, _R504[1], roster).status is Status.MISSING


def test_the_vague_claim_is_still_reported_about_its_own_author() -> None:
    """Said once, about the request that wrote it -- not swallowed."""
    vague = (514, "build/doorman", "This supersedes the two doorman branches.")
    clean = (459, "fix/mixed", "A publish gate.")
    assert unresolved_supersession_claims((vague, clean, _R515)) == (514,)


def test_a_declared_claim_is_not_also_reported_as_vague() -> None:
    assert unresolved_supersession_claims((_R504, _R515)) == ()


def test_an_unreadable_body_is_not_a_vague_claim() -> None:
    """Could-not-read and claimed-something-unresolvable are different answers;
    the footnote must not absorb the first into the second."""
    assert unresolved_supersession_claims(((515, "b", None),)) == ()
