# Second reader J: findings on 762, 763, 764, 765

A cold read by a reader outside the house, 2026-11-03. I did not merge, stamp, confirm, approve or comment on any of the four PRs. Main was `6de941c54` when I read. Each PR head was extracted with `git archive` into a scratch folder outside the repo and put first on `PYTHONPATH`; every probe printed `__file__` to show the head was what loaded. Findings say "reproduced" when I ran the real code, "from reading" otherwise. Where a scratch folder was a tarball export I note it.

Severity scale: **medium** = would be wrong or noisy in ordinary use, or would fail a gate; **low** = real but small or edge. No high findings in this batch.

| PR | high | medium | low |
|---|---|---|---|
| 762 | 0 | 0 | 1 |
| 763 | 0 | 1 | 2 |
| 764 | 0 | 2 | 3 |
| 765 | 0 | 1 | 4 |

---

## PR 762: the command root starts in a fresh home

**Head:** `5402927584eda6c2a25024826c4e2f0337e51e1d`. **Read:** whole diff (3 files), `capture_user_input` and `_ENFORCEMENT_ERRORS` in `core/enforcement.py`, the caller at `cli/__init__.py:316-317`, `emit_user_input` and both `EventValidationError` classes (`event/event_capture.py:52`, `event/event_validation.py:11`).

**Does it do what the title says?** Yes. The title is "starts in a fresh home"; the cause is an empty `sys.argv[1:]`, which is what the body says. The title undersells that, but the body is accurate.
**Duplicates main?** No. Main has no early return there.

