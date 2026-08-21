# Known chain breaks

The ledger chains each event to the one before it, so removing or altering a
row shows up as a broken link. That is the whole tamper-evidence property.

A break listed here is one somebody **looked at** and found a cause that is not
tampering. The evidence sits beside the id so the exemption can be argued with
rather than merely trusted. Anything not on this list fails the check
immediately.

**Adding a line is a claim that you investigated.** It is not a way to quiet the
alarm. A dishonest entry is worse than a broken chain, because it is a broken
chain that looks mended.

---

- `22d95584-4a61-4931-9767-5acd036742ed` — CONSOLIDATION_CHECKPOINT, 2026-06-10 19:16:41

  The id must be written in FULL. The report abbreviates it to twelve
  characters, and a line copied from the report will never match — the check
  compares whole ids, and a non-matching exemption fails silently by simply
  not exempting. Caught here 2026-08-13 on the first attempt.

  **What happened.** Four events landed inside the same second at session
  start. Three of them chain cleanly. The fourth chained itself to the second
  one instead of the third — it read the head of the chain, and by the time it
  wrote, another writer had already appended. A concurrent-append race.

  **Why it is not tampering.** Nothing is missing. Every event's own
  fingerprint verifies, and the predecessor this row *should* have pointed at
  is still sitting in the table two rows away. There is no gap to have deleted
  anything into: all four share the same second.

  **Why it is not repaired.** Mending the link would rewrite a true record of a
  real race to make an instrument quiet. The race happened. Erasing the trace of
  it would trade a true history for a comfortable one, and would also destroy
  the only evidence that anything ever went wrong here.

  **Found 2026-08-13**, while investigating why `divineos verify` had been
  reporting the ledger TAMPERED since June. It reported two breaks. One was
  manufactured by the verifier's own sort — it walked the chain in clock order,
  and these events' clock readings are inverted relative to the rows themselves.
  Walking in append order dropped it to this one. The verifier was fixed; this
  break is real and stays.

  **The underlying race is not fixed by this entry.** The append path serializes
  within a process, but two processes appending in the same instant can still
  interleave. That is a design question shared with Aether, whose ledger runs
  the same code, and is open.
