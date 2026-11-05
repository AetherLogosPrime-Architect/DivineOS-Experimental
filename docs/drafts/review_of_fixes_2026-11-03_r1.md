# Review of four repair PRs (#801, #805, #814, #817), round 1, 2026-11-03

What this is: a cold read of four small repairs, each stacked on an original PR. For each I extracted the repair head with `git archive` into a scratch folder, put it first on PYTHONPATH, printed `__file__` to prove the load, and ran the tests myself on the head and (with the head's test copied in) on the base. Severity counts: HIGH 0 everywhere; see each section.

Scratch folders (left in place): `C:\Users\aethe\AppData\Local\Temp\claude\C--DIVINE-OS-DivineOS-Experimental-Aria-new\39b9b1cd-4400-4356-81c3-a4a46accb33f\scratchpad\` holds `h801 b801 h805 b805 h814 b814 h817 b817` (head / base trees), `mut805_m1..m4` (mutated doorbell scripts), `p817.py` (selector probe).

Environment note: Windows, Git bash at `C:\Program Files\Git\bin\bash.exe`, plain `bash` is WSL. In the extracted trees `git rev-parse` needs a repo, so I ran `git init` in `h814` and `b814`; without it three of #814's tests fail for a reason that is my extraction, not the repair.

## #801 (docstring in enforcement.py, for #762) -- 0 high, 1 medium, 1 low

Tests: 3 pass on head; the new docstring-pin test fails on the base (as expected, it checks prose). REPRODUCED.

1. MEDIUM, `src/divineos/core/enforcement.py` docstring of `capture_user_input`: the new sentence says the empty-input early return "is what keeps [EventValidationError] from being raised on no input". Not shown, and the nearby evidence points the other way. I fed `[' ']` (non-empty, invalid): no EventValidationError came out; the invalid content was turned into a `ValueError` ("Invalid event payload", `core/ledger.py:336`) and caught by the `except ValueError` branch. So the early return is not what protects that path; the causal claim is a guess written as fact. REPRODUCED (the whitespace case); the stubbed case where `emit_user_input` really raises EventValidationError does propagate (REPRODUCED), so the "NOT caught" half is true.
2. LOW, same docstring, last bullet: "Logs the caught errors without crashing and returns the input string". The outer `except _ENFORCEMENT_ERRORS` returns `""`, not the input. The old docstring had the same slip; the repair rewrote this block and left it. FROM READING (and visible in the printed source).

Also LOW: the new test pins exact prose ("EventValidationError is NOT caught"), so any reword breaks it while the behaviour is unchanged. That is a docstring-pin by design; fine, but it does not guard behaviour.

Gets right: it reports honestly that behaviour is unchanged and does not decide whether EventValidationError should be caught.

Not checked: whether any caller relies on EventValidationError escaping.

## #805 (doorbell test for a folder with a space, for #763) -- 0 high, 1 medium, 1 low

Tests: 4 of 4 pass on head (25.9 s). The base file (plain `bash`) fails all 4 here, because plain `bash` is WSL on this machine; that is the thing the repair fixes. REPRODUCED.

Mutation probes on the head test, one change at a time to `scripts/letter_doorbell.sh` (copies, never the repo):
- `(cd $REPO && ...)` unquoted at line 177: new space test FAILS. REPRODUCED.
- `REPO="$(cd $(dirname ...)/.. && pwd)"` unquoted at line 175: new space test FAILS. REPRODUCED.
- unquote the trailing `"$REPO"` argument of the baton call at line 177: the new test PASSES (1 passed). REPRODUCED gap.
- remove `cd "$REPO" &&` entirely: that run did not finish in my session, so NOT CHECKED.

1. MEDIUM, `tests/test_the_doorbell_rings_on_a_new_letter.py` stub baton: the stub ignores its arguments, so the quoting of `"$DIR/$f"` and `"$REPO"` as arguments to the baton call (line 177) is not covered; I unquoted `"$REPO"` and the test still passed. Only the `cd` quoting is pinned. The body says the test now "can fail on an unquoted cd", which is true, but the test name and docstring read as if the whole start is pinned. REPRODUCED.
2. LOW, `_ring` timeout path: on POSIX it calls `p.kill()` on the starter only, so the sleeping bell child keeps running and holding the pipe; the drain thread is a daemon and `join(timeout=10)` bounds it, so tests do not hang, but each deliberate timeout now costs up to 10 s extra and leaves an orphan poller. The old `subprocess.run(timeout=...)` also left the grandchild on POSIX, so it is not a regression, only a cost. FROM READING (Windows path uses `taskkill /T` and I saw no hang).

Gets right: it noticed the original assertion could not fail (the unquoted `cd` gives "too many arguments", not "No such file"), and fixed the test so it can.

Could not check: Linux and macOS. The claim that the old assertion still passed under the unquoted `cd` I could not confirm directly, because the old test fails here for the WSL reason before it gets that far; the message difference is standard bash behaviour.

## #814 (push gate says could-not-check, for #765; guardrail-class) -- 0 high, 1 medium, 2 low

Tests: 15 pass on head (with a git repo in the folder). Head tests on base: 5 fail (drive-letter PYTHONPATH, cause field, advice by cause, and also both exit-11 parametrized cases). REPRODUCED. The classifier run by file path handles runner-missing, nothing-collected, FAILED-line, mixed log (FAILED wins) and empty log correctly in my own logs. A missing log file exits 1 and the shell falls back to `failed 10 classifier_unavailable ...`. No stdlib-named module in `src/divineos/core/` can shadow the stdlib when the file's folder is put first on sys.path (checked against `sys.stdlib_module_names`). REPRODUCED.

1. MEDIUM, `scripts/check_push_readiness.sh` line 767 (and 608, 810): the suite runner itself is still started with `PYTHONPATH="$PYTEST_WORKTREE/src${PYTHONPATH:+:$PYTHONPATH}"`. With a drive-letter PYTHONPATH under Git bash I reproduced the mangled value (`...\src:C:\nonexistent_a` as one entry, then `D:\nonexistent_b`): the worktree's `src` is no longer a clean first entry. The body calls these "outside this finding", but they are the same defect one step upstream, and this repair makes it worse in one respect: when the runner then fails to import `divineos.core.subprocess_jobs`, the classifier now prints `runner_missing` and the gate tells the pusher to "bring the branch up to date with main", which would be wrong advice for a path-join cause. The mangling is REPRODUCED; that it surfaces as runner_missing is FROM READING.
2. LOW, `tests/test_the_push_gate_says_could_not_check.py`: the new `_BASH` hardcodes two Git install paths. Elsewhere the same list is copied (also in the #805 test). Harmless, but a third copy.
3. LOW, claim in body: "the exit-11 'no tests ran' pin passes on both". On the base with my shell's own drive-letter PYTHONPATH set it fails, because the base classifier call is the thing the drive-letter path breaks. With PYTHONPATH unset it plausibly passes, so the claim holds only conditionally. REPRODUCED for the conditional.

Gets right: running the stdlib-only classifier by file path removes the join entirely instead of swapping the separator, and the cause field means other causes stop getting the wrong advice.

Review flag: this edits the push gate, so it needs the merge-gate review round named in CLAUDE.md before reaching main.

## #817 (`divineos running`, for #764) -- 0 high, 1 medium, 1 low

Tests: 13 pass on head; 2 of the new tests fail on the base (decoys, live CLI) exactly as the body says; `check_doc_counts.py` passes on head and prints `UNDOCUMENTED: core/running_processes.py` on base. REPRODUCED. The live test's controls are asserted alive before the read, which is the right shape.

I ran 30 command lines of my own through `_runs_divineos_or_pytest`. Right: `python -m pytest`, venv python with spaces in the path, `python3.13 -u -m divineos.cli`, `python -X dev -m pytest`, `py -3 -m pytest`, the Windows launcher shape, `grep`/`pip`/`node`/`vim divineos.py`/`python x.py divineos`, `python -m pip install pytest`.

1. MEDIUM, `src/divineos/core/running_processes.py` `_PATH`: the allowance for spaces in the program path lets any command whose last argument is a path ending in `/divineos` or `/pytest` count as ours. These matched (all REPRODUCED): `/usr/bin/cat /var/log/divineos`, `C:\Windows\explorer.exe C:\Users\me\divineos`, `/usr/bin/vim /home/u/pytest`, `/usr/bin/cp /src/pytest /dst/`, `C:\Program Files\Microsoft VS Code\Code.exe c:\work\divineos`. An editor or file manager open on a folder called `divineos` is a realistic decoy. The body only discloses the `ssh host /usr/bin/pytest` form; this is the same hole in a more common shape.
2. LOW, same function: `python -c divineos` matches (the `-c` argument is read as a script name). Missed on the other side: pytest-xdist worker processes (`python -c "import sys;exec(...)"`), `uv run pytest`, `poetry run pytest`, `python -m cProfile -m pytest`. These are false negatives; whether the roll call should list them is a product call. FROM the probe output.

Gets right: it replaces a word-anywhere match with "the program is the thing", and the live two-child test is a real control, not a mock.

Could not check: macOS/Linux process tables; only Windows was exercised.

## Summary of counts

| PR | high | medium | low |
|----|------|--------|-----|
| #801 | 0 | 1 | 2 |
| #805 | 0 | 1 | 1 |
| #814 | 0 | 1 | 2 |
| #817 | 0 | 1 | 1 |

No repair is broken. Each fixes what it says; the mediums are gaps next to the fix, not regressions.