**Tests at the head:** `tests/test_command_root_starts_in_fresh_home.py` + `tests/test_error_handling.py`: 30 passed.
**Does the fix matter (reproduced against main's src):** `capture_user_input([])` on main emits `['']` and `cli(['verify'], standalone_mode=False)` in a blank home raises `EventValidationError: content cannot be empty` (exit 1). At the head the same call returns `''`, emits nothing, and `verify` runs. The subprocess test fails against main's src for the right reason (I pointed the subprocess `PYTHONPATH` at main and it returned code 1 with that traceback).

### Findings

1. **low. The reason the crash happens is left in place.** `enforcement.py:153-163` still catches only `ValueError` and `_ENFORCEMENT_ERRORS` around `emit_user_input`, and `EventValidationError` derives from `Exception`, so any other validation failure from that call (the 1 MB branch, session id or timestamp) would still crash the command root, while the function's docstring still says it "catches validation errors". The early return removes the one input that reaches it today (reproduced: `[""]` and `[]` return `''`; `[" "]` still emits `' '`, which the validator accepts). Two classes with the same name exist (`event_capture.py:52`, `event_validation.py:11`), which is how the catch could have been missed. Not wrong, just a smaller fix than the title of the problem.

### Could not check
- The whole suite (I ran only the two files above).
- Behaviour with a real non-blank home, since the briefing gate blocks the CLI in my worktree.

### One thing it gets right
It writes the test to defeat the thing that hid the bug: pytest being in `sys.modules` skips the capture step, so the test starts the real root in a subprocess with `PYTEST*` removed from the environment. I confirmed it fails on main.

---

## PR 763: the doorbell tests run in a folder with a space in its name

**Head:** `dfda974bc761284b33a1e7b7d8af944c165af43b`. **Read:** diff (2 files), `scripts/letter_doorbell.sh` (whole), the existing `tests/test_the_doorbell_rings_on_a_new_letter.py`.

**Does it do what the title says?** The title reads like a fix, the body says the failure did not reproduce and this is a pin only. Honest in the body, a little misleading in the title.
**Duplicates main?** No. But **#776** (open) also edits `tests/test_the_doorbell_rings_on_a_new_letter.py` (and `scripts/letter_doorbell.sh`), so the two will touch the same file.

**Tests at the head:** the file's four tests pass (4 passed in 22 s; the new one takes 2.6 s).

### Findings

1. **medium. The new test does not catch the regression it exists to catch. Reproduced.** The only place the bell uses its own path is line 175: `REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"`. I removed the quotes there in the head's `scripts/letter_doorbell.sh` (`cd $(dirname ${BASH_SOURCE[0]})/..`) and re-ran: the new test still **passes**. With the unquoted line the bell prints `.../a b/scripts/letter_doorbell.sh: line 175: cd: too many arguments`, and the test only asserts that `No such file or directory` is absent and `LETTER ARRIVED` is present. Bash's real message is "too many arguments", so the first assertion cannot fire on this failure. The test's docstring promises that an unquoted path "would make bash report 'No such file or directory'"; the one place that matters reports something else. A sturdier assertion is that the output contains no `: line ` fault text, or that `BATON:` lines carry no shell error.
2. **low. It copies the whole `scripts/` folder (152 files, about 1.5 MB) to prove a one-file point.** `shutil.copytree(BELL.parent, spaced)`. Works, costs 2.6 s, and copies files the bell never reads. Copying just `letter_doorbell.sh` would do, though the BASH_SOURCE parent-dir lookup at line 175 does need `<tmp>/a b/scripts/..` to exist.
3. **low. Collision with #776** (see above). Whichever lands second will need a rebase of that test file.

### Could not check
- Windows, where the original report may have come from. I ran this on Windows with Git Bash, so the space case ran; I did not try other special characters, and the PR says it did not either.
- A scratch folder from my probe was left: `C:\Users\aethe\AppData\Local\Temp\p763_hg9zeiz0` and `...\p763_emrm2cux`.

### One thing it gets right
It says plainly that it could not reproduce the reported failure and refuses to dress a pin test up as a fix; the default of the new `bell` argument leaves every existing caller unchanged.

---

## PR 764: `divineos running`

**Head:** `cd6a17ea539b1d558304221db1ba5b14f2d647e3`. **Read:** diff (5 files), `core/running_processes.py` (whole), `cli/running_commands.py`, the tests, and for overlap `core/ear_sweep/__init__.py:210-230`.

**Does it do what the title says?** Mostly. It lists processes, flags dead parents, and kills nothing (the test on its own source is a real structural guard). "What the OS started" is wider than what it selects: it selects what mentions `divineos`, `pytest` or a `scripts/` path.
**Duplicates main?** Partly. `core/ear_sweep` already finds orphans by the same ancestry test (`_ancestry_is_broken(ppid, live_pids)` over `psutil.process_iter`) for its own watcher processes, and `scripts/push_watcher.py:508` walks the table too. This is a general read-only view over the same idea, not a copy of it, but the PR does not mention the overlap.

**Tests at the head:** `tests/test_divineos_running_lists_what_the_os_started.py`: 11 passed.

### Findings

1. **medium. It fails the repo's own doc-count check. Reproduced.** `python scripts/check_doc_counts.py` at the PR head: `Architecture tree drift: UNDOCUMENTED: cli/running_commands.py ... core/running_processes.py (exists but not in README architecture tree)` and exit 1. The same script on main prints `Doc checks OK`. The PR said it did not confirm this; it fails.
2. **medium. The selector is loose enough that the list is mostly noise on a real machine. Reproduced.** `_names_the_repo` (`:70-76`) accepts any command line containing the bare word `divineos` or `pytest`. With the head's own functions on this machine's live process table (276 processes) it returned 7: Claude Code's own `claude.exe`, four `bash -c source .../shell-snapshots/...` wrappers (the harness's own shells), and two doorbells. Constructed rows show the same: `grep -r divineos /etc`, `tail -f ~/.divineos/logs/a.log` (the home directory `.divineos` matches the word), `ssh host pytest`, `pip install pytest`, `python -m pytest /other/repo/tests` and `bash scripts/deploy.sh` all count as "ours". The PR admits the last of these; it does not mention the others. A list where most of the rows are not what was asked for teaches the reader to skim past the one that matters.
3. **low. The two ORPHAN lines I got may or may not be true, and the tool cannot tell.** It flagged two real `letter_doorbell.sh` processes (parents 54032 and 53436, gone from the table). Per the bell's own comments (lines near 65-75), a Windows parent that "bash can't see" is a known confusing case. The PR says Windows was not exercised; I exercised it and cannot say the flag is right. `ppid in live_pids` also cannot tell a reused pid from the real parent.
4. **low. Access-denied rows get an absurd age.** `read_live_rows` turns a missing `create_time` into `0.0`. Reproduced with a hand-made row: age prints as `20760d20h`. From reading, a real denied row would show the same.
5. **low. The CLI test cannot fail.** `test_the_command_runs_and_prints_a_header` asserts `"running" in output.lower()`, and both the empty message ("Running: nothing here...") and the header contain it. It would pass on a list of the wrong things. (The live-reader control test and the orphan tests are genuine.)

### Could not check
- `divineos running` end to end: the briefing gate blocked the CLI in my worktree, so I called `describe`/`format_report` on the real process table directly instead of through the command.
- Linux behaviour, `psutil` denial for other users' processes, and pid reuse.

### One thing it gets right
It keeps the decision logic on plain rows and proves the live reader can see a process that certainly exists (its own, with the right parent) before trusting an empty list, and `pid 1` is a soft note rather than an alarm.

---

## PR 765: the push gate says could-not-check

**Head:** `5d57c7283dc365f248728a8be635303432289c64`. **Read:** diff (4 files), `scripts/check_push_readiness.sh` (the new function and the region from the isolated-worktree run to `exit 10`), `src/divineos/core/push_gate_verdict.py`, the tests, `.claude/hooks/auto-push-finished-work.sh` and a repo-wide search for anything that reads exit code 10 or the old messages.

