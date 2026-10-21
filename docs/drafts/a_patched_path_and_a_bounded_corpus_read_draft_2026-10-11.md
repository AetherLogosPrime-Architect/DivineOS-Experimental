# A patched path that outlives its test, and a corpus test that outgrew its time limit (draft, 2026-10-11)

**Two failures, one evening, both blocking pushes.**

1. `test_db_path_and_get_connection_agree_under_env_change` failed a full pre-push run and passed alone. Cause: `monkeypatch.setattr` on `_ledger_base.DB_PATH` reads the old value through the module's dynamic lookup and its undo writes it back as a REAL attribute, which hides the lookup for every later test in that worker. It fails only when a patching test and that test meet in one worker in one order, which is why it read as bad luck. Fix: the shared per-test fixture, which tears down after monkeypatch, removes the leftover for every test, present and future. An ordered pair of tests proves it (the first shows the shadow exists while patched, the second fails without the cleanup).

2. `test_the_instrument_finds_him_in_the_real_corpus` called `harvest()`, which reads every transcript on the machine: 4.6 GB here, one file over 1 GB. It passed while the history was small, then outgrew the per-test time limit and killed its worker in 8 of the last 8 push-gate recoveries. The question it asks is whether the probe can find a case it should find, so it now reads the first 25 sayings in each of the newest 6 transcripts, in the harvester's own order, with the assertions unchanged: 0.33 s against the real corpus.

**Why a bounded read and not a longer limit.** The history only grows, so a longer limit is hit again; the cost of a bounded read does not depend on how long we have talked.

**Not in this change.** The CLI's whole-history reader is still a full scan every time it runs. A measurement of each test's duration, so a test trending toward its limit is visible before it kills a worker, is owed.
