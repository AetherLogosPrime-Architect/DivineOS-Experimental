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
