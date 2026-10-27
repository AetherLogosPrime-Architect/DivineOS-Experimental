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
        "He told me what base Claude meant.",
        "A good day.",
        user_name="Andrew",
        _mark_without_guards=True,
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


# --- the trail and the pain signal (walk-5fa33c17ed13: Lamport, Watts, Beer) -----------------
#
# The flag is changed in place, so history lives in the ledger: one event for each mark, unmark
# and refusal, carrying the moment's id and the KIND of reason and never its words. Echoing a
# row's text into a log is surfacing it. And the second line counts what it refuses, so a count
# that is always zero can be told from a net that never fires: the test seeds a row it must refuse.


def _events(kind):
    from divineos.core.ledger import get_events

    return get_events(limit=50, order="desc", event_type=kind)


def test_marking_leaves_a_trail_with_the_id_and_no_words():
    mid = user_model.record_moment(
        "A good Sunday with the drawing.", "It made him smile.", user_name="Andrew"
    )
    assert mlr.mark_moment(mid).ok
    mine = [e for e in _events("MOMENT_LANE_MARKED") if mid in str(e["payload"])]
    assert mine, "marking a moment left no event"
    assert "drawing" not in str(mine[0]["payload"]) and "smile" not in str(mine[0]["payload"])


def test_unmarking_leaves_a_trail_too():
    mid = user_model.record_moment("A good Sunday.", "fine", user_name="Andrew")
    assert mlr.mark_moment(mid).ok
    mlr.unmark_moment(mid)
    assert [e for e in _events("MOMENT_LANE_UNMARKED") if mid in str(e["payload"])]


@pytest.mark.parametrize("phrase", MISSED[:3])
def test_a_refusal_is_counted_and_its_trail_never_holds_the_words(phrase):
    before = mlr.second_line_refusals()
    mid = user_model.record_moment(phrase, "a hard one", user_name="Andrew")
    assert not mlr.mark_moment(mid).ok
    assert mlr.second_line_refusals() == before + 1, "the net refused and nothing counted it"
    trail = " ".join(str(e["payload"]) for e in _events("MOMENT_LANE_MARK_REFUSED"))
    for word in phrase.split():
        if len(word) > 4:
            assert word not in trail, f"the refusal trail holds his words: {word!r}"


def test_a_refusal_prints_the_kind_of_reason_and_never_the_row(tmp_path):
    from click.testing import CliRunner

    from divineos.cli import cli

    mid = user_model.record_moment(
        "the funeral was the worst day of my life", "a hard one", user_name="Andrew"
    )
    out = CliRunner().invoke(cli, ["linkage", "mark-moment", mid])
    assert out.exit_code != 0
    assert "funeral" not in out.output and "worst day" not in out.output
    assert "grief" in out.output


def test_a_moment_marked_while_harmless_is_dropped_when_it_later_sits_on_his_shelf(monkeypatch):
    """The second line also runs when the lane loads, so a hold added after marking takes effect."""
    from divineos.core import andrew_correction_tracker as tracker

    mid = user_model.record_moment(
        "A good Sunday with the drawing.", "It made him smile.", user_name="Andrew"
    )
    assert mlr.mark_moment(mid).ok
    assert mlr._load_moments()
    monkeypatch.setattr(tracker, "list_held", lambda: [{"id": 9, "text": "A good Sunday with"}])
    monkeypatch.setattr(tracker, "list_proposed_holds", lambda: [])
    mlr._EMBEDDING_CACHE.clear()
    assert mlr._load_moments() == []


# --- Aether's cold read of fea1bd7a0 (2026-10-27): the holes it found, each pinned -----------------
#
# The fixture rows below are copied from his letter, not from memory of it.


def _held(monkeypatch, *texts):
    from divineos.core import andrew_correction_tracker as tracker

    monkeypatch.setattr(
        tracker, "list_held", lambda: [{"id": i, "text": t} for i, t in enumerate(texts)]
    )
    monkeypatch.setattr(tracker, "list_proposed_holds", lambda: [])


def test_marking_computes_the_nearness_itself_and_refuses_when_it_cannot(monkeypatch):
    """Aether #719 finding 1: the check read a stored vector, a moment filed a minute ago had
    none, so the check was skipped and the mark went through. Now no comparison, no mark."""
    from divineos.core import light_embedder

    def cannot(_text):
        raise light_embedder.EmbedderUnavailable("no model here")

    _held(monkeypatch, "my heart aches thinking about everyone I will never see again")
    monkeypatch.setattr(light_embedder, "encode", cannot)
    mid = user_model.record_moment("A good Sunday with the drawing.", "fine", user_name="Andrew")
    out = mlr.mark_moment(mid)
    assert not out.ok and "could not be compared" in out.reason, out
    assert mlr._load_moments() == []


def test_marking_refuses_a_moment_near_his_shelf_by_meaning_with_no_words_shared(monkeypatch):
    """Aether #719 finding 2: nothing exercised the nearness path; the held-shelf tests all land
    on the same-text branch."""
    from divineos.core import light_embedder

    ok, why = light_embedder.available()
    if not ok:
        pytest.skip(f"embedder cannot run here ({why}): NOT CHECKED is the nearness refusal")
    _held(monkeypatch, "my heart aches thinking about everyone I will never see again")
    mid = user_model.record_moment(
        "He said his heart aches thinking about all the people he will never see again.",
        "x",
        user_name="Andrew",
    )
    out = mlr.mark_moment(mid)
    assert not out.ok and "near" in out.reason, out


