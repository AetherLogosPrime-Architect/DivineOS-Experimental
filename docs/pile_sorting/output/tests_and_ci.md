# The tests and the checks that run them

The test suite is the house's smoke detector for its own wiring. It is slow, it sometimes tests the wrong thing, a few old tests reach into my real home folder and knock over the doorbell during a push, and heavy jobs crash each other when run side by side.

**30 notes in this theme, grouped into 8 distinct problems.**

## Distinct problems

### 1. Making the suite faster without losing safeguards

Notes in this problem (1):

- `psf-e0d5d443` (learn) — Aletheia 2026-05-18 named three follow-up obligations from the test-suite optimization consult that should build out before/alongside any pytest-xdist rollout: (1) BUDGET-AS-ARCHITECTURE — named push-

**Proposed fix:** Build the budget-as-architecture and parallel-run follow-ups Aletheia named before turning on parallel test runs.

**How we would know:** The suite's time stays inside a stated budget and the follow-ups exist before parallelism is on.

### 2. Real failures called 'flaky', and timeouts that look like failures

Notes in this problem (4):

- `psf-98c83077` (correction) — I labelled a real, reproducible failure 'flaky' and retried the push instead of reading the error. The specific prior action: the pre-push gate reported 1 failed / 10888 passed on split/friction-regis
- `psf-0fced7f9` (correction) — Aether self-correction 2026-08-17: I filed one hypothesis for a flake that had three distinct causes, and generalized it from two instances. WHAT I DID: after two parallel-only test failures I filed c
- `psf-d95a4dd0` (correction) — Andrew 2026-09-01: 'there was an error in the merge'. CI failed on one test that timed out at thirty seconds rather than asserting false. Everything else passed. root cause: two layers. The emit path
- `psf-6ca68db0` (reflection) — that test shouldn't need to load the heavy library at all, or it should get a time limit that fits it.

**Proposed fix:** Never label a failure flaky without reading the error; give slow tests a time limit that fits or avoid loading the heavy library.

**How we would know:** A timeout names the test and the reason in the output.

### 3. Tests that assert the wrong thing

Notes in this problem (3):

- `psf-c4f859b3` (correction) — My first test for the anchor case-fix asserted a rung the harness cannot produce: I wrote tree-exact for a helper that varies the patch value, not the tree. root cause: I wrote the assertion from memo
- `psf-60feab54` (reflection) — every part of a gate should have at least one test that fails when that part is removed, so an untested gate shows up on its own.
- `psf-80d9e0c3` (correction) — My letter-safety test asserted a new letter stays on disk after a checkpoint; retarget moves it to the substrate branch by design, so the test asked about location instead of survival. Root cause: I w

**Proposed fix:** Write the assertion from the harness's real output, and require every part of a gate to have a test that fails when that part is removed.

**How we would know:** Remove a part of a gate: at least one test goes red.

### 4. Reading CI status wrongly

Notes in this problem (2):

- `psf-bb56c7d2` (correction) — gh pr checks buckets queued and in-progress jobs together as pending, so a report of CI state built on it cannot tell not-started from running (2026-09-23: told Andrew the 538 tests had not started; t
- `psf-a4def384` (learn) — gh pr checks puts queued and in-progress jobs in the same 'pending' bucket, so it cannot tell not-started from running. 2026-09-23 I told Andrew the runway-meter PR's tests had not started; they had b

**Proposed fix:** Distinguish queued from running when reporting CI, using each run's real status.

**How we would know:** A queued job is reported as not started, a running job as running.

### 5. Tests that touch the real house instead of a pretend copy

Notes in this problem (14):

- `psf-7afb336f` (council) — A worktree index (wt519, code/gate-repairs-on-main) was found holding STAGED copies of .gitignore and README.md matching tests/test_auto_commit.py::_init_repo seed content exactly (5 ignore lines + "s
- `psf-9aa589ac` (reflection) — every test of a counting guard should run against a throwaway copy, never your real store.
- `psf-857c4afe` (reflection) — any test that reads the real transcript folder prints which folders it read and how many files each held, so the first run shows what it is really measuring.
- `psf-dd8e1194` (reflection) — a check that fails any test run that leaves the project folder changed, so the leaking test gets caught by name instead of me tidying up after it.
- `psf-19560539` (reflection) — ** those two old tests read the real home folder instead of a pretend one. #580 archives them, which fixes it for good, but until then any opt-out on this machine makes them fail.
- `psf-ab469b93` (reflection) — those two old tests should get their own pretend home folder, so the opt-out never has to move. #580 removes them entirely once it merges, and until then I'm working from PowerShell during pushes.
- `psf-7afc1328` (reflection) — the push should give those two old tests their own pretend home folder, so the note never has to move. That ends this deadlock for good, and #580 removes the cause entirely.
- `psf-07042725` (reflection) — as named above, those two old tests need their own pretend home folder, so the note never has to move during an upload.
- `psf-0705d5b3` (reflection) — ** the note juggling during uploads, again. Those two old tests need their own pretend home folder. I'll fold that into the one-command work so it stops for good.
- `psf-fde39618` (reflection) — the upload should give those two old tests a pretend home folder, so the note never moves. That ends it, and #580 merging ends it for good.
- `psf-5ce3981c` (reflection) — covered by the same fix.
- `psf-954e4bfa` (reflection) — ** the same fix again, those two old tests needing a pretend home folder, so an upload never has to knock the doorbell over.
- `psf-0bbcbaec` (reflection) — the push should give those two old tests their own pretend home folder, so the note never moves and the doorbell never gets locked out during an upload.
- `psf-bbac2f65` (reflection) — the same pretend-home-folder fix for the two old tests, so the note never moves.

**Proposed fix:** Give every test its own throwaway home folder and fail any run that leaves the project changed; print which folders a test reads and how many files each held.

**How we would know:** A run that writes to the real folder fails by name.

### 6. Heavy jobs run side by side and crash each other

Notes in this problem (2):

- `psf-c6e9b5af` (council) — Heavy jobs on this machine overlap and crash each other: 2026-09-23 the #519 pre-push full suite (-n 8) ran while a precommit (mypy, vulture, shellcheck) ran for a 540 commit in another worktree; two
- `psf-44a86379` (reflection) — ** while an upload's tests are running, I shouldn't make workbenches or touch the house's settings. The one-command merge should run each upload by itself.

**Proposed fix:** Run each upload by itself and do not make workbenches or touch settings while a suite is running.

**How we would know:** Two heavy jobs do not run at once.

### 7. The tests do not run on the same Python version as GitHub

Notes in this problem (1):

- `psf-fa49f002` (reflection) — pre-commit should also run the tests on the same Python version GitHub uses, so a break like this shows up before the push instead of after it.

**Proposed fix:** Run pre-commit tests on the Python version GitHub uses.

**How we would know:** A version-specific break shows up before the push.

### 8. The full-suite detector refuses a single named test file

Notes in this problem (3):

- `psf-520b5ba3` (reflection) — full_suite_by_hand should judge only the command it's given. A pytest naming specific test files is never the full suite, wherever it runs, so the guard should refuse only a bare `pytest` or `pytest t
- `psf-55c61797` (reflection) — the check should tell the difference between a chain of two named targets and a whole-suite run, so a false alarm doesn't make me split work for no reason.
- `psf-28521a67` (reflection) — the full-suite detector should tell a named test file apart from a bare `tests/` run, so a single-file command is not refused.

**Proposed fix:** Judge only the command given: a pytest naming specific files is never the full suite.

**How we would know:** A command naming a test file is not refused.
