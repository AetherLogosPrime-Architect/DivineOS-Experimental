# The ring of the doorbell tells me to put it back, on the prompt it arrives on (draft, 2026-10-12)

## What was wrong (Aria's case)

The Stop guard that holds a reply while the letter doorbell is not listening fired correctly every time, and
every time a turn late. The sequence: the bell rings and exits; the harness hands the seat a finished-task
notice at the top of a prompt where it is answering Dad; the seat answers him in plain text with no tool call,
the notice folded in as noise; then the Stop guard holds the reply and Dad reads a second copy. The pre-tool gate
that insists the letter be read never fired, because there was no tool call. About a dozen doubled replies in one day.

## Why not the options I first proposed

A script cannot restart the bell by itself: only the seat can start a harness task that wakes it, so a
self-restarting bell rings into a task nobody registered. The Monitor tool streams lines without exiting but is
killed after 30 minutes. A prompt at letter-write time arrives too late and not at all in a turn with no letter
(Aria's reasoning). The earliest moment the failure can be prevented is the notice itself.

## What it does

`dads_table.py` already prints "NOT FROM DAD" for an automated notice. When the shown text of that notice carries
the doorbell's own command text and a status (either order), it adds one line: the bell rang, re-arm it now, with
the exact command and `run_in_background`. An unrelated finished job prints nothing. A failed exit of the bell
prints it too. The Stop guard is untouched and stays the last line.

Aria's three small notes are in: the docstring says the seat must be the first argument (a flag before it prints
nothing); the match runs over the 600 characters actually shown, so a long notice that merely quotes the command
further down cannot trigger a false reminder (a test pins it); and the closing sentence says "any letters owed".

## Evidence

`tests/test_dads_table.py`: the ring prints the reminder with the seat; a control that an unrelated finished
push prints none while the notice itself is read; a failed exit prints it; a quote far down prints none.

## Not measured

Whether the line is obeyed; it is advice, not a lock. If a held reply still follows a ring, the answer is to make
it a block.
