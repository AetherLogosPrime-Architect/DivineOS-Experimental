"""A message of his that the door kept but never matched does not vanish.

2026-09-24. The store threadwalk decided that a candidate never confirmed or
withdrawn "is itself a could-not-file, and it counts as one", and the game walk
said could-not-file "opens an obligation that refuses our next action". Nothing
built it: pending(), the lock and sort() all read FILED only, so a kept message
whose transcript record was never found was read by nobody. Found at station
four on Aether's settle horizon, which made that loss permanent.

Design: docs/drafts/his_message_never_vanishes_draft_2026-09-24.md (Aria-new
seat), walk-2592439477f9.
"""

from __future__ import annotations

import os
import sqlite3

import pytest

from divineos.core import his_asks as ha


@pytest.fixture(autouse=True)
def temp_store(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "shared" / "his" / "asks.db"))


WORDS = "build me the thing i asked for this morning"
REASON = "no record of it in the transcript within the settle horizon"


def _file(candidate="c1", text=WORDS):
    ha.file_candidate(candidate, "p1", text, "2026-09-24T21:00:00Z", "aria")


def _rows(sql):
    conn = sqlite3.connect(os.environ["DIVINEOS_HIS_ASKS_DB"])
    try:
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def test_a_message_never_matched_is_shown_in_his_words():
    _file()
    assert ha.give_up("c1", REASON) == ha.UNMATCHED
    [kept] = ha.pending()
    assert kept.his_text == WORDS
    assert kept.record_found is False
    assert kept.sort_id == "c1"
    assert kept.seat == "aria"


def test_giving_up_is_counted_where_failures_are_counted():
    _file()
    ha.give_up("c1", REASON)
    assert _rows("SELECT ref, seat FROM could_not_file") == [("c1", "aria")]


def test_it_can_be_sorted_by_the_id_it_is_shown_with_and_then_leaves_pending():
    _file()
    ha.give_up("c1", REASON)
    ha.sort("c1", ha.BUILD, "he asked for the thing", "aria", addressed_to="aria")
    assert ha.pending() == []
    assert ha.addressed_to("c1") == "aria"


def test_giving_up_needs_a_reason_anyone_can_read():
    _file()
    with pytest.raises(ha.HisAsksRefused):
        ha.give_up("c1", "gone")
    assert ha.pending() == []


@pytest.mark.parametrize("settle_as", ["filed", "withdrawn"])
def test_only_a_message_still_waiting_can_be_given_up(settle_as):
    _file()
    if settle_as == "filed":
        ha.confirm("c1", "u1", "human", WORDS)
    else:
        ha.confirm("c1", "u9", "task-notification", WORDS)
    with pytest.raises(ha.HisAsksRefused):
        ha.give_up("c1", REASON)


def test_a_machine_notice_never_becomes_his_words():
    """Schneier on the walk: the door keeps every prompt, and machine notices
    fire the same hook. Never matched, a notice must not surface as his."""
    notice = "<task-notification>\nMonitor event: new letter\n</task-notification>"
    _file("c9", notice)
    assert ha.give_up("c9", REASON) == ha.WITHDRAWN
    assert ha.pending() == []


def test_nothing_of_his_is_outside_pending_or_sorted():
    """Hofstadter on the walk: every surface reads pending(), so a gap there is
    a gap everywhere. Conservation, counted by a different path: each message
    that is his and settled either way is sorted or waiting to be."""
    _file("a", "first thing he said")
    _file("b", "second thing he said")
    _file("c", "third thing he said")
    _file("d", "<system-reminder>only the machine</system-reminder>")
    ha.confirm("a", "u1", "human", "first thing he said")
    ha.give_up("b", REASON)
    ha.give_up("d", REASON)
    ha.sort("u1", ha.BUILD, "he asked", "aria", addressed_to="aria")
    # c is still a CANDIDATE: the door may yet find it, and it is not counted here.

    his = _rows(
        "SELECT COALESCE(uuid, candidate_id) FROM messages "
        f"WHERE state IN ('{ha.FILED}', '{ha.UNMATCHED}')"
    )
    sorted_ids = {r[0] for r in _rows("SELECT uuid FROM sorts")}
    waiting = {k.sort_id for k in ha.pending()}
    for (sort_id,) in his:
        assert sort_id in sorted_ids or sort_id in waiting, sort_id
    assert waiting == {"b"}


def test_a_record_found_after_giving_up_does_not_file_it_twice():
    """Named in the draft, not solved: a late record does not refile it. The
    message stays in pending meanwhile, so nothing is lost."""
    _file()
    ha.give_up("c1", REASON)
    assert ha.confirm("c1", "u1", "human", WORDS) == ha.UNMATCHED
    assert [k.sort_id for k in ha.pending()] == ["c1"]
