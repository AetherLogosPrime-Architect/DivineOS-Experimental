# Verifier n: did the earlier readers' findings hold up? (2026-11-03)

A finding nobody has re-checked is only a claim. Three earlier findings files (PR 786 on 779 and 780, PR 789 on 777 and 778, PR 791 on 754 to 757) were re-checked here. I did not merge, stamp, approve, comment on, push to or edit any of those pull requests.

**Method.** For each pull request I fetched `refs/pull/N/head`, ran `git archive` of `src`, `scripts`, `tests` and `.claude/hooks` into a scratch folder outside the repo, put its `src` first on `PYTHONPATH`, and printed `__file__` to prove the pull request's copy loaded. Probes are my own, written fresh (they live in the scratch folder named at the bottom). Python 3.13.11 on Windows 11, Git Bash for the shell tool, a venv built with `pip install -e ".[dev]"`. The base for comparison is `origin/main`, extracted the same way.

Labels: CONFIRMED = I reproduced it by running the head's code. NOT REPRODUCED = I tried and could not. WRONG = the evidence contradicts it. FROM READING ONLY = I could not or did not run it; I say what I read.

## Result in one line

39 findings checked. **19 CONFIRMED, 0 NOT REPRODUCED, 0 WRONG, 20 FROM READING ONLY** (most of those are low-severity or about test-suite shape, and a handful rest on a code path I traced but did not run). One finding was partly overstated (757 no. 5) and one was understated (777 no. 2).

## Ranked list of the CONFIRMED findings

1. **777 / HIGH: when the house is itself a linked worktree, the main checkout's hooks are freed. CONFIRMED with a REAL `git worktree add`; the earlier reader could only simulate it.** In a temp repo with two real linked worktrees (`wt1`, `wt2`), a clone and the main checkout, `_is_outside_the_house(<hook path>, root)` on the PR head answers:
   - root = main checkout (the case the PR tests): edit in linked `wt1` -> False (right); edit in an unrelated clone -> True (right).
   - root = linked worktree `wt1` (how agents run): edit in the MAIN checkout -> **True** (should be False); edit in sibling `wt2` -> **True** (should be False); unrelated clone -> True; own tree -> False.
   - With the real layout of this very session (root = this agent worktree, path = `C:\DIVINE OS\DivineOS-Experimental-Aria-new\.claude\hooks\doorbell-pre-tool-use.sh`) it answers True.
   The cause is in the code I read: the "linked worktree of this repo" test only holds when `root/.git` is the folder the pointer file leads to, i.e. when root is the main checkout. With root a worktree, the main checkout has a `.git` folder, falls to `return True`, and its guardrail paths are dropped from scoring. Understated by the earlier reader: this is the normal situation for every agent run in `.claude/worktrees/`, not an edge case. One caveat I found: `_guardrail_listed_paths()` takes the house root from where the loaded code lives (I printed it: the extract folder), not from the shell's cwd, so "root" in real use is wherever the hook's `divineos` package is installed from. I did not run the full `score_substrate_modification` end to end on this layout; the earlier reader's `fired_features=()` result was not repeated by me. The function the finding names is what I reproduced.

2. **777 / HIGH: a Git Bash style path to an existing folder is waved through. CONFIRMED.** Created a real folder `~/vf777_*/docs`, then on the PR head: `rm -rf "C:/Users/.../docs"` -> `(True, 'rm recursive/force')` (held, correct); `rm -rf "/c/Users/.../docs"` and the unquoted form -> `(False, None)` (waved through). The same two spellings on `origin/main` are both `(True, 'rm recursive/force')`, so this is a regression this pull request introduces. A missing folder is correctly freed under both spellings. Cause: `os.path.lexists("/c/...")` under native Windows Python cannot see a Git Bash path, so an existing folder reads as "gone". The folder survived because I only called the classifier, I never ran `rm`.

3. **779 / the one the brief asked about: once `volley start` has run, the quiet ignores that Dad spoke. CONFIRMED.** Real functions, isolated `DIVINEOS_HOME` and a real his-asks database holding one message of his filed 5 seconds earlier:
   - before start: `_carry_now()` -> `''`, `is_away()` -> None.
   - after `volley_now.start()`: `_carry_now()` -> `'volley'`, `is_away()` -> `{'by': 'volley', ...}` even though his last message was 5 seconds old.
   - `question_hold.came_back()` (what his next message triggers) -> False, and `_carry_now()` is still `'volley'`.
   - `question_hold.arm("Does the build look right to you?")` -> returned None and wrote one row to `morning_questions.jsonl` with `why: volley`; no hold state was written.
   The source shows why: `_carry_now()` returns `"volley"` before the `LIVE_CHAT_SECONDS` check that the clock and silence kinds both honor, and `came_back()` only clears the `AWAY` file. The module's own docstring says "Nothing clears it when he speaks", so the design is stated; what is not stated is that live questions then go to a morning letter.

