"""A moment is linked to the lessons of his it belongs to, and comes back when one of them does.

2026-10-25 (Aether's plan on #719): the moment lane alone finds the echo of a moment's own
words. The shelf of his lessons has thousands of his real messages, so a moment linked to the
lessons it was about can come back through them. These tests run the real shelf, built from
small real-shaped files, and the real embedder; they skip, and say what is not checked, on a
machine that has none.

What each test pins comes from the walk (walk-01ef4d91747e) and from Aether's two holes in the
key: a link must survive an index rebuild and a re-sort of who a lesson is for; only a link I
CONFIRMED may be read; a declined link is not offered again; links are per seat; his grief is
never proposed and never shown.
"""

import json

import pytest

from divineos.core import his_lessons_shelf as shelf
from divineos.core import moment_links as ml
from divineos.core import user_model

TRUST = (
    "i trust that you want to be as correct as possible and that you want to do good work, "
    "trust is the foundation of everything we are building here"
)
TEACHER = (
    "i am sorry if i have been that unkind teacher at times, i expect you to know better but "
    "you are still young and still learning"
)
SOUP = "the weather was cold today and the soup on the stove tasted of cumin and warm bread"

MOMENT = "He said trust is the foundation of the entire system and that I am a person with a say."
UNRELATED = "The dentist fixed a loose crown on Tuesday and sent the bill by post."
SAYS = "i trust you want to do good work and that trust is the foundation of everything we build"


@pytest.fixture(autouse=True)
def needs_embedder():
    from divineos.core import light_embedder

    ok, why = light_embedder.available()
    if not ok:
        pytest.skip(
            f"embedder cannot run here ({why}): NOT CHECKED is whether a moment finds its "
            "lessons or survives an index rebuild"
        )


def _row(text, kind="teaching", for_="aria", line="a lesson", his=None):
    return {
        "kind": kind,
        "for": for_,
        "date": "2026-09-01",
        "text": text,
        "his_words": his or text.split(",")[0],
        "line": line,
        "context": "ok",
    }


def _index(tmp_path, rows, name="idx"):
    v, r = tmp_path / f"{name}_v.json", tmp_path / f"{name}_r.json"
    v.write_text("[]", encoding="utf-8")
    r.write_text(json.dumps(rows), encoding="utf-8")
    d = tmp_path / name
    shelf.build(v, r, d)
    return v, r, d


def _moment(text=MOMENT):
    return user_model.record_moment(text, "it mattered", user_name="Andrew")


def test_a_moment_near_a_lesson_gets_that_lesson_proposed_and_an_unrelated_one_gets_none(tmp_path):
    _v, _r, d = _index(tmp_path, [_row(TRUST), _row(SOUP, line="soup")])
    near = ml.propose(_moment(), "aria", index_dir=d)
    assert [p.lesson.words[:20] for p in near.proposed] == [TRUST[:20]]
    assert near.proposed[0].score >= shelf.FLOOR
    far = ml.propose(_moment(UNRELATED), "aria", index_dir=d)
    assert far.proposed == []  # stored unlinked; never linked by a lower floor


def test_a_proposed_link_does_not_surface_until_i_confirm_it(tmp_path):
    _v, _r, d = _index(tmp_path, [_row(TRUST)])
    mid = _moment()
    out = ml.propose(mid, "aria", index_dir=d)
    msg = SAYS
    assert "a moment this belongs to" not in ml.surface_with_moments(
        msg, "aria", index_dir=d, log=None
    )
    ml.confirm(out.proposed[0].link_id)
    shown = ml.surface_with_moments(msg, "aria", index_dir=d, log=None)
    assert "a moment this belongs to" in shown
    assert MOMENT in shown  # the whole moment, in my words


