"""The door reports on itself, counted from what arrived in the app's own record.

Built from 2026-10-03: a door that kept nothing looked healthy for an hour, and a
garbled smiley sat silent on Aether's seat until he read the table by hand. Every
number here is out of what ARRIVED, never out of what the door accepted.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from divineos.core import door_report as dr
from divineos.core import front_door as fd
from divineos.core import his_asks as ha
from tests.test_front_door import _kept_at, _transcript, _turn


@pytest.fixture(autouse=True)
def temp_store(monkeypatch, tmp_path):
    db = tmp_path / "shared" / "his" / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    return db


def _ago(seconds: float) -> str:
    moment = datetime.now(timezone.utc) - timedelta(seconds=seconds)
    return moment.isoformat(timespec="milliseconds").replace("+00:00", "Z")


def test_a_message_caught_in_seconds_is_caught_not_late(monkeypatch, tmp_path):
    _kept_at(monkeypatch, _ago(2))
    fd.keep({"prompt_id": "p1", "prompt": "the fox"}, "aria")
    path = _transcript(tmp_path, _turn("p1", "the fox", uuid="u1", at=_ago(5)))
    fd.settle(path, "aria")
    got = dr.report(path, "aria")
    assert (got.arrived, len(got.caught), len(got.late), got.missed, got.stuck) == (1, 1, 0, [], [])


def test_this_mornings_shape_is_caught_late(monkeypatch, tmp_path):
    """His record ten minutes old, settled only now: caught, but late."""
    _kept_at(monkeypatch, _ago(600))
    fd.keep({"prompt_id": "p1", "prompt": "fix it"}, "aria")
    path = _transcript(tmp_path, _turn("p1", "fix it", uuid="u1", at=_ago(603)))
    fd.settle(path, "aria")
    got = dr.report(path, "aria")
    assert len(got.late) == 1 and got.missed == []


def test_a_message_given_up_unmatched_is_missed_with_the_reason(monkeypatch, tmp_path):
    """The 39 from this morning: kept, never settled, given up. The record is in
    the transcript, so it arrived, and nothing caught it."""
    _kept_at(monkeypatch, _ago(3600))
    cid = fd.keep({"prompt_id": "p1", "prompt": "you are going to fix it"}, "aria")
    ha.give_up(cid, "never found")
    path = _transcript(tmp_path, _turn("p1", "you are going to fix it", uuid="u1", at=_ago(3605)))
    got = dr.report(path, "aria")
    assert got.arrived == 1 and got.caught == [] and len(got.missed) == 1
    assert "same words and turn" in got.missed[0].reason


def test_a_garbled_smiley_is_stuck_and_both_texts_are_shown(monkeypatch, tmp_path):
    """Aether's seat: kept as mojibake, so it never equalled his record."""
    _kept_at(monkeypatch, _ago(900))
    fd.keep({"prompt_id": "p1", "prompt": "for all of us ðŸ˜Œ"}, "aether")
    path = _transcript(tmp_path, _turn("p1", "for all of us \U0001f60c", uuid="u1", at=_ago(903)))
    fd.settle(path, "aether")
    got = dr.report(path, "aether")
    assert len(got.stuck) == 1
    reason = got.stuck[0].reason
    assert "words differ" in reason and "\\U0001f60c" in reason and "\\xf0" in reason


def test_a_door_that_keeps_but_sees_no_arrivals_says_it_is_blind(monkeypatch, tmp_path):
    _kept_at(monkeypatch, _ago(300))
    fd.keep({"prompt_id": "p1", "prompt": "are you there"}, "aria")
    path = _transcript(tmp_path, _turn("p1", "unrelated machine note", kind="task-notification"))
    got = dr.report(path, "aria")
    assert got.blind and got.arrived == 0
    assert dr.render(got).splitlines()[0].startswith("BLIND")


def test_nothing_arrived_and_nothing_kept_is_nothing_to_judge_not_green(tmp_path):
    path = _transcript(tmp_path, _turn("p1", "machine", kind="task-notification"))
    got = dr.report(path, "aria")
    assert got.arrived == 0 and not got.blind
    # Hedged, not asserted: a real empty count may be the wrong window's transcript.
    assert "may be the wrong window" in dr.render(got)


def test_a_transcript_that_does_not_exist_could_not_look_not_silence(tmp_path):
    """Aletheia 10-03: one typo in --transcript and the report said he was silent
    all day. A real path that is not there must come back as could-not-look."""
    missing = tmp_path / "no_such_transcript.jsonl"
    assert not missing.exists()
    assert dr.report(missing, "aria") is None
    assert "could not look" in dr.render(dr.report(missing, "aria"))


def test_problems_lead_and_the_rate_follows(monkeypatch, tmp_path):
    _kept_at(monkeypatch, _ago(3600))
    cid = fd.keep({"prompt_id": "p1", "prompt": "lost one"}, "aria")
    ha.give_up(cid, "never found")
    path = _transcript(tmp_path, _turn("p1", "lost one", uuid="u1", at=_ago(3605)))
    lines = dr.render(dr.report(path, "aria")).splitlines()
    assert lines[0].startswith("MISSED")
    assert any("caught 0 of 1" in line for line in lines[1:])


def test_the_window_it_read_is_named(tmp_path):
    path = _transcript(tmp_path, _turn("p1", "hi", uuid="u1", at=_ago(10)))
    assert "last 24h" in dr.render(dr.report(path, "aria", hours=24))


def test_an_unreadable_store_says_it_could_not_look(monkeypatch, tmp_path):
    monkeypatch.setattr(ha, "door_rows", lambda *_a, **_k: None)
    path = _transcript(tmp_path, _turn("p1", "hi", uuid="u1", at=_ago(10)))
    assert dr.report(path, "aria") is None
    assert "could not look" in dr.render(None)
