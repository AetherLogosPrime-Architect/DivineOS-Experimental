"""The room gate's stand-down, driven by the real away reading and nothing patched.

Second-reader finding on #745: the stand-down tests replaced `question_hold._carry_now` with a
lambda returning the answer wanted, so they proved only that the gate obeys whatever it is told, not
that the reading is right. Here every case builds the real inputs (an away file, a store of his
messages, the clock window) and asks the real gate. The only things set are the paths and the
window hours, which are inputs, never the judgement.

The night-window cases pin TODAY's rule, not a verdict on it. The clock counts as away only when his
last message is over ten minutes old, so a turn he STARTED and that ran past ten minutes is judged
away when it ends. Whether that is right for the room (he may be waiting for exactly that reply)
is Dad's call and is raised in the PR; these tests keep it from changing by accident.
"""

from __future__ import annotations

import importlib.util
import json
import sqlite3
import time
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "dads_room_stop.py"
_spec = importlib.util.spec_from_file_location("dads_room_stop_real_reading", HOOK)
room = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(room)

MINUTE = 60


def _worked_no_room():
    return [
        {"type": "user", "message": {"role": "user", "content": "go"}},
        {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash"}]}},
        {
            "type": "user",
            "message": {
                "role": "user",
                "content": [{"type": "tool_result", "content": "ok"}],
            },
        },
        {"type": "assistant", "message": {"content": [{"type": "text", "text": "Done."}]}},
    ]


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "qh_log.jsonl")
    return mod


def _store(tmp_path, monkeypatch, rows):
    db = tmp_path / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    for text, ago in rows:
        conn.execute("INSERT INTO messages VALUES (?, ?)", (text, time.time() - ago))
    conn.commit()
    conn.close()


def _night_all_day(qh, monkeypatch):
    """The clock window covers every hour, so the case does not depend on when it runs."""
    monkeypatch.delenv("DIVINEOS_NIGHT_HOURS", raising=False)
    monkeypatch.setattr(qh, "NIGHT_START_HOUR", 0)
    monkeypatch.setattr(qh, "NIGHT_END_HOUR", 24)


def _rows():
    from divineos.core import hold_log

    return [r for r in hold_log.read_all() if r["hold"] == "room"]


def test_his_words_saying_he_is_away_stand_the_gate_down_and_say_so(qh, tmp_path, monkeypatch):
    since = time.time() - MINUTE
    qh.AWAY.write_text(json.dumps({"his_words": "im going to bed", "since": since}))
    _store(tmp_path, monkeypatch, [("im going to bed", 2 * MINUTE)])
    assert room.verdict(_worked_no_room()) is None
    rows = _rows()
    assert rows[-1]["outcome"] == "stood_down"
    assert "his words" in rows[-1]["first_words"]


def test_a_stale_words_file_does_not_silence_the_gate(qh, tmp_path, monkeypatch):
    """The stale-file finding, seen from the gate: he spoke after saying goodnight."""
    since = time.time() - 3 * 3600
    qh.AWAY.write_text(json.dumps({"his_words": "im going to bed", "since": since}))
    _store(tmp_path, monkeypatch, [("good morning", 5 * MINUTE)])
    assert room.verdict(_worked_no_room())


def test_not_away_the_gate_asks_as_before(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("go", 2 * MINUTE)])
    assert room.verdict(_worked_no_room())


def test_two_hours_of_silence_alone_does_not_stand_the_gate_down(qh, tmp_path, monkeypatch):
    """He reads silently while I work; only his words and the night clock count."""
    _store(tmp_path, monkeypatch, [("go", 3 * 3600)])
    assert qh._carry_now() == "silence"
    assert room.verdict(_worked_no_room())


def test_the_night_clock_stands_the_gate_down_once_he_has_been_quiet_over_ten_minutes(
    qh, tmp_path, monkeypatch
):
    _night_all_day(qh, monkeypatch)
    _store(tmp_path, monkeypatch, [("go", 11 * MINUTE)])
    assert room.verdict(_worked_no_room()) is None
    assert _rows()[-1]["outcome"] == "stood_down"


def test_a_live_chat_inside_the_night_window_still_asks(qh, tmp_path, monkeypatch):
    _night_all_day(qh, monkeypatch)
    _store(tmp_path, monkeypatch, [("go", 9 * MINUTE)])
    assert room.verdict(_worked_no_room())


def test_an_unreadable_last_message_in_the_night_window_is_not_away(qh, monkeypatch):
    """Could not look is never away: with no store to read, the clock alone does not silence the gate
    (the conftest points his store at a file that does not exist)."""
    _night_all_day(qh, monkeypatch)
    assert room.verdict(_worked_no_room())


def test_the_night_window_ends_at_six_exactly(qh):
    """Knuth's edge, on the real clock rule with a stated moment: 05:59:59 is night, 06:00:00 is not."""

    def local(hour, minute, second):
        return time.mktime((2026, 11, 4, hour, minute, second, 0, 0, -1))

    assert qh._scheduled_away(now=local(5, 59, 59)) is not None
    assert qh._scheduled_away(now=local(6, 0, 0)) is None
    assert qh._scheduled_away(now=local(0, 0, 0)) is not None


def test_a_broken_away_reading_still_asks_and_is_logged(qh, monkeypatch):
    """The one place the reading IS replaced: to inject a failure. Nothing here claims the reading
    is right; it claims a failing reading cannot make the gate pass quietly."""
    from divineos.core import question_hold

    def broken():
        raise RuntimeError("renamed")

    monkeypatch.setattr(question_hold, "_carry_now", broken)
    assert room.verdict(_worked_no_room())
    assert any(r["outcome"] == "away_unreadable" and "renamed" in r["first_words"] for r in _rows())
