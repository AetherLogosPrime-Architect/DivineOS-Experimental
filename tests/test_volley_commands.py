"""`divineos volley start|stop|status`: the plain front door to the stepped-away path.

Outside readers (2026-11-03) found the first version was a keyless switch: any seat could run
`volley start` and hand itself "he is away" with no proof he said so, and once on it carried a
question to the morning list while he was typing. The reshape adds NO second away kind. `start`
takes his going-to-bed words and runs the existing question_hold.step_away, whose proof is that
the words appear in his latest real message as the house filed it, which a seat cannot write.
Real store, real sqlite file; the clock window is switched off so no result depends on the hour.
"""

from __future__ import annotations

import importlib.util
import sqlite3
import time

import click
import pytest
from click.testing import CliRunner

from divineos.core import question_hold as qh

BED = "ok I'm going to bed now, you two volley"


@pytest.fixture(autouse=True)
def _house(tmp_path, monkeypatch):
    monkeypatch.setattr(qh, "AWAY", tmp_path / "away.json")
    monkeypatch.setattr(qh, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(qh, "_scheduled_away", lambda now=None: None)  # the clock is not under test
    db = tmp_path / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    conn.commit()
    conn.close()
    return db


def _he_says(db, text: str, at: float | None = None) -> None:
    conn = sqlite3.connect(db)
    conn.execute("INSERT INTO messages VALUES (?, ?)", (text, time.time() if at is None else at))
    conn.commit()
    conn.close()


def _cli() -> click.Group:
    from divineos.cli.volley_commands import register

    group = click.Group()
    register(group)
    return group


def _run(*args: str):
    return CliRunner().invoke(_cli(), ["volley", *args])


def test_start_with_his_real_words_begins_the_quiet(_house):
    _he_says(_house, BED)
    r = _run("start", "--his-words", "I'm going to bed now, you two volley")
    assert r.exit_code == 0, r.output
    away = qh.is_away()
    assert away is not None and "going to bed" in away["his_words"]
    assert "the-night-letter-to-andrew-" in r.output and "## From" in r.output


def test_start_with_no_words_is_refused_and_nothing_starts(_house):
    # The keyless switch: no proof he said anything. Must not start.
    _he_says(_house, BED)
    r = _run("start")
    assert r.exit_code != 0
    assert qh.is_away() is None


def test_start_in_words_he_did_not_say_is_refused(_house):
    _he_says(_house, "can you look at the doorbell test again")
    r = _run("start", "--his-words", "I'm going to bed now")
    assert r.exit_code != 0 and "not in his latest message" in r.output
    assert qh.is_away() is None


def test_start_cannot_be_forged_when_his_words_cannot_be_read(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "nowhere" / "none.db"))
    r = _run("start", "--his-words", "I'm going to bed now, you two volley")
    assert r.exit_code != 0
    assert qh.is_away() is None  # could-not-look refuses, never passes


def test_words_that_do_not_mean_away_are_refused_even_when_he_said_them(_house):
    _he_says(_house, "ok go ahead and proceed")
    r = _run("start", "--his-words", "ok go ahead and proceed")
    assert r.exit_code != 0 and "do not say he is away" in r.output
    assert qh.is_away() is None


def test_there_is_no_second_away_kind():
    assert importlib.util.find_spec("divineos.core.volley_now") is None
    assert not hasattr(qh, "_volley_started")


def test_a_question_is_carried_only_while_his_words_stand(_house):
    _he_says(_house, BED, at=time.time() - 60)
    assert qh._carry_now() == ""  # control: before he says it, a question is held as usual
    assert _run("start", "--his-words", "going to bed now, you two volley").exit_code == 0
    assert qh._carry_now() == "his words"
    # He types again: the house clears the away (the same call his message triggers), and the
    # question is held for him, not sent to the morning list while he is present.
    _he_says(_house, "wait, one more thing before I go")
    assert qh.came_back() is True
    assert qh._carry_now() == ""
    assert qh.is_away() is None


def test_stop_and_status_read_the_one_away_there_is(_house):
    assert "not" in _run("status").output
    _he_says(_house, BED)
    _run("start", "--his-words", "going to bed now, you two volley")
    assert "is running" in _run("status").output
    assert "ended" in _run("stop").output
    assert qh.is_away() is None
    assert "not" in _run("status").output
