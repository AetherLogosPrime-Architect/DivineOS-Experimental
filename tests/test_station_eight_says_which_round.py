"""Station eight must say WHICH round names the request, not only that one does.

THE FAULT. The board printed `audit round names PR #499` and I read it as the
handoff to Aletheia having happened. It had not -- no round for that request
existed, and I filed one only after Andrew asked whether I had written to her.
A verdict that cannot be checked from the place it is read is a verdict that
gets believed.

WHAT IS PROVEN HERE AND WHAT IS NOT. That a bare number matches inside a longer
one is proven below by construction. Whether THAT is what happened on #499 is
not proven and is not claimed: my scan of the store used a looser pattern than
the station does, and two probes disagreeing is not a measurement. The quoted
evidence exists so the next instance is answerable rather than arguable.

Sits beside test_audit_station_scope.py, which pins what a MISS must name, and
test_audit_station_content_binding.py, which pins the confirm ladder. This one
pins what a PASS must show.
"""

from __future__ import annotations

from divineos.core.build_flow import Status, check_audit_station


def test_the_verdict_carries_the_round_it_matched():
    """The whole repair. A green station now hands over its own evidence."""
    result = check_audit_station(
        pr_number=499,
        branch="fix/a-refusal-must-say-what-did-not-run",
        audit_refs=("PR #499 fix/a-refusal-must-say-what-did-not-run -- tree-hash: 69e5",),
    )

    assert result.status is Status.SATISFIED
    assert "tree-hash: 69e5" in result.detail, (
        "a reader must be able to tell a real round from a coincidental match "
        "without leaving the board"
    )


def test_a_number_inside_a_longer_number_is_not_a_match():
    """`#499` must not be found in `#4991`. Proven by construction, because
    this is the half I can prove; the #499 incident itself is not claimed as
    an instance of it."""
    result = check_audit_station(
        pr_number=499,
        branch="fix/some-branch",
        audit_refs=("PR #4991 an entirely different request",),
    )

    assert result.status is Status.MISSING


def test_an_unrelated_round_quoting_the_number_is_still_shown_not_hidden():
    """The boundary check cannot catch every coincidence -- a round whose prose
    happens to contain `#499` standing alone still matches. That is why the
    evidence rides along: the station cannot decide this case correctly, so it
    shows its working and lets the reader decide."""
    ref = "PR #310 settings change, superseding the approach taken in #499"
    result = check_audit_station(pr_number=499, branch="fix/x", audit_refs=(ref,))

    assert result.status is Status.SATISFIED, "still a match -- this is the honest limit"
    assert "#310" in result.detail, (
        "and the reader can SEE it is a round about a different request, which "
        "is the whole point of quoting rather than asserting"
    )


def test_the_branch_match_carries_its_evidence_too():
    """An audit filed before the request exists names the branch, not a number.
    That path is the normal order and must not lose the evidence the number
    path gained."""
    result = check_audit_station(
        pr_number=999,
        branch="split/docs-research-buildflow",
        audit_refs=("audited split/docs-research-buildflow on 08-03 and confirmed",),
    )

    assert result.status is Status.SATISFIED
    assert "confirmed" in result.detail