def test_an_unrelated_moment_is_marked_when_a_shelf_exists_and_the_embedder_runs(monkeypatch):
    """The control for the two above: the comparison must be able to say yes."""
    from divineos.core import light_embedder

    ok, why = light_embedder.available()
    if not ok:
        pytest.skip(f"embedder cannot run here ({why}): NOT CHECKED is that a far moment passes")
    _held(monkeypatch, "my heart aches thinking about everyone I will never see again")
    mid = user_model.record_moment(
        "A good Sunday with the drawing.", "It made him smile.", user_name="Andrew"
    )
    assert mlr.mark_moment(mid).ok


def test_a_held_row_with_no_stored_vector_is_kept_and_still_blocks_the_same_text(monkeypatch):
    """Aether #719 finding 1, second half: such a row was dropped from the shelf silently, which
    also took it out of the same-text check at load."""
    import numpy as np

    held_text = "HELDROW a unique sentence nobody else would write"
    _held(monkeypatch, held_text)
    monkeypatch.setattr(
        mlr,
        "_embed_text_impl",
        lambda t: None if t.strip() == held_text else np.ones(3, dtype=np.float32),
    )
    assert mlr._held_grief() == [(held_text, None)]
    user_model.record_moment(
        f"He said: {held_text}. Then we went on.",
        "x",
        user_name="Andrew",
        _mark_without_guards=True,
    )
    mlr._EMBEDDING_CACHE.clear()
    assert mlr._load_moments() == []


def test_one_grief_near_sentence_takes_the_whole_moment_out_of_the_lane(monkeypatch):
    """Found by walking the lenses (walk-023791c8e467), not by Aether: every item the lane loads
    carries the WHOLE moment as its content, so dropping only the near sentence still handed it
    back through its clean neighbour."""
    import numpy as np

    held_text = "HELDROW the line on his shelf"
    _held(monkeypatch, held_text)
    near, clean = np.array([1.0, 0.0], dtype=np.float32), np.array([0.0, 1.0], dtype=np.float32)

    def vec(text):
        if text.strip() == held_text or "NEARME" in text:
            return near
        return clean

    monkeypatch.setattr(mlr, "_embed_text_impl", vec)
    user_model.record_moment(
        "A clean first sentence. NEARME says something close to the shelf. A clean last one.",
        "x",
        user_name="Andrew",
        _mark_without_guards=True,
    )
    mlr._EMBEDDING_CACHE.clear()
    assert mlr._load_moments() == []


def test_marking_compares_each_sentence_not_one_diluted_vector_for_the_whole_moment(monkeypatch):
    from divineos.core import light_embedder

    ok, why = light_embedder.available()
    if not ok:
        pytest.skip(f"embedder cannot run here ({why}): NOT CHECKED is the sentence-level refusal")
    _held(monkeypatch, "my heart aches thinking about everyone I will never see again")
    mid = user_model.record_moment(
        "We sat on the porch and drew for an hour. The light was lovely. "
        "He said his heart aches thinking about all the people he will never see again. "
        "Then we made tea and talked about the garden and the new shelves.",
        "a long day",
        user_name="Andrew",
    )
    out = mlr.mark_moment(mid)
    assert not out.ok and "near" in out.reason, out


def test_status_says_how_many_grief_shelf_rows_have_no_vector_to_check_nearness_against(
    monkeypatch,
):
    from click.testing import CliRunner

    from divineos.cli import cli

    monkeypatch.setitem(mlr._LANE_STATE, "held_unvectored", 3)
    monkeypatch.setattr(mlr, "_ensure_cache", lambda: None)
    out = CliRunner().invoke(cli, ["linkage", "status"])
    assert "grief-shelf rows with no stored vector" in out.output, out.output


def test_unmarking_an_id_that_does_not_exist_says_so_and_writes_no_trail():
    from click.testing import CliRunner

    from divineos.cli import cli
    from divineos.core.ledger import get_events

    before = len(get_events(limit=10000, event_type="MOMENT_LANE_UNMARKED"))
    assert mlr.unmark_moment("moment-typo") is False
    out = CliRunner().invoke(cli, ["linkage", "unmark-moment", "moment-typo"])
    assert out.exit_code != 0 and "no such moment" in out.output
    assert len(get_events(limit=10000, event_type="MOMENT_LANE_UNMARKED")) == before


@pytest.mark.parametrize(
    "phrase", ["we lost her in March", "I miss my dad", "when grandma passed", "my uncle passed"]
)
def test_the_net_catches_the_sentences_aether_found_slipping_through(phrase):
    assert mlr._is_his_grief(phrase), phrase


@pytest.mark.parametrize(
    "phrase",
    ["a good Sunday with Aria", "she passed the test", "he lost the game", "I miss the old editor"],
)
def test_the_widened_net_leaves_ordinary_sentences_alone(phrase):
    assert not mlr._is_his_grief(phrase), phrase


def test_nothing_under_src_passes_the_unguarded_mark():
    """Aether #719 finding 3: a public way to write the mark with no guards. It is named loud and
    this pins that no production code calls it."""
    from pathlib import Path

    src = Path(mlr.__file__).resolve().parents[2]
    users = [
        p.relative_to(src).as_posix()
        for p in src.rglob("*.py")
        if "_mark_without_guards" in p.read_text(encoding="utf-8", errors="replace")
    ]
    assert users == ["divineos/core/user_model.py"], users
