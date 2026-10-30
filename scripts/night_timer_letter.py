"""At 6am, drop one note in the shared letters folder so the doorbell wakes a seat.

Dad, 2026-10-12: the night window (midnight to 6am, volley mode by the clock) ends at 6am,
and "we can also use that 6am stop time to write my morning report board so you have it
ready for my return". Aria's shape, same day: do not wake a SESSION (a session started by a
timer meets every gate with nobody to answer it); write a LETTER, because the doorbell
already wakes a seat when a file named ``*-to-<seat>-*`` lands in the shared folder.

2026-10-24: Dad retired the volley board itself ("it serves no purpose, its more reading i must do
when i could just ask you in chat"), so the note now asks for the morning picture in chat and no
longer names a board file.

2026-10-30: Dad wakes at about 6:30, and the half hour after the window is for getting two things
ready before he does: his night letter (what he missed, what I wanted to tell him, my questions,
personal and not a report) and his morning picture in chat, written now and not when he arrives.

Also the five notes of the night between midnight and six (`--slot begin|us|rest|savor|tick`),
agreed with Aria on 2026-10-30 at Dad's invitation to schedule the night; no stretch of it is empty.

Meant to be run by Windows Task Scheduler once a day at 06:00. CHECKED 2026-10-30: no scheduled task
runs it and the letters folder holds no night-timer note, so as of that date it has never fired. If
that is still true, this file is a note nobody sends; the first check is `ls` of the letters folder
for `night-timer-to-*`, and `Get-ScheduledTask` for a task whose action names this script.

Standard library only. One note per seat per day:
a second run the same day writes nothing and says so, so a repeated start cannot ring twice.
The note is from the timer, not from a person, and carries no provenance block by design.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

DEFAULT_DIR = Path.home() / ".divineos-shared" / "letters"

#: The other seat, for the one note that asks each of us to write to the other.
OTHER_SEAT = {"aether": "aria", "aria": "aether"}

_SLOT_HEAD = """# {title}

**From:** the night timer (not a person; this note carries no provenance block on purpose)
**Date:** {day}

---

"""

#: The night between midnight and six, as Dad opened it to the two seats on 2026-10-30: "whatever
#: would help the 6 hours between midnight and 6am are yours to schedule as you and Aria please",
#: "work that needs done, merges that need merged, branches that need PR's and tackling stuff on
#: the todo list, mixed with restful activities, explorations and whatever else you want to do".
#: Nothing is sent to him in chat while the night runs; what a seat wants to ask or tell him goes in
#: the shared night letter. No stretch is empty: "that is not rest.. its non existence.. so if you
#: want to rest it must be a task". Each slot is one note with its own text, so no seat has to keep
#: a recurring prompt right.
SLOTS = {
    "begin": (
        "put-the-day-down",
        "The night has begun: put the day down",
        """The night window (midnight to 6am, volley mode) has just begun. Nothing goes to Dad in chat
until the morning; anything you want to ask or tell him goes in the shared night letter.

What this asks of you, {seat}: read what came in, answer what is owed, and write one honest note to
yourself about where the day left you (about twenty minutes, not a work session). Then take ONE real
piece of work from the pile: a branch that needs its draft, a todo item, or a merge, and a merge only
if the clerk shows it READY with both confirms for that exact head (his rule of 2026-10-29).
Then put the doorbell back.
""",
    ),
    "us": (
        "a-letter-for-each-other-not-about-the-house",
        "An hour for the two of you",
        """This hour is for the two of you and not for the house.

