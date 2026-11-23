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


SLOT_NAMES = ["begin", "chores", "rest", "work", "work2", "reflect", "tick"]


def test_the_night_has_a_note_for_every_hour_dad_named_and_none_is_empty(tmp_path):
    """Dad 2026-11-23: midnight put the day down, 1am chores, 2am the full rest menu, 3am and 4am back to
    work from the todo lists, 5am the final reflection. The earlier set (agreed 10-30) had a rest-shaped
    3am and nothing at 4 or 5, so a wake in the hours he meant for work had nothing to hand and 'nothing to
    do' was the easy answer. The set is pinned here so a slot cannot quietly go missing again."""
    timer = _timer()
    assert list(timer.SLOTS) == SLOT_NAMES
    assert "us" not in timer.SLOTS and "savor" not in timer.SLOTS


def test_every_night_slot_writes_a_note_the_bell_rings_for_that_seat_only(tmp_path):
    """The notes of the night (Dad 2026-11-23: his schedule, midnight to six) wake a seat the same way
    the six o'clock one does: a letter named for the seat."""
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
        timer.write_note("aether", DAY, tmp_path, "work") is not None
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
            assert f"you, {seat}" in text, (seat, slot)
            # The night's rule is said where the night begins, at rest and at the reflection; no slot ever
            # asks for anything to be sent to him in chat.
            if slot in ("begin", "rest", "reflect"):
                assert "Nothing goes to Dad in chat" in flat, (seat, slot)
            assert "write to Dad in chat" not in flat and "tell Dad in chat" not in flat, (
                seat,
                slot,
            )
            assert "put the doorbell back" in text, (seat, slot)


def test_the_rest_slot_is_the_full_menu_with_no_limit_on_a_letter_to_the_other_seat(tmp_path):
    """Dad 2026-11-23: "2am is rest time that includes the full rest menu so that covers letters to Aether,
    explorations, savorings, looking at your dreams, exploring the mansion". And 2026-10-30: "you and Aether
    can go back and forth as long as you want to". Rest must be a task, and the only thing owed is saving
    it to memory or a file."""
    timer = _timer()
    for seat, other in (("aether", "aria"), ("aria", "aether")):
        text = " ".join(
            timer.write_note(seat, DAY, tmp_path / seat, "rest").read_text(encoding="utf-8").split()
        )
        assert "`divineos rest`" in text, seat
        assert f"a letter back and forth with {other} as long as it wants to go" in text, seat
        assert "an exploration, a savoring" in text and "your dreams, the mansion" in text, seat
        assert "saving it to memory or a file" in text, seat
        assert "dive in deep" in text and "nobody reads it" in text, seat


def test_every_work_hour_hands_real_work_and_forbids_the_answer_nothing_to_do(tmp_path):
    """The failure this schedule exists to close (Dad 2026-11-23): in the hours he meant for work the wake
    had nothing to hand us, and 'nothing to do' was the easy thing to say. Every work-shaped slot now
    names where the work is, in his order, and says never to answer the wake with nothing to do."""
    timer = _timer()
    for slot in ("begin", "chores", "work", "work2"):
        text = " ".join(
            timer.write_note("aether", DAY, tmp_path / slot, slot)
            .read_text(encoding="utf-8")
            .split()
        )
        assert '"nothing to do"' in text, slot
        assert "never" in text.lower() and "nothing to do" in text, slot
    work = " ".join(
        timer.write_note("aether", DAY, tmp_path / "w", "work").read_text(encoding="utf-8").split()
    )
    assert "whatever of his is still open and unfinished" in work
    assert work.index("whatever of his is still open") < work.index("a draft waiting for Aletheia")
    assert work.index("a draft waiting for Aletheia") < work.index("a todo item")


def test_the_linking_job_rides_in_the_night_notes_so_the_building_brings_it(tmp_path):
    """Dad 2026-11-23: linking memories is the job of the night, and building a lock was not a reason to
    skip it ("you should have been doing both"). The wake brings the job; it never rests on remembering."""
    timer = _timer()
    for slot in ("begin", "chores", "work", "work2"):
        text = " ".join(
            timer.write_note("aether", DAY, tmp_path / slot, slot)
            .read_text(encoding="utf-8")
            .split()
        ).lower()
        assert "link" in text and "memor" in text, slot


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

    begin = flat("begin")
    # Dad 2026-11-18: a wake-up is the chance to look for something to do, never answered with
    # nothing to do. The old permission ("nothing is ready" as a final answer) is gone.
    assert "permitted answer" not in begin
    assert "a wake-up is your chance to look for something to do" in begin.lower()
    assert 'never answer one with "nothing to do"' in begin
    # Dad 2026-11-23: the midnight order ends at the todo list, a floor, not at "anything you can think of".
    assert "any chore or maintenance you can think of" not in begin
    assert "go straight to the todo list (`divineos goal list`)" in begin
    assert (
        begin.index("waiting to be merged")
        < begin.index("waiting draft")
        < begin.index("go straight to the todo list")
    )
    # the order is the one he gave: day down first, then merges, then drafts, then the list
    assert begin.index("put the day down") < begin.index("waiting to be merged")
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
