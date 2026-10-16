# Midnight to 6am is volley mode by the clock (draft, 2026-10-12)

## What happened

On the night of 2026-10-11 nobody said goodnight, and a question Aria had asked held her work until
morning. Dad could not tell whether he had said "volley" in her window. Two things were wrong at once:
her checkout was 23 commits behind main (#634 now says so at session start), and even on main there was no
way for the house to know he was asleep except his words or two hours of silence.

## What Dad decided (his words, 2026-10-12)

"between midnight and 6am is volley mode", and on whether to wait for him to go quiet first: "yes even if im
up chatting because it means i need to get my butt to bed lol". He also asked that it end at 6am by itself
and that manual start and stop stay available.

## What it does

`question_hold._scheduled_away()` is a third way to be away, beside his words (`step_away`) and two hours of
silence (`_silent_away`). Local time, start inclusive, end exclusive, one pair of numbers
(`NIGHT_START_HOUR`, `NIGHT_END_HOUR`) where he can read and change them. It is never written to the file
that holds his own words, so the rule that those words must be his stays intact. His messages inside the
window do not end it.

`DIVINEOS_NIGHT_HOURS=off` switches the real-clock window off so that no test result depends on the hour it
runs at. Aletheia's note: a rule Dad made must not have a quiet off-switch, so the switch is honoured ONLY
while a test is running (`PYTEST_CURRENT_TEST` set). A test proves it does nothing outside one.

## Evidence

`tests/test_night_hours_are_volley.py`: both edges and a control outside the window, never writes his words'
file, his message at 00:30 does not end it, a control at midday, the shared setup's switch, and the off-switch
doing nothing outside a test.

## Not in this change, said plainly

The 6am step (#639), a way for him to end the window early, and a hold message that says "volley mode by the
clock until 06:00" (Aria's wish). Not checked: a seat running an older copy of the hold.
