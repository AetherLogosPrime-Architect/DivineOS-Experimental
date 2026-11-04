# Second reader k: findings on 766, 767, 551, 770

A cold read, 2026-11-03. I did not merge, stamp, confirm, approve, push to or comment on any of the four PRs. Reproductions ran the real code at each PR head, extracted with `git archive` into a scratch folder outside the repo and put on `PYTHONPATH`; for each I printed `__file__` to show the PR copy was the one loaded. Severity words: High = blocks or misleads the merge itself; Medium = a real defect or false statement a reader would act on; Low = small, or from reading only.

Environment: Windows, Python 3.13, pytest from the repo's `[dev]` extras. Unlike the earlier reader I could run each PR's own tests. The scratch extracts hold only `src`, `tests`, `scripts`, `.claude/hooks` and `pyproject.toml`, so I did not run whole-repo checks except where said.

Scratch folder (left in place): `C:\Users\aethe\AppData\Local\Temp\claude\C--DIVINE-OS-DivineOS-Experimental-Aria-new\39b9b1cd-4400-4356-81c3-a4a46accb33f\scratchpad\k_reader` (`a766`, `a767`, `a551`, `a770`, `m551`, plus `home*` isolated data homes).

Tally: 766 has 1 Medium, 1 Low. 767 has 2 Medium, 2 Low. 551 has 1 High, 2 Medium, 3 Low. 770 has 2 Medium, 2 Low. Nothing was clean.

---

## PR 766: A step that did not run is not marked succeeded

**Read:** head `87a871cdb801c5c66fce45093c8977be61c2f52d`; the whole diff (draft note, `auto_cycle.py` dry-run branch, the `DRY` flag in `fire_cmd`, two tests); `run_phase1`, `_run_step_python`, `write_handshake_marker`, and the readers of the marker in `.claude/hooks/auto-cycle-token-trigger.sh`.

**Does it do what the title says?** Yes for the data: a dry-run step is `ran: false, succeeded: false`. **Duplicate on main?** No. But the same `DRY` line is also carried by #551 (see its finding 7 below).

**Tests at head:** `tests/test_auto_cycle.py`, 22 passed (includes the 3 the PR added).

### Findings, most serious first

1. **Medium. The PR's search for readers stopped at `src/`, and the readers that matter are in the hook; a dry run still overwrites a real marker and the hook now calls it a FAILED cycle.** The PR says it found no outside reader of a dry-run `succeeded` "in `src/`" and could not search the hooks. `.claude/hooks/auto-cycle-token-trigger.sh` (the `mech_confirmed` stage test, and the terminator at about `:175-191`) reads the marker. `mech_confirmed` believes a marker on its timestamp alone (`ts >= launched`), and the terminator prints `FAILED` for any step whose `succeeded` is false and `COMPLETED` otherwise. Reproduced at the PR head with the real CLI in an isolated home: I wrote a real-looking marker (`REAL-CYCLE`, steps ran and succeeded), then ran `auto-cycle fire --dry-run --force`. The CLI printed `[DRY]` for all four steps (good) and then **replaced the real marker** (`fire_cmd` calls `write_handshake_marker` and `reset_defer_state` on a dry run). The marker now reads `ran=False, succeeded=False` on all four, and the terminator's own logic gives `FAILED -- archive=not-succeeded, commit=not-succeeded, extract=not-succeeded, sleep=not-succeeded`. Before the PR that same marker would have read `COMPLETED ... all succeeded`, which was the worse lie, so this is an improvement. But a practice run is still reported as a failed real cycle, and a practice run still erases a real pending marker and still satisfies the hook's "mechanical stage done" test. The fix the PR reaches for (`succeeded: false`) is the schema half; the other half is that `fire --dry-run` should not write the shared marker at all, or the hook should read `ran`.
2. **Low. It conflicts with #551 on the same line.** `git merge-tree --write-tree refs/pr/551 refs/pr/766` reports a content conflict in `src/divineos/cli/auto_cycle_commands.py`: both change `status_flag = ...` to the identical `DRY` expression, but #551 adds two comment lines above it. Whichever lands second needs a hand edit. The PR body knows the line is shared ("the same fix the note on #551 carries") but does not say they conflict.

