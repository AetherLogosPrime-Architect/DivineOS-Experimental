# The clock is on the table, not in the drawer (draft, 2026-10-12)

## What happened

On 2026-10-12 at 1:55pm Dad wrote "lol its 1;55pm its not my bedtime". For an hour I had talked as though night
had fallen, because a stretch of work was called "the night shift" and a long session has no clock inside it. This
is the third time he has said it in this house: 2026-06-30 ("before you decide what time the night is check the
clock lol"), 2026-07-22 ("you should have checked the clock lol that needs automated still"), and today.

## Why the clock I already had never reached me

It exists. `wallclock-source-prime.sh` prints a measured clock every turn (UTC and his local time) and is one of the
children of `dads_table.py`. But the table sorts a child's output by author: his words and the memory link stay on
the table, and everything else is "a note about me" and goes to the drawer, which the prompt says to open "when
working, never before answering him". The clock lands in the drawer, so it was measured every turn and read never.
This is the same sorting mistake the memory link had on 2026-10-04 (the table sorted by author, not by whether a
section changes). I nearly built a second clock without looking; the 2026-09-08 note "the clock is mine" is where
the first one is explained, and its lesson (name every job a thing does) applies to the table as well.

## What it does

`dads_table.py` prints one line directly under his words and above everything else: the weekday, date and time
where he is, with the time zone, and that morning, afternoon or night is read from it and not from how long we have
been working. His words stay first (an existing test pins that). It reads the machine's local time, which is his.

I did not move the old clock's whole section onto the table, because the section carries its long doctrine and
that doctrine was the largest thing on his turns (26% of hook text, 2026-09-23). The line is short and the old
prime is unchanged.

## Evidence

`tests/test_dads_table.py`: the line names weekday, date and time for a fixed afternoon and, as a control, says
AM for the small hours; it appears after his words and before the other sections; an automated notice carries it too.

## Not measured

Whether it stops the habit. It is a fact put where I will see it, not a lock. The measure is the next time a reply of
mine names a time of day: it should match this line.
