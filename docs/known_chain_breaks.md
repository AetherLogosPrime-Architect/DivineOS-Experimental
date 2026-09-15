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

---

- `64c74f6b-d3cd-4625-9b6f-712982256c4f` — USER_INPUT, 2026-08-20 07:57:40
- `91342a07-299f-4de7-b23f-1e072c90fcc3` — OS_QUERY, 2026-08-21 21:52:55
- `5c852365-c5da-4a27-8a9e-e51fc5132dd4` — BRIEFING_LOADED, 2026-08-24 20:21:47
- `a0108949-2037-4d02-8627-91fd8c74e1a0` — USER_INPUT, 2026-09-03 00:59:33

  Four instances of the race in the entry above, found 2026-09-14. Listed
  together because they are one investigation: the signature is identical in
  all four and it is the signature already written up there.

  **What was measured, each one individually.** The breaking row's `prior_hash`
  points at the row TWO back rather than the row immediately above it. The row
  it points at is still present in the table. The three rows involved land
  inside the same second, and their clock readings are inverted against their
  append order — the row above the break carries an EARLIER timestamp than the
  row above that.

  **Why it is not tampering, and this is decidable from the data rather than
  assumed.** A deletion leaves a predecessor that cannot be found. In all four
  the predecessor is two rows away and intact, every event passes its own
  content hash, and there is no interval to have removed anything into: the
  whole cluster occupies one second. Read the other direction, a forger would
  have to remove a row and leave its hash still resolving to a live row, which
  is not a thing removal can produce.

  **Why they are not repaired.** Same reason as above. The races happened.

  **What they cost, and this is the part worth carrying.** The entry above ends
  by calling the underlying race an open design question. These four are its
  answer: it recurred four times in fifteen days across sleep, briefing, session
  checkpoint and user input, so it is not a once-in-June curiosity. It is the
  normal behaviour of two processes appending in the same instant.

## The 2026-08-20 stress block, and why the alarm is still stuck

Walking the entire chain rather than stopping at the first break finds **943
breaks, not one.** 939 of them lie inside a twenty-minute window on 2026-08-20
in which a fuzz harness wrote 8170 events of two throwaway types into the LIVE
store, concurrently. They are all the same race, at volume, and the four above
are its stragglers — the first of them is the junk block's own tail.

They are deliberately NOT listed here, and that is not an omission.

**One id per line is one investigation per line.** This file says adding a line
is a claim that you looked. Pasting 939 ids would be 939 false claims of
individual investigation, to buy quiet. The dishonest entry this file warns
about is precisely that, at scale.

So the alarm stays stuck until the exemption mechanism can hold a CLASS with
one investigation behind it — one cause, one record, many instances — and until
the walk stops returning at its first finding. Both are owed. Until then
`divineos verify` reports one event id and the words *the database has been
tampered with*, over 943 breaks that contain no evidence of tampering at all.
