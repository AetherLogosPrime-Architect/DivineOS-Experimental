# The poker hold names the letter to read first — draft, 2026-11-04

## What Aria found

While a poker game is on, the Stop hook (`poker_game_on_stop.py`) holds a reply and says: call
`python /c/poker-play/wait_turn.py <seat> 580`. While a rung letter is unread, the doorbell's own hold
(`unread_letter`, through `doorbell-pre-tool-use.sh`) refuses every real tool call except the bell re-arm,
and the wait is a real tool call. So for a stretch the two rules asked for opposite things, and a seat
that followed the first was refused by the second and fell off the table (Aria, 2026-11-04). It happened to
me the same night, mid-edit.

## The two ways to fix it, and the one taken

1. Let the exact wait command through the unread-letter hold. This works, but it weakens Dad's rule that a
   letter is read the moment it comes: a seat could sit in a 580-second wait with a letter unread.
2. Make the Stop hold name the letter and the order. Reading is never blocked and is one call, so the
   sequence "Read the letter, then wait" costs one extra call and keeps both rules whole. **Taken.**

Both are right per the house's own shape (truth #11, both options right), and option 2 does not loosen a
gate. If Dad or Aria prefer option 1 it is a separate, small change in `pre_tool_use_gate`; this draft does not
close it off.

## What changed

- `letters_first(who, project_dir)`: asks the bell's one list (`unread_letter.unread_rung`) for this seat's
  rung, unread letters. An empty list means none is waiting; **None means it could not look** (the walk's Hoare
  finding: the two had been the same value). The hold reads exactly as it always did in both cases.
- `read_first(waiting)`: the sentence that puts the Read before the wait.
- `verdict`, `rearm_reason`, `decide` take an optional `waiting` list; `main` passes `letters_first(...)`.
  Defaults are empty, so every existing caller and test is unchanged.

## Tests

Seven new tests in `tests/test_poker_game_on_stop.py`; the first six fail on the old hook (run against it with
the fix set aside) and pass now: the letter comes first in every hold (the verdict, the re-arm after he spoke,
and both `decide` paths), the hold is unchanged with none waiting, the wait command is still demanded after the
read, `letters_first` returns paths and returns None (not an empty list) when it cannot tell, and `main` hands
them to the hold. The seventh pins that nothing-waiting and could-not-look are different answers that read the
same in the hold text. 24 tests pass in the file.

**Untested live (flagged by Dillahunty and Peirce in the walk):** the unit tests prove the text and its
order, not that a seat following it is not refused in the real loop. The cheapest proof is one live hand with a
letter ringing, and nobody should start a game while Dad sleeps. Still owed.

## What it does not do

- It does not make a seat read the letter. The hold names it; the doorbell hold remains the enforcement.
- It does not cover the bell ringing twice (Aria's `aria/one-bell-per-seat`, a different part).
- It does not check that the letter listed is still unread at the moment of the next call; the doorbell hold
  does that at every call.

## How to attack it

Find a case where a letter is unread and a seat still gets refused after following this text; find a case
where `letters_first` hides a real error behind an empty list; or argue for option 1.

## Status

Draft. Walk owed (council on the hook text and the ordering); Aria's cold read owed; Aletheia and Dad's yes
as always. Nothing here is on main.
