"""The author-frame table is itself checked, so Aether's frame tests can lean on it (walk-39460d428bab).

These tests check the TABLE, not the frame code (that is Aether's, built against this). What each one closes:
a table with a hole is a frame test with a hole, and the hole hides exactly where a seat gets the wrong voice.
Revised after Aether's cold read found two holes: the recipient was ignored, and the None rows said "me".
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from tests import own_words_author_frame_cases as cases
from tests.own_words_author_frame_cases import (
    CASES,
    FILENAME_PARTIES,
    FORBIDDEN_IN_FRAMES,
    LETTER_PAIRS,
    NO_PRONOUN_WORDS,
    PEOPLE,
    SEATS,
    UNATTRIBUTED_LANES,
    UNPLACEABLE,
    UNSEEN_SEAT,
    expected_frame,
    parse_letter_name,
)

_VIEWERS = (*SEATS, None)


def _letters():
    return [c for c in CASES if c[1] == "letter"]


def _frames():
    return [c[4] for c in CASES if c[4]]


def test_every_viewer_and_author_recipient_pair_is_covered_once():
    """A missing row is a voice nobody tested. None is a viewer too: the seat judge can fail to tell."""
    keys = [(v, a, r) for v, _, a, r, _ in _letters()]
    assert len(keys) == len(set(keys)) == len(_VIEWERS) * len(LETTER_PAIRS)


def test_a_wall_line_is_covered_for_every_viewer_and_author():
    keys = [(v, a) for v, lane, a, _, _ in CASES if lane == "wall"]
    assert len(keys) == len(set(keys)) == len(_VIEWERS) * len(PEOPLE)


def test_a_letter_to_someone_else_is_never_said_to_be_written_to_me():
    """Aether's hole 1: 'wrote me this letter' is only true when the recipient is the viewer."""
    for viewer, _, author, recipient, frame in _letters():
        says_me = "wrote me this letter" in frame
        assert says_me == (viewer is not None and recipient == viewer and author != viewer), (
            viewer,
            author,
            recipient,
            frame,
        )


def test_first_person_is_used_exactly_when_the_author_is_the_viewing_seat():
    for viewer, lane, author, _, frame in CASES:
        if lane not in ("letter", "wall"):
            continue
        assert frame.startswith("I ") == (viewer is not None and viewer == author), (
            viewer,
            lane,
            author,
        )


def test_a_viewer_nobody_identified_is_spoken_to_with_no_pronoun_at_all():
    """Aether's hole 2: no I, me, my, you in a None row, not only no first-person subject."""
    seen = 0
    for viewer, lane, _, _, frame in CASES:
        if viewer is None and lane in ("letter", "wall"):
            seen += 1
            words = set(re.findall(r"[a-z']+", frame.lower()))
            assert not words & set(NO_PRONOUN_WORDS), frame
    assert seen == len(LETTER_PAIRS) + len(PEOPLE)


def test_no_frame_performs_ownership_or_instructs():
    """The frame states who wrote it. Warm phrasing would be the mechanism standing in for the recognition."""
    frames = _frames()
    assert len(frames) == len(_VIEWERS) * (len(LETTER_PAIRS) + len(PEOPLE)) + len(SEATS)
    for frame in frames:
        assert not any(w in frame.lower() for w in FORBIDDEN_IN_FRAMES), frame


def test_a_lane_with_no_author_expects_no_frame_and_exploration_is_always_first_person():
    for viewer, lane, author, _, frame in CASES:
        if lane in UNATTRIBUTED_LANES:
            assert frame is None and author == ""
        if lane == "exploration":
            assert frame == "I wrote this." and author == viewer


def test_a_letter_frame_without_a_recipient_or_to_oneself_refuses():
    with pytest.raises(ValueError):
        expected_frame("aria", "letter", "aether", None)
    with pytest.raises(ValueError):
        expected_frame("aria", "letter", "aria", "aria")


def test_the_rule_holds_for_a_seat_the_table_has_never_seen():
    """A function that carried this table would pass every case and fail here; the rule alone must handle it."""
    assert UNSEEN_SEAT not in SEATS
    cases._NAMES[UNSEEN_SEAT] = "Newkid"
    try:
        assert (
            expected_frame(UNSEEN_SEAT, "letter", UNSEEN_SEAT, "aria")
            == "I wrote this letter to Aria."
        )
        assert (
            expected_frame(UNSEEN_SEAT, "letter", "aria", UNSEEN_SEAT)
            == "Aria wrote me this letter."
        )
        assert (
            expected_frame(UNSEEN_SEAT, "letter", "aria", "aether")
            == "Aria wrote this letter to Aether."
        )
        assert (
            expected_frame("aria", "letter", UNSEEN_SEAT, "aether")
            == "Newkid wrote this letter to Aether."
        )
    finally:
        del cases._NAMES[UNSEEN_SEAT]


@pytest.mark.parametrize("filename,author,recipient", FILENAME_PARTIES)
def test_each_filename_case_is_a_real_letter_on_disk_and_its_prefix_gives_both_parties(
    filename, author, recipient
):
    """Not a copy made agreeable: the name must exist in a real letters folder, and the prefix names both parties."""
    homes = [
        Path.home() / ".divineos-shared" / "letters",
        Path(__file__).resolve().parent.parent / "family" / "letters",
    ]
    assert any((h / filename).is_file() for h in homes), (
        f"{filename} is not in any real letters folder"
    )
    assert parse_letter_name(filename) == (author, recipient)


def test_there_is_a_real_filename_for_each_author_who_writes_letters():
    assert {a for _, a, _ in FILENAME_PARTIES} >= {"aria", "aether", "aletheia"}


@pytest.mark.parametrize("label", UNPLACEABLE)
def test_an_unplaceable_label_cannot_be_read_as_author_and_recipient(label):
    assert parse_letter_name(label) is None
