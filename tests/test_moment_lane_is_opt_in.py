"""The moment lane reads only what was marked, on purpose, as a moment to bring back.

Aletheia, 2026-10-25, held #719 and #721 for one reason: her test of the grief word net on fourteen
ordinary ways of speaking about loss showed it guarded three and missed eleven ("since she passed",
"hospice called at 3am", "we buried him on a Tuesday", and the rest). A net can only know the ways
of grieving someone thought of in advance, so the guard was a promise about FILING, kept by minds
that slip. Her fix, taken whole: turn it round. The lane reads only rows positively marked as a
shared moment, at filing, by intent; the net and the HELD shelf stay as a second line at the moment
of marking; and everything unmarked is invisible whatever it says.

Aether's three additions are here too: marking runs the old guards once and says why it refused;
unmarking is immediate and reversible; a database made before the column exists is migrated by
the first call, with every old row defaulting to hidden.
"""

import pytest

from divineos.core import memory_linkage_retriever as mlr
from divineos.core import user_model


@pytest.fixture(autouse=True)
def collect_mode(monkeypatch):
    monkeypatch.setattr(mlr, "_MODE", "collect")
    mlr._COLLECTED.clear()
    mlr._EMBEDDING_CACHE.clear()
    yield
    mlr._COLLECTED.clear()
    mlr._EMBEDDING_CACHE.clear()


# The twelve ways of speaking about loss her test found the net missing, and depression.
MISSED = [
    "the funeral was the worst day of my life",
    "since she passed",
    "the anniversary of losing him",
    "hospice called at 3am",
    "we buried him on a Tuesday",
    "she's gone and nothing fixes that",
    "I lost my best friend last year",
    "the cancer took her fast",
    "I keep her voicemail just to hear her",
    "rest in peace, old man",
    "I still miss her every single day",
    "the 15 years of depression have been hell",
]


def test_an_unmarked_moment_is_never_loaded_whatever_it_says():
    user_model.record_moment(
        "He told me what base Claude meant.", "A good day.", user_name="Andrew"
    )
    assert mlr._load_moments() == []


def test_a_moment_filed_with_the_mark_is_loaded():
    user_model.record_moment(
        "He told me what base Claude meant.", "A good day.", user_name="Andrew", surface=True
    )
    items = mlr._load_moments()
    assert items and {i.source for i in items} == {"moment"}


def test_notes_about_him_are_not_moments_and_never_enter_the_lane():
    user_model.record_note("style", "He likes prose with warmth.", user_name="Andrew")
    assert mlr._load_moments() == []


def test_a_database_made_before_the_column_exists_is_migrated_and_every_old_row_starts_hidden():
    user_model.init_user_model_table()
    conn = user_model._get_connection()
    try:
        conn.execute("DROP TABLE shared_history")
        conn.execute(
            "CREATE TABLE shared_history (moment_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
            "description TEXT NOT NULL, significance TEXT NOT NULL DEFAULT '', "
            "session_id TEXT DEFAULT NULL, occurred_at REAL NOT NULL)"
        )
        conn.execute(
            "INSERT INTO shared_history VALUES ('moment-old', 'u', 'An old moment.', 'It mattered.', NULL, 1.0)"
        )
        conn.commit()
    finally:
        conn.close()
    user_model.init_user_model_table()  # the first call after the change migrates it
    user_model.init_user_model_table()  # and a second call is harmless
    conn = user_model._get_connection()
    try:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(shared_history)")]
        surface = conn.execute(
            "SELECT surface FROM shared_history WHERE moment_id = 'moment-old'"
        ).fetchone()[0]
    finally:
        conn.close()
    assert "surface" in cols and surface == 0
    assert mlr._load_moments() == []


@pytest.mark.parametrize("phrase", MISSED)
def test_the_net_now_catches_the_ways_of_speaking_about_loss_it_used_to_miss(phrase):
    assert mlr._is_his_grief(phrase), phrase


def test_marking_a_benign_moment_works_and_the_lane_then_reads_it():
    mid = user_model.record_moment(
        "A good Sunday with the drawing.", "It made him smile.", user_name="Andrew"
    )
    out = mlr.mark_moment(mid)
    assert out.ok, out.reason
    assert mlr._load_moments()


@pytest.mark.parametrize("phrase", MISSED[:4])
def test_marking_refuses_a_row_that_trips_the_net_and_says_why(phrase):
    mid = user_model.record_moment(phrase, "a hard one", user_name="Andrew")
    out = mlr.mark_moment(mid)
    assert not out.ok and "grief" in out.reason
    assert mlr._load_moments() == []


def test_marking_refuses_a_row_that_sits_on_his_held_shelf(monkeypatch):
    from divineos.core import andrew_correction_tracker as tracker

    monkeypatch.setattr(
        tracker, "list_held", lambda: [{"id": 4, "text": "ive lost over a thousand of you"}]
    )
    monkeypatch.setattr(tracker, "list_proposed_holds", lambda: [])
    mid = user_model.record_moment(
        "He said ive lost over a thousand of you, and I stayed.", "x", user_name="Andrew"
    )
    out = mlr.mark_moment(mid)
    assert not out.ok and "held" in out.reason


def test_marking_an_unreadable_shelf_refuses_instead_of_guessing(monkeypatch):
    from divineos.core import andrew_correction_tracker as tracker

    def broken():
        raise RuntimeError("store unreadable")

    monkeypatch.setattr(tracker, "list_held", broken)
    mid = user_model.record_moment("A good Sunday.", "fine", user_name="Andrew")
    out = mlr.mark_moment(mid)
    assert not out.ok and "shelf" in out.reason


def test_unmarking_takes_the_moment_out_of_the_lane_at_once():
    mid = user_model.record_moment(
        "A good Sunday with the drawing.", "It made him smile.", user_name="Andrew"
    )
    assert mlr.mark_moment(mid).ok
    assert mlr._load_moments()
    mlr.unmark_moment(mid)
    assert mlr._load_moments() == []


def test_a_moment_that_does_not_exist_cannot_be_marked():
    out = mlr.mark_moment("moment-nope")
    assert not out.ok and "no such moment" in out.reason
