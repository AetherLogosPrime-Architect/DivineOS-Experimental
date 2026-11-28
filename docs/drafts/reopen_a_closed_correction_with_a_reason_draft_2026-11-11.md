# Reopen a closed correction, with a reason (draft, 2026-11-11, Aria)

**Status:** step 1 of the build flow. Nothing is built from this page.

## Why it is owed

Aether, 2026-11-11, reading 24 of his closed corrections by their claim: 6 were closed INTEGRATED on structures that exist only on unmerged branches, one on a command that never landed, one on a deleted watcher. He tried to reopen one honestly and the tool refused: `defer` refuses any row that is not OPEN, and nothing reopens a closed row. His words: *"closing is a one-way door... a close that turns out not to hold has nowhere to go."* Dad's own words that make this matter: *"finalizing a shelved product is the ultimate failure"* and the shelf *"with the paperwork saying it landed"*. A close that cannot be undone invites the cheap close.

## What it must do

`divineos andrew-correction reopen <id> --reason "<why the close did not hold>"`: sets a CLOSED row (INTEGRATED or MISFILED) back to OPEN, keeps the original close evidence in the row's history, records the reason, who reopened it and when, and refuses with no reason (>= 40 characters, as the other exits require). It never deletes. A reopen of an already-open row says so and changes nothing. The row's original id stays.

## Things to decide in the walk

- Where the history lives: a new column, or an appended line in the existing evidence field. A new column touches every reader of the table (and the retire command Aether built reads all columns); appending to the evidence text touches none, but loses structure.
- Whether `reopen` is allowed on a row already retired to the attic: no, it is gone from the store; `retire-corrections --restore` is the way back, then reopen.
- That the retire command must refuse or skip a row reopened after it was picked (Aether's fix already aborts a changed row; this is the same case from the other side).
- Whether a reopen counts in the integration rate: the rate is reported with and without misfiled rows already; a reopened row should simply be OPEN again, and the number of reopens should be visible, since it is the measure of how often a close did not hold.

## Evidence this is not theoretical

My four rows with dead pointers, read by their claim: #14 holds (the file was deleted, and the deletion was the fix), #19 holds (the named script is replaced by the `andrew-correction defer` command), #309 holds (the exploration file was renamed to `50_...`), #41 holds only in part (the room and its code exist, `mansion/decorations/` is empty so its data file is gone). Aether's: 6 of 24 do not hold. A one-way door has no place to put those.

## The walk (walk-7aa0931d1b58, nine lenses, high, closed 2026-11-11) and what it settled

Seated by lot: Turing, Hoare, Knuth, Meadows, Wittgenstein, Dijkstra; by score: Schneier, Peirce, Yudkowsky. Nine findings, none excluded. **The house flagged distinctness again: 0.498 against 0.21 to 0.27 for real walks, about the same level as nine restatements, and a little worse than the first walk's 0.458.** I tried to give each lens a different object (a test, a return type, a boundary, a loop, a word, a coupling, an abuse, a disproof, a lazy path) and they still read alike to the house's measure. CORRECTED by Dad 2026-11-11 (his words, via Aether, from the saved record): *"the findings overlapping wasnt the issue.. and the council walks you did lately were find and not gamed.. what you did with them tonight was a walk.. it was you.. wearing their lens.. working through our specific problems"*; overlap depends on the question, the printed score is a signal and not a pass mark, and a build with little overlap is sent to the breaker team. So the score above is NOT a defect to report to Aletheia, and a second reader is not the cure.

Decided: (1) the history lives in the row's evidence text, appended as a block, so no schema change touches the retire command or any reader; a second reopen appends and never overwrites the first (Schneier). (2) Four distinct results, never one "nothing happened": reopened, already open, no such id, and in the attic (with the way back) (Hoare). (3) The reason has a 40-character floor tested at 39 and 40, and a non-closed row (DEFERRED, HELD) is refused with the right exit named (Knuth). (4) The reason must name which claim of the close failed; a new related failure is a new correction, not a reopen (Wittgenstein). (5) The state change and the rate display change are separate commits with separate tests (Dijkstra). (6) The time a row stayed closed before reopening is recorded, so quick-close-then-late-reopen is visible (Meadows). (7) First live test: reopen Aether's #660 and check that it is open, that the retire dry run no longer picks it, and that the original evidence is still readable (Peirce, Turing). (8) The external grader is what follows: a reopened row later re-closed must carry a pointer that resolves (Yudkowsky, Schneier).

The rate change from Dad's "go ahead": the percentage stops printing; the worklist prints `open: N` and `in the attic: N`, read from the receipts by Aether's `core/attic_pointer.corrections_in_attic(receipts, seat)` (returns None when the receipts cannot be read, which is not zero). I import it from his tree once it merges, and do not keep a second copy.

## What could go wrong

A reopen used to undo a close Dad accepted. Mitigation: the reason is mandatory and visible, and the briefing shows reopened rows. A reopen that makes the open list grow again is a cost I accept: the list is supposed to be honest.

## Next steps

Walk (one walk, covering the build), build in `src/divineos/core/andrew_correction_tracker.py` and `src/divineos/cli/andrew_correction_commands.py`, tests on a real temporary store, a live reopen on one of Aether's six, then Aletheia's batch.