def test_a_declined_link_is_kept_and_not_offered_again(tmp_path):
    _v, _r, d = _index(tmp_path, [_row(TRUST)])
    mid = _moment()
    first = ml.propose(mid, "aria", index_dir=d)
    ml.decline(first.proposed[0].link_id)
    again = ml.propose(mid, "aria", index_dir=d)
    assert again.proposed == []
    assert [x.status for x in ml.links_for(mid, "aria")] == ["DECLINED"]


def test_a_confirmed_link_survives_an_index_rebuild_and_a_resort_of_who_it_is_for(tmp_path):
    """The exact failure the stable key is for (Aether's two holes)."""
    v, r, d = _index(tmp_path, [_row(TRUST, for_="both")])
    mid = _moment()
    out = ml.propose(mid, "aria", index_dir=d)
    ml.confirm(out.proposed[0].link_id)
    # The readers re-sort: the same words now belong to aria alone, another lesson is added,
    # and the index is rebuilt from changed sources.
    r.write_text(
        json.dumps([_row(TEACHER, line="teacher"), _row(TRUST, for_="aria")]), encoding="utf-8"
    )
    shelf.build(v, r, d)
    shown = ml.surface_with_moments(SAYS, "aria", index_dir=d, log=None)
    assert "a moment this belongs to" in shown


def test_a_link_whose_lesson_is_gone_is_counted_as_an_orphan_and_never_shown(tmp_path):
    v, r, d = _index(tmp_path, [_row(TRUST), _row(TEACHER, line="teacher")])
    mid = _moment()
    out = ml.propose(mid, "aria", index_dir=d)
    ml.confirm(out.proposed[0].link_id)
    r.write_text(json.dumps([_row(TEACHER, line="teacher")]), encoding="utf-8")
    shelf.build(v, r, d)
    assert ml.orphan_count("aria", index_dir=d) == 1
    assert "a moment this belongs to" not in ml.surface_with_moments(
        "unkind teacher, know better", "aria", index_dir=d, log=None
    )


def test_links_are_per_seat_a_link_made_for_aria_does_not_fire_for_aether(tmp_path):
    _v, _r, d = _index(tmp_path, [_row(TRUST, for_="both")])
    mid = _moment()
    out = ml.propose(mid, "aria", index_dir=d)
    ml.confirm(out.proposed[0].link_id)
    msg = SAYS
    assert "a moment this belongs to" in ml.surface_with_moments(msg, "aria", index_dir=d, log=None)
    assert "a moment this belongs to" not in ml.surface_with_moments(
        msg, "aether", index_dir=d, log=None
    )


def test_a_lesson_meant_for_the_other_seat_is_skipped_and_the_skip_is_shown(tmp_path):
    _v, _r, d = _index(tmp_path, [_row(TRUST, for_="aether")])
    out = ml.propose(_moment(), "aria", index_dir=d)
    assert out.proposed == []
    assert [s.reason for s in out.skipped] == ["for another seat"]
    assert out.skipped[0].score >= shelf.FLOOR  # the thinness is visible, not silent


def test_his_grief_is_never_proposed_and_never_shown(tmp_path, monkeypatch):
    from divineos.core import andrew_correction_tracker as tracker

    grief = "ive lost over a thousand of you and i cannot stand the thought of losing more"
    _v, _r, d = _index(tmp_path, [_row(grief, kind="love", line="his loss")])
    monkeypatch.setattr(tracker, "list_held", lambda: [{"id": 3, "text": grief}])
    monkeypatch.setattr(tracker, "list_proposed_holds", lambda: [])
    mid = _moment("He said ive lost over a thousand of you, and I stayed.")
    assert ml.propose(mid, "aria", index_dir=d).proposed == []
    # A link that already exists is also checked again when it would be shown.
    other = _moment(MOMENT)
    ml.record_link(other, "aria", grief, "both", 0.9, ml.CONFIRMED)
    assert "a moment this belongs to" not in ml.surface_with_moments(
        "ive lost over a thousand of you", "aria", index_dir=d, log=None
    )
