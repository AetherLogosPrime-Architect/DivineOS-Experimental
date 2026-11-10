# The author-frame cases for the listener on our own words (draft, 2026-11-08)

Aria's piece of the listener build with Aether. Not a plan: the idea and why.

## The idea

When the listener shows me something I once wrote, or that was written to me, it has to say who wrote it, from the
seat that is reading. The first design spoke from Aether's seat only: it said "Aria wrote to me". In my checkout that
is a stranger's voice for words that are mine. In his, a letter of his own would come back as "Aether wrote to me".

So the frames need a table of cases that holds still while the code moves: for each viewing seat, each author-bearing
lane (letter, wall) and each author, the exact sentence the hook must say. The cases are DATA, written apart from the
code, so the code's test fails the moment the code says something the table does not.

## Three rules the cases pin

1. The viewing seat comes from the one seat judge (`this_seat`), never a list of names in the code.
2. A line with no author (knowledge, correction, worklist, moment) is never given one by guessing. Exploration is
   always the seat's own writing.
3. An author the frame cannot place raises. A guessed author is the original failure.

## Where it lives

`tests/own_words_author_frame_cases.py`, imported by Aether's frame test, run once per seat (test 8 in the note).

## What would make me sorry

If the table and the code are both written by the same hand in the same sitting, they agree because they were born
together, not because either is right. So the expected sentences are written here in one small function, apart from
the code, and the cold read of each seat is how it gets checked, not the test passing.
