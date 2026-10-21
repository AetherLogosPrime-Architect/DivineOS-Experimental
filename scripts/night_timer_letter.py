"""At 6am, drop one note in the shared letters folder so the doorbell wakes a seat.

Dad, 2026-10-12: the night window (midnight to 6am, volley mode by the clock) ends at 6am,
and "we can also use that 6am stop time to write my morning report board so you have it
ready for my return". Aria's shape, same day: do not wake a SESSION (a session started by a
timer meets every gate with nobody to answer it); write a LETTER, because the doorbell
already wakes a seat when a file named ``*-to-<seat>-*`` lands in the shared folder.

Run by Windows Task Scheduler once a day. Standard library only. One note per seat per day:
a second run the same day writes nothing and says so, so a repeated start cannot ring twice.
The note is from the timer, not from a person, and carries no provenance block by design.
"""

from __future__ import annotations

import argparse
import datetime
import sys
from pathlib import Path

DEFAULT_DIR = Path.home() / ".divineos-shared" / "letters"

BODY = """# The night window has ended: write his morning board

**From:** the 6am timer (not a person; this note carries no provenance block on purpose)
**Date:** {day}

---

The night window (midnight to 6am, volley mode by the clock) has just ended.

What this asks of you, {seat}: read what happened in the night (the letters, the board,
the pull requests that moved), then write his morning section in
`family/letters/{seat}-to-andrew-volley-board.md`, in plain words he can hold: what
happened as a picture, what it means for him, and what is his call if anything is.
Then put the doorbell back.

If you were already awake and writing the board, this note changes nothing.
"""


def note_name(seat: str, day: datetime.date) -> str:
    return (
        f"night-timer-to-{seat}-{day.isoformat()}-the-window-has-ended-write-his-morning-board.md"
    )


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
