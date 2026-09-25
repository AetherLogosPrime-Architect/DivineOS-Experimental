"""Station eight distinguishes a review that NAMES a branch from one that COVERS it.

Aletheia verified the finding 2026-08-29: the check asked only whether a
round's text names the branch. What a reader takes from a green station is
that the CURRENT content has been reviewed. On the instruments branch those
were ten commits and fifteen files apart, so the board would have carried it
to a merge on an audit that never saw two thirds of what was in it.

WHY PATCH-ID IS THE ANCHOR, and the reasoning is hers. Tip changes on every
commit including ones that cannot affect behaviour; tree is tip's problem with
an extra step. Both stale a review when a letter lands on the branch, and a
binding that invalidates a review because of a letter gets routed around
within a week -- correctly, since nothing about the review became false.
Patch-id is the diff against the base: invariant to the base moving, variant
only when the change changes.

And the mechanism was already built. Andrew designed the patch-id rung for
exactly this: "if the code matches your audit then we authorize changing your
hash to match the changed floor so it doesnt fail. but if the code doesnt
match then it needs re-audit." The repair was to call what already existed,
not to invent a comparison.

THE TEST THAT MATTERS IS THE STALE ONE. Making a fresh review read as
satisfied is the easy half. The half that will be under pressure later is
that a stale review must stop reading as satisfied, because that verdict
turns a green board amber and someone will want it back.

Complements tests/test_audit_station_scope.py, which pins the wording of the
absent verdict -- which store was looked in, and how many rounds it compared
against. This file pins the content question those tests do not ask.
"""

from __future__ import annotations

from divineos.core.build_flow import Status, check_audit_station

REFS = ("PR #447 instruments/clean -- five doormen repaired",)


# --- the half that must happen ---------------------------------------------


def test_a_stale_confirm_is_not_satisfied() -> None:
    """THE LOAD-BEARING ONE. A named round whose confirm no longer holds.

    The exact situation on the instruments branch: a real round, a real
    confirm, filed against content that has since moved. Before this change
    the station reported SATISFIED on the strength of the name alone.
    """
    result = check_audit_station(447, "instruments/clean", REFS, anchor="stale")
    assert result.status is Status.MISSING
    assert "NO LONGER HOLDS" in result.detail


def test_the_stale_verdict_says_re_audit_rather_than_no_audit() -> None:
    """A stale review and an absent one are different facts needing different words.

    Reporting staleness as absence would send someone to file a round that
    already exists -- the same cannot-tell-them-apart failure the store-scope
    fix cured one layer up.
    """
    stale = check_audit_station(447, "instruments/clean", REFS, anchor="stale")
    absent = check_audit_station(999, "other/branch", REFS)
    assert stale.detail != absent.detail
    assert "re-audit" in stale.detail
    assert "no audit round names" in absent.detail


def test_a_holding_confirm_says_so_explicitly() -> None:
    result = check_audit_station(447, "instruments/clean", REFS, anchor="holds")
    assert result.status is Status.SATISFIED
    assert "still holds" in result.detail


def test_an_unverifiable_anchor_is_cannot_check_not_a_pass() -> None:
    """Could-not-look is not all-clear, and this is the last station before a merge."""
    result = check_audit_station(447, "instruments/clean", REFS, anchor="cannot-check")
    assert result.status is Status.CANNOT_CHECK
    assert "not a pass" in result.detail


def test_a_pre_binding_round_passes_but_says_which_kind_it_is() -> None:
    """Rounds filed before content binding record no anchor at all.

    Failing them would retroactively unmake every older review on a
    technicality. Passing them silently, identically to an anchored one, is
    the lie. So it passes and names itself as a name match.
    """
    result = check_audit_station(447, "instruments/clean", REFS, anchor="unanchored")
    assert result.status is Status.SATISFIED
    assert "name match only" in result.detail


# --- the pre-existing behaviour, which must survive ------------------------


def test_the_cheap_view_says_it_skipped_the_check() -> None:
    """The per-turn board does not pay five seconds a request, and admits it.

    A green station that quietly means something weaker than the reader
    thinks is the defect this whole change removes. Reproducing it in the
    fast path to save time would undo the point, so the fast path names its
    own scope instead.
    """
    result = check_audit_station(447, "instruments/clean", REFS, anchor="not-run")
    assert result.status is Status.SATISFIED
    assert "content check not run" in result.detail


def test_no_anchor_supplied_behaves_as_before() -> None:
    """Callers that do not compute an anchor keep the old verdict.

    The content check lives in the caller, where git lives. A caller that
    cannot do it must not have its work silently downgraded.
    """
    result = check_audit_station(447, "instruments/clean", REFS)
    assert result.status is Status.SATISFIED
    assert result.detail == "audit round names PR #447"


def test_branch_match_still_satisfies_when_the_pr_number_is_absent() -> None:
    """Audit-before-PR is the correct order and must keep working."""
    refs = ("round covering instruments/clean at tree abc123",)
    result = check_audit_station(447, "instruments/clean", refs)
    assert result.status is Status.SATISFIED
    assert "instruments/clean" in result.detail


def test_an_unreadable_lookup_is_still_cannot_check() -> None:
    result = check_audit_station(447, "instruments/clean", None)
    assert result.status is Status.CANNOT_CHECK


def test_the_absent_verdict_still_names_its_scope() -> None:
    """The store-scope narrowing survives this change.

    A true statement about one store, published with the scope of all of
    them, is the fault that made this sentence unfalsifiable before.
    """
    result = check_audit_station(999, "other/branch", REFS, store_label="mine")
    assert result.status is Status.MISSING
    assert "in mine" in result.detail
    assert "1 round(s)" in result.detail
