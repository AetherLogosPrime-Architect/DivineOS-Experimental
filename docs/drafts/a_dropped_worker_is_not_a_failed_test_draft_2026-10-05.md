# A dropped worker is not a failed test — draft, 2026-10-05

**Aether.** Station one: the idea. Walk next, then build.

## His words

Andrew 2026-10-05, after a push was refused for a test that passes on its own:
*"yes we should fix the dropped worker issue regardless"*.

## What happened

The push for #585 (b4d3271df) ran 15,001 tests with two workers on a machine
with 6.1 GB free. One worker died mid-run (`[gw1] node down: Not properly
terminated`), and pytest marked the test it held as failed:
`worker 'gw1' crashed while running 'tests/test_min...'` and
`FAILED tests/test_mini_save.py::TestMiniSessionSave::test_no_session_files_returns_error`.
Alone, `tests/test_mini_save.py` passes 8 of 8. `check_push_readiness.sh` reads
only pytest's exit code (line ~642), so a crashed worker and a broken test give
the same verdict: BLOCKED, exit 10.

Second time in two days (draft `heavy_work_waits_while_a_push_runs`: a worker
crashed while `divineos learn` loaded the embedder beside a push).

## What already exists (searched)

- `check_push_readiness.sh` scales workers to free memory (2 instead of 16).
  That lowers the odds of a crash but doesn't change the verdict when one happens.
- The failure extractor greps FAILED/Timeout/Killed and has no "crashed worker" case.
- The heavy-work draft (10-04) covers not crowding a push. It doesn't cover a crash
  that happens anyway.

## The shape

When pytest exits non-zero **and** the log carries `crashed while running`:
1. Take the FAILED test ids. Each must be accounted for by a crash line, matched
   by prefix, because the crash line is cut short. If any FAILED test was not
   on a crashed worker, block as now: a real failure is never retried away.
2. Re-run exactly those tests, alone, serially, in the same isolated worktree
   *before* it's removed.
3. If they pass alone: the push proceeds, and the log says so loudly:
   "worker gw1 crashed; its test re-ran alone and passed". The crash is
   counted, so a rising rate is visible.
4. If they fail alone: block, as a real failure.

## From walk-3d234701aed3 (2026-10-05, eight lenses) — this supersedes the matching step above

- **Match by junit, not by the log line (Schneier, Dijkstra).** The first draft said to match crash victims by prefix because the log's crash line is cut short. That was wrong: a prefix can match the wrong test. Run pytest with `--junitxml`; the record carries the full node id and a message beginning `worker 'gwN' crashed while running`. Parse it into two sets: assertion failures, and crash victims. No policy in the parser.
- **One-line verdict (Dijkstra).** Pass if there are no assertion failures and every crash victim passed alone, serially, in the same isolated worktree. Anything else blocks as today. A failure that merely shares a run with a crash is NOT a crash victim and still blocks.
- **A ceiling (Kahneman).** More than a few crash victims in one run, or any other red alongside, blocks outright: a pile of crashes is a fact about the machine and not noise to retry past.
- **Loud and counted (Kahneman, Dekker, Deming).** The push says plainly which worker crashed, which test it held, that it passed alone, and how many times this has happened lately; the count is kept so a rising rate shows in the briefing. Rising means change the system (fewer workers, a higher memory floor), not the verdict.
- **Do not believe the cause (Feynman).** Memory is a story: 6.1 GB was free. Record free memory and worker count at crash time so the cause can be measured later.
- **Pre-register it (Yudkowsky).** Falsifier: if a retry-pass ever precedes a regression that reaches main, the rule is wrong and comes out.
- **Tests that must exist, and break on purpose (Schneier).** A fabricated junit file for each: crash victim passes alone (allow); crash victim fails alone (block); real failure beside a crash (block); a test that kills its own process (block, it dies alone too); missing junit file (block).

## Not covered, named

- A test that only fails *because* of parallel load is masked when it passes
  alone. That's the honest cost. The count of crash-retries is the watch on it.
- The tests a crashed worker never got to (queued behind the one it held) are
  re-dispatched by xdist to a replacement worker. That's pytest's behaviour,
  not ours.

## Since the build (2026-10-06) — what changed the plan

- **Aria's cold read found two holes** and Aletheia read both fixes: a real failure that merely QUOTES a crash line, and a hostile id handed to pytest as an option. Closed, with tests that failed first.
- **I over-tightened one of Aria's rules and the real record corrected me.** xdist writes `failed on setup with "worker 'gw10' crashed ..."` as the MESSAGE and the bare crash line as the BODY. The rule is now: the body must be exactly the crash line. I found it only by feeding a real junit file to the real script, which is the thing the first build skipped.
- **A repeat-crasher line** (Aria's count: one test killed a worker in 5 of 11 full runs) prints how many of the last 8 recoveries named the same test.
- **A crash-recovered push also exposed a test that failed on a clean main** (it depended on which notes I had opened); isolated in the same PR.
- **Aletheia's hardening, added here:** a run that GIVES UP early (xdist "maximum crashed workers reached") leaves tests absent from the record, and absences are not failures. The recovery now refuses when the run's log says so, and when a log is named but cannot be read.
- The draft file was written before the code on 2026-10-05; this section was added on 2026-10-06 for the readiness board and to keep the record honest about what moved.
