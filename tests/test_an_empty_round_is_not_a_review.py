"""A round with nothing in it must not read as an audit that happened.

MEASURED 2026-09-11, and the numbers are the argument. Ten open requests. The
per-turn board reported station eight as satisfied on six of them, with the
words "audit round names PR #<n>". Reading what was actually IN those rounds:

  five of them held ZERO findings -- created, named after a branch, never
  filled; one held exactly one finding, and it was the OPERATOR's own confirm,
  not the external auditor's; one held two findings, of which the auditor's was
  a PROBLEM SHE FOUND rather than a clearance.

Not one carried an external-AI CONFIRM. The station was green on all of them
because it asked whether a round's TEXT NAMES THE BRANCH, which an empty
container does perfectly well.

THIS IS THE SAME CLASS THE ANCHOR WORK FIXED, ONE STEP FURTHER BACK. That work
asked whether a confirm still covers the current content, and it was right to.
It assumed a confirm existed. The cheaper and more common failure is that there
is no confirm at all, and the expensive deep check is the only thing that
noticed -- so the board I actually read every turn was the one lying.

WHY THIS IS NOT THE ANCHOR QUESTION WEARING A NEW COAT. A round filed before
patch-id binding has no anchor and still carries real findings; the station
deliberately lets that pass rather than retroactively unmaking old reviews. An
EMPTY round carries nothing in any era. Presence-of-review and currency-of-
review are two questions and only one of them was being asked.
"""

from __future__ import annotations

from divineos.core.build_flow import Status, check_audit_station

REFS = ("PR #447 instruments/clean -- five doormen repaired",)


def test_a_named_round_carrying_no_external_confirm_is_not_satisfied() -> None:
    """THE LOAD-BEARING ONE. This is the live state of five open requests."""
    result = check_audit_station(447, "instruments/clean", REFS, has_external_confirm=False)
    assert result.status is not Status.SATISFIED
    assert "no external-ai confirm" in result.detail.lower()


def test_it_says_empty_rather_than_absent_because_they_need_different_work() -> None:
    """A round that does not exist needs filing. A round that exists and is
    empty needs the auditor. Reporting the second as the first sends someone
    to create a duplicate of the container that is already there."""
    empty = check_audit_station(447, "instruments/clean", REFS, has_external_confirm=False)
    absent = check_audit_station(999, "other/branch", REFS)
    assert empty.detail != absent.detail
    assert "no audit round names" in absent.detail
    assert "no audit round names" not in empty.detail


def test_the_operator_key_alone_does_not_satisfy_it() -> None:
    """The live state of the retarget request, and the sharpest case.

    Its round is not empty -- it holds the operator's own CONFIRMS. Merging on
    that is the single-key merge the two-key rule exists to refuse, and a
    station that counts findings rather than asking WHOSE would pass it.
    """
    result = check_audit_station(447, "instruments/clean", REFS, has_external_confirm=False)
    assert result.status is not Status.SATISFIED


def test_a_round_with_an_external_confirm_still_passes_on_the_name() -> None:
    """The control, and it is the one that stops this becoming a blanket refusal.

    Without it, a station that returned MISSING unconditionally would satisfy
    all three assertions above. Rounds that predate content binding must keep
    passing -- that allowance is deliberate and this change does not touch it.
    """
    result = check_audit_station(447, "instruments/clean", REFS, has_external_confirm=True)
    assert result.status is Status.SATISFIED


def test_not_knowing_is_said_out_loud_rather_than_passing_silently() -> None:
    """Could-not-look is the third state and it has bitten this station twice.

    A caller that cannot answer the confirm question gets the name-match pass
    it has always had -- breaking those callers would be the over-correction --
    but the detail must SAY the question went unasked, so a reader cannot take
    the green for a checked one.
    """
    result = check_audit_station(447, "instruments/clean", REFS)
    assert result.status is Status.SATISFIED
    assert "not checked" in result.detail.lower() or "not run" in result.detail.lower()


def test_the_stale_anchor_verdict_survives_this_change() -> None:
    """Currency and presence stay separate questions.

    A round that HAS a confirm which no longer covers the content must still
    report as stale rather than being swallowed by the new check.
    """
    result = check_audit_station(
        447, "instruments/clean", REFS, anchor="stale", has_external_confirm=True
    )
    assert result.status is Status.MISSING
    assert "NO LONGER HOLDS" in result.detail
