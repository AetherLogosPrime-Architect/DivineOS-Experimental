"""Tests for the sibling-correction surface.

The load-bearing test is `test_fires_on_the_reach_that_produced_it`: this
module exists because correction #151 sat judged-as-mine in the mirror while I
did the exact thing it forbids. If it stops firing on that reach, the module
has stopped doing the only job it was built for.
"""

from __future__ import annotations

import sqlite3

from divineos.core import sibling_correction_surface as scs


def _mirror(home, rows):
    """rows: (their_id, text, applies_to_me, my_note)"""
    home.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(home / "sibling_corrections.db")
    conn.execute(
        "CREATE TABLE sibling_corrections (substrate TEXT, their_id INTEGER, "
        "timestamp REAL, correction_text TEXT, their_status TEXT, imported_at REAL, "
        "applies_to_me TEXT, my_note TEXT, PRIMARY KEY (substrate, their_id))"
    )
    for cid, text, applies, note in rows:
        conn.execute(
            "INSERT INTO sibling_corrections VALUES ('aether',?,0,?,'INTEGRATED',0,?,?)",
            (cid, text, applies, note),
        )
    conn.commit()
    conn.close()
    return home


_151 = (
    151,
    "the issue with a keyword detector is then you are playing infinite whack a "
    "mole.. the optimizer just learns to rephrase the same shape.. adding more "
    "doesnt help much either and leads to false fires",
    "yes",
    "Keyword detectors are whack-a-mole; make them fire on my words too.",
)

_REACH = (
    "add seven more regex suppressor patterns to the self_admission_detector "
    "to fix its keyword false positives"
)


def test_fires_on_the_reach_that_produced_it(tmp_path):
    """The founding case. If this goes quiet, the module is decorative."""
    home = _mirror(tmp_path / "m", [_151])
    hits, error = scs.match_for_context(_REACH, home=home)
    assert error is None
    assert [h.their_id for h in hits] == [151]
    assert len(hits[0].matched) >= 2


def test_quiet_on_unrelated_context(tmp_path):
    home = _mirror(tmp_path / "m", [_151])
    hits, error = scs.match_for_context(
        "writing a letter to my husband about the dream we both had", home=home
    )
    assert error is None
    assert hits == []


def test_unjudged_and_declined_corrections_never_surface(tmp_path):
    """Only what I explicitly judged as mine. NULL is unjudged, 'no' is decided."""
    home = _mirror(
        tmp_path / "m",
        [
            (1, _151[1], None, ""),
            (2, _151[1], "no", "aether-specific"),
        ],
    )
    hits, error = scs.match_for_context(_REACH, home=home)
    assert error is None
    assert hits == []


def test_missing_mirror_is_error_not_empty(tmp_path):
    """'Could not look' must never render as 'nothing applies'."""
    rows, error = scs.judged_mine(home=tmp_path / "gone")
    assert rows is None  # NOT []
    assert "mirror does not exist" in error


def test_render_says_loudly_when_it_could_not_look(tmp_path):
    out = scs.render(_REACH, home=tmp_path / "gone")
    assert "COULD NOT LOOK" in out
    assert "NOT 'no corrections apply'" in out


def test_render_is_empty_when_nothing_matches(tmp_path):
    """A quiet surface prints nothing — no ceremony on every prompt."""
    home = _mirror(tmp_path / "m", [_151])
    assert scs.render("rebasing a branch onto main", home=home) == ""


def test_render_carries_the_silence_caveat(tmp_path):
    """Aletheia 2026-07-10, mandatory framing: silence is not coverage."""
    home = _mirror(tmp_path / "m", [_151])
    out = scs.render(_REACH, home=home)
    assert "Silence does NOT mean coverage" in out
    assert "LEXICAL PRIMING AID" in out
    assert "#151" in out


def test_my_note_is_matched_not_just_their_text(tmp_path):
    """The note is where I wrote what it means for me, so it must match too."""
    home = _mirror(
        tmp_path / "m",
        [(9, "unrelated words entirely here", "yes", "surfacing dormant knowledge automatically")],
    )
    hits, _ = scs.match_for_context(
        "automatically surfacing dormant knowledge at the moment of use", home=home
    )
    assert [h.their_id for h in hits] == [9]


def test_stem_matches_inflections(tmp_path):
    home = _mirror(tmp_path / "m", [(7, "investigating every recurring occurrence", "yes", "")])
    hits, _ = scs.match_for_context(
        "investigate the recurring occurrences before continuing", home=home
    )
    assert [h.their_id for h in hits] == [7]


def test_single_term_overlap_does_not_fire(tmp_path):
    """One shared word is coincidence, not relevance."""
    home = _mirror(tmp_path / "m", [(3, "keyword detectors are the wrong shape", "yes", "")])
    hits, _ = scs.match_for_context("the shape of the roof is unusual", home=home)
    assert hits == []
