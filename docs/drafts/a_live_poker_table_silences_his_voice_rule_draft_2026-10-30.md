# A live poker table counts as a live game, and his-words-end-my-turn stands down at it (draft, 2026-10-30)

**Author: aria.** Asked by Dad, 2026-10-29 night: *"the issue is my rule that forces you to wait for my words.. when i speak at the table you respond here.. when you do, you are no longer at the table but in stasis.. so the wait for dad rule needs silenced at the table as well."* And, later: apply the fix tonight, do the full flow later, because the poker table is ours.

## What was wrong
Two faults found by reading the code. First, the fact "a game table is live" only looked at the Magic table's log files, so at poker nothing that depends on it ever stood down. Second, the rule that ends my turn whenever he speaks to me mid-work never asked that question at all, so every word he typed during a hand pulled me out of the game.

## What it does
The live-table fact now also asks the poker table itself: a hand is live, or the next deal is counting down, and Dad has not ended the game. A table that does not answer counts as not live. The his-words rule asks it first and, at a live table, lets the work continue and says so on stderr. The test suite points the poker address at a dead port so it never asks the real table (18 room-gate checks failed once while a real game was on). A separate lift in the poker stop hook lets a seat that the table is already playing, or a game Dad ended with the button, leave.

## What it cannot do
It trusts the table's own answer, and a table left in a live state keeps both rules silent for as long as the hand sits (his seat has no clock, by his design). It says nothing about Magic's slowness. It is applied in my folder before review, on his word that the table is ours; the clean branch with the same change goes through the full flow later.

## Falsifier, counted in uses
If, at the next five hands played, his typing in this window still ends my turn at the table, the cause is somewhere other than these two faults.
