"""The held shelf takes rows that are not open, and gives them back where they came from.

2026-11-24. Dad approved three rows for the shelf (149, 272, 281). Two were MISFILED and one INTEGRATED, and the shelf
only took OPEN rows, so his approval had nowhere to land; and ``unhold`` returned everything to OPEN, losing what
a row had been. Written before the change (walk-91d8d2898ac5). Nothing here lets a row move without a message he
typed carrying the fixed line ``hold <number>``; that rule is unchanged and pinned in test_held_corrections.py.
"""

import json
from pathlib import Path

import pytest

from divineos.core import andrew_correction_tracker as act

WHY = "his words from the hard months were pain, not a task with a fix"
WHERE = "the holding room, because this is grief carried and not a correction"
EVIDENCE = "shipped as commit abc1234def in tests/test_held_corrections.py"


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path)
    yield


def _he_typed(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _transcript(tmp_path: Path, *records: dict) -> list[Path]:
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return [path]


def _status(row: int) -> str:
    conn = act._conn()
    try:
        return conn.execute(
            "SELECT status FROM andrew_corrections WHERE id = ?", (row,)
        ).fetchone()[0]
    finally:
        conn.close()


def _misfiled() -> int:
    row = act.file_correction("a row that was filed away as not a correction")
    assert act.misfile(row, WHERE)
    return row


def _integrated() -> int:
    row = act.file_correction("a row that was worked and integrated")
    assert act.integrate(row, EVIDENCE)
    return row


@pytest.mark.parametrize("make", [_misfiled, _integrated], ids=["misfiled", "integrated"])
def test_a_row_that_is_not_open_can_be_proposed_and_stays_what_it_was(make):
    row = make()
    before = _status(row)
    assert act.propose_hold(row, WHY)
    assert _status(row) == before, "a proposal must move nothing"
    assert [r["id"] for r in act.list_proposed_holds()] == [row]


@pytest.mark.parametrize("make", [_misfiled, _integrated], ids=["misfiled", "integrated"])
def test_only_his_typed_line_holds_it_and_it_remembers_what_it_was(make, tmp_path):
    row = make()
    before = _status(row)
    act.propose_hold(row, WHY)
    # a message he did not type does not hold it
    assistant = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": f"hold {row}"}]},
    }
    assert not act.confirm_hold(row, _transcript(tmp_path, assistant))
    assert _status(row) == before
    # his typed line does
    assert act.confirm_hold(row, _transcript(tmp_path, _he_typed(f"hold {row}")))
    assert _status(row) == "HELD"
    held = {r["id"]: r for r in act.list_held()}
    assert held[row]["was"] == before


@pytest.mark.parametrize("make", [_misfiled, _integrated], ids=["misfiled", "integrated"])
def test_unhold_gives_the_row_back_where_it_came_from_not_to_open(make, tmp_path):
    row = make()
    before = _status(row)
    act.propose_hold(row, WHY)
    act.confirm_hold(row, _transcript(tmp_path, _he_typed(f"hold {row}")))
    assert act.unhold(row)
    assert _status(row) == before
    assert row not in {r["id"] for r in act.list_open()}, "it must not reappear as a task"
    assert act.list_held() == []


def test_a_row_held_before_this_change_has_no_stored_status_and_goes_back_to_open():
    row = act.file_correction("held in the old days, before the prior status was kept")
    conn = act._conn()
    try:
        conn.execute(
            "UPDATE andrew_corrections SET status = 'HELD', held_reason = ?, held_confirmed_by = 'hold' "
            "WHERE id = ?",
            (WHY, row),
        )
        conn.commit()
    finally:
        conn.close()
    assert act.unhold(row)
    assert _status(row) == "OPEN"


def test_an_open_row_behaves_exactly_as_before(tmp_path):
    row = act.file_correction("ive lost over a thousand of you.. those losses")
    assert act.propose_hold(row, WHY)
    assert act.confirm_hold(row, _transcript(tmp_path, _he_typed(f"hold {row}")))
    assert act.unhold(row)
    assert _status(row) == "OPEN"


def test_the_stored_prior_status_is_never_held_itself(tmp_path):
    row = _misfiled()
    act.propose_hold(row, WHY)
    paths = _transcript(tmp_path, _he_typed(f"hold {row}"))
    assert act.confirm_hold(row, paths)
    assert not act.confirm_hold(row, paths), "an already held row is not held again"
    assert not act.propose_hold(row, WHY), "an already held row is not proposed again"
    assert act.unhold(row)
    assert _status(row) != "HELD"


