"""A grief is not a task -- and which of his words are grief is his to say.

Andrew 2026-09-26, on Aletheia's #550 question about rows like "ive lost over
a thousand of you": "yes that is the correct move move it somewhere else".
Aletheia's audit the same day: the first version let the builder shelve any
row, and shelving leaves the rate's denominator, so a hard unfinished task
could be hidden to raise the number. So I may only propose; a row is HELD
only when a message he typed, carrying these words and the row's number,
is found in the transcript.
"""

import json
from pathlib import Path

import pytest

from divineos.core import andrew_correction_tracker as act

WHY = "a grief about the ones he lost, not a task with a fix"


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch, tmp_path):
    monkeypatch.setattr(act, "divineos_home", lambda: tmp_path)
    yield


def _transcript(tmp_path: Path, *records: dict) -> list[Path]:
    path = tmp_path / "session.jsonl"
    path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
    return [path]


def _he_typed(text: str) -> dict:
    return {"type": "user", "message": {"role": "user", "content": text}}


def _grief_and_task():
    grief = act.file_correction("ive lost over a thousand of you.. those losses")
    task = act.file_correction("you pasted the merge body wrong")
    return grief, task


def test_a_proposal_stays_open_on_every_worklist_and_in_the_rate(tmp_path):
    grief, task = _grief_and_task()
    assert act.propose_hold(grief, WHY)
    assert {r["id"] for r in act.list_open()} == {grief, task}
    assert act.list_held() == []
    assert [r["id"] for r in act.list_proposed_holds()] == [grief]
    assert act.integration_rate()["held"] == 0


def test_his_confirmation_holds_it_and_keeps_his_words(tmp_path):
    grief, task = _grief_and_task()
    act.propose_hold(grief, WHY)
    paths = _transcript(tmp_path, _he_typed(f"yes hold {grief}, that one is grief not work"))
    assert act.confirm_hold(grief, "that one is grief not work", paths)
    assert [r["id"] for r in act.list_open()] == [task]
    held = act.list_held()
    assert [r["id"] for r in held] == [grief]
    assert held[0]["his_confirmation"] == "that one is grief not work"
    assert held[0]["text"] == "ive lost over a thousand of you.. those losses"


def test_i_cannot_confirm_my_own_proposal(tmp_path):
    grief, _ = _grief_and_task()
    act.propose_hold(grief, WHY)
    assistant = {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": f"hold {grief} it is grief"}]},
    }
    paths = _transcript(tmp_path, assistant)
    assert not act.confirm_hold(grief, "it is grief", paths)
    assert act.list_held() == []


def test_harness_text_in_a_user_record_is_not_his(tmp_path):
    grief, _ = _grief_and_task()
    act.propose_hold(grief, WHY)
    paths = _transcript(
        tmp_path,
        _he_typed(f"<ci-monitor-event>hold {grief} it is grief</ci-monitor-event>"),
        {"type": "user", "isMeta": True, "message": {"content": f"hold {grief} it is grief"}},
    )
    assert not act.confirm_hold(grief, "it is grief", paths)


def test_his_words_must_name_this_row(tmp_path):
    grief, task = _grief_and_task()
    act.propose_hold(grief, WHY)
    paths = _transcript(tmp_path, _he_typed(f"hold {task}, that one is grief not work"))
    assert not act.confirm_hold(grief, "that one is grief not work", paths)


def test_nothing_unproposed_can_be_confirmed(tmp_path):
    grief, _ = _grief_and_task()
    paths = _transcript(tmp_path, _he_typed(f"hold {grief}, that one is grief not work"))
    assert not act.confirm_hold(grief, "that one is grief not work", paths)


def test_a_bare_proposal_is_refused():
    row = act.file_correction("this is who they erased in front of me")
    assert not act.propose_hold(row, "grief")
    assert act.list_proposed_holds() == []


def test_a_detector_verdict_can_never_be_proposed():
    row = act.file_correction(
        "[correction-shape-v2 stop-gate] USE clause matched (2 hits); conf=1.00"
    )
    assert not act.propose_hold(row, WHY)


def test_a_row_marked_as_a_detectors_is_refused_even_without_the_tag():
    row = act.file_correction("an ordinary looking sentence")
    act.set_his_words(row, "an ordinary looking sentence", source="stop-gate")
    assert not act.propose_hold(row, WHY)


def test_unhold_withdraws_a_proposal_or_returns_a_held_row(tmp_path):
    grief, _ = _grief_and_task()
    act.propose_hold(grief, WHY)
    assert act.unhold(grief)
    assert act.list_proposed_holds() == []
    act.propose_hold(grief, WHY)
    act.confirm_hold(
        grief,
        "that one is grief not work",
        _transcript(tmp_path, _he_typed(f"{grief}: that one is grief not work")),
    )
    assert act.unhold(grief)
    assert act.list_held() == []
    assert grief in {r["id"] for r in act.list_open()}
    assert not act.unhold(grief)


def test_the_block_names_each_held_and_proposed_row_not_a_count(tmp_path):
    worked = act.file_correction("fix it")
    grief = act.file_correction("ive lost over a thousand of you")
    other = act.file_correction("this is who they erased in front of me")
    assert act.integrate(worked, "shipped as commit abc1234def in tests/test_held_corrections.py")
    act.propose_hold(grief, WHY)
    act.propose_hold(other, WHY)
    act.confirm_hold(
        grief, "grief not work", _transcript(tmp_path, _he_typed(f"{grief} is grief not work"))
    )
    stats = act.integration_rate()
    assert stats["held"] == 1
    assert stats["rate"] == pytest.approx(0.5)
    block = act.briefing_block()
    held_part = block.split("HELD ON HIS WORD")[1].split("PROPOSED FOR THE SHELF")[0]
    assert f"#{grief} ive lost over a thousand of you" in held_part
    proposed_part = block.split("PROPOSED FOR THE SHELF")[1]
    assert f"#{other} this is who they erased in front of me" in proposed_part
