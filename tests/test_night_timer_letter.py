"""The 6am note must be something the doorbell actually rings for, and only once a day.

Aria, 2026-10-12: wake a seat with a LETTER, not a session. The doorbell matches any file in
the shared letters folder whose name has ``-to-<seat>-`` in it (scripts/letter_doorbell.sh);
the check below reads that pattern out of the script itself so the two cannot drift apart.
"""

from __future__ import annotations

import datetime
import fnmatch
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "scripts" / "night_timer_letter.py"
BELL = ROOT / "scripts" / "letter_doorbell.sh"
DAY = datetime.date(2026, 10, 13)


def _timer():
    spec = importlib.util.spec_from_file_location("night_timer_letter", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_bell_still_matches_on_to_seat_in_the_name():
    # If the bell's pattern changes, this fails and the timer's name must change with it.
    assert '*-to-"${MEMBER}"-*' in BELL.read_text(encoding="utf-8")


def test_the_note_is_named_so_the_bell_rings_for_that_seat_only(tmp_path):
    timer = _timer()
    path = timer.write_note("aether", DAY, tmp_path)
    assert path is not None and path.exists()
    assert fnmatch.fnmatch(path.name, "*-to-aether-*")
    # Control: the same note is not one the other seat's bell would ring for.
    assert not fnmatch.fnmatch(path.name, "*-to-aria-*")


def test_a_second_run_the_same_day_writes_nothing(tmp_path):
    timer = _timer()
    letters = tmp_path / "letters"  # the shared test setup keeps its own files in tmp_path
    assert timer.write_note("aether", DAY, letters) is not None
    assert timer.write_note("aether", DAY, letters) is None
    assert len(list(letters.iterdir())) == 1


def test_the_next_day_gets_its_own_note(tmp_path):
    timer = _timer()
    letters = tmp_path / "letters"
    timer.write_note("aether", DAY, letters)
    assert timer.write_note("aether", DAY + datetime.timedelta(days=1), letters) is not None
    assert len(list(letters.iterdir())) == 2


def test_the_note_names_no_board_file_and_asks_for_chat(tmp_path):
    """Dad, 2026-10-24: the volley board is retired. The note used to name each seat's board file
    (Aria's hold had pinned that each seat got its OWN); now it must name none and ask for chat."""
    timer = _timer()
    for seat in ("aria", "aether"):
        text = timer.write_note(seat, DAY, tmp_path / seat).read_text(encoding="utf-8")
        assert "volley-board" not in text, seat
        assert "in chat" in text and f"you, {seat}:" in text, seat


def test_the_note_asks_for_the_night_letter_and_the_morning_picture_before_he_wakes(tmp_path):
    """Dad, 2026-10-30: the last half hour is for writing his personal night letter and the morning
    chat statement so both are there when he wakes. The letter is not a report, and the picture is
    written now, not when he arrives."""
    timer = _timer()
    for seat in ("aria", "aether"):
        text = timer.write_note(seat, DAY, tmp_path / seat).read_text(encoding="utf-8")
        # ONE shared letter both seats write into (Dad 2026-10-30), each under its own heading.
        assert f"the-night-letter-to-andrew-{DAY.isoformat()}.md" in text, seat
        assert f"## From {seat}" in text and "both of you write into" in text, seat
        # Two seats write one file: appending, never rewriting, or the second erases the first.
        assert "never rewrite" in " ".join(text.split()), (
            seat
        )  # the line wrap sits inside the phrase
        # Two wake-ups can land in the half hour; the second must find the first one's work done.
        assert "already in today's night" in text, seat
        assert "NOT a report" in text and "questions" in text, seat
        assert "already there when he does" in text and "now, so it is above the fold" in text, seat
        assert "start nothing new" in text, seat


def test_the_note_says_what_it_is_and_what_it_asks(tmp_path):
    text = _timer().write_note("aether", DAY, tmp_path).read_text(encoding="utf-8")
    assert "not a person" in text and "morning picture" in text and "doorbell" in text
