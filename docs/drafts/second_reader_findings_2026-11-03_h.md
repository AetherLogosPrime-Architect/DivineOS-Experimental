# Second reader h: findings on 754, 755, 756, 757

A cold read of four open pull requests, 2026-11-03, by a reader working from a scratch extract of each head. I did not merge, stamp, confirm, approve, comment on or push to any of the four. "Reproduced" means I ran the PR's real code, extracted with `git archive` into a scratch folder outside the repo and put first on `PYTHONPATH`; each probe printed `__file__` to prove the PR copy loaded (for 755/756/757/743 the printed path was under `C:\Users\aethe\AppData\Local\Temp\sr_h\p<N>\src`). Otherwise the finding says "from reading". Windows 11, Python 3.13.11, a freshly built venv with `pip install -e ".[dev]"`, so pytest was available and I ran the PRs' own tests.

Scratch folders left in place (not deleted): `C:\Users\aethe\AppData\Local\Temp\sr_h\` containing `p743`, `p755`, `p756`, `p757` (extracts) and the probe scripts `probe*.py`; also `.direnv/python-3.13.11` inside my worktree.

---

## PR 754: the previous reader's findings note

**Read:** head `0dcbbe0a76c92c6d7728facbc26314451c1df847`. One new file, `docs/drafts/second_reader_findings_2026-11-02.md`, read whole, plus the PR body.

**Does it do what its title says?** Yes: it is a findings note on 743, 745 and 753 and nothing else. No duplicate on main.

**Findings**

- No serious findings. Nothing under `src/` or any guardrail file is touched.
- Low, checked: I re-ran the note's six checkable claims about PR 743 at 743's head (`7d293d6aca70e8813831e511fad67ab1551fbfba`, the same sha the note names) with the real `find_stamp`. All six reproduced exactly, with the control passing: `'Done.\n\n"Nothing needs your answer."'` returns `''`; the inch-mark case returns `''`; `'**Your call:** none.'` returns `''`; `'Nothing needs your answer, but the cat wants dinner.'` returns `''`; the URL-with-`?` case returns `''`; the plain `'Done.\n\nNothing needs your answer.'` returns the sentence. So the note's 743 findings 1 to 4 are real.
- Low: the note describes 753 at head `9515a24`; the PR's head is now `139f95ce98615d3327ecd88d3705fc73092d9302`. Its 753 findings may or may not still apply; the note does not say it is pinned to a sha that has since moved. I could not fetch the new head into a ref (the fetch printed nothing), so I did not re-check 753.

**Tests:** none to run (docs only).

**Could not check:** the 745 and 753 claims (not re-run; 753's head moved).

**One thing it gets right:** it separates "reproduced against the head" from "from reading" per finding and says plainly that it did not run the test suites.

**Counts:** 0 serious, 0 medium, 2 low.

---

## PR 755: a word that frees a command from the walk can never free a command that writes (pin test)

**Read:** head `cbecaca9e6fc52525097030d310aad99f728418b`. Whole diff: `tests/test_look_list_verbs_never_write.py` (481 lines), `docs/drafts/look_list_verbs_never_write_draft_2026-11-02.md`. Code read: `_LOOK_SUBVERBS` use, `src/divineos/core/emergency_completion.py` around the unlinks, and the CLI files the walker walks.

**Does it do what its title says?** Partly. It pins the 92 commands behind the look words against a list of write shapes, and the list of shapes is narrower than "writes". Not a duplicate: no look-list test exists on main.

**Findings, most serious first**

1. **The write detector misses most ordinary write shapes, and the PR note does not say so for the main ones.** `find_writes` flags only: SQL literals matching `INSERT INTO|UPDATE x SET|DELETE FROM|REPLACE INTO`, `.commit(`, `log_event`/`write_text`/`write_bytes`/`eval`/`exec`, `open(...)` with a literal write mode, `os.system`, any `subprocess`, and calls starting `record_ store_ save_ file_ set_ delete_ append_`. Reproduced against the head's own `find_writes` on small functions:
   - MISSED: `update_row(1)`, `mark_done(1)`, `add_item(1)`, `write_state(1)`; `c.executemany(...)`; `open(p, m)` with a variable mode; `p.unlink()`, `p.mkdir()`, `os.remove(p)`, `shutil.copy(a, b)`; `os.popen(...)`; `from subprocess import run` then `run([...])`; an SQL string built in a variable or concatenated.
   - MISSED and not in the note: an f-string `f'UPDATE {tbl} SET a = 1'` (the f-string's constants are split at `{tbl}`, so the regex never sees `UPDATE ... SET` in one piece), while `f'INSERT INTO {tbl} ...'` IS caught. So the detector treats the two verbs differently.
   - The note's "what it cannot see" lists `mkdir`, `unlink`, `shutil`, `os.rename`, CREATE/DROP, but not the `update_`/`mark_`/`add_`/`write_` prefixes, `executemany`, f-string UPDATE, or `Popen`/`from subprocess import`.
   Severity: medium. The test is a guard that says green when its patterns are absent, and the note's last line ("a green result means no write was found within those limits") is true but the limits are wider than listed.
2. **A wider net over the same 92 commands finds one more real write inside an already-allowed command.** I patched the detector's prefix and name sets in a probe (not in the PR) and re-ran `collect_writes` on all 92 commands. Almost everything new was noise (`str.replace`, lazy `mkdir`, `executescript` for lazy schema). One was real: `divineos ec status` reaches `emergency_completion.py:259, 264, 269` (`path.unlink(missing_ok=True)`), deleting the arm marker on a malformed, mistyped or expired arm. The PR's finding for `ec status` says only that it appends an `EMERGENCY_COMPLETION_EXPIRED` ledger event. Because `_ALLOWED_WRITES` is keyed by (command, token), the unlink would not have been flagged at all and is not described. Severity: low to medium (the command is already listed as a writer; the description undercounts).
3. **The detector also has false positives that the allowlist has to carry.** `set_title('x')` and `file_size(1)` are flagged as writes purely by prefix (reproduced). The `_EXCUSED_FUNCTIONS` list is keyed by (file name, function name) with no directory, and has generic names (`_conn`, `_git`, `_init`, `_ensure_schema` in several files). Two different files with the same basename and function name would share one excuse. From reading; I did not find a live collision. Severity: low.
4. **Test strength.** The "red check" in the PR body (adding `log_event` to `claims search` and seeing it fail) is real evidence for `log_event`; the other shapes are pinned only by snippets on `find_writes`, not by the whole-command path. Low.

**Tests at head:** I ran `tests/test_look_list_verbs_never_write.py` from a head extract. **25 passed.** The scan found 92 commands, as the PR says.

**Could not check:** whether the 92-command list is the whole set (commands registered by `add_command` or outside `src/divineos/cli/` are invisible, as the note says); whether the four named findings (`ec status`, `auto-cycle status`, `linkage status`, `work-item status`) are all of the real writers.

**One thing it gets right:** the exceptions are split into two lists, one for functions that only look like writes and one for commands that really write, each with a stale-entry check, so neither can quietly grow. And it names its own four real findings instead of burying them in an allowlist with no comment.

**Counts:** 0 serious, 2 medium (1, 2), 2 low (3, 4).

---

## PR 756: the memory floor arrives on every start

**Read:** head `2cc6ac0f66c97123786b644e5cc56f14c9fc43b5`. Whole diff (hook one line, `src/divineos/core/memory_floor.py`, `tests/test_the_memory_floor_card.py`), the hook file in full at the head, the hook's registration in `.claude/settings.json` (timeout 5), and `src/divineos/cli/his_words_commands.py`.

**Does it do what its title says?** It prints a four-line card at the end of the goal-boundary SessionStart hook. Whether the card then arrives "on every start" depends on that hook registration, which I read and which is wired to SessionStart. Not a duplicate on main (no `memory_floor` anywhere).

**Findings, most serious first**

1. **One of the PR's four tests fails on Windows, which is the house's own platform.** Reproduced at head: `test_broken_import_prints_nothing_and_exits_zero` runs `subprocess.run('"<python>" -c "..." 2>/dev/null; exit 0', shell=True)`. On Windows `shell=True` is `cmd.exe`, where `2>/dev/null` is a path error and `;` does not separate commands. Result: `returncode=1`, `stderr='The system cannot find the path specified.'`, so `assert out.returncode == 0` fails. Run result: `1 failed, 3 passed`. The PR body says the new file was run and passed in a Linux container ("54 passed, 68 skipped" across three files). Severity: medium (a red test on the checkout it will be maintained on; it also does not exercise the hook, only a re-typed copy of its Python call).
2. **The card sends "his words" to the corrections list, not to the tool that finds his words.** Line 2 of the card says: "his words `divineos andrew-correction list`". The repo has `divineos his-words find ...` (`his_words_commands.py`), documented as "look it up before quoting him": it searches all of his typed messages and says plainly when he never typed the words. `andrew-correction list` lists his corrections only. From reading (I did not run either command). Severity: medium, because the card is the one line meant to stop "he said X" being asserted from memory, and it names the narrower tool.
3. **Line 3 makes a claim the PR does not verify and the test does not pin.** "Arrives by itself: his past words and the memory link's matches on each of his messages." The PR body says so honestly (it could not observe it working). I found hook files that mention these surfaces (`his-words-door-surface.sh`, `state-gravity-surface.sh`, `dads_table.py`) but did not trace that the two named surfaces fire on each message. A card that teaches "this arrives, so do not go looking" and is wrong would suppress exactly the search it is there to cause. Severity: medium, from reading, plainly unverified.
4. **The hook now does two interpreter starts inside a 5-second timeout.** I measured the import of the new module at about 250 to 310 ms per start and `hud_state` at about 235 to 255 ms, so about half a second together on this box, well inside the 5 s limit. Not a failure; recorded so the margin is known. Low.
5. **The hook file's name and header comment say "goal boundary"; it now also prints a memory card.** The file header describes only the goal boundary. A future reader looking for the memory card will not look here. Low.
6. **The tests check that the five commands exist (`--help` exits 0), not that the sentence about them is true.** Fine for what it claims. Low.

**Tests at head:** `tests/test_the_memory_floor_card.py` from a head extract on Windows: **3 passed, 1 failed** (finding 1).

**Could not check:** that the card appears at the start of a real session (I did not start one), and finding 3.

**One thing it gets right:** the card's wording lives in one module and the hook only asks for it, prints nothing and exits 0 if the import fails. And the PR body says outright what it could not observe instead of presenting line 3 as verified.

**Counts:** 0 serious, 3 medium (1, 2, 3), 3 low (4, 5, 6).

---

## PR 757: the full-suite door reads what runs, not the word

**Read:** head `2cb03249655ee575d67623c611cfec3777abe5b3`. Whole diff (`src/divineos/core/full_suite_by_hand.py`, `tests/test_full_suite_record_commands.py`, 405 lines), `command_parsing.py` for `_SUBSTITUTION_MARKS` and `split_shell_segments`, `hud_commands.py` around `goal`.

**Does it do what its title says?** Mostly. Quoted text in nine named `divineos` record commands no longer trips the door, and the refusal now says which rule fired. It leaves several false alarms with advice that cannot be followed (findings 1 and 2). Not a duplicate: nothing like `_RECORD_COMMANDS` on main.

**Findings, most serious first**

1. **The new refusal tells people to do something that cannot work for the cases it fires on.** Reproduced at head with the real `decide`:
   - `bash -c "pytest tests/test_a.py -q"` is refused with the new text: "The one way out: put the words in a divineos record command ... If it really was a test run, name the test files." The test files WERE named. The text says it is "treated as a run with no test files named", which is false for this command.
   - `gh pr create --body "tests run with pytest"` and a heredoc, `cat > x.py <<'EOF' ... print('pytest') ... EOF`, are refused with "the one way out ... a divineos record command". Neither a PR body nor a file write can be turned into `divineos learn`. The text claims a single way out; for these there is none.
   - These are exactly the false alarms an earlier call of mine hit in this house (a heredoc probe carrying the word was refused by the live door). The PR says read-only process listings are not fixed; it does not say heredocs or `gh` bodies are not. Severity: medium (the whole point of part B was "say which rule fired and the way out"; for these the way out named is wrong).
2. **A path-qualified `divineos` is not exempt, and on this Windows house that is the normal spelling.** `_is_record_segment` requires `tokens[0] == "divineos"` (raw string). Reproduced: `.direnv/python-3.13.11/Scripts/divineos.exe learn "pytest tests/ is slow"`, `/usr/bin/divineos learn "pytest"`, `divineos.exe learn "pytest"` are all refused, the first with the word text, the others with the old "run" text. The module already has `_program()` which normalises a path to a program name; it is used elsewhere in the same function and not here. Severity: medium (the door's own remaining false alarm for a record command, plus advice that says "use a divineos record command" to someone who just did).
3. **`<(` and `>(` in the exemption list protect nothing, because an unquoted process substitution is already invisible to the door.** Reproduced, and the same on main (checked with the worktree copy of main): `cat <(pytest)`, `diff <(pytest) x`, `divineos learn "pytest" --file <(pytest tests/)` all PASS. The PR's test (`divineos learn "<(pytest)"`, quoted) is refused only because the quoted form reaches the word rule. So the hole is not new, but the new comment and test suggest `<(`/`>(` are handled, and an unquoted `<(pytest)` after a record command runs the suite by hand and passes. Severity: medium, pre-existing, not introduced here.
4. **The "real run" test is "any token whose basename is pytest", so a plain argument counts.** `python probe.py --name pytest` gets the old "run the tests for what you changed" advice (reproduced), because the bare token `pytest` is treated as the program. Only affects which message is shown, not whether it refuses. Low.
5. **The safety pin cannot see several ways a command can run text.** `find_executors` is run over a function's AST and flags only `subprocess` names, `shlex`, `eval/exec/compile` calls and `os.<system|popen|exec*|spawn*>`. Reproduced on small functions: MISSED are `from subprocess import run` then `run(...)`, `Popen(...)` without the module name, `getattr(os, 'system')(x)`, `__import__('subprocess').run(x)`, `asyncio.create_subprocess_shell(x)`, `webbrowser.open(x)`. The module-level `import subprocess` is also outside the function walked, though a use via `subprocess.` inside the function is caught. I also grepped the seven command files that hold the nine commands: the only `import subprocess` is in `goal auto-close` in `hud_commands.py:260`, a different command from `goal add`, so no current command is affected. The PR states its limits (depth, dynamic dispatch); it does not list "imported by name". Severity: low now, medium if a later core function does `from subprocess import ...`.
6. **Private-name import and a second copy of a walker.** `from divineos.core.command_parsing import _SUBSTITUTION_MARKS` imports an underscore name across modules; the test re-implements ~250 lines of the call-following walker that 755 also contains (the PR says "no dependency on it"). Two copies will drift. Low.
7. **`prereg assess ... --actor aletheia` and similar are exempt by name only** (the PR's own stated weakness). Nothing wrong today. I note the set is checked by `ast` for 9 commands and that all 9 were found by the walker (`feel` is registered in `claim_commands.py`, which is where a reader would not look). Low.

**Tests at head:** `tests/test_full_suite_record_commands.py` from a head extract: **63 passed.** The PR body says 160 across this file and `test_full_suite_by_hand.py`; I did not run the second file.

**Could not check:** `tests/test_full_suite_by_hand.py` unchanged-pass claim (file not in my extract); behavior of the live hook with the new text in a real session.

**One thing it gets right:** the exemption is narrow and fails closed on every shape I tried that actually chains or executes: `;`, `&&`, `||`, `&`, `|`, newline, `$()`, backtick and `${}` after or inside a record command are all refused (reproduced, 20 variants), and `reflection-note` was left out because it has no Click function in the repo (I searched `src/` and confirmed there is none).

**Counts:** 0 serious, 3 medium (1, 2, 3), 4 low (4, 5, 6, 7).

---

## Where I found nothing serious

None of the four PRs is clean, and none has a finding I would call serious (a way to defeat a guard that is introduced by the PR itself). The closest are 757 findings 1 and 2 (the new refusal gives a wrong way out; a path-qualified `divineos` is not exempt) and 756 finding 1 (a red test on Windows).
