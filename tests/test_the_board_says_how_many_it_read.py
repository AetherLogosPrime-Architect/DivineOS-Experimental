"""The board prints what it read beside what GitHub says is open.

Aletheia, 2026-11-27, confirming the one-line journal fix: "when the board reads
all 71 requests, show me the count it actually read alongside the 71." A board
that lists 50 of 71 and says nothing about the other 21 looks identical to a
board that listed everything. The second number must come from a DIFFERENT
question to GitHub than the list itself, or it only agrees with itself.
"""

from __future__ import annotations

from divineos.cli import build_flow_commands as bfc
from divineos.core.build_flow import PrFlowStatus


def _statuses(n: int) -> list[PrFlowStatus]:
    return [
        PrFlowStatus(number=1000 - i, branch=f"b{i}", gravity=0, required_lenses=0)
        for i in range(n)
    ]


def test_the_count_line_says_read_and_github_both() -> None:
    line = bfc.read_count_line(read=71, github_total=71)

    assert "71" in line
    assert "read 71" in line
    assert "GitHub" in line


def test_a_shortfall_is_loud_not_quiet() -> None:
    line = bfc.read_count_line(read=50, github_total=71)

    assert "50" in line and "71" in line
    assert "NOT ALL" in line
    assert "21" in line


def test_an_unreadable_total_is_could_not_check_not_a_match() -> None:
    line = bfc.read_count_line(read=71, github_total=None)

    assert "could not ask" in line
    assert "NOT ALL" not in line


def test_the_rendered_board_carries_the_line(monkeypatch) -> None:
    monkeypatch.setattr(bfc, "_open_pr_total", lambda: 71)
    # The rest of the page scans every branch and asks git about provenance; this
    # test is about the count line only, so those slow neighbours are stood in.
    monkeypatch.setattr(bfc, "_outside_the_flow_lines", lambda _refs: [])
    monkeypatch.setattr(bfc, "_work_item_lines", lambda: [])
    monkeypatch.setattr(bfc, "_judge_version_line", lambda: "  judge: test")
    monkeypatch.setattr(bfc, "judging_code_provenance", lambda: (bfc.Status.SATISFIED, "test"))

    text = bfc.render(_statuses(71), ())

    assert "read 71" in text
    assert "GitHub says 71" in text


def test_the_total_is_asked_by_a_different_question_than_the_list(monkeypatch) -> None:
    asked: list[list[str]] = []

    def fake(args: list[str]) -> str | None:
        asked.append(args)
        return "71"

    monkeypatch.setattr(bfc, "_gh", fake)

    assert bfc._open_pr_total() == 71
    assert asked and asked[0][0] == "api"
    assert "pr" not in asked[0][:1]


def test_an_unreadable_answer_is_none(monkeypatch) -> None:
    monkeypatch.setattr(bfc, "_gh", lambda args: "not a number")

    assert bfc._open_pr_total() is None
