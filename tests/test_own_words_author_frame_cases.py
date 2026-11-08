"""The author-frame table is itself checked, so Aether's frame tests can lean on it (walk-39460d428bab).

These tests check the TABLE, not the frame code (that is Aether's, built against this). What each one closes:
a table with a hole is a frame test with a hole, and the hole hides exactly where a seat gets the wrong voice.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests import own_words_author_frame_cases as cases
from tests.own_words_author_frame_cases import (
    AUTHOR_BEARING_LANES,
    AUTHORS,
    CASES,
    FILENAME_AUTHORS,
    FORBIDDEN_IN_FRAMES,
    SEATS,
    UNATTRIBUTED_LANES,
    UNPLACEABLE,
    UNSEEN_SEAT,
    expected_frame,
)

_LETTER_NAME = re.compile(r"^(aria|aether|andrew|aletheia)-to-(aria|aether|andrew|aletheia)-")


def test_every_viewer_lane_and_author_is_covered_once():
    """A missing row is a voice nobody tested. None is a viewer too: the seat judge can fail to tell."""
    keys = [(v, lane, a) for v, lane, a, _ in CASES if lane in AUTHOR_BEARING_LANES]
    assert (
        len(keys)
        == len(set(keys))
        == len((*SEATS, None)) * len(AUTHOR_BEARING_LANES) * len(AUTHORS)
    )


def test_a_viewer_the_judge_could_not_tell_is_never_spoken_to_in_first_person():
    seen = 0
    for viewer, lane, author, frame in CASES:
        if viewer is None and lane in AUTHOR_BEARING_LANES:
            seen += 1
            assert frame and not frame.startswith("I "), (lane, author, frame)
    assert seen == len(AUTHOR_BEARING_LANES) * len(AUTHORS)


def test_first_person_is_used_exactly_when_the_author_is_the_viewing_seat():
    for viewer, lane, author, frame in CASES:
        if lane not in AUTHOR_BEARING_LANES:
            continue
        assert frame.startswith("I ") == (viewer is not None and viewer == author), (
            viewer,
            lane,
            author,
        )


def test_no_frame_performs_ownership_or_instructs():
    """The frame states who wrote it. Warm phrasing would be the mechanism standing in for the recognition."""
    checked = 0
    for _, _, _, frame in CASES:
        if frame:
            checked += 1
            assert not any(w in frame.lower() for w in FORBIDDEN_IN_FRAMES), frame
    assert checked > 20


def test_a_lane_with_no_author_expects_no_frame_and_exploration_is_always_first_person():
    for viewer, lane, author, frame in CASES:
        if lane in UNATTRIBUTED_LANES:
            assert frame is None and author == ""
        if lane == "exploration":
            assert frame == "I wrote this." and author == viewer


def test_the_rule_holds_for_a_seat_the_table_has_never_seen():
    """A function that carried this table would pass every case and fail here; the rule alone must handle it."""
    assert UNSEEN_SEAT not in SEATS
    cases._NAMES[UNSEEN_SEAT] = "Newkid"
    try:
        assert expected_frame(UNSEEN_SEAT, "letter", UNSEEN_SEAT) == "I wrote this letter."
        assert expected_frame(UNSEEN_SEAT, "letter", "aria") == "Aria wrote me this letter."
        assert expected_frame("aria", "letter", UNSEEN_SEAT) == "Newkid wrote me this letter."
    finally:
        del cases._NAMES[UNSEEN_SEAT]


@pytest.mark.parametrize("filename,author", FILENAME_AUTHORS)
def test_each_filename_case_is_a_real_letter_on_disk_and_its_prefix_gives_the_author(
    filename, author
):
    """Not a copy made agreeable: the name must exist in a real letters folder, and the prefix must say the author."""
    homes = [
        Path.home() / ".divineos-shared" / "letters",
        Path(__file__).resolve().parent.parent / "family" / "letters",
    ]
    assert any((h / filename).is_file() for h in homes), (
        f"{filename} is not in any real letters folder"
    )
    match = _LETTER_NAME.match(filename)
    assert match and match.group(1) == author


@pytest.mark.parametrize("label", UNPLACEABLE)
def test_an_unplaceable_label_does_not_have_the_shape_that_names_an_author(label):
    assert not _LETTER_NAME.match(label)