**Does it do what the title says?** Yes for the named case (a branch cut before `subprocess_jobs` reached main): reproduced, the real log line `No module named divineos.core.subprocess_jobs` (with and without quotes, and with a Windows `python.exe:` prefix) classifies as could-not-check, exit 11. Real `FAILED`/`ERROR` lines always win.
**Duplicates main?** No such module on main. It builds on the "collected NO tests" branch that exists on main. The cited note (`docs/drafts/push_gate_cannot_check_draft_2026-09-22.md`, "PR 551") is not in main's `docs/drafts`, and #551 is titled "Auto-cycle phase two...", so a reader cannot check that citation from main.
**Guardrail:** the PR says `check_push_readiness.sh` is guardrail-class and needs review; I did not weigh in.

**Tests at the head:** `tests/test_the_push_gate_says_could_not_check.py` + `tests/test_check_push_readiness_failure_surface.py`: with my environment's `PYTHONPATH` set to a Windows path, **one of the new tests failed** (see finding 1); with `PYTHONPATH` unset the function returned the right answer. Three tests in the second file skip ("not in a git repo", since my copy was an export; I `git init`-ed it for the first file).

### Findings

1. **medium. The classifier fails silently when `PYTHONPATH` is already set to a Windows-style path, and the failure reads as a test failure. Reproduced.** `_gate_verdict_for_log` builds `PYTHONPATH="$(git rev-parse --show-toplevel)/src${PYTHONPATH:+:$PYTHONPATH}"` (script, new function). In my shell `PYTHONPATH` held a `C:\...` path; the result was `failed 10` for the runner-missing log and the PR's own test `test_the_script_decides_from_the_log_with_distinct_words_and_exit_codes[...could_not_check-11]` failed. With `PYTHONPATH` unset the same call printed `could_not_check 11`. The cause is probably the `:` join with a drive-letter path (the script's existing worktree line uses the same pattern, so this is not new). It matters because of what comes next: when the classifier cannot run, the function prints `failed 10 the classifier could not run`, but the caller only prints the reason in the could-not-check branch, so the reader gets the old "tests failing ... Do NOT push red" and never learns the new check did not run. That is the exact could-not-look-as-found-a-fault confusion the PR is removing.
2. **low. The advice printed for every could-not-check is the advice for one of the causes.** The new branch always says "Bring the branch up to date with main and push again". That fits a missing runner module. It does not fit "no tests ran" (the case the old branch was written for, where the cause was the checkout landing in a different folder on Windows), nor the empty-log case.
3. **low. A branch that breaks its own import of the runner is told it is not a failure.** `_RUNNER_MISSING` matches the quoted form `No module named 'divineos.core.subprocess_jobs'` anywhere in the log. Reproduced with a log of `ImportError while loading conftest` + that line (no FAILED/ERROR line): `could_not_check 11`. Still blocks, but the label says "NOT a test failure" about a real fault.
4. **low. Two branches of the classifier are unreachable from the isolated run.** The gate writes `[gate-env]` lines into the log first, so an "empty log" cannot happen on that path. The log is only the `python -m subprocess_jobs ... pytest` run, so a missing `suite_slot` (called outside the log, line ~781) can never appear in it. Harmless, but the PR describes both as recognised causes.
5. **low. Exit code 11 and the removed message are not pinned for "no tests ran".** The PR says it changed 10 to 11 for that case; I found no consumer of exit 10 or the old "collected NO tests" text (searched `scripts/`, `tests/`, `.claude/hooks/`, `setup/`), so nothing else breaks, but only the classifier is tested for that log, not the printed result.

### Could not check
- The real pre-push path end to end against an old branch (needs a stale branch and a ten-minute suite).
- That the real Linux CI hits finding 1; this is from a Windows Git Bash shell.
- The questions the PR leaves for a human (block vs allow by destination).

### One thing it gets right
It keeps could-not-check deliberately narrow, makes any real `FAILED`/`ERROR` line win, and leaves anything it does not recognise as a failure; it also pulls the real function out of the real script in the test instead of testing a copy.

---

## Scratch left behind
`C:\Users\aethe\AppData\Local\Temp\claude\C--DIVINE-OS-DivineOS-Experimental-Aria-new\39b9b1cd-4400-4356-81c3-a4a46accb33f\scratchpad\` (heads `h762`, `h763` (its bell script was edited by me to unquote line 175 for the mutation test), `h764`, `h765`, probe scripts) and the two `p763_*` folders under `C:\Users\aethe\AppData\Local\Temp\`. The sealed environment I built is `.direnv\python-3.13.11` in this worktree.
