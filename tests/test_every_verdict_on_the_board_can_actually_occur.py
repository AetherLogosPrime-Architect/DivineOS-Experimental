"""A verdict no request can reach is not a verdict.

2026-09-21, hours after repairing this same summary for the mirror fault.
This morning: a draft could print READY, because the draft station is
SATISFIED while the thing is a draft, so the very fact making it unmergeable
counted toward merging. Fixed by testing draft first.

This afternoon, from the other side: once a request LEAVES draft, the draft
station reports MISSING, and the summary's READY branch was guarded on
``mergeable`` -- "nothing is blocking". Leaving draft is the only road to a
merge, so nothing that had taken that road could ever be mergeable, and the
READY branch was unreachable by construction. The board printed zero ready for
every request it had ever seen. Two sat in the ATTENTION column with every
station proven except the flag, which is not a fault -- it is the last step.

THE GENERAL TEST, and it is why this file is not just four cases. Every
verdict the summary can print must be reachable by some arrangement of
stations. A branch nothing can enter is dead code that reads as coverage, and
both halves of this bug were exactly that: a verdict with one possible value
for the population it judged.
"""

from __future__ import annotations

from divineos.core.build_flow import PrFlowStatus, StationResult, Status
from divineos.cli.build_flow_commands import render


def _pr(number: int, *, draft: bool, others_ok: bool) -> PrFlowStatus:
    draft_station = (
        StationResult("7-draft", Status.SATISFIED, "draft")
        if draft
        else StationResult("7-draft", Status.MISSING, "OPEN AS READY")
    )
    ok = Status.SATISFIED if others_ok else Status.MISSING
    return PrFlowStatus(
        number=number,
        branch=f"b/{number}",
        gravity=1,
        required_lenses=2,
        stations=[
            StationResult("2-council", ok, "lenses"),
            StationResult("4-aria", ok, "reading"),
            draft_station,
            StationResult("8-audit", ok, "round"),
        ],
    )


def _render(*statuses) -> str:
    return render(list(statuses))


def test_a_finished_request_out_of_draft_reads_ready():
    out = _render(_pr(1, draft=False, others_ok=True))
    assert "READY" in out
    assert "1 ready" in out
    assert "needing attention: #1" not in out.lower()


def test_leaving_draft_too_early_still_reads_attention():
    """The control in the other direction. A fix that made every non-draft
    read READY would pass the test above and destroy the station's purpose."""
    out = _render(_pr(2, draft=False, others_ok=False))
    assert "ATTENTION" in out
    # The verdict, not the word -- "OPEN AS READY" is the draft station's own
    # detail line and says nothing about the verdict.
    assert "READY — out of draft" not in out
    assert "0 ready" in out
    assert "#2" in out.split("Needing attention:")[-1]


def test_a_draft_still_never_reads_ready():
    """This morning's repair must survive this afternoon's."""
    out = _render(_pr(3, draft=True, others_ok=True))
    assert "READY" not in out
    assert "OUT OF DRAFT" in out.upper()


def test_a_draft_with_work_ahead_is_in_flight_not_attention():
    out = _render(_pr(4, draft=True, others_ok=False))
    assert "DRAFT" in out
    assert "ATTENTION" not in out
    assert "1 in flight" in out


def test_all_four_verdicts_are_reachable_in_one_board():
    """THE CARRYING TEST. Both halves of this bug were a verdict that no
    arrangement of stations could produce. Assert each one occurs."""
    out = _render(
        _pr(1, draft=False, others_ok=True),
        _pr(2, draft=False, others_ok=False),
        _pr(3, draft=True, others_ok=True),
        _pr(4, draft=True, others_ok=False),
    )
    assert "READY — out of draft" in out
    assert "ATTENTION — marked ready for review" in out
    assert "MINE TO TAKE OUT OF DRAFT" in out
    assert "still ahead of it" in out
    assert "1 ready, 2 in flight, 1 needing attention (of 4)." in out


def test_the_attention_count_names_only_real_faults():
    """The draft flag is what MAKES a finished request non-draft, so counting
    it as an unproven station told two requests they had a fault they did
    not have."""
    out = _render(_pr(2, draft=False, others_ok=False))
    # Three real stations are unproven here. The draft flag is a fourth
    # MISSING row and must not be counted, because leaving draft is what a
    # finished request DOES -- counting it told two requests they carried a
    # fault they did not carry.
    assert "3 station(s) unproven" in out
    assert "4 station(s) unproven" not in out