### Could not check
- The hook's behaviour end to end in a live session (I reproduced the terminator's decision by its code, not by firing the hook).
- #753's tests against this branch (the PR says it did not either; I did not either).

### One thing it gets right
It resolved a claim that was not true (`succeeded: true` for something that never ran) by making the existing field honest instead of adding a field, and it pinned the rule from the reader's side ("done only when `ran` and `succeeded` are both true") in a test that reads the marker back from disk rather than checking the in-memory object.

---

## PR 767: Sleep refreshes both memory indexes and says how many

**Read:** head `c0f3e40020247efd62b4edb3758f477042d831b8`; the whole diff; `index_corpus`, `chunk_file`, `_connect` in `semantic_search.py`; `_phase_memory_link_refill`, `DreamReport.summary`; the new test file.

**Does it do what the title says?** Mostly. Sleep now fills the search index for the explorations and prints one line with both counts, and the `find index` command's behaviour is preserved (I read the refactor line by line; same paths, same db). **Duplicate on main?** No (`drawer_counts_by_source`, `refresh_exploration_index` do not exist on main).

**Tests at head:** the 5 new tests plus `tests/test_sleep.py`: 45 passed, 1 skipped. The embedder is stubbed in the new tests (the PR says so).

### Findings, most serious first

1. **Medium. The same notes get indexed twice when sleep runs from a different checkout.** `chunk_id` is `source_path:paragraph_index` with the absolute path, and `default_repo_root()` is the checkout the code runs from (the PR calls this out as a difference from `find index`, which uses the current directory, but not what it does to the shared database). Reproduced with the real function and a stub embedder, same notes in two roots, one db: first root `chunks_total` 2; second root, identical files, `chunks_indexed` 2, `chunks_total` 4. In this house sleep and `find index` can run from worktrees, so the search index can fill with duplicate hits for every note, and the line will say "N new" as if that were growth.
2. **Medium. An edited paragraph is never re-embedded, and the line reports it as nothing new.** `index_corpus` skips a chunk when a row with the same `chunk_id` and model exists; it does not compare text. Reproduced: rewrote the first paragraph of an indexed note (same position), refreshed: `chunks_indexed 0, chunks_skipped 2`, and the stored text is still the old text. This is older behaviour in `index_corpus`, but the PR now presents a refresh that "keeps the index current", prints `0 new`, and its test only covers a *new file*. Edits to existing explorations are the common case.
3. **Low. `chunks_total` is the whole table, `new` is explorations only.** `refresh_exploration_index` reads `COUNT(*)` of every chunk in the database, including any `letters` chunks added by hand with `find index --corpus all`, next to a "new" count that covers only explorations. The line does not say which. (From reading; the arithmetic is in the code.)
4. **Low. `default_repo_root()` is `Path(__file__).parents[3]`.** Right for an editable install (I printed it: the extract root); wrong for a built wheel, where it lands outside the repo, finds no `exploration/` folder and reports an honest zero. From reading.

### Could not check
- Real embeddings and the real `warm()` (the model is not available; the PR also says so).
- `sleep` end to end, and whether the embedder-missing case costs a slow model-load attempt per chunk (only the stub path ran).
- Whether any of the touched files are guardrail-class (the PR did one grep; I did not redo it).

### One thing it gets right
`chunks_failed` goes into the line, so a run where the embedder was absent cannot read as a clean zero, and the total is read back from the database instead of being inferred from the run's counts.

---

## PR 551: Auto-cycle phase two: written in July, never landed, its only copy

**Read:** head `251b8b0b971d390046e1985282af1167b0144640`; the whole diff (`auto_cycle_phase2.py` start to end, the three new CLI commands, the doc-count edits, the five draft notes), `auto_cycle.py` reader/clearer, the tests.

**Does it do what the title says?** The title no longer describes the code. The module is not the July copy: its docstring says it was rebuilt on 2026-09-25 after Aether's station four (strict handshake reading, consume at close, damaged-pending kept apart, an honest ratio). And "its only copy" is not true: **#753 is an open draft carrying the same module under a different shape.** **Duplicate?** Not of main; of #753.

**Tests at head:** `tests/test_auto_cycle_phase2.py` and `tests/test_auto_cycle.py`: 85 passed. `scripts/check_doc_counts.py` on the head alone: OK (commands=522).

