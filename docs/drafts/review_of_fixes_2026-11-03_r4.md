# Review of the six repairs, round 4 (2026-11-03)

A cold read of draft PRs #800, #804, #808, #810, #813 and #816. Each repair sits on the branch of the original pull request, so its diff is the repair alone. For each: head extracted with `git archive` into a scratch folder, put first on PYTHONPATH, `__file__` printed to prove the load, new tests run on the base head and on the fix head, then my own probes. Every finding is marked REPRODUCED (I ran it) or FROM READING.

Scratch folders left in place: `C:\Users\aethe\AppData\Local\Temp\claude\C--DIVINE-OS-DivineOS-Experimental-Aria-new\39b9b1cd-4400-4356-81c3-a4a46accb33f\scratchpad\` (`x\h<N>` fix heads, `x\b<N>` base heads, `w816\` index experiments, `p*.py` probe scripts).

Severity count (high / medium / low): #800 0/0/2, #804 0/0/1, #808 0/1/2, #810 0/1/3, #813 0/1/2, #816 1/2/2.

## #800 docs-only corrections (for #770)

Clean on the three claims it set out to correct. All three checked against the repo and this machine.

- Item 6 (exit 127): REPRODUCED. From Windows Python, `bash` found by Python and `C:/Windows/System32/bash.exe` both exit 127 on a `C:/...` script path; `C:/Program Files/Git/usr/bin/bash.exe` exits 0 on the same path. The relative-path form, which the body says it did not test, also works with Git's bash (exit 0). `where.exe bash` lists three: Git's, System32's and a WindowsApps stub.
- Item 3: REPRODUCED by reading. `scripts/check_prereg_for_new_infra.py` only reads `DIVINEOS_NEW_INFRA_EMERGENCY` (line 127) and the reason must be 20 characters or more.
- Item 5: REPRODUCED by reading. `session-init-once.sh` header says UserPromptSubmit; it is wired through `.claude/hooks/dads_table_children.json`, not `settings.json` (the body says it did not trace this; it is traceable and the doc claim holds). `listed_child_missing` is written at line 225 to `$HOME/.divineos/hook-liveness.log`. `INIT_HOOKS=` is at line 129, as the doc says.

Findings
1. LOW, REPRODUCED. The wrong bypass name is still taught elsewhere: `setup/setup-hooks.sh:341` ("Bypass: DIVINEOS_NEW_INFRA_NO_PREREG=1") and the docstring of `scripts/check_prereg_for_new_infra.py:8`. The doc now says the docstring is wrong but leaves the docstring. This is the retired-rule-served-again shape CLAUDE.md warns about.
2. LOW, FROM READING. Item 6 says the `bash` Python finds first "can be" the WSL launcher; on this box CreateProcess finds System32's first, while `where.exe` order (Git first) differs. The doc says "check which comes first on yours", which is the honest hedge, but it does not say Python's search and the shell's PATH order can disagree.

What it gets right: it replaced a confident wrong cause with a tested one and kept the one thing it could not test labelled.

## #804 memory floor card (for #756)

Clean.

- Tests: REPRODUCED. 4 passed on the fix head (`__file__` under `x\h804\src`). Run on the base head with the new test file copied in: `test_every_command_the_card_names_exists` fails (`['his-words','find']` not named). The old shell test fails on this Windows box on the base head (returncode 1, "The system cannot find the path specified"). The portable new test passes on both heads, which is the point of it.
- Probe: REPRODUCED. `divineos his-words find --help` exists; the card prints `his-words find "words"`. No other doc line in the repo still pairs "his words" with `andrew-correction list`.

Findings
1. LOW, FROM READING. The rewritten `test_broken_import_prints_nothing_and_exits_zero` no longer runs the hook's shell line; it reads the text for `2>/dev/null` and a last line of `exit 0`. The fixer says so. A change that kept the text but broke the behaviour (for example `set -e` added above) would pass. The line at hook line 22 uses `&&`, so a failure there is already contained, but nothing pins it.

What it gets right: it kept a control in the new test (the broken import really fails, returncode non-zero) so the stdout-empty check cannot pass by the import quietly succeeding.

## #808 look-list never-write pin widened (for #755)

Tests: REPRODUCED. 48 passed on the fix head. The detector lives inside the test file, so "fails on base" cannot be shown by running tests; I loaded the OLD detector and fed it the new write snippets: it misses `unlink`, `mkdir`, f-string `UPDATE`, `os.remove`, `shutil.copy`, `mark_done()`, `executescript`, `Popen` (8 of 9), and catches only `'UPDATE %s' % t`. That matches the body.

`ec status`: REPRODUCED by reading. `_load_valid_arm` in `core/emergency_completion.py` lines 259, 264, 269 unlinks the arm file on unreadable, malformed or expired. The finding is real and correctly worded.

Findings
1. MEDIUM, REPRODUCED. New false-positive classes the fixer did not list. The rule "any `shutil.*` call" flags `shutil.which` and `shutil.get_terminal_size` (both reads). The widened prefixes `add_` and `update_` flag `add_argument`, `add_row`, `add_column`, `add_text`, `functools.update_wrapper`, `mark_safe` (all reads or in-memory). The source today passes, so nothing fails now, but the next rich `Table.add_row` inside a status command will be reported as a writer and someone will excuse it by name, which erodes the list. The read-looking exception list is five exact names; this shows it is a list that will grow.
2. LOW, FROM READING. The excusal list is keyed by file name plus function name. `("db.py","get_family_connection")` and `("_dir")`, `("_connect")` are generic names. The fixer says this. There is one `db.py` under `core/family/` today, so nothing is over-excused now. Also `_SCHEMA` now includes `executescript(`, so the existing schema-setup excusals (`claim_store.init_claim_tables`, `memory.init_memory_tables`, `decision_journal.init_decision_journal`) now permit any script text, including DROP, which the detector still cannot see. Excusal breadth grew with the token set, without a line saying so.
3. LOW, REPRODUCED. Blind spots stay as stated: `Path.replace`, `os.rename` is caught but `p.replace('x')` is not, SQL with the verb in a variable-first concat (`q + ' WHERE 1'`) is not. Documented in the draft; I confirm the list is accurate.

Excusal list for anything too broad: nothing excused hides a write beyond `mkdir`, `executescript` or the earlier commit/schema tokens, and the stale-entry check fails if an excusal stops matching. I read `work_item_doorman._connect`: it does `executescript(_SCHEMA)` and then a try/except `ALTER TABLE ADD COLUMN` migration, which the detector cannot see, so its excusal reason "lazy schema" quietly also covers a migration. Accurate enough, but not stated.

Prior-art / council gap: the missing search shows mildly. The prefix net was widened by adding names rather than by checking how many existing non-writers share the prefixes (finding 1 is exactly that).

What it gets right: it built the control the right way round, putting 18 write shapes and 5 read shapes through parametrised tests, and it recorded the one real new writer as a FINDING instead of excusing it.

## #810 full-suite door text and path-qualified divineos (for #757)

Tests: REPRODUCED. 173 passed on the fix head. With the new file copied onto the base head: 9 failed, 164 passed. The 9 are the ones the body names.

I ran `decide()` on 52 commands on both heads (`p810.py`, outputs `o810b.txt` and `o810h.txt`). Decisions (allowed or refused) differ between heads only for the record-command exemption cases, as claimed: `./divineos.exe learn`, `DIVINEOS.EXE`, a quoted `"C:\Program Files\x\divineos.exe" learn`, `'/c/My Dir/divineos'`, `~/.local/bin/divineos` become allowed. `divineos ask`, `divineos-other`, `divineos learn "x" && pytest`, `divineos learn "x" | pytest`, `$(...)` and backticks inside quotes stay refused.

Findings
1. MEDIUM, REPRODUCED (pre-existing, unchanged by this repair; I ran it on both heads). A real full-suite run goes through the door: `echo $((1+2)); pytest -q` is ALLOWED, as are `echo $((1<<2)); pytest -q`, `echo $((2)) && pytest tests/`, and `echo $(( 1 )); pytest`. The same text without the arithmetic (`echo ok; pytest -q`) is refused. Also allowed: `pytest -q tests/ -k foo`, `pytest -k thing`, `tox`, `bash scripts/precommit.sh` (the last two are not pytest by name). The repair did not touch this and the body does not claim to, but the task was to try to get a run through, and this is how.
2. LOW, REPRODUCED. The new heredoc rule mislabels a real run that comes after a heredoc. `cat <<EOF\nx\nEOF\npytest`, `x=1 <<EOF\nEOF\npytest -q` and `echo a<<b; pytest` are real full-suite runs but now get the heredoc advice ("write the text to a file") and not the run advice with the changed test files. Still refused, so the decision is unchanged, but the message is wrong for them, and the fixer's own note that "a segment that repeats earlier text could be placed wrongly" understates it: the test is simply `command.find(segment) >= heredoc.end()`, so anything after the marker line counts as body, including the line after the terminator.
3. LOW, REPRODUCED. Honest record commands still refused: `python -m divineos learn "pytest tests/"` (word message), and an unquoted Windows path `C:\x\divineos.exe learn "pytest tests/"` (shlex eats the backslashes), and `bash -lc 'divineos learn "pytest"'` (wrapper). The message for the first two tells the writer to use a divineos record command, which is what they did.
4. LOW, FROM READING. The note "a path-qualified divineos is exempt by name alone; a different program called divineos would be exempt" is correct and the same weakness the old bare-name check had, only wider. It is a nudge door, not a security boundary; I do not rate it higher.

Earlier in this review the door refused my own honest, file-naming run when it was wrapped in a group `(cd ... && PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_x.py 2>&1 | tail -15)`. On the fix head that exact command now gets "The files you named are not the problem; the wrapper is", which is true and was the point of the repair. REPRODUCED: before, with no `kind` text, it got the generic run advice.

Prior-art / council gap: it shows in the heredoc position test (finding 2), a location-by-substring that a short walk of "what comes after the terminator" would have caught.

What it gets right: the refusal text now matches how the word arrived, and the four control tests (run-before-heredoc, three "exemption does not widen") are real controls, which pass on the base head by design.

## #813 dry run no longer writes the real marker (for #766)

Tests: REPRODUCED. 106 passed, 18 skipped on the fix head. With the new test files copied onto the base head: 4 failed, 102 passed, 18 skipped. The four are the four named.

Findings
1. MEDIUM, REPRODUCED. A marker with no steps is reported as success. `steps: {}` prints `CYCLE ... COMPLETED -- 0 step(s), all succeeded`. The fixer's rule is "never prints COMPLETED for a step that did not run"; a marker that records nothing is the same shape one level up. Pre-existing, not introduced. Related, REPRODUCED: `{"ran": False, "succeeded": True}` (a contradiction) prints `DID NOT RUN ... (a dry run)`, and `ran` as the string `"false"` or null is read as an ordinary failure `sleep=not-succeeded`. The hook text hard-claims "(a dry run)" for any all-not-run marker; in `run_phase1` only a dry run produces `ran=False`, so it is true today, but it is a belief, not a read.
2. LOW, FROM READING. `auto-cycle status` (`auto_cycle_commands.py:205-209`) still reports "handshake marker present ... phase 2 has not consumed it yet" for an old dry-run marker already on disk, the same marker the hook now calls DID NOT RUN. The fix cleaned up the hook and the writer, not this reader. The body's own search for readers (`git grep succeeded`) missed this one because it reads `cycle_id`, not `succeeded`.
3. LOW, REPRODUCED by diff. The body says both PRs "change the same line ... the `status_flag = ...` line". That line is not in #813's diff; it is already in the base branch (`job5-...`). So the conflict with #551 is between #551 and the original #766, not this repair, and resolving it is not this repair's job. I confirmed #551's diff has that line at `gh pr diff 551`.

The reader search: the fixer says a reader of `succeeded` under another name would not be found. `grep` for `write_handshake_marker`/`read_handshake_marker` shows exactly two readers (the hook and `status`) and a second writer at `defer_check_cmd` (line 290), which is a real cycle and rightly keeps the marker.

Prior-art / council gap: finding 2 is the kind a short "who else reads this marker" search shows; the fixer searched on the field name, not the file.

What it gets right: dry run now writes nothing and says so in words, and the hook still never prints COMPLETED for a step that did not run, tested in both the all-not-run and the mixed case.

## #816 relative chunk ids, edited paragraphs, removed paragraphs (for #767)

Tests: REPRODUCED. With the stubbed embedder, 10 passed in the target file, 18 passed and 8 skipped with `test_semantic_search.py`, on the fix head. On the base head with the new test file: 4 failed, 6 passed. One of the four (`...not_every_row_in_the_database`) fails on the base head only because `index_corpus` has no `root` argument (a TypeError), not on the behaviour it names, so that test proves less than it looks.

Probes against an index built the old way (`p816.py`, scenarios `old_build`, `migrate`, `oldother`): REPRODUCED. Old index of 3 chunks with absolute ids, then the fix head's `refresh_exploration_index` from the same checkout: first run `chunks_indexed 3, chunks_removed 3`, rows 3; second run `chunks_indexed 0, chunks_skipped 3`; sleep line reads "3 chunks of the explorations (0 new)". Migration works for the checkout you run it from, and it throws away the old vectors and re-embeds all of them (the real model, once), where it could have kept them for unchanged text. Old rows from a different checkout stay beside the new ones (6 rows for 3 paragraphs in `oldother`), as the body admits; searches show both.

Findings
1. HIGH, REPRODUCED. Two checkouts with different versions of a note fight over one set of chunk ids forever. This machine runs several worktrees that share one database. With checkout A holding a note and checkout B holding the same note with one paragraph rewritten, alternating `refresh_exploration_index` A, B, A, B gives `chunks_indexed 1, chunks_updated 1` on every run after the first, each re-embedding with the real model and each sleep line saying "1 edited". If B's copy is shorter, B deletes A's extra paragraphs (`chunks_removed 2`) and the next A run re-embeds them (`chunks_indexed 2`). Before the repair the second checkout simply added rows; now nothing converges. Making the id relative was the fix for double counting, but it makes the id a shared name for non-identical text, and nothing in the repair or tests tries two different versions. The body's "What I could not check" says only that a shared database shows the last path.
2. MEDIUM, REPRODUCED. `divineos find index` passes `root=Path.cwd()`, not the checkout root, while sleep passes the checkout root. Run from any subfolder, files fall outside the root, ids fall back to absolute, and the two callers alternately delete each other's rows by `source_path`: sleep (3 chunks) then `find index` from `exploration/` gave `chunks_removed 3, chunks_indexed 3`, then sleep again gave `chunks_removed 3, chunks_indexed 3` (all embedded again, for no change). The body says both "pass their checkout root"; for the CLI that is only true when run from the root.
3. MEDIUM, REPRODUCED. A note deleted or renamed on disk keeps its rows. The new comment in `index_corpus` says "an emptied or deleted file" is cleaned, but only files in the walked list are examined and a deleted file is not in it. Two files indexed (4 chunks), one deleted: second refresh reports `chunks_total 2, chunks_removed 0` while the database still holds 4 rows. Emptying a file works (3 removed). The new "total" counts only the walked set, so the stray rows do not appear in the sleep line at all, and search results still return them.
4. LOW, FROM READING. Every paragraph inserted above others shifts the index, so ids after it are "edited" and re-embedded one by one; the line says "N edited" for what is a shift. Pre-existing id design, now visible.
5. LOW, FROM READING. `find index` prints `indexed: N` only; it was not updated for `chunks_updated` and `chunks_removed`, so it says nothing of removals that the same run just made.

Prior-art / council gap: it shows. Findings 1 and 2 are exactly what an "how do other callers and other checkouts hold this key" search or a short walk would have turned up; the repair was built and tested for the narrow case the finding described (the same notes twice) and nothing tested different notes under the same id.

What it gets right: counting `chunks_total` over exactly the walked set means total, new, edited, removed and failed finally describe one set, and the migration for the current checkout is real (I ran it against an index built by the old code).

## What I could not check

- The real embedding model on any of #816 (I used a stub, as the PR's tests do), so timings and the real cost of finding 1's re-embedding are not measured.
- Phase 2 (#753, #551) against the #813 marker: not on these bases.
- That the hook surfaces the new #810 text correctly on screen: I read only `decide()` return values, the same limit the fixer names.
- I did not run the three or four wider test files on any head beyond the ones named; no full suite.
- #800's claim that `session-init-once.sh` is wired for UserPromptSubmit I confirmed from `dads_table_children.json`, not from a live session.
