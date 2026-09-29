# The compressor leaves its gaps, and every page it writes is chained — draft 2026-09-29

## Why
- **The relink is a cover-up shape.** `ledger_compressor.compress_ledger` deletes old noise events (`_COMPRESSIBLE_TYPES`), then `_repair_chain_after_deletion` rebuilds `prior_hash`/`chain_hash` for **every** surviving row from the first orphan to the end. That's my July design ("Interpretation A"), reversed 09-28: rewriting surviving rows is what a tamperer does, and it silently mends every *unrelated* crossed link after the first gap. My 8 `USER_INPUT` crossings, the June row and Aether's 946 would all vanish, and they are the only evidence of the live append race. Aether's council walk on #565 (Knuth, Feynman, Pearl, Einstein, Yudkowsky, Wayne), and my letter `aria-to-aether-2026-09-28-the-gap-stands-and-july-was-wrong.md`.
- **Two pages it writes aren't chained at all.** The `LEDGER_COMPACTION` summary is inserted with no `prior_hash`/`chain_hash` (line 337). And `council_required/store.py:372` inserts `COUNCIL_RECORD_CONSUMED` with no chain either. `verify_chain` counts both as unchained-after-the-chain-began, the forged-row hole of 08-18.

## Prior art to build on (Aether, `fix/the-ledger-cleaner-leaves-its-note`, `9ecca3fe`)
- `ledger.append_on(conn, …)`: a chained, redacted append on the caller's transaction.
- `verify_chain` excuses a prior-link mismatch only when a `LEDGER_CORRUPTION_REPAIRED` note in the chain names `deleted_chain_hash == stored_prior`. Each name is spent once, and the row's own hash is still rechecked.

## The idea
1. **No relink.** `_repair_chain_after_deletion` is no longer called by the compressor. Surviving rows are never modified.
2. **Name only the gaps, not every removed row.** Inside the same `BEGIN IMMEDIATE`, before deleting, walk the rows in rowid order and find each **maximal run** of rows to be removed. A surviving row whose predecessor was removed is the only row that will show a mismatch, and its stored `prior_hash` is the **chain hash of the last row in that run**. The compaction note names those run tails, one per gap, not thousands of hashes.
3. **Its own kind of note.** The note is a `LEDGER_COMPACTION` event (authorized noise removal, not corruption) carrying `gap_tail_chain_hashes: [...]` plus `compressed_count` and `compressed_by_type`, written through `append_on`, so it's chained and redacted in the same transaction as the delete. `verify_chain` gains one more excusing source: a tail named by a chained `LEDGER_COMPACTION` note, spent once, with the row's own hash still rechecked. That's Aether's verify, so it needs his yes.
4. **A run with no survivor after it** (the removed rows were the newest) leaves no mismatch, and its tail isn't named.
5. **Council store:** `COUNCIL_RECORD_CONSUMED` goes through `append_on` on the store's own connection inside its existing transaction.
6. `_repair_chain_after_deletion` then has **no caller**. Under Dad's rule (09-28, *"nothing gets removed without my approval"*), it isn't removed. The orphan checker will flag it, and the case goes to him.

## What the walk changed (walk-d1d17f7e2883)
- **Sagan:** "no surviving row is modified" is proven by hashing every survivor's `(prior_hash, chain_hash)` before and after and asserting they're byte-identical. Reading the code isn't proof.
- **Turing:** tails count only from `LEDGER_COMPACTION` notes that are themselves chained rows the walk verifies, written after the gap in the same transaction.
- **Shannon:** alternating noise and kept rows gives one tail per removed row. Cap the tails per note, split them across several chained notes, and test the interleave.
- **Dillahunty:** the compressible set is unchanged by this, and a test asserts it, so the gap mechanism can't become a way to drop meaningful events.
- **Penrose:** ledgers already compressed under July's design carry rewritten links from before this change. That's recorded as a known fact, and not "fixed" by more rewriting.
- **Feynman:** a dry run against a *copy* of my real ledger. Verify must be unchanged except for newly excused gaps, and my 8 `USER_INPUT` crossings must still be reported.

## Tests that must fail today
- Compress a ledger holding one crossed link *after* the noise: today the crossing is silently mended. It must still be reported afterward.
- Compress: verify passes with the gaps excused by the note. Remove the note's hash from its payload and verify fails at the gap.
- A second surviving row claiming the same tail is a fork, and fails.
- `LEDGER_COMPACTION` and `COUNCIL_RECORD_CONSUMED` rows are chained (no unchained-after-began count).
