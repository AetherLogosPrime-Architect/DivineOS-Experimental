# The full ledger fault run, and the tests it asks for (draft, 2026-10-20)

Aria, 2026-10-20. Dad asked for a way to see which tests are solid. `scripts/mutate_copy.py`
plants small deliberate faults in a disposable copy and records which test notices. This note is
the readout of its first full run on `src/divineos/core/ledger.py`, and the idea for the next batch
of tests. Not a plan; the idea.

## What was run

All 213 faults the tool knows how to plant in ledger.py, one at a time, against 14 test files
(`tests/test_ledger*.py`, the Fable verify tests, the order tests, and three files written earlier
tonight). Untouched tests were green first. Result: 137 caught, 75 missed, 1 errored (65% of the
214 that gave an answer).

**The 65% is a floor.** 125 other test files import the ledger and were not run (the tool now says
so itself), so some misses are caught elsewhere. One "gap" earlier tonight was exactly that.

## What the 75 are

- Log-folder housekeeping and log-level settings (about 17): where logs go, how many old ones are
  cleared. Operational, not about trust. Left.
- Error-message wording and display slices (about 14): `[:12]` vs `[:13]`, `or` inside a message.
  The decision is unchanged. Left.
- Default values of arguments (about 11): 100 rows, 50 results, 20 recent. Real but cheap, and
  covered below.
- The actor-authenticity warning (4): warns only, by design (Phase 1). Left.
- **A wiped ledger (9).** When the ledger is empty but its anchor remembers N events, verify_chain
  reports tail truncation. No test tried an empty ledger with a remembering anchor. Covered below.
- **The main write path's fingerprint (4).** log_event hashes the payload with ensure_ascii=False
  and sort_keys=True; only non-ASCII text and out-of-order keys show a change. Same class as the
  append_on fault fixed earlier. Covered below.
- **The file that excuses recorded chain breaks (1).** `parents[3]` to `parents[4]` and nothing
  noticed; a wrong path would read as "no recorded breaks" and report each as tampering. Covered below.
- Wrappers and read-side defaults (about 14): `Ledger.log_event`, `Ledger.get_events`, the
  recent-context filter. Covered below.
- **Repair-note bookkeeping (6): NOT covered, on purpose.** One note excuses one link; a fork
  should not be excused twice. Tried to build the fork: the row after it fails its own link
  anyway, so these faults are masked by the walk's continuity check. Guarded twice; testing the
  first guard alone needs a forgery that rewrites every later row. Stated as a limit.

## What the words mean (council walk walk-e2b73836ae48)

- **Caught:** a supplied test went red when the fault was planted. It does not mean the test understood anything.
- **Missed:** none of the supplied tests went red. It does not mean the code is wrong.
- **Left alone on purpose:** judged not worth pinning. It does not mean proven harmless. These piles
  are hypotheses (weak test, same-behaviour change, dead code, or caught in a file not run). To
  reopen one, rerun with the unrun importer files added (`--tests` plus the names the tool prints),
  and plant the same fault again after any fix: that second break is the experiment.
- **Contract tests vs integrity tests:** the wiped-ledger alarm, the fingerprint and the
  known-breaks path are integrity tests. The default row counts and the wrapper pass-throughs are
  contract tests: other code leans on them, but they say nothing about trust.
- Read 65% with its floor: 125 files not run, most misses housekeeping or wording.
- Testing shows faults, never their absence. This run says nothing about faults the tool has no
  shape for.

## The tests

One new file, `tests/test_ledger_wipe_and_write_path_defences.py`, for the piles marked covered
above. Each test names the fault that left the earlier tests green. Afterwards the same faults are
planted again; a fix counts only if the second break is caught.

## Limits, written before the run of the new tests

- Sampling: this was every fault the tool can plant, but the tool plants only seven kinds of fault.
  A kind it has no shape for (a dropped statement, a swapped argument order) is invisible to it.
- Equivalent faults cannot be told from weak tests by the machine. Each miss was read by a person.
- One file. The house has hundreds.
