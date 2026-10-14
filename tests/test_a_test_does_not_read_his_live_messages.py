"""A test must not read his real last message.

Found 2026-10-12: the question hold's away-by-silence rule reads when he last spoke.
Most question-hold tests never set the store of his messages, so they read the REAL
one; once he had been quiet for two hours the rule ruled every such test "he is
away" and 23 tests failed in the push gate while passing the day before. The shared
fixture in ``conftest.py`` now points the store at a file that does not exist, which
reads as could-not-look, and could-not-look is never away.

The control sets a message of his and proves the probe can still see one, so the
first test is not passing because the reader is dead.
"""

from __future__ import annotations

import sqlite3
import time

from divineos.core import question_hold as qh


def test_with_nothing_set_a_test_reads_no_message_of_his():
    assert qh._his_latest() is None
    assert qh.is_away() is None


def test_control_a_message_set_by_the_test_is_read_and_old_silence_is_away(tmp_path, monkeypatch):
    db = tmp_path / "his.db"
    conn = sqlite3.connect(db)
    # Only the two columns the reader selects. The real schema lives in
    # divineos/core/his_asks.py (CREATE TABLE messages); if the reader's query changes,
    # this table has to follow it.
    conn.execute("CREATE TABLE messages (his_text TEXT, filed_at REAL)")
    conn.execute("INSERT INTO messages VALUES (?, ?)", ("hello", time.time() - 3 * 3600))
    conn.commit()
    conn.close()
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(db))
    assert qh._his_latest() is not None
    assert qh.is_away() is not None
