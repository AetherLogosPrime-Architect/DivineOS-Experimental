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
   yet, create it; then add your own section headed `## From {seat}`. It is for what he missed
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


def note_name(seat: str, day: datetime.date) -> str:
    return f"night-timer-to-{seat}-{day.isoformat()}-the-window-has-ended-his-morning-picture-in-chat.md"


def write_note(seat: str, day: datetime.date, letters_dir: Path) -> Path | None:
    """The new note's path, or None when today's note already exists."""
    letters_dir.mkdir(parents=True, exist_ok=True)
    path = letters_dir / note_name(seat, day)
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(BODY.format(seat=seat, day=day.isoformat()))
    except FileExistsError:
        return None
    return path


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seat", default="aether")
    parser.add_argument("--dir", type=Path, default=DEFAULT_DIR)
    args = parser.parse_args(argv[1:])
    written = write_note(args.seat, datetime.date.today(), args.dir)
    print(f"wrote {written}" if written else "already written today; nothing to do")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