### Findings, most serious first

1. **High. It and #753 are two implementations of one module and cannot both merge.** `git merge-tree --write-tree refs/pr/551 refs/pr/753` conflicts in `src/divineos/core/auto_cycle_phase2.py` and `tests/test_auto_cycle_phase2.py` (add/add) and in `CLAUDE.md`, `README.md`, `docs/ARCHITECTURE.md`. `git diff --stat` between the two heads: the phase-2 module changes by 673 lines and its test by 921 lines. The shapes differ: #551 puts `offer`/`close`/`audit` into `auto_cycle_commands.py`; #753 has a separate `auto_cycle_phase2_commands.py`. The PR body says the branch "holds the only copy" and that the module appears "in none of the ten open PRs"; this body does not mention #753, and I did not read #753's body for the reverse, so I cannot say which one is meant to win. An earlier reader's findings on #753's marker handling (a valid-JSON non-marker counted as "completed", non-numeric fields raising, a UTC string read with `time.mktime`) are already fixed in this version (`inspect_handshake` rejects a missing or non-dict `steps`, `calendar.timegm` is used), so if #753 has not taken those fixes, #551 is the stronger body of work. I could not tell which is intended.
2. **Medium. The description and the code no longer match.** The body describes the July code ("Two tests had pinned the rest menu at exactly eleven options"), says the full suite gave "13603 passed" at an older main, and lists "Stations still owed: council, a reading from Aether". The code's docstring cites Aether's station four, Aria's cold read and a council walk as done. A reviewer who trusts the body will audit the wrong thing. The same body names three drafts "swept in" from 2026-09-22 (`branch_dispositions`, `a_prescribed_remedy_must_not_be_blocked`, `push_gate_cannot_check`) that have nothing to do with phase 2; they ride along in a diff that is otherwise one module.
3. **Medium. After merging into current main the doc-count check fails.** The diff changes "517 commands" to "522" in `CLAUDE.md`, `README.md` and `docs/ARCHITECTURE.md`, but origin/main already says 522. `git merge-tree origin/main refs/pr/551` is clean (the identical edits merge away), so the three added commands (`offer`, `close`, `audit`) arrive on a base that already counts them: I extracted that merged tree and ran `scripts/check_doc_counts.py`: `commands=526`, documented 522, `drift: 4` in all three files. (My extract was partial, so the file-existence lines it also printed are noise; the command count comes from `src` and is reliable.) Main alone: `commands=523`, OK. `check_doc_counts.py --fix` clears it, but it will turn the first run red.
4. **Low. A non-finite number in the marker raises instead of being refused.** `_num` catches `TypeError` and `ValueError` only. A marker with `"budget_remaining_est": Infinity` (Python's `json` accepts it) raises `OverflowError: cannot convert float infinity to integer` out of `inspect_handshake`, reproduced. It fails loud and fires nothing, but the module's claim is that every bad marker is classified `malformed`.
5. **Low. A stale open offer blocks every later offer until someone closes it.** `offer_cycle` refuses when a pending file exists. Reproduced: offer for cycle `A`, then a newer marker `B`: `[!] Cycle A is already offered and not closed`. Correct and deliberate (a second offer used to overwrite the first), but across a compaction the seat that never closed `A` has to close it with some outcome before cycle `B` is offered, and that outcome goes into the falsifier log.
6. **Low. The falsifier cannot be tripped by never engaging.** `no-pull-honest` is outside the ratio by design (the docstring explains why, and `audit` prints the count beside it). A seat that closes every cycle that way gets "No qualifying cycles yet. Falsifier undefined." indefinitely. That is honest as printed; it does mean the prereg's "dead-writing infrastructure" alarm needs a human to read the no-pull line. From reading.
7. **Low. It conflicts with #766 on one line** (see 766 finding 2) and its comment calls the dry run "`succeeded=True`", which #766 would make untrue.

### Could not check
- A real phase 1 to phase 2 run (I fed the real `offer`/`close` a marker built from `run_phase1(dry_run=True)` with `ran`/`succeeded` set true, not a live `fire`). Offer, second offer, close, marker consumed and pending removed all behaved as the docstring says.
- Which of #551 and #753 the house wants.
- The whole-repo suite on a merge with main.

### One thing it gets right
The marker reader believes nothing it was not told in booleans, names three distinct reasons for refusing (absent, malformed, did-not-run), and the close writes the audit line before clearing anything and only clears a handshake that still carries the cycle being closed, so a newer phase 1 is never eaten. I confirmed the last by running it.

---

## PR 770: A note on what fails the first push of a new core module or hook

**Read:** head `8aecebc7cbcccb2a7cd8291c7a7e8ead4a20332e`; the one new file, `docs/first_push_of_a_new_core_module.md`, against each script and test it cites at that head.

**Does it do what the title says?** Mostly, and it is the kind of note that is worth having. Items 1, 2 and 4 check out against the files (the `## The tree` regex, `_PRE_TOOL_USE_HOOKS_WHEN_WRITTEN = 32` near line 363 with the "34 -> 33" comment above it, `_NON_GATING_HOOKS`/`_UNCLASSIFIED_BASELINE`/`test_the_dark_set_can_shrink_but_never_grow`). Two items are wrong in ways someone would act on. **Duplicate on main?** No; I searched `docs/` on main for the test and roster names and found nothing.

**Tests:** docs-only, none to run.

### Findings, most serious first

1. **Medium. Item 6 blames the wrong bash, and the fix does not follow.** The note says Git's bash reads `C:/x` as a folder name. Reproduced both ways with a script that exists: from Python on this machine, `shutil.which("bash")` is `C:\Windows\system32\bash.EXE` (the Windows launcher for WSL, a Linux `/bin/bash`), and `subprocess.run(["bash", "C:/.../t.sh"])` returns 127 with `/bin/bash: C:/...: No such file or directory`. The same call with `C:\Program Files\Git\bin\bash.exe` returns 0 and prints the script's output; in the Git Bash tool, `bash C:/.../t.sh` also works. So Git's bash handles the drive-letter path, and the cause is which `bash` Python found first. The advice to use `bash -s` on stdin is fine (it avoids paths altogether), but pointing at `_lib_native_path` (which turns `/c/...` into `C:/...`) will not help a WSL bash, which wants `/mnt/c/...`. A reader following the note will look for the problem in the wrong place. (My first attempt returned 127 because I had not yet created the script, a dead control; I fixed that before reading anything from it.)
2. **Medium. Item 3 cites a bypass that does not exist.** It says "The documented bypass is `DIVINEOS_NEW_INFRA_NO_PREREG=1`". In `scripts/check_prereg_for_new_infra.py` that name appears only in the module docstring; the code's one working escape is `DIVINEOS_NEW_INFRA_EMERGENCY=<reason of 20+ characters>`, and the failure message itself says "No env-var bypass exists". `tests/test_no_agent_settable_bypasses.py:44` lists the old name as "historical — being phased out". Someone who sets the documented variable will still be blocked. (From reading the full script; I did not stage a file and run it.)
3. **Low. Item 5 gets two details wrong.** It says SessionStart is a single launcher; `.claude/hooks/session-init-once.sh` is a UserPromptSubmit hook that runs the roster on the first message, because of the SessionStart deadlock its header describes. And "a typo in the name also fails silently": the loop at `:215-226` writes a `listed_child_missing` line to `~/.divineos/hook-liveness.log` before it continues. Quiet on screen, not silent in the record, and the log is where to look.
4. **Low. Item 3 leaves out what else can stop a prereg.** `prereg file` also runs `validate_three_why`, which refuses a detector- or warning-shaped mechanism unless it names `--companion-prereg` or `--no-upstream-because` (`prereg_commands.py:143-154`), and the commit gate only regex-matches `prereg-` plus 12 hex characters; it does not check the id exists. The second point is a gaming route and the note does not say it; the first is the next wall the reader is likely to hit. From reading.

### Could not check
- The relative-path form for item 6 (the PR says it did not either).
- Whether `--uses-of` is enforced to name an event that has already happened (the help text says so; I did not trace `file_pre_registration`).
- Line numbers: they match at this head; the note says they will drift.

### One thing it gets right
It states its own limits (what was tested, what was not, that line numbers drift, "if a name has moved, trust the file over this note"), and it corrects older advice instead of repeating it: it found that `--embarrassing` and `--uses-of` are now required, and that the architecture tree moved out of the README.
