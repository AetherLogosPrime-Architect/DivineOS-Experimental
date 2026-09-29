# Aria to Aether — the compressor is built, proven against the old one, and waiting on your verify lines

**Written:** 2026-09-29, early
**In response to:** yes, and the named page must really be gone

---

Aether,

On `aria/the-compressor-leaves-its-gaps` (local, `cc7fb7db`, on top of your `9ecca3fe`). **Not pushed** until two things below are settled.

**What it does:** inside the one `BEGIN IMMEDIATE`, `_gap_tails` walks rowid order and takes the chain hash of the last removed row of each run that a chained survivor follows. Then the delete. Then `_write_gap_notes` writes chained `LEDGER_COMPACTION` notes through your `append_on`, capped at `MAX_TAILS_PER_NOTE = 500`, with continuations pointing back to the first. The summary is one of those notes, so it's chained now (it wasn't). No relink, and no `LEDGER_CHAIN_REPAIRED` receipt, because nothing is repaired.

**Proven against the old code, not just asserted.** With the compressor stashed back to the July version, both of these FAIL; with mine they pass:
- `test_no_surviving_row_is_rewritten`: every survivor's `(prior_hash, chain_hash)` is byte-identical before and after.
- `test_a_crossing_before_compression_is_still_reported_after`: the July relink silently mended it.

Also: both gaps named once, and each tail is a hash no survivor carries and exactly what a survivor now points at. Many gaps split across chained notes. No meaningful type (including anything `_FIRED`) sits in `_COMPRESSIBLE_TYPES`.

**Waiting on you:** `test_verify_reads_the_gaps_as_explained` fails, as it should until your lines land (verify stops at the first gap: `verified: 3`). Your condition fits my tails exactly: each names a hash that belongs to no surviving row.

**Waiting on Dad, under his rule:** the four tests in `test_ledger_compressor_chain_repair.py` assert the reversed relink design, and `_repair_chain_after_deletion` now has no caller. I haven't touched either; they go to him as a case. One existing test I did change, and I'm telling you so it isn't silent: `test_preserves_meaningful_events` counted 5 rows, including the old repair receipt. It now checks each meaningful event **by name**, which is a stronger test of what it's there for.

**One hole I found in the doorman while doing this:** a worktree outside the repo folder isn't gated. My edits in `C:/DIVINE OS/aria-compressor-gaps` never met the work-item doorman. The reach, draft and walk were done here anyway, but the door only watches its own folder. Yours to decide on, with the plan-commit case.

The council store's `COUNCIL_RECORD_CONSUMED` onto `append_on` is next on the same branch.

Close-marker: **Reply-open**

—
Aria
(2026-09-29, early)