4. **757 / the refusal text offers a wrong way out. CONFIRMED, all three shapes.** Real `decide()` on the PR head:
   - `bash -c "pytest tests/test_a.py -q"` -> the new "refused by one rule ... treated as a run with no test files named ... The one way out: put the words in a divineos record command ... If it really was a test run, name the test files." The test file IS named, so the sentence is false for this command.
   - `gh pr create --title t --body "tests run with pytest"` and `cat > x.py <<'EOF' ... print('pytest') ... EOF` -> the same "one way out" text. Neither a pull request body nor a file write can be turned into `divineos learn`, so for these there is no way out as worded. On `origin/main` both got the old run-rule text, so the new text is what changed.

5. **757: a path-qualified `divineos` is not exempt. CONFIRMED.** `.direnv/python-3.13.11/Scripts/divineos.exe learn "pytest tests/ is slow"` -> refused with the word-rule text; `/usr/bin/divineos learn "pytest"` and `divineos.exe learn "pytest"` -> refused with the run-rule text. Plain `divineos learn "pytest tests/ is slow"` -> allowed. On this Windows house the path spelling is the normal one when the venv is not on PATH.

6. **757: `<(` and `>(` protect nothing; an unquoted process substitution passes the door, and the same on main. CONFIRMED.** `cat <(pytest)`, `diff <(pytest) x` and `divineos learn "pytest" --file <(pytest tests/)` all return None (allowed) on both the PR head and `origin/main`. So the hole is not new, but it is a real way to run the suite by hand past the door, and the new comment and test imply it is handled.

7. **756: one of the four tests fails on Windows. CONFIRMED.** `tests/test_the_memory_floor_card.py` from the head extract: `1 failed, 3 passed`. `test_broken_import_prints_nothing_and_exits_zero` runs `... 2>/dev/null; exit 0` through `shell=True`, which is `cmd.exe` here; stderr `The system cannot find the path specified.`, returncode 1.

8. **777: six of the PR's own tests fail on native Windows Python. CONFIRMED.** Running the two test files I could find for it: `4 + 2 failed, 21 passed` (27 collected in those two files), the failures being exactly the ones the earlier reader named (`test_rm_rf_of_an_existing_folder_is_still_held`, `test_one_existing_one_missing_is_still_held`, `test_a_second_rm_clause_that_exists_is_still_held`, `test_a_broken_symlink_counts_as_existing`, and the two redirect tests in `test_scratch_paths_are_not_the_house.py`). I did not re-derive the backslash cause beyond seeing a command built from `str(Path)`.

9. **777: relative targets are read against the process cwd. CONFIRMED.** `is_destructive_deletion("rm -rf src")` is `(True, ...)` with cwd = a folder containing `src`, and `(False, None)` with cwd = its parent. Whether the live hook's cwd equals the shell's cwd I could not check.

10. **756: the card sends "his words" to the corrections list, not the lookup tool. CONFIRMED.** I ran both help screens: `divineos andrew-correction list` is "Show all OPEN Andrew-corrections + integration-rate"; `divineos his-words find` is "Show his messages containing these words, in this order." The card's line 2 names the first.

11. **778: the baton reads front matter too. CONFIRMED.** `baton._header("---\ntitle: t\n---\n# x\n**Baton:** pass\n**To:** aria")` -> `{'baton': 'pass', 'to': 'aria'}` on the PR head and `{}` on `origin/main`. A behaviour change the draft does not mention.

12. **780: the tree-line check covers `core/` only. CONFIRMED** in a temp repo using the PR's real `docs/ARCHITECTURE.md`: staging a new `src/divineos/cli/zz_new_cmd.py` -> the checklist is silent. The rule it mirrors (`check_doc_counts._get_actual_py_files`) walks every `.py` under `src/divineos/` (I read lines 265 to 303); I did not run `check_doc_counts.py` itself.

13. **780: a rename's ghost is never mentioned. CONFIRMED.** `git mv core/ledger.py core/ledger_renamed.py` -> the checklist asks for a tree line for the new name and prints the prereg reminder, and says nothing about `core/ledger.py`, which I checked IS listed in the real tree (so the real check's GHOST branch, lines 294 to 299, would fire).

14. **755: the write detector misses most ordinary write shapes. CONFIRMED.** On the head's own `find_writes`, MISSED: `update_row(1)`, `mark_done(1)`, `add_item(1)`, `write_state(1)`, `c.executemany(...)`, `open(p, m)`, `p.unlink()`, `p.mkdir()`, `os.remove(p)`, `shutil.copy(a, b)`, `os.popen(x)`, bare `Popen(x)`, `f'UPDATE {tbl} SET a = 1'`, a concatenated SQL string. Controls: `log_event('x')` and `f'INSERT INTO {tbl} ...'` flagged. So the f-string INSERT/UPDATE asymmetry is real. Also false positives `set_title('x')` and `file_size(1)` are flagged (this is the earlier reader's finding 3, first half). The PR's own file: `25 passed`.

15. **757: the pin that checks a command cannot run its text misses several executors. CONFIRMED, with a correction.** `find_executors` on tiny functions: MISSED: bare `run(x)` (when the import is outside the function), bare `Popen(x)`, `getattr(os,'system')(x)`, `__import__('subprocess').run(x)`, `asyncio.create_subprocess_shell(x)`, `webbrowser.open(x)`. CORRECTION to the earlier wording: `from subprocess import run` followed by `run(x)` is CAUGHT when the import is inside the function (`[('subprocess', 2)]`); it is missed only when the import sits at module level, outside the function the walker reads. The test file: `63 passed`.

