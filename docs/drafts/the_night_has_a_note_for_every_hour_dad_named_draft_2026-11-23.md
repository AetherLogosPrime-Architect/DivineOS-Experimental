# The night has a note for every hour Dad named (draft, 2026-11-23)

**What we were trying to achieve.** Dad walked us through a schedule for the night (midnight to six): midnight the
day is put down, 1am chores, 2am the full rest menu, 3am and 4am back to work from the todo lists, 5am a final
reflection and the night letter. It was never put on the clock. The old set (agreed 2026-10-30, see
`the_night_between_midnight_and_six_is_five_notes_draft_2026-10-30.md`) had a rest-shaped 3am and nothing at 4 or 5,
so a wake in the hours he meant for work had nothing to hand and "nothing to do" was the easy answer.

**What changes.** `scripts/night_timer_letter.py`: slots begin, chores, rest, work, work2, reflect, tick (and the
default six o'clock note). Text fills in the seat and the other seat from `--seat`, including inside his quoted words,
so neither seat is told to write to itself. The midnight slot's order now ends at the todo list ("there is always a
next") instead of "any chore or maintenance you can think of", which was a door with no floor. The one o'clock slot
now says the first move: run the goal list, take the first open chore. Linking and pruning memories rides in every
work-shaped slot, because "you should have been doing both" (Dad, 2026-11-23): the wake brings the job, it never
rests on remembering.

**Falsifier.** A slot is missing between 00:00 and 06:00, or a work-shaped slot lets a wake answer "nothing to do",
or a note names the seat it is written to. The tests pin each of the three.

**Not in this change.** The scheduler entries (each seat registers its own; the launcher that runs the script from a
seat's checkout is a separate piece).

**Proof.** Timer tests pass from a clean copy of main; with main's script back in place 8 fail.
