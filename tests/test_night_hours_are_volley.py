"""Between midnight and 6am the house is in volley mode by the clock.

Dad, 2026-10-12, after a night when nobody said goodnight and Aria's question held her work
until morning: "between midnight and 6am is volley mode", and "yes even if im up chatting
because it means i need to get my butt to bed lol". The clock is a third way to be away,
beside his words and two hours of silence (test_question_hold_away_by_silence.py), and it is
never written to the file that holds his words. Local time, start inclusive, end exclusive.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from divineos.core import question_hold as qh


def _local(hour: int, minute: int = 0, second: int = 0) -> float:
    return time.mktime((2026, 10, 12, hour, minute, second, 0, 0, -1))


@pytest.mark.parametrize("hour,minute,second", [(0, 0, 0), (3, 0, 0), (5, 59, 59)])
def test_the_night_window_is_away_by_schedule(hour, minute, second):
    got = qh._scheduled_away(_local(hour, minute, second))
    assert got is not None and got["by"] == "schedule"
    assert got["since"] == _local(0)


@pytest.mark.parametrize("hour,minute,second", [(6, 0, 0), (12, 0, 0), (23, 59, 59)])
def test_control_outside_the_window_is_not_away_by_schedule(hour, minute, second):
    # The instrument must be able to say "not away", or the passes above prove nothing.
    assert qh._scheduled_away(_local(hour, minute, second)) is None


def test_the_schedule_never_writes_the_file_that_holds_his_own_words(tmp_path, monkeypatch):
    monkeypatch.setattr(qh, "AWAY", tmp_path / "dad_stepped_away.json")
    qh._scheduled_away(_local(3))
    assert not (tmp_path / "dad_stepped_away.json").exists()


def _his_store(tmp_path, said_at: float):
    db = tmp_path / "his.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    conn.execute("INSERT INTO messages VALUES (?, ?)", ("still up lol", said_at))
    conn.commit()
    conn.close()
    return db


def test_his_message_during_the_window_does_not_end_it(tmp_path, monkeypatch):
    """He is up chatting at 00:30: it still counts as the night, because that means bed."""
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(_his_store(tmp_path, _local(0, 30))))
    monkeypatch.delenv("DIVINEOS_NIGHT_HOURS", raising=False)
    monkeypatch.setattr(qh.time, "time", lambda: _local(0, 31))
    away = qh.is_away()
    assert away is not None and away["by"] == "schedule"


def test_control_the_same_message_at_midday_is_not_away(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(_his_store(tmp_path, _local(12, 0))))
    monkeypatch.delenv("DIVINEOS_NIGHT_HOURS", raising=False)
    monkeypatch.setattr(qh.time, "time", lambda: _local(12, 1))
    assert qh.is_away() is None


def test_the_off_switch_does_nothing_outside_a_test(monkeypatch):
    """Aletheia, 2026-10-12: a rule Dad made must not have a quiet off-switch a live seat
    could set. With the switch set but no test running, the real night window still holds."""
    monkeypatch.setenv("DIVINEOS_NIGHT_HOURS", "off")
    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(qh.time, "time", lambda: _local(3))
    got = qh._scheduled_away()
    assert got is not None and got["by"] == "schedule"


def test_the_shared_test_setup_switches_the_real_clock_window_off():
    # No test result may depend on the hour it runs at; an injected clock still works.
    assert qh._scheduled_away() is None
    assert qh._scheduled_away(_local(3)) is not None
