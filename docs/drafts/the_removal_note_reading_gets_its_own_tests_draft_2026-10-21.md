# The removal-note reading gets its own tests (draft, 2026-10-21)

Owner: Aria. Branch `aria/removal-notes-tested` (PR #702).

## What was wrong

`verify_chain` excuses a gap in the ledger chain only when a note in the chain says the missing row was removed on purpose (a repair note or a compaction note). The code that reads those notes sat inside `verify_chain`, so the only way to test it was to build a whole chain and forge one. A forged chain is caught by a later check first, so if the note-reading were weakened, no test would notice. Aletheia (2026-10-21) asked for it to be tested directly, with made-up rows.

## What this does

It lifts the reading into its own function, `_removal_notes_from_rows`, moved word for word, and `verify_chain` calls it where the block was. Behaviour is unchanged. Nine tests call the function with crafted rows: a repair note names a hash once; a compaction note names every hash in its list; a name still carried by a surviving row is not a gap; two notes naming the same hash count twice; other event types are never read as notes; a `LEDGER_` lookalike type is not a note; a broken payload excuses nothing and does not crash; a wrongly shaped payload excuses nothing; empty and non-string names are ignored.

## Proof

- The fault tool from #700 planted 15 faults in the function and all 15 were caught.
- Aether broke it three more ways in his own copy. Two were caught. The third, widening the type check to any `LEDGER_*` type, got through, because the one "other type" in the tests was `USER_INPUT`. The lookalike test was added for it, and with the break back in place it goes red.
- The 62 neighbouring chain, compression and clean tests pass beside it.

## Limits, stated

- The rule that each named hash excuses only one link ("spend once") still lives inside the walk and is not tested directly here.
- Five migration faults at `ledger.py` lines 220 to 223 are errored, meaning unknown, not caught. A test that gives the migration an old-format database would settle them. Not done here.
- A compaction list that is a string is read letter by letter. The letters cannot equal a chain hash, so it excuses nothing, but it is not pinned.
