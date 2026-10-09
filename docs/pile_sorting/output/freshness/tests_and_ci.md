# Is the note still true? The tests and the checks that run them

*Round nine, errand one. 2026-10-09, cloud helper. Read-only: nothing was closed or marked resolved. Evidence is `origin/main` at `cbd35baf` (a scratch copy of it); live probes ran in a scratch home with controls. Verdicts are per group of rows describing the same failure; row text in the pile is cut off at about 200 characters. **NOT TESTABLE** means the note is an incident record, a habit or a lesson that no run can check; it is not the same as UNKNOWN (I looked and could not tell) or NOT EXAMINED (I did not look at that row this round).*

A picture: the smoke detectors of the house. One of them I tripped myself twice last round: it refuses a test command if it cannot read where the shell is standing, which is on purpose, written down with a test, and which contradicts what the old notes ask. Most of the other notes about tests touching the real home folder were answered by a merge that moved the old tests out and a per-test private home folder.

## Problem 1: Making the suite faster without losing safeguards

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-e0d5d443` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 2: Real failures called 'flaky', and timeouts that look like failures

4 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-98c83077`, `psf-0fced7f9`, `psf-d95a4dd0` | **NOT TESTABLE** | An incident record of something I did or said. No run can check it. | none |  |
| `psf-6ca68db0` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 3: Tests that assert the wrong thing

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c4f859b3`, `psf-80d9e0c3` | **NOT TESTABLE** | An incident record of something I did or said. No run can check it. | none |  |
| `psf-60feab54` | **LIVE** | The tool that asks 'does this test fail when the code it names is removed' is the cut-away checker, and it is **not on main**: `git ls-tree --name-only origin/main scripts/ | grep -c cutaway` → 0 (control: the same listing finds other scripts). It lives on `aria/the-cutaway-checker`, where round seven ran it on ten files. The row asks the question of every part of a *gate*; the checker asks it of every test. | `tests/test_cutaway.py` (on the branch) | Not a defect in the checker; a gap on main until it lands. |

## Problem 4: Reading CI status wrongly

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-bb56c7d2`, `psf-a4def384` | **LIVE** | `src/divineos/cli/ship_command.py:83` decides 'waiting' with `state in ("", "PENDING", "QUEUED", "IN_PROGRESS", "EXPECTED")`: queued and running are one state, the thing the rows complain `gh pr checks` does. (Control: the same line separates 'waiting' from 'failed'.) | `tests/test_ship_command.py` | A read of one line; I did not look for a second reporter elsewhere. |

## Problem 5: Tests that touch the real house instead of a pretend copy

14 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-dd8e1194` | **LIVE** | `grep -rln 'git status --porcelain|leaves the project|tree_unchanged|left the working tree' tests/conftest.py scripts/precommit.sh scripts/check_push_readiness.sh` → no file. Control: `tests/conftest.py:142-178` is read by the same grep and does isolate `DIVINEOS_HOME` per test, so the search reaches the file. | none | A name search; a check under another name would be missed. |
| `psf-19560539`, `psf-ab469b93`, `psf-7afc1328`, `psf-07042725`, `psf-0705d5b3`, `psf-fde39618`, `psf-5ce3981c`, `psf-954e4bfa`, `psf-0bbcbaec`, `psf-bbac2f65` | **STALE** | #580 is on main: `4bb72cd8 Retire the letter watch: the doorbell is the one listener (#580)`. `git show --stat` shows five letter-watch test files moved to `archive/superseded/tests/` (`test_letter_announced_record`, `test_letter_monitor_health_verdicts`, `test_letter_monitor_singleton`, `test_monitor_orphan_checkout_roots`, `test_monitor_singleton`). Also, `tests/conftest.py:142-178` gives every test its own `DIVINEOS_HOME` folder. | the whole suite no longer collects the moved files | The rows do not name the 'two old tests' in the part the pile keeps; I assume they are among the five moved and did not confirm which two read the real home folder. |
| `psf-7afb336f`, `psf-9aa589ac`, `psf-857c4afe` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 6: Heavy jobs run side by side and crash each other

2 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-c6e9b5af` | **LIVE** | Half met. `scripts/check_push_readiness.sh:433-469` refuses to start the suite when free memory is low (the comment gives a 16 GB threshold and a memory-scaled worker count). That is a guard against overload, not a lock between two heavy jobs: nothing there stops a precommit and a pre-push suite from starting together when memory is high. | none for a lock | I read the lines that print the refusal, not the whole 500-line script. |
| `psf-44a86379` | **NOT EXAMINED** | I did not look at these rows this round. | none | I did not look at these rows this round. |

## Problem 7: The tests do not run on the same Python version as GitHub

1 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-fa49f002` | **LIVE** | `.github/workflows/tests.yml:29` runs the tests on `python-version: ["3.12"]` only. This machine runs Python 3.13.16 (`python3 --version`; the cached files under `src` are `cpython-313`). `grep -n 'python3\.|PYTHON_VERSION|3\.1[0-9]' scripts/precommit.sh` → no match, so the pre-commit run does not check for the version CI uses. (Control: the same grep style finds the version lines in `tests.yml`.) | none | I did not read the whole pre-commit script for an implicit check. |

## Problem 8: The full-suite detector refuses a single named test file

3 rows.

| Rows | Verdict | Evidence (so a second reader can sample it) | Standing test | What the evidence does not show |
|---|---|---|---|---|
| `psf-520b5ba3`, `psf-55c61797`, `psf-28521a67` | **LIVE** | `src/divineos/core/full_suite_by_hand.decide` on main: controls behave (`pytest tests/ -q` refused; `pytest tests/test_hook_layer.py` allowed; three named files allowed; absolute paths with `--rootdir` allowed). But the exact command I met twice in round eight, `S=<folder> && cd $S/wt_main && python3 -m pytest <three named test files> -q …`, is **refused** ('THE FULL SUITE IS THE PUSH'S JOB'); with the folder written out literally instead of `$S` it is allowed. **This is by design, not an oversight:** `tests/test_full_suite_by_hand.py` (97 passed) lists `cd $SOMEWHERE && pytest tests/test_a.py` among the refused forms, because the check cannot see where an unreadable `cd` lands (Aria's three, 2026-10-04). So the notes' wish ('a named file is never the suite, wherever it runs') is not met, and the refusal is intended. | `tests/test_full_suite_by_hand.py` (pins the refusal) | Whether the design should change is the owners' decision; the notes and the test disagree. |

