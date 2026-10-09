# Draft: a guard for the bare-bash slip, written as a test and not wired

*2026-10-09, cloud helper, round ten. A proposal only. It changes no test file and no script, and nothing runs it except whoever runs the test.*

**The idea.** The same slip keeps coming back: a test asks the machine for bash by a plain name and takes whatever it hands back. On Windows that can be a do-nothing stand-in, so the test fails there for a reason that has nothing to do with the code it names. The house already has a proper finder (`tests/_bash_resolver.py`, `bash_executable()`), which tries the shell before trusting it. This draft puts a lookout at the door: a test that reads every test file and says which ones still take the unchecked answer.

**What the test does.** `tests/pile_repro/test_no_bare_bash_start_guard.py` reads the syntax of all 974 test files (skipping the archive and the finder itself) and applies two rules.

1. **The literal.** A call whose first argument is a list starting with the plain word `bash` or `sh`, for example `subprocess.run(["bash", script])`.
2. **The unchecked lookup.** A file that asks `shutil.which("bash")` and then shows none of three signs of care: it imports the house finder, it refuses the stand-in by its folder name `System32` in code (a mention in a comment does not count), or it tries the shell first (a command with `-c` and `echo ok` or `exit 7`).

It has ten passing controls on made-up sources (each rule fires on the slip, each is spared by the safe shape, a comment does not count, and the scan really reads more than 200 files and sees the lookup in at least 20), and one strict expected failure: "no test file does either". It is marked as an expected failure because main breaks it today; when the files are repaired the test passes, and the strict mark rings.

## What it flags on main right now

Run against main at `cbd35baf`: **12 of 974 test files**.

- **Rule 1, the literal: none.** No test file on main starts a shell by a literal `["bash", …]`. The two I found in round nine were in my own drafts #608 and #609, and are repaired in this round.
- **Rule 2, the unchecked lookup: 12 files**, each on the line that asks the lookup:

| File | Line |
|---|---|
| `tests/test_check_branch_freshness.py` | 43 |
| `tests/test_check_cleanup_period_hook.py` | 39 |
| `tests/test_check_push_readiness_failure_surface.py` | 47 |
| `tests/test_ci_check_guardrail_trailer.py` | 41 |
| `tests/test_family_wrapper_required_hook.py` | 50 |
| `tests/test_hooks_import_their_own_checkout.py` | 43 |
| `tests/test_hooks_run_in_worktrees.py` | 25 |
| `tests/test_push_gate_substrate_scope.py` | 47 |
| `tests/test_push_gate_tag_only.py` | 69 |
| `tests/test_remedy_allowlist.py` | 290 |
| `tests/test_stragglers_coverage.py` | 97 |
| `tests/test_the_doorbell_rings_on_a_new_letter.py` | 20 |

Eleven of these are the "dangerous" ones in the round-ten table (`docs/pile_sorting/output/round10/shutil_which_bash_on_main.md` on the notes branch). The twelfth, `test_check_cleanup_period_hook.py`, is a **false flag**: I read it as safe, because on Windows it only looks in two Git folders and never reaches the lookup. The guard cannot see that, since it shows none of the three signs. I left it visible and did not add a list of excused files, because a list of excused files is a new place for the slip to hide.

## What it cannot see

- A finder reached through an import under another name.
- A shell started inside a command string (`bash script.sh` typed as text for another shell). One such case is in `test_the_doorbell_rings_on_a_new_letter.py` line 37.
- A probe that only looks like one.
- It reads syntax; it does not run anything, and it has not been run on Windows.
- Seven other files try the shell and then **fail loudly** instead of skipping when there is no real bash. That is a deliberate choice by their authors, and the guard does not touch it.

## What it does not do

It is not wired into the suite, the push check or any hook. It changes no test file. Whether to wire it, loosen it, or repair the twelve files first is for the owners.
