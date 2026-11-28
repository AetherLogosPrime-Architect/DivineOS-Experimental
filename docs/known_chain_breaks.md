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

## Written down, not exempted: the 946 forks in Aether's own ledger

This section is prose on purpose. It has no bullet that begins with an event id,
so it excuses nothing: `divineos verify` on Aether's ledger still reads
INTEGRITY: FAIL, and that is true. Listing 946 ids to make it say PASS is a
design decision that is not made here (see "Still open").

**What it is.** On 2026-11-27 the whole real ledger (489,753 rows) was walked
read-only, in append order. Every row recomputes its own chain hash (0 fail) and
none is unchained. 946 rows store a prior hash that is not the hash of the row
just before them. All 946 are forks, none is a gap: in each, the stored parent
exists as another row. The rowids run 1 to 489,753 and the table holds 489,753
rows, so none is missing by sequence. Nothing was deleted, cut or edited.

**Who made it, and when.** 940 are from a 25-second window, 2026-08-20 07:57:14
to 07:57:39 UTC, and are rows of the types `fuzzprobe`, `racenoise` and
`xproc_noise`: bare `python -c` probes that Aether ran against the production
ledger while hunting a test flake. They ran outside pytest, so outside its
isolating fixture, and the cross-process probe made many writers append in the
same instant. Aether named the probes and marked the rows in a letter to
Aletheia the same night, and Dad said the same on 2026-09-08 and 2026-11-27:
the chain was tested, on the real ledger and not on a copy. The first break is
the row 9a47e603-b8fd-4b10-b257-ff67b6ec4b50 (rowid 46591, a `xproc_noise` row),
which names rowid 46589 as its parent while rowid 46590, a `fuzzprobe` row,
names the same one. The other six are ordinary-use races, on 2026-08-21,
2026-08-24, 2026-09-02, 2026-09-22 (twice) and 2026-09-26, with none since.

**Why it is not tampering.** A removal leaves a gap (a stored parent that exists
nowhere). This ledger has no gap. Every mismatch is a fork between rows that are
all still present and all intact.

**Why it must not be repaired.** Re-linking the 946 would rewrite a true record
of a real race, to quiet an instrument that is reading it correctly. Do NOT run
`backfill_chain_hashes` or anything that re-links hashes to "mend" this: it
would erase the evidence, and nothing here needs mending. A read-only copy of the
ledger as found is kept (taken 2026-11-28 00:11:10 UTC, SHA-256
`be001ee800d6e5417844e6e1c418c596eaae46eab8443379666635481376ac36`).

**What this does not prove.** A forged fork would look like a race. The case
rests on the hashes, the contiguous rowids, and the 25-second window of Aether's
own probe types, not on anyone's word. Re-run it: the two read-only scripts are
`ledger_allbreaks_readonly_probe_2026-11-27.txt` and
`ledger_one_break_readonly_probe_2026-11-27.txt` in the shared workbench.

**Still open** (from Aether's letter to Aria of 2026-09-28, awaiting a reply):
1. close the cross-process append race (a lock around the head read and the
   insert, or read the head inside `BEGIN IMMEDIATE` and retry on a change);
2. how a range of 940 is recorded, one range entry with its evidence and not 940
   lines, which is a change to how this file is read;
3. a bare `python -c` must not reach the production ledger silently.
Until these are decided, the check keeps saying FAIL. An alarm that always
cries cannot report real tampering, so this is owed and not optional.
