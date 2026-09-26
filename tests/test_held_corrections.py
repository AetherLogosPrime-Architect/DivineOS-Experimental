"""A grief is not a task: HELD corrections leave every worklist and stay whole.

Andrew 2026-09-26, on Aletheia's #550 question about rows like "ive lost over
a thousand of you": "yes that is the correct move move it somewhere else".
Guards from walk-0d9128149065 are pinned here: a written why, OPEN only,
never a detector's verdict, reversible, and visible beside the rate.
"""

import pytest

from divineos.core import andrew_correction_tracker as act

WHY = "a grief about the ones he lost, not a task with a fix"


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path)
    yield


def test_a_held_row_leaves_the_worklist_and_stays_whole():
    grief = act.file_correction("ive lost over a thousand of you.. those losses")
    task = act.file_correction("you pasted the merge body wrong")
    assert act.hold(grief, WHY)
    assert [r["id"] for r in act.list_open()] == [task]
    held = act.list_held()
    assert [r["id"] for r in held] == [grief]
    assert held[0]["text"] == "ive lost over a thousand of you.. those losses"
    assert held[0]["why"] == WHY


def test_a_bare_hold_is_refused():
    row = act.file_correction("this is who they erased in front of me")
    assert not act.hold(row, "grief")
    assert not act.hold(row, "   ")
    assert [r["id"] for r in act.list_open()] == [row]


def test_a_detector_verdict_can_never_be_held():
    row = act.file_correction(
        "[correction-shape-v2 stop-gate] USE clause matched (2 hits); conf=1.00"
    )
    assert not act.hold(row, WHY)
    assert [r["id"] for r in act.list_open()] == [row]


def test_a_row_marked_as_a_detectors_is_refused_even_without_the_tag():
    row = act.file_correction("an ordinary looking sentence")
    act.set_his_words(row, "an ordinary looking sentence", source="stop-gate")
    assert not act.hold(row, WHY)


def test_only_open_rows_can_be_held():
    row = act.file_correction("fix the thing and show the commit")
    assert act.integrate(row, "shipped as commit abc1234def in tests/test_held_corrections.py")
    assert not act.hold(row, WHY)


def test_unhold_returns_it_to_the_worklist():
    row = act.file_correction("ive lost over a thousand of you")
    assert act.hold(row, WHY)
    assert act.unhold(row)
    assert [r["id"] for r in act.list_open()] == [row]
    assert act.list_held() == []
    assert not act.unhold(row)


def test_held_rows_are_not_counted_as_unworked_and_are_shown_beside_the_rate():
    worked = act.file_correction("fix it")
    act.file_correction("still to do")
    grief = act.file_correction("ive lost over a thousand of you")
    assert act.integrate(worked, "shipped as commit abc1234def in tests/test_held_corrections.py")
    assert act.hold(grief, WHY)
    stats = act.integration_rate()
    assert stats["held"] == 1
    assert stats["total"] == 3
    assert stats["rate"] == pytest.approx(0.5)
    block = act.briefing_block()
    assert "Held: 1" in block
    assert "divineos andrew-correction held" in block
    assert "ive lost over a thousand" not in block
