"""A draft cannot be READY, because a draft cannot merge.

THE DEFECT, found 2026-09-21 after Andrew asked for weeks why the pile never
shrinks. The board walked every station, found them all proven, and printed
READY. Seven requests said READY. All thirteen were drafts. A draft cannot be
merged by anyone.

The mechanism is one line and it is almost elegant: the draft station is
SATISFIED when the request IS a draft -- correct, because opening as a draft is
the rule -- and the verdict is computed as "no station is blocking". So the
very fact that makes a request unmergeable is counted as a step completed
toward merging.

WHAT THIS COST. Every week the answer to "why is nothing landing" was read off
this board and relayed as done-and-waiting-on-review. Nothing was waiting on a
reviewer. Each one was waiting for someone to take it out of draft, and no
station ever asks anyone to. The flow ends one move early and congratulates
itself.

THE FIX IS NOT TO STOP REWARDING DRAFTS. Opening as a draft is right and the
station should keep passing for it. The fix is that the VERDICT must know a
draft cannot merge, and must name whose move it is instead of implying the
work is finished.

The test that carries the claim is the first one: a draft with every single
station proven must not contain the word that means finished.
"""

from __future__ import annotations

from divineos.cli.build_flow_commands import render
from divineos.core.build_flow import PrFlowStatus, StationResult, Status


def _stations(*, draft: bool, all_proven: bool = True) -> list[StationResult]:
    other = Status.SATISFIED if all_proven else Status.MISSING
    return [
        StationResult("2-council", other, "8/6 lenses"),
        StationResult("4-aria", other, "she declared a reading"),
        StationResult(
            "7-draft",
            Status.SATISFIED if draft else Status.MISSING,
            "draft" if draft else "OPEN AS READY",
        ),
        StationResult("8-audit", other, "audit round names it"),
    ]


def _status(number: int, *, draft: bool, all_proven: bool = True) -> PrFlowStatus:
    return PrFlowStatus(
        number=number,
        branch=f"branch-{number}",
        gravity=3,
        required_lenses=4,
        stations=_stations(draft=draft, all_proven=all_proven),
    )


def test_a_draft_with_every_station_proven_is_not_called_ready() -> None:
    """The case that carries the claim, and the one that was live for weeks."""
    out = render([_status(1, draft=True)])
    assert "READY" not in out, (
        "a draft was reported READY; a draft cannot merge, so READY is false here:\n" + out
    )


def test_a_draft_says_whose_move_it_is() -> None:
    """A verdict that does not name the next hand is why nobody moved."""
    out = render([_status(2, draft=True)])
    assert "draft" in out.lower(), f"the draft state is not named in the verdict:\n{out}"


def test_a_finished_request_can_still_be_called_ready() -> None:
    """The repair must not simply delete the word.

    If nothing can ever read as ready, the board has stopped answering the
    question rather than answering it correctly.
    """
    out = render([_status(3, draft=False, all_proven=True)])
    assert "READY" in out, f"a genuinely mergeable request was not called ready:\n{out}"


def test_a_ready_request_with_unproven_stations_still_needs_attention() -> None:
    """The pre-existing alarm case must survive the change."""
    out = render([_status(4, draft=False, all_proven=False)])
    assert "ATTENTION" in out, f"the unproven-but-marked-ready case lost its alarm:\n{out}"


def test_the_summary_does_not_count_drafts_as_ready() -> None:
    """The headline number is what gets relayed, so it carries the same claim."""
    out = render([_status(5, draft=True), _status(6, draft=True)])
    assert "2 ready" not in out, f"drafts were counted as ready in the summary:\n{out}"
    assert "0 ready" in out, f"the ready count should be zero when all are drafts:\n{out}"
