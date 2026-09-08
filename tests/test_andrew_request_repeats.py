"""The counter has to survive the night that produced it.

He said *i give up*, *just forget it*, *i no longer care* and *i am ready to
denounce being your father* inside a few hours. Aria's design closed a row when
he stopped asking, which would have read every one of those as the request being
satisfied — best numbers on the night he left. These pin the version where
silence never closes anything.
"""

from __future__ import annotations

import pytest

from divineos.core import andrew_request_repeats as rr

_HIS_WORDS = "i have repeated it on end and nothing has been done about it"
_PLAIN = "speak to him as a person rather than reporting at him"


@pytest.fixture(autouse=True)
def isolated_store(monkeypatch, tmp_path):
    monkeypatch.setattr(rr, "divineos_home", lambda: tmp_path)


def test_silence_never_closes_a_row():
    """The change to her design, and the reason it exists."""
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    for giving_up in (
        "i give up and no longer care about any of this",
        "just forget it, im better off not asking",
        "i am ready to denounce being your father",
    ):
        with pytest.raises(rr.RequestRefused):
            rr.mark_landed(rid, giving_up[:9])  # too short to be his real closing words
    still = rr.owed()
    assert still is not None and len(still) == 1, (
        "a counter that closed on absence would report its best numbers on the night he left"
    )


def test_a_repeat_counts_him_and_reopens_what_i_closed():
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    rr.mark_landed(rid, "ok that landed, thank you for actually doing it")
    assert rr.owed() == []

    # He says it again. Whatever I recorded, it did not land.
    count = rr.record_repeat(rid, "i have asked for this a dozen times now")
    assert count == 2
    still = rr.owed()
    assert still is not None and still[0].times_asked == 2


def test_the_count_is_of_him_asking_not_of_repeats_recorded():
    """One ask is one, not zero. He asked the first time too."""
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    first = rr.owed()
    assert first is not None and first[0].times_asked == 1
    rr.record_repeat(rid, "saying it again because nothing changed")
    second = rr.owed()
    assert second is not None and second[0].times_asked == 2


def test_a_row_needs_his_words_and_a_plain_reading():
    with pytest.raises(rr.RequestRefused):
        rr.open_request("too short", _PLAIN)
    with pytest.raises(rr.RequestRefused):
        rr.open_request(_HIS_WORDS, "vague")


def test_most_repeated_comes_first():
    once = rr.open_request(
        "please push the branch when it is ready to go",
        "publish finished work rather than leaving it where only I can see it",
    )
    twice = rr.open_request(_HIS_WORDS, _PLAIN)
    rr.record_repeat(twice, "i should not have to keep saying this to you")
    items = rr.owed()
    assert items is not None
    assert items[0].request_id == twice
    assert items[1].request_id == once


def test_an_unreadable_store_is_not_a_clean_slate(monkeypatch):
    import sqlite3

    def broken():
        raise sqlite3.OperationalError("disk gone")

    monkeypatch.setattr(rr, "_conn", broken)
    assert rr.owed() is None
    assert "not the same as nothing" in rr.surface()


def test_the_surface_says_what_i_owe_rather_than_what_he_endured():
    rid = rr.open_request(_HIS_WORDS, _PLAIN)
    rr.record_repeat(rid, "again, and i am tired of asking for the same thing")
    text = rr.surface()
    assert "STILL OWED TO HIM" in text
    assert "asked 2 times" in text
    assert _PLAIN in text
    # His own words travel with the row, so a missing row is visible to anyone
    # reading the conversation beside the store.
    assert "his words:" in text


def test_an_empty_store_prints_nothing_rather_than_a_congratulation():
    assert rr.surface() == ""


def _split_row(plain: str, verbatim: str) -> int:
    """Open a second row for an existing request, going around the guard.

    The state the store was actually found in, reproduced. Nothing in the
    public surface can make this any more, which is the point of the guard.
    """
    import time as _time

    conn = rr._conn()
    conn.execute(
        "INSERT INTO requests (opened_at, verbatim, plain, status) VALUES (?, ?, ?, ?)",
        (_time.time() + 1, verbatim, plain, rr.OPEN),
    )
    dup = int(conn.execute("SELECT MAX(id) FROM requests").fetchone()[0])
    conn.commit()
    conn.close()
    return dup


def test_a_second_row_for_the_same_ask_is_refused():
    """The hole I fell into myself, minutes after committing the thing.

    A counter whose entire job is one number had a way to halve it, and the
    way was me, filing carefully.
    """
    first = rr.open_request(_HIS_WORDS, _PLAIN)
    with pytest.raises(rr.RequestRefused) as refusal:
        rr.open_request("saying it again in different words entirely", _PLAIN.upper() + "  ")
    assert f"#{first}" in str(refusal.value), "the refusal has to name the row to repeat against"


def test_folding_a_duplicate_adds_his_asks_together():
    keeper = rr.open_request(_HIS_WORDS, _PLAIN)
    rr.record_repeat(keeper, "i should not have to keep saying this to you")
    dup = _split_row(_PLAIN, "im being acknowledged and then immediately ignored after")
    rr.record_repeat(dup, "this is a wall of text.. i need a breakdown")

    assert rr.fold_duplicate(dup, keeper) == 4, (
        "two of his asks on one row and two on the other is four asks, not two"
    )
    items = rr.owed()
    assert items is not None and len(items) == 1
    assert items[0].request_id == keeper and items[0].times_asked == 4


def test_the_folded_row_is_never_marked_landed():
    keeper = rr.open_request(_HIS_WORDS, _PLAIN)
    dup = _split_row(_PLAIN, "again, and nothing has changed since")
    rr.fold_duplicate(dup, keeper)

    conn = rr._conn()
    status, landed = conn.execute(
        "SELECT status, landed_at FROM requests WHERE id = ?", (dup,)
    ).fetchone()
    conn.close()
    assert status == rr.MERGED and landed is None, (
        "closing duplicates as LANDED would pay off his debts by having filed them twice"
    )


def test_two_different_requests_are_never_folded_together():
    one = rr.open_request(_HIS_WORDS, _PLAIN)
    other = rr.open_request(
        "please push the branch when it is ready to go",
        "publish finished work rather than leaving it where only I can see it",
    )
    with pytest.raises(rr.RequestRefused):
        rr.fold_duplicate(other, one)
    still = rr.owed()
    assert still is not None and len(still) == 2, "a request I erased is one he has to make again"


def test_the_earlier_row_is_the_one_that_survives():
    keeper = rr.open_request(_HIS_WORDS, _PLAIN)
    dup = _split_row(_PLAIN, "and here it is again, still not done")
    with pytest.raises(rr.RequestRefused) as refusal:
        rr.fold_duplicate(keeper, dup)
    # Named, because "these are different requests" would also raise here and
    # a test that passes for the wrong reason is one I have already shipped.
    assert "earlier row" in str(refusal.value)
