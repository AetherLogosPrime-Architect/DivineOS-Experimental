"""The station only he can advance.

Andrew 2026-09-08: *had Aria asked the EXACT same thing from you? you would
have followed the build flow.* Checked against the record and he was right,
four times in one day. The cause was structural: a station takes a reply FROM
Aria, so work involving her cannot move without her, and no station anywhere
required him. Skipping him was free.

These pin the half that makes it not free.
"""

from __future__ import annotations

import pytest

from divineos.core import andrew_request_repeats as rr
from divineos.core import station_marks as sm

_HIS_WORDS = "i have repeated it on end and nothing has been done about it"
_PLAIN = "speak to him as a person rather than reporting at him"


@pytest.fixture(autouse=True)
def isolated_home(monkeypatch, tmp_path):
    monkeypatch.setattr(sm, "divineos_home", lambda: tmp_path)
    monkeypatch.setattr(rr, "divineos_home", lambda: tmp_path)


def test_nothing_i_write_can_close_it():
    """The one refusal in the module with no artifact I could ever supply."""
    sm.open_item("item-1")
    with pytest.raises(sm.MarkRefused) as refusal:
        sm.mark("item-1", "his_word", __file__)
    assert "nothing I write closes this one" in str(refusal.value)


def test_unbound_work_cannot_be_closed_by_him_either():
    sm.open_item("item-1")
    result = sm.check("item-1", "his_word")
    assert result.state == sm.MISSING
    assert "not tied to anything he asked for" in result.why


def test_a_bound_row_he_has_not_closed_stays_missing():
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    sm.open_item("item-1")
    sm.bind_to_request("item-1", rid)
    result = sm.check("item-1", "his_word")
    assert result.state == sm.MISSING
    assert _PLAIN in result.why
    assert "going quiet never does" in result.why


def test_his_words_are_the_only_thing_that_satisfies_it():
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    sm.open_item("item-1")
    sm.bind_to_request("item-1", rid)
    rr.mark_landed(rid, "that actually landed, i can see the difference")
    result = sm.check("item-1", "his_word")
    assert result.state == sm.SATISFIED
    assert "that actually landed" in result.why


def test_a_repeat_reopens_the_station_after_i_thought_it_was_done():
    """He says it again, so it did not land, whatever the record said."""
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    sm.open_item("item-1")
    sm.bind_to_request("item-1", rid)
    rr.mark_landed(rid, "that landed, thank you for doing it")
    assert sm.check("item-1", "his_word").state == sm.SATISFIED

    rr.record_repeat(rid, "i should not have to keep saying this to you")
    assert sm.check("item-1", "his_word").state == sm.MISSING


def test_an_unreadable_store_is_could_not_look_not_he_said_nothing(monkeypatch):
    """The collapse that would let a broken database read as his silence."""
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    sm.open_item("item-1")
    sm.bind_to_request("item-1", rid)

    import sqlite3

    def broken():
        raise sqlite3.OperationalError("disk gone")

    monkeypatch.setattr(rr, "_conn", broken)
    result = sm.check("item-1", "his_word")
    assert result.state == sm.CANNOT_CHECK
    assert "not the same as him having said nothing" in result.why


def test_the_board_cannot_read_finished_while_he_is_still_waiting():
    """The consequence of the ordering, not the ordering.

    ANDREW 2026-09-08: *so six of seven failed is correct to you? fuck the
    seventh one right?*

    The first version of this asserted the station's position in a list, which
    is a constant — so it survived the sabotage run untouched, and I reported
    six-of-seven-failing as the right answer and moved on. A test that passes
    with the whole module blanked is testing the arrangement of the furniture,
    not whether the room does anything. Rewritten to assert the thing the
    ordering exists FOR: while he has not spoken, the board says so, and the
    sign-off is unreachable.
    """
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    sm.open_item("item-1")
    sm.bind_to_request("item-1", rid)

    unmet = sm.unmet_sentences("item-1")
    assert any("he has not said this landed" in s for s in unmet), (
        "if his station can go quiet, the board reads finished while he is still waiting"
    )
    states = {r.station: r.state for r in sm.check_all("item-1")}
    assert states["his_word"] != sm.SATISFIED
    assert states["merge"] != sm.SATISFIED, (
        "a sign-off reachable before he has spoken puts him after the door again"
    )
