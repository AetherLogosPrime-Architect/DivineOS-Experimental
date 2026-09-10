"""His words are a first-class thing in the store, or they are my essay's epigraph.

Andrew 2026-09-08, killing the first version of this: *"it obviously doesnt
work.. you are just moving them to a new place to be ignored."* He was right
about the read-marker, and the correction is the shape of these tests: nothing
here asserts that a flag can be set. What is asserted is that the flag cannot
move WITHOUT his sentence being handed back, and that an unproveable carrier
never reads as a carried one.

The store is opened for real rather than mocked. A mock here would test my
model of the table, and the whole defect class this file guards is my model
standing in for the thing.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.fixture
def tracker(tmp_path, monkeypatch):
    monkeypatch.setenv("DIVINEOS_HOME", str(tmp_path))
    import divineos.core.andrew_correction_tracker as t

    importlib.reload(t)
    monkeypatch.setattr(t, "_db_path", lambda: tmp_path / "andrew_corrections.db")
    return t


class TestReadingIsDeliveryNotDeclaration:
    def test_the_count_moves_only_by_handing_the_words_back(self, tracker):
        """The rejected design had a settable marker. This one cannot be set
        at all -- the only path that increments is the one that returns his
        sentence, so a row marked read has provably been delivered."""
        row = tracker.file_correction("He said the room reads like the rest of the post.")
        assert tracker.unread_count() == 1

        got = tracker.read_one(row)
        assert got is not None and "reads like the rest" in got
        assert tracker.unread_count() == 0

    def test_there_is_no_hand_settable_marker(self, tracker):
        """Guards the correction itself. If a later edit reintroduces a
        set-a-flag entry point, this fails and names why it was removed."""
        assert not hasattr(tracker, "mark_read")

    def test_a_row_that_does_not_exist_counts_nothing(self, tracker):
        tracker.file_correction("A real one.")
        assert tracker.read_one(999999) is None
        assert tracker.unread_count() == 1


class TestAnUnprovenCarrierNeverReadsAsCarried:
    def test_an_invented_carrier_is_not_carried(self, tracker):
        assert tracker.carrier_state("a_module_that_was_never_written") == tracker.NOT_CARRIED

    def test_an_empty_carrier_is_not_carried(self, tracker):
        assert tracker.carrier_state("") == tracker.NOT_CARRIED
        assert tracker.carrier_state(None) == tracker.NOT_CARRIED

    def test_a_search_that_cannot_run_says_so_rather_than_passing(self, tracker, monkeypatch):
        """Three-valued, per the standing rule: found, found-nothing, and
        could-not-look are different answers. A broken search must never
        resolve to CARRIED, because that is the direction that lies in my
        favour."""

        import subprocess

        def _explode(*_a, **_k):
            raise OSError("no git here")

        monkeypatch.setattr(subprocess, "run", _explode)
        assert tracker.carrier_state("anything") == tracker.CANNOT_CHECK


class TestHisWordsAreStoredApartFromMyEssay:
    def test_his_sentence_survives_separately_from_my_root_cause(self, tracker):
        """The defect this whole change exists for: his sentence was the
        opening line of my analysis of myself, with no field of its own, so
        there was no way to read what he said without reading what I made
        of it."""
        row = tracker.file_correction(
            "Andrew: 'the jargon isnt even the issue' root cause: I had been "
            "treating the register as the fault."
        )
        assert tracker.set_his_words(row, "the jargon isnt even the issue") is True

        import sqlite3

        conn = sqlite3.connect(tracker._db_path())
        try:
            his, source = conn.execute(
                "SELECT his_words, source FROM andrew_corrections WHERE id = ?", (row,)
            ).fetchone()
        finally:
            conn.close()

        assert his == "the jargon isnt even the issue"
        assert source == "HIM"
        assert "root cause" not in his