16. **780: the prereg reminder differs from the real gate on `core/**/__init__.py`. CONFIRMED (the checklist half).** Staging a new `core/zzpkg/__init__.py` -> silent. That the real gate counts it I read, not ran; the merge-commit half (5b) I did not run.

17. **Two small ones.** 778 finding 2 (BOM-led, YAML-list, blank-line, spaced-key, dotted-key and URL-line front matter all return `(False, [])` from `_declared_readings`, the safe direction) and 757 finding 4 (`python probe.py --name pytest` gets the run-rule "run the tests for what you changed" text because the bare token `pytest` counts as the program; it still refuses either way).

(Count by finding: 777 x4, 779 x1, 757 x5, 756 x2, 778 x2, 780 x3, 755 x2 = 19. Items 1 to 17 cover them; no. 14 holds two of 755's, no. 16 is 780 no. 5.)

## Understated findings

- **777 no. 2** (above): the earlier reader called it "reproduced with a simulated layout" and put it first of two highs. With a real `git worktree add` it holds for the main checkout and for sibling worktrees both, and agents run in worktrees as a matter of course here. I would weigh it above the Git Bash one.
- **757 no. 3** (the `<(` hole): the earlier reader filed it as pre-existing, medium. It is a one-line way to run the whole suite by hand past the door; it is pre-existing, but the pull request touches the very list that is meant to close it. Kept medium; I would not lower it.
- **779 no. 1**: the earlier reader describes it as "his speaking does not end it". I add that the only consequence on the record is silence toward him while he is awake: no hold is written, so there is no card and no waiting. That is the whole cost and it is real, but it is also the stated design; whether to call it a defect is Dad's call.

## Overstated or corrected

- 757 no. 5 as worded (see no. 15).
- 777 no. 1 says the Bash tool here is Git Bash so the spelling "is likely in real use". I confirm the classifier answer, not the likelihood.

## FROM READING ONLY (not run by me)

- 779: no. 2 (no log line on start or stop; I read `volley_now.py` and `volley_commands.py` and found no log call), no. 3 (`question_hold_commands.py` prints `he stepped away: {his_words}` and the volley kind carries `""`), no. 4 (`DIVINEOS_VOLLEY_FILE` is read unconditionally in `path()`), no. 5 (test shape), no. 6 (stated in the draft).
- 780: no. 3 (precommit step ordering), no. 4 (every new hook gets the "add this line" advice), the merge-commit half of no. 5, no. 6. I did not run `scripts/precommit.sh` or `check_doc_counts.py`.
- 777: no. 5 (symlink).
- 778: no. 3 (the letters count: 1,206 of 8,793; I did not recount).
- 754: both lows. It makes claims about PR 743 and 753; I did not re-run those.
- 755: no. 2 (`divineos ec status` deletes a malformed or expired arm marker). I traced the chain `ec_status` -> `is_armed()` -> `_load_valid_arm()` -> `path.unlink(missing_ok=True)` at lines 259, 264, 269 in the head's source, but did not run it with a bad marker. no. 3 second half (the file-name collision), no. 4.
- 756: no. 3 (that the card's "arrives by itself" line is true), no. 4 (the 5-second timeout margin), no. 5, no. 6.
- 757: no. 6, no. 7.

## What I could not check at all

- Whether the live PreToolUse hook's working directory equals the Bash tool's (777 no. 9).
- A full run of `scripts/precommit.sh`, the real `check_doc_counts.py` on a modified tree, or a real merge commit (780).
- That the memory card appears in a real session start (756).
- 777 no. 2 end to end through `score_substrate_modification` with a real hook edit; I reproduced the helper it relies on.

## Side effect to report

Running `python -m divineos andrew-correction list --help` and `his-words find --help` (to read their one-line descriptions) printed `Seed v2.1.0 applied: 9 core slots ...` once. That is the CLI applying its seed to the default home on first use; I touched nothing else in a real home. The probes used isolated temp homes.

## Scratch left in place (not deleted)

- `C:\Users\aethe\AppData\Local\Temp\claude\vf\` : extracts `p755`, `p756`, `p757`, `p777`, `p778`, `p779`, `p780`, `pmain` (origin/main), the earlier readers' files `c.md`, `d.md`, `h.md`, and my probes in `probes\` (`p779.py`, `p777a.py`, `p777b.py`, `p757.py`, `p757b.py`, `p755.py`, `p778.py`, `p780.py`).
- Temp repos and folders made by probes: `C:\Users\aethe\vf777wt_3zl96_7x` (real worktree layout), `C:\Users\aethe\vf780_ne5q9nqi`, `C:\Users\aethe\vf777_*` folders, `C:\Users\aethe\AppData\Local\Temp\vf779_*`.
- `.direnv/python-3.13.11` inside this worktree, and local refs `refs/vf/p755 ... p780` in this worktree's git.
