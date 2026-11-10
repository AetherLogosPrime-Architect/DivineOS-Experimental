"""A "he said he is stepping away" file is only true until he speaks again.

Second-reader finding on #745: `_carry_now` answered "his words" whenever the away file existed.
The file is cleared by his next message through a hook (`came_back`), but if that hook never ran
the file went on saying "away" with a newer message of his sitting in the store, and the room
gate (and the question hold) stood down for a man who was typing. The rule under test: a
words-away file is stale once a real message of his was filed AFTER it was set. Real file, real
(temporary) store, the judge is never patched. Could-not-look keeps the file standing, as before:
without a readable message nothing can show it stale.
"""

from __future__ import annotations

import json
import sqlite3
import time

import pytest


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    return mod


def _set_away(mod, seconds_ago: float) -> float:
    since = time.time() - seconds_ago
    mod.AWAY.write_text(
        json.dumps({"his_words": "im going to bed", "since": since}), encoding="utf-8"
    )
    return since


def _store(tmp_path, monkeypatch, rows):
    """A his-asks store holding (text, filed_at) rows."""
    db = tmp_path / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    for text, filed_at in rows:
        conn.execute("INSERT INTO messages VALUES (?, ?)", (text, filed_at))
    conn.commit()
    conn.close()


def test_a_message_of_his_after_the_file_makes_it_stale(qh, tmp_path, monkeypatch):
    """THE DEFECT: he spoke an hour after saying goodnight and the gate still stood down."""
    since = _set_away(qh, seconds_ago=7200)
    _store(tmp_path, monkeypatch, [("good morning, are you there", since + 3600)])
    assert qh._carry_now() == ""


def test_the_file_stands_while_his_latest_message_is_the_one_that_set_it(qh, tmp_path, monkeypatch):
    """CONTROL: the goodnight message itself was filed BEFORE the file was written."""
    since = _set_away(qh, seconds_ago=600)
    _store(tmp_path, monkeypatch, [("im going to bed", since - 5)])
    assert qh._carry_now() == "his words"


def test_a_message_filed_at_the_very_instant_does_not_make_it_stale(qh, tmp_path, monkeypatch):
    """Boundary (Knuth): equal times are not 'after'."""
    since = _set_away(qh, seconds_ago=600)
    _store(tmp_path, monkeypatch, [("im going to bed", since)])
    assert qh._carry_now() == "his words"


def test_a_notice_filed_after_the_file_is_not_him_and_does_not_make_it_stale(
    qh, tmp_path, monkeypatch
):
    since = _set_away(qh, seconds_ago=600)
    _store(
        tmp_path,
        monkeypatch,
        [
            ("im going to bed", since - 5),
            ("<task-notification>done</task-notification>", since + 60),
            ("&lt;system-reminder>x&lt;/system-reminder>", since + 90),
        ],
    )
    assert qh._carry_now() == "his words"


def test_without_a_readable_message_the_file_still_stands(qh):
    """Could not look cannot show the file stale, so it keeps its old meaning (the conftest points
    the store at a file that does not exist)."""
    _set_away(qh, seconds_ago=600)
    assert qh._carry_now() == "his words"


def test_ignoring_a_stale_file_is_counted_in_the_log(qh, tmp_path, monkeypatch):
    since = _set_away(qh, seconds_ago=7200)
    _store(tmp_path, monkeypatch, [("good morning", since + 3600)])
    qh._carry_now()
    rows = [json.loads(line) for line in qh.HOLD_LOG.read_text(encoding="utf-8").splitlines()]
    assert any(r["kind"] == "stale_away_ignored" for r in rows)
