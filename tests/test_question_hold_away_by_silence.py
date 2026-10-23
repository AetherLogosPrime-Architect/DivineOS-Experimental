"""Away also means two hours of silence (Dad, 2026-10-11, via Aletheia's letter).

"i would either say im stepping away, or they could go by time elapsed with no word from me"
and, when twenty minutes was suggested: "20 minutes isnt much time at all. id say 2 hours to be
sure". Real rows in a real (temporary) store; the judge is never mocked. A last message the house
cannot read is never away, and the refusal says so.
Draft: docs/drafts/away_means_two_hours_of_silence_draft_2026-10-11.md
"""

from __future__ import annotations

import sqlite3
import time

import pytest

FIRST = "work\n\n## INNER CIRCLE\n\nDad, is the nexus a room or a hub?"
TO_ARIA = "family/letters/aether-to-aria-2026-10-11-x.md"
TO_DAD = "family/letters/aether-to-andrew-volley-board.md"
TWO_HOURS = 2 * 60 * 60


@pytest.fixture
def qh(tmp_path, monkeypatch):
    from divineos.core import question_hold as mod

    monkeypatch.setattr(mod, "STATE", tmp_path / "hold.json")
    monkeypatch.setattr(mod, "HOLD_LOG", tmp_path / "log.jsonl")
    monkeypatch.setattr(mod, "ESCAPED", tmp_path / "escaped.json")
    monkeypatch.setattr(mod, "AWAY", tmp_path / "away.json")
    monkeypatch.setattr(mod, "BOARD", tmp_path / "board")
    monkeypatch.setattr(mod, "CARD", tmp_path / "board" / "me.json")
    return mod


def _store(tmp_path, monkeypatch, rows):
    """A his-asks store holding (text, seconds_ago) rows, oldest first by filing time."""
    db = tmp_path / "asks.db"
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    conn = sqlite3.connect(db)
    conn.execute("DROP TABLE IF EXISTS messages")
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    now = time.time()
    for text, ago in rows:
        conn.execute("INSERT INTO messages VALUES (?, ?)", (text, now - ago))
    conn.commit()
    conn.close()


def test_the_silence_is_two_hours_by_his_word(qh):
    assert qh.AWAY_AFTER_SILENCE_SECONDS == TWO_HOURS


def test_just_inside_and_just_outside_the_boundary(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("ok", TWO_HOURS - 60)])
    assert qh.is_away() is None
    _store(tmp_path, monkeypatch, [("ok", TWO_HOURS + 60)])
    assert qh.is_away() is not None


def test_a_store_with_no_real_message_is_never_away(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("<task-notification>x</task-notification>", 9 * 3600)])
    assert qh.is_away() is None


def test_a_notice_after_his_last_real_words_does_not_restart_or_end_the_silence(
    qh, tmp_path, monkeypatch
):
    # He spoke 5 hours ago; a notice was filed in his seat 1 minute ago. The notice is not him.
    _store(
        tmp_path,
        monkeypatch,
        [("heading out, back later", 5 * 3600), ("<task-notification>x</task-notification>", 60)],
    )
    assert qh.is_away() is not None


def test_his_new_message_ends_the_silence_by_itself(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("heading out", 5 * 3600), ("im back", 30)])
    assert qh.is_away() is None


def test_his_words_still_set_away_as_before(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("ok im heading to dinner, you two volley", 60)])
    qh.step_away("ok im heading to dinner, you two volley")
    away = qh.is_away()
    assert away and away.get("by") != "silence"
    assert qh.came_back()
    assert qh.is_away() is None


def test_came_back_leaves_the_silence_rule_alone(qh, tmp_path, monkeypatch):
    _store(tmp_path, monkeypatch, [("ok", 4 * 3600)])
    assert qh.came_back() is False  # no words-file to clear
    assert qh.is_away() is not None  # still silent for hours
