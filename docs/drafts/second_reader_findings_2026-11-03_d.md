# Second reader: findings on 779 and 780

A cold read, 2026-11-03. I did not merge, stamp, confirm, approve or comment on either PR. Each finding below was reproduced against the PR head in a scratch checkout with the PR's real code (no monkeypatching of the code under test; stand-in inputs are named) unless it says "from reading". Probes ran in an isolated `DIVINEOS_HOME`. Both PRs' own test files pass at their heads (9 for 779, 21 for 780); that tells you nothing about the findings below, which are about what the tests do not pin.

---

## PR 779: `divineos volley start|stop|status`

**Read:** head `fa1e68b0097e2b29db969ff5be98c409701ac8f9`. Whole diff, `core/volley_now.py`, `cli/volley_commands.py`, the three-line change to `question_hold.is_away()` / `_carry_now()`, `tests/test_volley_now.py`, the draft note, and the callers of `is_away()` / `came_back()` (`.claude/hooks/question_hold.py`, `cli/question_hold_commands.py`). `scripts/check_doc_counts.py` passes at the head (526 commands).

### Findings, most serious first

1. **Once started, the quiet carries every question to the morning list even while he is typing to me, and his speaking does not end it.** `question_hold.py` `_carry_now()` returns `"volley"` as soon as the marker is live, before the live-chat check (`LIVE_CHAT_SECONDS`, ten minutes) that the clock and silence kinds both honor. The module docstring says it plainly ("Nothing clears it when he speaks"), and `came_back()` only clears the `AWAY` file, not this marker. Reproduced with the real functions: his last message 5 seconds old, `volley_now.start()`, then `_carry_now()` -> `'volley'` (before the start: `''`); after calling `qh.came_back()` (what his next message triggers) it is still `'volley'`; `qh.arm("Does the build look right to you?")` returned `None` and wrote one row to the morning list instead of holding. So "he said goodnight, then came back at 21:30 and asked me something" gets a seat that sends its questions to a morning letter until midnight. The existing comment above `LIVE_CHAT_SECONDS` states exactly why the other kinds guard against this ("it would carry a live question to a morning he is not waiting for"); the new kind is the only one that does not. The cost is a seat that quietly stops asking while he is awake and waiting.
2. **Starting and stopping the quiet leaves no trace, so quiet is not countable.** `volley_now.start()` / `stop()` write no log line. The sibling `step_away()` calls `_log("stepped_away", his_words=...)`; the `carried_to_morning` log line records only the question and `why="volley"`, not who started it or when. Any seat can run `divineos volley start` with no words of his attached (the draft says that is the intent), so the only evidence that a seat silenced him is a marker file that is overwritten the next day. Nothing checks the seat's judgment after the fact, and nothing counts how often it is used. From reading plus the file read above (no `_log` in `volley_now.py`).
3. **`divineos question-hold` (no subcommand) prints a blank for a volley start.** `question_hold_commands.py` prints `he stepped away: {away['his_words']}`, and the volley kind carries `his_words: ""`. Reproduced: with a live marker the output is `he stepped away: ` followed by nothing (the schedule and silence kinds have the same empty field, so this is old, but this PR adds a third reachable path to it and its own `status` command is the only place the new kind is described properly).
4. **The override variable works outside tests.** `volley_now.path()` honors `DIVINEOS_VOLLEY_FILE` whenever it is set (reproduced: pointing it at another directory moves the marker). The neighbouring `DIVINEOS_NIGHT_HOURS=off` was deliberately limited to a running test (Aletheia, 2026-10-12: "a rule Dad made must not have a quiet off-switch a live seat could set"). This one is a quiet way to make `active()` read a file the seat controls, or to make a started quiet read as not running. Small, but it is the same shape the clock was fixed for.
5. **Tests lean on the clock being off and never pin the live-chat case.** `test_the_existing_reader_sees_it` and `test_a_question_is_carried_while_it_runs` assert `is_away() is None` / `_carry_now() == ""` as the control and rely on the shared test setup having switched the night window off; `test_a_question_is_carried_while_it_runs` uses a could-not-look store, so the case in finding 1 (he spoke 5 seconds ago) is exactly the case no test builds. Nothing pins that a marker is dead the next local day under the real `is_away()` (only `active(now=...)` is tested).
6. **The other seat is not quieted.** Stated in the draft ("each seat runs it"). Worth saying because the night letter file is shared: one seat can be quiet while the other is still asking him in chat.

### Could not check
- Whether the seat's reading of "he is going to bed" is reliable. That is judgment by design, and nothing here can see it.
- The next-day behavior under the real clock in a real session (I tested `active(now=...)` only through the code paths above, in a UTC container).
- Whether any other consumer of `is_away()` I did not search for treats `by == "volley"` unexpectedly; the callers I found (`hooks/question_hold.py`, the CLI group) only test truthiness.

### One thing it gets right
It reuses the single reader (`is_away()`) instead of adding a second notion of "away", keeps the clock window untouched, makes an unreadable marker mean "not away" (so a broken file cannot silence him), and gives the marker a one-day life so a forgotten start cannot run past midnight. Both the marker and the `status` command are small enough to read in one sitting.

---

## PR 780: advisory new-module checklist at commit time

**Read:** head `e102b80cd5dc6baa2ef21a1d73c6390fa5cff6bf`. Whole diff, `scripts/new_module_checklist.py`, the `scripts/precommit.sh` step 9, `tests/test_new_module_checklist.py` (21 pass), the draft note, and the rules it mirrors: `scripts/check_doc_counts.py` (`_parse_tree_block`, `check_architecture_tree`), `scripts/check_prereg_for_new_infra.py`, `tests/test_every_exit_passes_every_gate.py`, `tests/test_gate_deny_messages_name_remedy.py`, and `scripts/precommit.sh` step 4.

