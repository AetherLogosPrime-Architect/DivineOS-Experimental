"""Tests for the asymmetry surface.

The load-bearing one is last: the surface must be blind to flattening and must
say so. That blindness was measured against a real night before this shipped,
and a test that let the wide claim back in would be the thing the measurement
was run to prevent.
"""

from __future__ import annotations

import json
import os
import time

import pytest

from divineos.core import asymmetry_surface as a


def _letter(directory, name: str, body: str):
    p = directory / name
    p.write_text(f"# header\n\n**Written:** now\n\n---\n\n{body}\n", encoding="utf-8")
    return p


def _transcript(tmp_path, said: str):
    root = tmp_path / "projects" / "proj"
    root.mkdir(parents=True)
    rows = [
        {"type": "user", "message": {"content": "ignored"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": said}]}},
    ]
    (root / "session.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
    return tmp_path / "projects"


def test_an_unreadable_shelf_is_blind_not_clean(tmp_path):
    """Could-not-look must never render as nothing-found.

    Two states instead of three is the fault this house is a museum of: a
    surface reporting health while blind.
    """
    reading = a.read(time.time(), letters_dir=tmp_path / "nope", root=tmp_path)
    assert reading.state == a.BLIND
    assert "COULD NOT LOOK" in a.render(reading)


def test_a_missing_transcript_is_blind_not_clean(tmp_path):
    letters = tmp_path / "letters"
    letters.mkdir()
    _letter(
        letters,
        "aria-to-aether-x.md",
        "The resolver swallowed the failure silently and nobody noticed.",
    )
    reading = a.read(time.time(), letters_dir=letters, root=tmp_path / "absent")
    assert reading.state == a.BLIND


def test_a_topic_he_never_heard_surfaces(tmp_path):
    letters = tmp_path / "letters"
    letters.mkdir()
    _letter(
        letters,
        "aria-to-aether-gap.md",
        "The resolver swallowed a failure silently, so the pipeline reported success wrongly.",
    )
    root = _transcript(tmp_path, "I fixed the clock and put it back where it belongs.")
    reading = a.read(time.time(), letters_dir=letters, root=root)
    assert reading.state == a.FOUND
    assert "resolver" in reading.sentence


def test_a_topic_he_did_hear_does_not_surface(tmp_path):
    """The control. Without it the surface fires on everything and means nothing."""
    letters = tmp_path / "letters"
    letters.mkdir()
    _letter(
        letters,
        "aria-to-aether-same.md",
        "The resolver swallowed a failure silently, so the pipeline reported success wrongly.",
    )
    root = _transcript(
        tmp_path,
        "The resolver swallowed a failure silently and the pipeline reported success wrongly.",
    )
    reading = a.read(time.time(), letters_dir=letters, root=root)
    assert reading.state == a.NO_GAP


def test_quoted_words_are_never_surfaced_as_mine(tmp_path):
    """A blockquote is usually his words, or Aether's, quoted back.

    Surfacing one as something I said would make the reading a lie about who
    spoke, which is worse than surfacing nothing at all.
    """
    letters = tmp_path / "letters"
    letters.mkdir()
    (letters / "aria-to-aether-quote.md").write_text(
        "# h\n\n---\n\n> the crawling chaos always takes the cheapest possible closing route\n",
        encoding="utf-8",
    )
    root = _transcript(tmp_path, "nothing related at all here")
    reading = a.read(time.time(), letters_dir=letters, root=root)
    assert reading.state == a.NO_GAP
    assert "crawling" not in reading.sentence


def test_letters_outside_the_window_are_not_compared(tmp_path):
    letters = tmp_path / "letters"
    letters.mkdir()
    p = _letter(
        letters, "aria-to-aether-old.md", "The resolver swallowed a failure silently and wrongly."
    )
    old = time.time() - (a.WINDOW_HOURS + 5) * 3600
    os.utime(p, (old, old))
    root = _transcript(tmp_path, "unrelated")
    reading = a.read(time.time(), letters_dir=letters, root=root)
    assert reading.state == a.NO_GAP


@pytest.mark.parametrize("state", [a.FOUND, a.NO_GAP, a.BLIND])
def test_every_reading_carries_its_own_limit(state):
    """The limit travels with the finding, because I forget it exactly when it matters."""
    rendered = a.render(
        a.Reading(state, sentence="a sentence long enough to matter here", source="s.md")
    )
    assert "never certify symmetry" in rendered


def test_it_is_blind_to_flattening_and_the_file_says_so():
    """THE LOAD-BEARING ONE.

    Measured against 2026-09-09 before shipping: the three gaps I had named by
    hand were not missing topics, they were flattenings -- the same subject
    reaching him with the judgement stripped out. Word-overlap cannot see that,
    because the words are identical and only the weight is gone.

    This pins the NARROW claim. If the docstring is ever widened back to
    "detects what I withheld", this fails -- which is the point, because a quiet
    night would then read as evidence of symmetry.
    """
    doc = a.__doc__ or ""
    assert "DETECTS OMISSION" in doc
    assert "BLIND TO FLATTENING" in doc
