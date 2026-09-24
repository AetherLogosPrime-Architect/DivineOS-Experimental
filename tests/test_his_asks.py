"""His asks' store: the front door's record, tested against its game walk.

Every test here runs on a temporary file. The store itself refuses to open his
real record under pytest, and the last test proves that refusal holds.
"""

from __future__ import annotations

import os

import pytest

from divineos.core import his_asks as ha


@pytest.fixture(autouse=True)
def temp_store(monkeypatch, tmp_path):
    monkeypatch.setenv("DIVINEOS_HIS_ASKS_DB", str(tmp_path / "shared" / "his" / "asks.db"))


def _file(candidate="c1", text="build me the thing i asked for", prompt="p1"):
    ha.file_candidate(candidate, prompt, text, "2026-09-24T21:00:00Z", "aria")


def _kept(candidate="c1", text="build me the thing i asked for", uuid="u1"):
    _file(candidate, text)
    return ha.confirm(candidate, uuid, "human", f"<system-reminder>x</system-reminder>{text}")


def test_his_message_is_kept_then_confirmed_onto_his_record():
    assert _kept() == ha.FILED
    assert [k.uuid for k in ha.pending()] == ["u1"]


def test_filing_twice_at_the_door_keeps_one():
    _file("c1", "build me the thing")
    _file("c1", "build me the thing")
    assert [c.candidate_id for c in ha.unsettled()] == ["c1"]


def test_a_notification_in_his_seat_is_withdrawn_with_the_stamp_as_reason():
    _file("c1", "Monitor event: new letter")
    assert ha.confirm("c1", "u9", "task-notification", "Monitor event: new letter") == ha.WITHDRAWN
    assert ha.pending() == []
    assert ha.unsettled() == []


def test_a_candidate_cannot_be_settled_onto_a_record_that_does_not_hold_his_words():
    """Game walk 2: the uuid binds the words."""
    _file("c1", "build me the thing")
    with pytest.raises(ha.HisAsksRefused):
        ha.confirm("c1", "u1", "human", "something he never typed")


def test_a_resumed_sessions_copy_of_his_record_is_kept_once():
    """The photocopy finding: a resumed session carries his record's uuid."""
    assert _kept("c1", uuid="u1") == ha.FILED
    assert _kept("c2", uuid="u1") == ha.WITHDRAWN
    assert [k.uuid for k in ha.pending()] == ["u1"]


def test_an_unsettled_candidate_is_visible_not_silent():
    _file("c1", "build me the thing")
    assert [c.candidate_id for c in ha.unsettled()] == ["c1"]
    assert ha.pending() == []


def test_not_an_ask_needs_a_reason():
    _kept()
    with pytest.raises(ha.HisAsksRefused):
        ha.sort("u1", ha.NOT_AN_ASK, "", "aria")
    ha.sort("u1", ha.NOT_AN_ASK, "an acknowledgement of a fix he asked for", "aria")
    assert ha.pending() == []


def test_a_second_sort_without_superseding_is_refused_from_either_seat():
    """Game walk: 'let the other one sort it' is not available."""
    _kept()
    first = ha.sort("u1", ha.BUILD, "he asked for a build", "aria")
    with pytest.raises(ha.HisAsksRefused):
        ha.sort("u1", ha.NOT_AN_ASK, "only chatting, nothing asked", "aether")
    second = ha.sort("u1", ha.STANDING, "a way he wants to be treated", "aether", supersedes=first)
    assert second > first


def test_superseding_must_name_the_latest_sort():
    _kept()
    first = ha.sort("u1", ha.BUILD, "he asked for a build", "aria")
    ha.sort("u1", ha.STANDING, "a way he wants to be treated", "aether", supersedes=first)
    with pytest.raises(ha.HisAsksRefused):
        ha.sort("u1", ha.BUILD, "back to a build after all", "aria", supersedes=first)


def test_only_filed_messages_can_be_sorted_or_marked_same_ask():
    _file("c1", "build me the thing")
    with pytest.raises(ha.HisAsksRefused):
        ha.sort("unknown-uuid", ha.BUILD, "he asked", "aria")
    with pytest.raises(ha.HisAsksRefused):
        ha.same_ask_as("unknown-uuid", 1, "aria")


def test_could_not_file_is_its_own_record():
    ha.could_not_file("p1", "database is locked", "aria")
    assert ha.pending() == []  # nothing filed -- and the failure is not lost:
    import sqlite3

    conn = sqlite3.connect(os.environ["DIVINEOS_HIS_ASKS_DB"])
    assert conn.execute("SELECT ref, error FROM could_not_file").fetchall() == [
        ("p1", "database is locked")
    ]


def test_both_seats_reach_the_same_file(tmp_path, monkeypatch):
    """D2: one store for both seats, proven on a temporary shared dir."""
    _file("c1", "said to aria")
    first = ha.his_asks_path()
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path / "another-seat"))
    assert ha.his_asks_path() == first
    ha.file_candidate("c2", "p2", "said to aether", "t", "aether")
    assert sorted(c.candidate_id for c in ha.unsettled()) == ["c1", "c2"]


def test_an_unreadable_store_says_so_rather_than_nothing_owed(monkeypatch):
    def broken():
        raise OSError("disk gone")

    monkeypatch.setattr(ha, "_conn", broken)
    assert ha.pending() is None
    assert ha.unsettled() is None


def test_a_test_can_never_open_his_real_record(monkeypatch):
    monkeypatch.delenv("DIVINEOS_HIS_ASKS_DB")
    assert ha.his_asks_path() == ha._real_path()
    with pytest.raises(ha.HisAsksRefused):
        ha.file_candidate("c1", "p1", "a fake message of his", "t", "aria")


def test_many_of_his_messages_under_one_prompt_id_are_all_kept():
    """The real case (Aether, 2026-09-24): one promptId, c701829a, sat on ten of
    his messages across eight hours, because a message sent mid-turn fires the
    prompt hook with the running turn's id. Keyed on the prompt id, all but the
    first were silently dropped."""
    said = [
        ("i am quiet because i am given no space to answer", "2026-09-24T21:40:01Z"),
        ("also if you are making a shared copy it needs attribution", "2026-09-24T21:40:09Z"),
        ("proceed", "2026-09-24T21:52:30Z"),
    ]
    for text, at in said:
        cid = ha.mint_candidate_id("c701829a", text, at)
        ha.file_candidate(cid, "c701829a", text, at, "aria")
    kept = ha.unsettled()
    assert sorted(c.his_text for c in kept) == sorted(t for t, _ in said)
    assert {c.prompt_id for c in kept} == {"c701829a"}


def test_the_minted_id_is_stable_and_tells_messages_apart():
    one = ha.mint_candidate_id("p", "proceed", "2026-09-24T21:52:30Z")
    assert one == ha.mint_candidate_id("p", "proceed", "2026-09-24T21:52:30Z")
    assert one != ha.mint_candidate_id("p", "proceed", "2026-09-24T21:59:00Z")