Probes were run in a scratch checkout of the head, staging files in the index and running the script plus `check_doc_counts.py`.

### Findings, most serious first

1. **The tree-line check covers `core/` only; the real check covers every package, and a new file outside `core/` gets silence.** `new_module_checklist.py` `run()` filters on `CORE_PREFIX`. `check_doc_counts.check_architecture_tree` compares the tree against every `.py` under `src/divineos/` (`_get_actual_py_files`). Reproduced: staging a new `src/divineos/cli/zz_new_cmd.py` -> the checklist printed nothing and exited 0 ("looked, nothing to add"), while `check_doc_counts.py` reports `UNDOCUMENTED: cli/zz_new_cmd.py`. The module's own contract is "silence means looked, nothing to add"; this is the confident wrong answer it promises not to give. (PR 779, read in the same pass, adds a new `cli/volley_commands.py`.)
2. **A rename is mis-described and its ghost is never mentioned.** `--no-renames` turns a rename into delete + add by design. Reproduced with `git mv core/ledger.py core/ledger_renamed.py`: the checklist asked for a tree line for the new name and added the prereg reminder, but said nothing about `core/ledger.py`, which `check_doc_counts.py` flags as `GHOST: core/ledger.py (listed ... but doesn't exist)`. A second stumble the push will hit, unseen. Also the prereg reminder is wrong for a pure move: the real prereg gate reads `--name-status` without `--no-renames` and so sees `R`, not `A`.
3. **In the only place it is wired, item 1 is mostly dead.** `precommit.sh` step 4 (line 268) already runs `check_doc_counts.py`, and on failure runs `--fix` (which appends a best-effort tree line) and re-stages `docs/ARCHITECTURE.md`; step 9 then reads the index after that. So for `core/` the "no tree line" message appears only when the fixer already failed, at which point step 4 has already called `note_fail`. From reading (I did not run the whole precommit script): the claim in the PR's draft that the tree stumble is "only visible late" holds for a bare `git commit` with no precommit, not for the documented flow (CLAUDE.md rule 7 says to run `precommit.sh` first). The hook-count and `_NON_GATING_HOOKS` items (2 and 4) have no such earlier fixer and are the useful part.
4. **Every new gating hook gets the "not named in `_NON_GATING_HOOKS`" advice.** `check_non_gating` flags any staged new `.claude/hooks/*.sh` not in the set. Reproduced with a hook that denies with a `Run:` remedy: the checklist printed the "add this line" advice. The second sentence ("If it CAN refuse, leave it out") is right, but the first thing a reader sees is an instruction that is wrong for exactly the kind of hook this house mostly adds. The check cannot tell the two cases apart (the real test uses a denial pattern), so the output is a half-answer printed every time. Related: a hook that is not declared and has no detectable denial also fails `test_the_dark_set_can_shrink_but_never_grow` (`_UNCLASSIFIED_BASELINE`), which the checklist does not mention.
5. **The prereg reminder differs from the real gate in two ways it does not say.** (a) It excludes new `core/**/__init__.py`; the real gate (`_is_protected`: prefix `src/divineos/core/` and `.py`) includes it. Reproduced: a staged new `core/zzpkg/__init__.py` gave silence from the checklist. (b) Merge commits: the real gate subtracts files already present at `MERGE_HEAD` (the 2026-07-31 false positive), the checklist does not, so during a merge it would remind about every module the other side added (from reading; I did not build a merge). Advisory only, so the cost is noise and a reminder that is missing where the real gate bites.
6. **Two small things in the tests.** The tests build their own throwaway repos with hand-written stand-ins for `ARCHITECTURE.md` and the two pinned tests; none of them runs the script against the real files, so a change to the real tree block or to the `_NON_GATING_HOOKS` literal would pass the suite and degrade this to "could not look". (I did run it against the real files at this head: the hook-count check agrees with the pin when `settings.json` is touched, and nothing staged is silent.) And `check_pretooluse_count` sums `hooks` in every PreToolUse group the same way the real test does, which is right, but the checklist re-implements the arithmetic rather than importing `_pre_tool_use_hook_count`; the PR says why (read-as-text so shape change reads as could-not-look), and it holds.

### Could not check
- A full run of `scripts/precommit.sh` end to end (it runs many other steps and I did not want its side effects). Finding 3 is from reading step 4 and step 9 in order.
- Behavior under a merge commit (finding 5b), and on a machine where `python` on PATH is not the repo's interpreter (the step uses bare `python`, as its neighbours do).
- Whether the exit-0 promise survives a hung `git` (the calls have no timeout; the real prereg gate uses 10 seconds).

### One thing it gets right
The "could not look" discipline. Outside a repository it says so instead of the clean answer that `git diff` would have implied (I ran it against `C:\Windows`: it reported `git rev-parse failed`, exit 0), it reads the index rather than the working tree, and it exits 0 on every path including its own crash. A refused-by-the-fixer step is not made into a new blocker.

---

## Counts

| PR | High | Medium | Low | Total |
|---|---|---|---|---|
| 779 | 1 | 2 | 3 | 6 |
| 780 | 0 | 2 | 4 | 6 |

Mapping to the numbering above: 779 is High 1; Medium 2 and 4; Low 3, 5, 6. 780 is Medium 1 and 2; Low 3, 4, 5, 6.

Neither came back clean. 779's one serious finding is a design call the PR states openly (it does not clear on his speaking) but whose effect on live questions the PR does not name; 780 is a small, honest checklist whose gaps are against the rules it says it mirrors.
