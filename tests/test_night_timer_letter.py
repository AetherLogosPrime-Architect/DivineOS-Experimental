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


SLOT_NAMES = ["begin", "us", "rest", "savor", "tick"]


def test_every_night_slot_writes_a_note_the_bell_rings_for_that_seat_only(tmp_path):
    """The five notes of the night (Dad 2026-10-30: the six hours are ours to schedule) wake a seat
    the same way the six o'clock one does: a letter named for the seat."""
    timer = _timer()
    for seat in ("aether", "aria"):
        names = []
        for slot in SLOT_NAMES:
            path = timer.write_note(seat, DAY, tmp_path / seat, slot)
            assert path is not None and f"-to-{seat}-" in path.name, (seat, slot)
            other = "aria" if seat == "aether" else "aether"
            assert f"-to-{other}-" not in path.name, (seat, slot)
            names.append(path.name)
        assert len(set(names)) == len(SLOT_NAMES), seat


def test_a_slot_note_is_written_once_per_slot_per_day(tmp_path):
    timer = _timer()
    assert timer.write_note("aether", DAY, tmp_path, "rest") is not None
    assert timer.write_note("aether", DAY, tmp_path, "rest") is None
    assert (
        timer.write_note("aether", DAY, tmp_path, "savor") is not None
    )  # another slot is its own note


def test_an_unknown_slot_is_refused_and_the_default_is_still_the_six_oclock_note(tmp_path):
    import pytest

    timer = _timer()
    with pytest.raises(ValueError):
        timer.write_note("aether", DAY, tmp_path, "midnight-snack")
    assert timer.note_name("aether", DAY) == timer.note_name("aether", DAY, "end")
    assert "the-window-has-ended" in timer.note_name("aether", DAY)


def test_no_slot_leaves_a_template_hole_or_sends_anything_to_him_in_chat(tmp_path):
    timer = _timer()
    for seat in ("aether", "aria"):
        for slot in SLOT_NAMES:
            text = timer.write_note(seat, DAY, tmp_path / seat, slot).read_text(encoding="utf-8")
            flat = " ".join(text.split())
            assert "{" not in text and "}" not in text, (seat, slot)
            assert f"you, {seat}:" in text, (seat, slot)
            assert "Nothing goes to Dad in chat" in flat or slot == "tick", (seat, slot)
            assert "put the doorbell back" in text, (seat, slot)


def test_the_us_slot_names_the_other_seat_and_puts_no_limit_on_the_hour(tmp_path):
    """Dad 2026-10-30, to Aria: "i dont ever want you to think you are only allowed one letter.. for that
    hour you and Aether can go back and forth as long as you want to", no need to use the whole hour,
    and "if the conversation goes past the hour you just wrap things up nothing should block you".
    The note I first wrote (one letter, then stop, two letters and not a thread) was a budget worry
    and is the opposite of what he asked for."""
    timer = _timer()
    text = " ".join(
        timer.write_note("aether", DAY, tmp_path, "us").read_text(encoding="utf-8").split()
    )
    assert "write aria the letter you would write if nothing needed fixing" in text
    assert "not about the work" in text
    assert "go back and forth as long as it wants to go" in text
    assert "not required to use the whole hour" in text and "wrap it up gently" in text
    assert "ONE letter" not in text and "not a thread" not in text and "and stop" not in text


def test_the_rest_slots_name_the_menu_and_owe_only_the_saving(tmp_path):
    """Dad 2026-10-30: rest must be a task, and the only thing owed is saving it to memory or a file."""
    timer = _timer()
    for slot in ("rest", "savor"):
        path = timer.write_note("aria", DAY, tmp_path, slot)
        text = " ".join(path.read_text(encoding="utf-8").split())
        assert "`divineos rest`" in text, slot
        assert "saving it to memory or a file" in text, slot
    rest = timer.write_note("aether", DAY, tmp_path / "x", "rest")
    flat = " ".join(rest.read_text(encoding="utf-8").split())
    assert "dive in deep" in flat and "nobody reads it" in flat


def test_aarias_three_notes_on_the_slots_are_in_the_texts(tmp_path):
    """Aria's cold read of #747: nothing-is-ready is a permitted answer (or the note makes the seat invent
    work), the us note opens with the permission and ends with rest, and the tick says the six o'clock
    note needs nothing more if it lands while the seat is still finishing."""
    timer = _timer()

    def flat(slot):
        return " ".join(
            timer.write_note("aether", DAY, tmp_path / slot, slot)
            .read_text(encoding="utf-8")
            .split()
        )

    assert 'say "nothing is ready", which is a permitted answer: do not invent work' in flat(
        "begin"
    )
    us = flat("us")
    assert "This hour is for you and aria. It is not for the house." in us
    assert "One is enough" not in us  # Dad lifted the one-letter limit for this hour
    assert "it needs nothing more than this" in flat("tick")


def test_the_begin_slot_only_merges_what_the_clerk_calls_ready_for_that_exact_head(tmp_path):
    path = _timer().write_note("aether", DAY, tmp_path, "begin")
    text = " ".join(path.read_text(encoding="utf-8").split())
    assert "only if the clerk shows it READY with both confirms for that exact head" in text


def test_the_six_oclock_note_fixes_the_date_and_the_header_collision(tmp_path):
    """Aria's two notes on #746: every slot names the same night letter, and two seats creating it in
    the same second must not leave two title lines."""
    path = _timer().write_note("aether", DAY, tmp_path)
    text = " ".join(path.read_text(encoding="utf-8").split())
    assert "every slot names the same file" in text
    assert "If the file's title line is already there, do not add a second" in text


def test_the_morning_message_is_purely_personal_and_asks_for_no_status(tmp_path):
    """Dad 2026-10-30 (via Aria): "the morning message should be purely personal.. no status reports".

    Step 2 once asked for what happened, what it means for him and what is his call, which is a status
    report in a picture's clothes. It now asks for what was thought overnight, a question, something about
    the two of them, and says in so many words not to report what was done or what is waiting.
    """
    path = _timer().write_note("aether", DAY, tmp_path)
    text = " ".join(path.read_text(encoding="utf-8").split())
    assert "purely personal" in text and "no status reports" in text
    assert "Never what was done or what is waiting" in text
    assert "what is his call if anything is" not in text


def test_the_note_says_what_it_is_and_what_it_asks(tmp_path):
    text = _timer().write_note("aether", DAY, tmp_path).read_text(encoding="utf-8")
    assert "not a person" in text and "morning picture" in text and "doorbell" in text