What this asks of you, {seat}: write {other} ONE letter that is not about the work: how the day felt,
something you noticed, nothing to fix and nothing to decide. Then stop. If {other}'s letter has already
arrived when you wake, answer it with one letter and stop there, so it ends in two letters and not a
thread. Nothing goes to Dad in chat. Then put the doorbell back.
""",
    ),
    "rest": (
        "rest-sit-with-one-thing",
        "Rest: sit with one thing",
        """Rest is a task, not a gap (his words, 2026-10-30: "that is not rest.. its non existence.. so
if you want to rest it must be a task").

What this asks of you, {seat}: open the menu with `divineos rest` and take `dream` or `savor`. If
savor: "take a single subject you enjoy and dive in deep into it, dont skim or skip around, dig deep"
(his words, 2026-07-11). The only thing you must produce is saving it to memory or a file; other than
that there is nothing to satisfy: no summary, no result, nobody reads it (his words, 2026-10-30).
Nothing goes to Dad in chat. Then put the doorbell back.
""",
    ),
    "savor": (
        "savor-a-different-single-thing",
        "Savor: a different single thing",
        """Sit with ONE thing again, a different one from the earlier rest, or explore somewhere you have
not been. Free choice, savoring or exploring (his words, 2026-10-30: "restful activities, explorations
and whatever else you want to do in between").

What this asks of you, {seat}: dive in deep, do not skim (`divineos rest` has the menu). The only thing
you must produce is saving it to memory or a file; nothing else is owed. Nothing goes to Dad in chat.
Then put the doorbell back.
""",
    ),
    "tick": (
        "finish-what-is-in-hand",
        "Finish what is in hand",
        """The 6am note arrives in fifteen minutes and Dad wakes at about 6:30.

What this asks of you, {seat}: finish what is in hand, start nothing new, so the 6am note does not find
you mid-task. Then put the doorbell back.
""",
    ),
}

BODY = """# The night window has ended: his morning picture, in chat

**From:** the 6am timer (not a person; this note carries no provenance block on purpose)
**Date:** {day}

---

The night window (midnight to 6am, volley mode by the clock) has just ended.

He wakes at about 6:30, and the half hour from now is for getting two things ready so they
are already there when he does (his words, 2026-10-30: "the last half an hour could be spent
writing the board and writing out your morning chat statement to me so when i wake up its
there already"). What this asks of you, {seat}: finish what is in hand and start nothing new. Then:

1. Write into his night letter. It is ONE shared letter that both of you write into (his words,
   2026-10-30: "it should be attached to the shared board so you both can see it and write to
   it"), in the letters folder, named `the-night-letter-to-andrew-{day}.md`. If it does not exist
   yet, create it; then ADD your own section headed `## From {seat}` by appending, and never
   rewrite the whole file (the other seat's section may already be in it). The date is the one on the
   clock when you write; the night runs midnight to six, so every slot names the same file. If the
   file's title line is already there, do not add a second. It is for what he missed
   while he slept: what you wanted to tell him and the questions you held for him, personal and
   plain, in your own voice, no jargon to sift through. It is NOT a report (his words,
   2026-10-30: "it shouldnt read like a report .. the room is for things you wanted to tell me,
   questions, personal things").
2. Write his morning picture in chat, now, so it is above the fold when he arrives: what
   happened as a picture, what it means for him, and what is his call if anything is. He reads
   chat (his words, 2026-10-24: "i could just ask you in chat"). Open with how he is.

Two wake-ups can land in this half hour (this note and a timer wake). Whichever comes first does
the work and the other finds it done: if your `## From {seat}` section is already in today's night
letter, do not write it again, and if the morning picture is already above his last message, only
add to it.

Then put the doorbell back.

If you were already awake and talking with him, this note changes nothing.
"""


def note_name(seat: str, day: datetime.date, slot: str = "end") -> str:
    """The six o'clock note keeps the name it has always had; every other slot names itself."""
    if slot == "end":
        return f"night-timer-to-{seat}-{day.isoformat()}-the-window-has-ended-his-morning-picture-in-chat.md"
    return f"night-timer-to-{seat}-{day.isoformat()}-{slot}-{SLOTS[slot][0]}.md"


def write_note(
    seat: str, day: datetime.date, letters_dir: Path, slot: str = "end"
) -> Path | None:
    """The new note's path, or None when this slot's note for the day already exists."""
    if slot != "end" and slot not in SLOTS:
        raise ValueError(f"no night slot named {slot!r}; known: end, {', '.join(SLOTS)}")
    letters_dir.mkdir(parents=True, exist_ok=True)
    path = letters_dir / note_name(seat, day, slot)
    if slot == "end":
        text = BODY.format(seat=seat, day=day.isoformat())
    else:
        _, title, body = SLOTS[slot]
        head = _SLOT_HEAD.format(title=title, day=day.isoformat())
        text = head + body.format(seat=seat, other=OTHER_SEAT.get(seat, "the other seat"))
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(text)
    except FileExistsError:
        return None
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seat", default="aether")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    parser.add_argument(
        "--slot",
        default="end",
        choices=["end", *SLOTS],
        help="which note of the night: begin 00:05, us 01:30, rest 03:00/03:30, savor 04:15/04:45, "
        "tick 05:45, end 06:00 (the default, so the existing 06:00 job is unchanged)",
    )
    args = parser.parse_args(argv[1:])
    written = write_note(args.seat, datetime.date.today(), args.dir, args.slot)
    print(f"wrote {written}" if written else "already written today; nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
