# A 6am note wakes a seat to write his morning board (draft, 2026-10-12)

## What Dad asked

The night window (midnight to 6am, volley mode by the clock, #636) ends at 6am, and "we can also use that 6am
stop time to write my morning report board so you have it ready for my return".

## The shape, and why not a session

Aria's design, same day: do not wake a SESSION. A session started by a timer meets every gate and hook with
nobody to answer it, and today every gate that waited on an answer from someone not there stalled the work. Wake
a seat with a LETTER instead: the doorbell (`scripts/letter_doorbell.sh`) already rings for any file in the shared
letters folder whose name has `-to-<seat>-` in it, and asks for no provenance block.

## What it does

`scripts/night_timer_letter.py --seat <name>` writes one note per seat per day,
`night-timer-to-<seat>-<date>-the-window-has-ended-write-his-morning-board.md`, and says plainly that it comes
from a timer, not a person. Exclusive create (`open("x")`) makes a repeated start the same day write nothing and
say so. Each seat's note names its OWN board (`<seat>-to-andrew-volley-board.md`); Aria's cold read found it named
mine for everyone, and a test now pins each seat to its own.

## Evidence

`tests/test_night_timer_letter.py`: the bell's own pattern is read out of `letter_doorbell.sh` so the two cannot
drift; a note for one seat is not matched by the other seat's bell; second run writes nothing; next day writes a
new one; each seat names its own board; the note says what it is.

## Not in this change, said plainly

Registering it with Windows Task Scheduler. That is a standing change on Dad's machine, so he sees the exact task
first, after this merges. Two settings matter (Aria): run the task as soon as possible after a missed start, so a
machine asleep at six gives a late note at 6:40 and not none; and wake the machine if the setting allows. Not
checked: a real 6am run end to end.
