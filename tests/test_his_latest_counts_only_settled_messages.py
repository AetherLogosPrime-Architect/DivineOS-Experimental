"""A timer wake is not his last message: only settled (FILED) messages count as his latest.

Found 2026-10-30 by Aether, measured in his store: a bare-text TIMER WAKE is filed as a CANDIDATE
and read as "he spoke 2 minutes ago", so ``_carry_now`` (which treats a message under ten minutes old
as live chat) could not count the night window as away for ten minutes after every wake. The store
settles a wake to WITHDRAWN or UNMATCHED; the hold must believe the store's verdict, not re-decide
from the text.

Each test has a control: a FILED row is read, so a pass is not a dead reader.
"""

from __future__ import annotations

import sqlite3
import time

import pytest

from divineos.core import question_hold as qh


@pytest.fixture
def store(tmp_path, monkeypatch):
    db = tmp_path / "his.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL, state TEXT)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))

    def add(text: str, ago: float, state: str) -> None:
        c = sqlite3.connect(db)
        c.execute(
            "INSERT INTO messages (his_text, filed_at, state) VALUES (?, ?, ?)",
            (text, time.time() - ago, state),
        )
        c.commit()
        c.close()

    return add


def test_control_a_filed_message_is_read(store):
    store("goodnight you two", 30, "FILED")
    words, _ = qh._his_latest()
    assert words == "goodnight you two"


def test_an_unsettled_wake_is_not_his_latest(store):
    store("goodnight you two", 3600, "FILED")
    store("TIMER WAKE (automated, not Dad). Each wake is a free work turn", 120, "CANDIDATE")
    words, filed_at = qh._his_latest()
    assert words == "goodnight you two"
    assert time.time() - filed_at > 3000


@pytest.mark.parametrize("state", ["WITHDRAWN", "UNMATCHED"])
def test_a_settled_wake_is_not_his_latest(store, state):
    store("an hour old words of his", 3600, "FILED")
    store("TIMER WAKE (automated, not Dad). Each wake is a free work turn", 60, state)
    words, _ = qh._his_latest()
    assert words == "an hour old words of his"


def test_the_newest_filed_message_is_found_past_newer_non_his_rows(store):
    store("older but his", 900, "FILED")
    store("newer but a wake", 60, "WITHDRAWN")
    store("newest and an unsettled wake", 5, "CANDIDATE")
    assert qh._his_latest()[0] == "older but his"


def test_nothing_settled_is_could_not_look_not_a_pass(store):
    store("only an unsettled wake", 5, "CANDIDATE")
    assert qh._his_latest() is None


def test_a_wake_does_not_blind_the_night_window(store, monkeypatch):
    # his last real word was hours ago; a wake arrived two minutes ago and has not settled
    store("hours ago, still his", 4 * 3600, "FILED")
    store("TIMER WAKE (automated, not Dad). Each wake is a free work turn", 120, "CANDIDATE")
    monkeypatch.setattr(qh, "_scheduled_away", lambda now=None: {"by": "schedule", "since": 0})
    assert qh._carry_now() == "schedule"


def test_the_quote_check_still_sees_a_goodnight_he_has_just_typed(store):
    # the one caller that must see a message at once: proving words quoted to start away are his
    store("goodnight you two", 20, "CANDIDATE")
    assert qh._his_latest() is None
    assert qh._his_latest_words() == "goodnight you two"