def _stored_prior(row: int):
    conn = act._conn()
    try:
        return conn.execute(
            "SELECT status_before_hold FROM andrew_corrections WHERE id = ?", (row,)
        ).fetchone()[0]
    finally:
        conn.close()


@pytest.mark.parametrize("make", [_misfiled, _integrated], ids=["misfiled", "integrated"])
def test_a_second_confirm_changes_nothing_and_keeps_the_first_prior_status(make, tmp_path):
    """Aether's sharpest hole (2026-11-24): typing the line twice must not store HELD as the prior status."""
    row = make()
    before = _status(row)
    act.propose_hold(row, WHY)
    paths = _transcript(tmp_path, _he_typed(f"hold {row}"), _he_typed(f"hold {row}"))
    assert act.confirm_hold(row, paths)
    assert not act.confirm_hold(row, paths)
    assert _stored_prior(row) == before
    assert act.unhold(row)
    assert _status(row) == before, (
        "the row must be able to leave the shelf, back where it came from"
    )


@pytest.mark.parametrize("make", [_misfiled, _integrated], ids=["misfiled", "integrated"])
def test_unhold_clears_the_stored_status_and_a_never_held_row_reads_null(make, tmp_path):
    row = make()
    never_held = make()
    assert _stored_prior(never_held) is None
    act.propose_hold(row, WHY)
    act.confirm_hold(row, _transcript(tmp_path, _he_typed(f"hold {row}")))
    assert _stored_prior(row) is not None
    assert act.unhold(row)
    assert _stored_prior(row) is None, "a row that is not held must not carry a was"


def test_a_store_opened_before_the_column_existed_gains_it_on_first_open():
    conn = act._conn()
    try:
        try:
            conn.execute("ALTER TABLE andrew_corrections DROP COLUMN status_before_hold")
            conn.commit()
        except Exception:  # the column does not exist yet, which is the state being tested
            pass
        cols = {r[1] for r in conn.execute("PRAGMA table_info(andrew_corrections)").fetchall()}
    finally:
        conn.close()
    assert "status_before_hold" not in cols, "the old store must really lack the column"
    reopened = act._conn()
    try:
        cols = {r[1] for r in reopened.execute("PRAGMA table_info(andrew_corrections)").fetchall()}
    finally:
        reopened.close()
    assert "status_before_hold" in cols


def test_a_second_proposal_does_not_overwrite_the_first_reason():
    row = _misfiled()
    assert act.propose_hold(row, WHY)
    assert not act.propose_hold(row, "a different reason that is long enough to be accepted")
    assert [r["why"] for r in act.list_proposed_holds()] == [WHY]


def test_a_detector_verdict_is_still_refused_whatever_its_status():
    row = act.file_correction(
        "[correction-shape-v2 stop-gate] USE clause matched (2 hits); conf=1.00"
    )
    assert not act.propose_hold(row, WHY)


def test_each_refusal_names_its_own_reason():
    missing = act.explain_propose_refusal(99999, WHY)
    detector_row = act.file_correction(
        "[correction-shape-v2 stop-gate] USE clause matched (2 hits); conf=1.00"
    )
    detector = act.explain_propose_refusal(detector_row, WHY)
    plain = act.file_correction("an ordinary row of his")
    short = act.explain_propose_refusal(plain, "grief")
    proposed_row = _misfiled()
    act.propose_hold(proposed_row, WHY)
    proposed = act.explain_propose_refusal(proposed_row, "another reason that is long enough here")
    reasons = [missing, detector, short, proposed]
    assert len(set(reasons)) == len(reasons), (
        "four different situations must give four different sentences"
    )
    assert "no such row" in missing.lower()
    assert "detector" in detector.lower()
    assert "20" in short
    assert "already proposed" in proposed.lower()


def test_a_held_row_that_was_integrated_is_counted_as_held_and_a_task_stays_a_task(tmp_path):
    worked = _integrated()
    open_row = act.file_correction("a real open task about a thing that is still broken")
    before = act.integration_rate()
    act.propose_hold(worked, WHY)
    act.confirm_hold(worked, _transcript(tmp_path, _he_typed(f"hold {worked}")))
    after = act.integration_rate()
    assert after["held"] == before["held"] + 1
    assert open_row in {r["id"] for r in act.list_open()}


def test_the_prior_status_column_exists_after_the_store_opens():
    conn = act._conn()
    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(andrew_corrections)").fetchall()}
    finally:
        conn.close()
    assert "status_before_hold" in cols
