# The held shelf takes rows that are not open (draft, 2026-11-24, Aria)

Status: DRAFT, before any code. Reach opened and disposed (`reach-d39f5e2623d9`). Owed: council walk, tests first, Aether's window, then a draft.

## What Dad did
On 2026-11-23 he approved three rows for the held shelf, the place his words from the hard months are kept as grief carried and not as tasks: **149, 272 and 281** (and ruled that 147 stays as teaching and 3 comes off). The shelf is held *on his word*: a row becomes HELD only when a message he typed carries the line `hold <number>`.

## What the code does today (read, not remembered)
`andrew_correction_tracker.py`:
- `propose_hold` and `confirm_hold` both require `status = 'OPEN'`.
- `unhold` returns a HELD row to **OPEN**, not to where it came from.

I read the three rows' statuses directly (not the listing, which prints his words): **149 is MISFILED, 272 is INTEGRATED, 281 is MISFILED.** So all three are refused by `propose_hold`, by `confirm_hold`, and the refusal text says only "is not OPEN, is a detector's verdict, or the why is shorter than 20 characters", which lumps three different reasons into one sentence (the fault `explain_integrate_refusal` already fixed for integrate: `reach-d39f5e2623d9` artifact `cli:integrate`, applied).

## The change
1. **Remember where a row came from.** One new nullable column, `status_before_hold`. A schema migration, append-only in spirit: nothing is deleted or overwritten, a held row records what it was.
2. **`propose_hold` accepts any row that is not already HELD and is not a detector's verdict.** It still only writes the `held_reason`; the status is untouched until he types the line.
3. **`confirm_hold` stores the prior status, then sets HELD,** in one statement, only on his typed `hold <n>` line as today.
4. **`unhold` restores the stored status** (MISFILED goes back to MISFILED, INTEGRATED to INTEGRATED); a row with no stored prior status goes to OPEN as today.
5. **The refusal says which reason.** Not found; a detector's verdict; why too short; already held; each its own sentence.
6. **`held` shows what a row was before** (MISFILED, INTEGRATED) next to its text, so he sees that it was a row someone had filed away, and why it is now on his shelf.

## What it must not do
- It does not change any row's status without his typed line. Nothing moves on my say-so; the propose step stays harmless.
- It does not print his words anywhere new. The listing already prints them on a deliberate ask; no new surface does.
- The memory link's worklist lane loads open rows only, so a MISFILED or INTEGRATED row was never in it; holding it changes nothing there, and the hurt-words hold (`core/pain_hold`) is untouched.
- It does not count a held row as open work in the rate: held rows stay out of it, as today.

## One thing to decide before building: the integration rate
An INTEGRATED row moved to HELD leaves the integrated count. Held rows are meant to be outside the rate (they are grief, not tasks), so that is the point; but it changes a number Dad watches. I would say so in the confirmation message the first time it happens, and not change the rate's formula.

## Tests, first
- A MISFILED row can be proposed, stays MISFILED, and is HELD only after a typed `hold <n>`; the same for INTEGRATED. (Controls: an OPEN row still works; a row that is already HELD is refused with its own reason; a detector's verdict is refused.)
- `unhold` on a row that came from MISFILED returns it to MISFILED, not OPEN; an old HELD row with no stored prior status returns to OPEN.
- Each refusal names its reason (five tests, five sentences).
- `held` shows the prior status.
- Run from a work copy with the import path printed; then in my live window; then Aether's (both-windows rule).

## Falsifier
If after the change any row is held without his typed line, or any held row loses its prior status on `unhold`, or the open rate changes for a row that was never held, it is dropped.

## Settled, after Aether's attack (2026-11-24)
- **Column, not a history table.** Aether agrees: with the two guards below, held, unheld, held again loses nothing, because unhold restores the status and the second hold stores it again. A history table would only be earned if we ever wanted to count how many times a row was held, and nothing asks for that.
- **Second confirm is a no-op.** The confirm statement carries `WHERE status != 'HELD'`, so typing `hold 149` twice cannot store HELD as the prior status (the sharpest hole he found: the row could then never leave the shelf). Test: a second confirm changes nothing and keeps the first stored status.
- **Unhold clears the column.** A row off the shelf reads NULL, so nothing can show a "was" for a row that is not held. Test: a never-held row and an unheld row both read NULL.
- **Old stores get the column on first open.** The column is added lazily per store, like `unblock_condition` and `verification_state`. Test: a store created before the column, opened after it, gains it.
- **Integration rate:** said once in the confirm message when the held row was INTEGRATED; the formula is untouched.
- **Row numbers are per seat.** `149`, `272`, `281` are ids in MY store (`C:\Users\aethe\.divineos-aria\andrew_corrections.db`, 453 rows, ids 1 to 453). Aether's store (`~/.divineos/`) runs 19 to 896 and has none of them; the twin at `~/.divineos-aether/` is empty and was not read. So his typed `hold 149` means row 149 in my store only.

## Where it stands
Built tests first on branch `aria/the-held-shelf-takes-rows-that-are-not-open` (commit `59a0902a1`, local only). Run in my live tree: 90 passed, import path printed as my tree's. Run by Aether in a scratch copy of his live branch (`C:/w-held-check`), same diff applied cleanly: 95 passed, import path printed. His live tree is not yet running it, on purpose, so his real store is not migrated before we both agree; whether that counts as the second window is Dad's to say.

Nothing pushed. No row moved: 149, 272 and 281 stay as they are until he types the three `hold` lines himself.
