# Second reader (f): findings on 772, 773, 753

A cold read by a reader outside the house, 2026-11-03. I did not merge, stamp, confirm, approve or comment on any of the three PRs, and pushed nothing to them. Reproductions ran the real functions from each PR head, checked out in my own worktree (editable install, `python -I`), with an isolated `DIVINEOS_HOME` where state was involved. The machine is Windows, so a timezone probe (`time.tzset`) could not run. I ran each PR's own test file: 772 passed 14, 753 passed 71; 773's tests I did not run.

Method note: I read the earlier reader's file (`second_reader_findings_2026-11-02.md`) first and followed its shape.

---

## PR 772: the clerk says when a round has no tree-hash line

**Read:** head `5bd1fca2a49601097950f87932dbf48c86209818`. The whole diff: `landing_homework.py` (new `TREE_LINE_PREFIX`, `_TREE_LINE`, `rounds_without_tree_line`, the matcher now using the shared prefix, the round writer), `landing_commands.py` (the listing and `file_confirm_cmd` hooks), the new test file. I also read `list_rounds` in `watchmen/store.py`.

### Findings, most serious first

1. **The commonest "no match" cause stays silent: a round that has a tree-hash line for an older head.** `landing_homework.py` `_TREE_LINE` accepts any 40-hex tree after the prefix; the matcher (`her_confirm_filed_at`) needs this head's tree. Reproduced (real functions): notes `tree-hash: bbbb...` against tree `aaaa...` gives `warns: False` and `matcher ok: False`. After a push, the round's line names the previous tree and the fix shows unconfirmed with no cause, which is the exact symptom the PR set out to explain. The warning text also says "cannot be matched to a head", which is a claim about every head, so it is the right sentence only for the no-line case. The PR does say it "only explains" the missing line, so this is a scope gap and not a wrong answer.
2. **The warning only sees a round whose focus names the PR as `#N` or `PR N`, and the refusal path depends on it too.** Reproduced with PR 7: focus `PR #7` warns; `pull 7`, `PR-7` and `pr7` do not (and `pr7` is the form `\bPR\s+` rejects). In `file_confirm_cmd` the round is the one the operator named by id, so the clerk already knows it is the round in question, yet the explanation is still gated on the focus text: a named round whose focus reads "pull 772" refuses with the generic "holds no confirm of hers" and no cause. The test table `_FORMS` pins notes forms only, never focus forms.
3. **`list_rounds(limit=500)` can drop old rounds silently** (`landing_commands.py`, `list_rounds` orders by `created_at DESC LIMIT ?`). From reading, not reproduced (I did not count rounds in the real store). The PR is careful to say aloud when the read raises, but a read that succeeds and is cut short says nothing, and the line it prints for an unreadable store is "not a clean bill" while this case is quietly one.

### Could not check
- The real count of audit rounds, so whether 500 is reached.
- `divineos landing` end to end against live GitHub; the tests fake `open_prs` and `classify_pile`.
- Whether `her_confirm_filed_at` has other reasons to return `None` (no external-confirm finding by her) that the listing could also explain; the PR explains only the missing line.

### One thing it gets right
The matcher, the writer and the warning share one constant (`TREE_LINE_PREFIX`), and the last parametrised test forces the warning and the real matcher to agree on seven forms including no-space, double-space and capitals. I reproduced the agreement in the cases it covers; the warning is never looser than the matcher except in case 1 above.

---

## PR 773: `reach open` also lists open pull requests

**Read:** head `46fe8bb037350386957e3995a6b27e807150dfc4`. The whole diff: `core/reach_open_prs.py`, the three added lines in `cli/reach_commands.py`, `docs/ARCHITECTURE.md`, `tests/test_reach_open_prs.py`. I read the whole of `reach_open_cmd`.

### Findings, most serious first

1. **No stemming, so ordinary inflection of the same idea misses.** `content_words` splits on non-letters and compares whole words, with a two-word minimum. Reproduced against a PR titled "Gate stamp ending check": `gates checking endings` returns `[]`, `stamps checks` returns `[]`, while `gate check` matches. The tests pass because their symptoms reuse the PR's exact words (the "refresh" in the first test is matched by "memory", "sleep" and "indexes", not by "refresh"). The failure here is silence that reads as "none found among N open PR(s)", which is the sentence that licenses a rebuild, the thing the PR exists to prevent. A cheap fix is a crude suffix strip.
2. **Only titles and branch names are searched, and drafts are not marked.** `gh pr list --json number,title,headRefName` (`reach_open_prs.py`): the body, the file list and `isDraft` are not asked for. The origin story is a fix that existed as a draft. A PR whose title does not use the symptom's words but whose diff touches the file will not show. Say so in the output ("searched titles and branch names"), or ask for `files`. Medium-low.
3. **The wiring has no test.** The tests call `format_open_pr_section` and `matching_prs`; nothing runs `divineos reach open` and sees the section print, or sees that it prints when the check found items and when it found none. From reading `reach_open_cmd`, the section is after the early branches and is reached on both paths. Low.

### Could not check
- `gh` behaviour when unauthenticated or offline beyond the code reading: the failure path returns the sentence the test pins. I did run `gh_open_prs()` on this machine (it returned the open PRs, 35 of them), so `--limit 100` is not reached yet. When the repo passes 100 open PRs the output would say "none found among 100 open PR(s)", which is true as worded.
- I did not run this PR's tests.

### One thing it gets right
Failure is loud and worded as a failure: any exception from the look becomes "Could not look at open PRs (...): this is not a clean bill." and an empty list prints "none found among N", never nothing. The matching is pure and the runner is injected, which is why every branch is testable without the network.

---

## PR 753: auto-cycle phase 2 (current head)

**Read:** head `139f95ce98615d3327ecd88d3705fc73092d9302`, three commits after the head the earlier reader read (`9515a24ff...`). I read the diff between the two heads in full, and the whole of `read_handshake`, `offer_cycle`, `close_cycle`, `compute_falsifier_ratio`, `_use_counts_since_last_cycle` at the new head. Probes: a marker file in an isolated home, run through `read_handshake`, `offer_cycle`, `close_cycle` and the ratio.

### Status of the earlier reader's six findings

| # | Earlier finding | Now |
|---|---|---|
| 1 | Valid JSON with no/wrong `steps` read as completed | **Fixed.** Reproduced: `{}`, `steps: {}`, `steps: [1]` all return `None`. Steps whose values are junk give `any_step_failed=True`, the right direction. |
| 2 | Ratio: re-offers counted as failures; skipping cannot go red | **Half fixed.** Re-offers now close as the machine-only outcome `superseded`, which the ratio skips (reproduced: two offers then one `no-pull-honest` gives `(1, 1, 1.0)`; the log row says `superseded`). The other bias is untouched: `no-pull-honest` still counts toward the numerator, so a seat that always closes that way scores 100%. |
| 3 | Non-numeric values raise | **Mostly fixed, one hole left** (new finding 1 below). `"abc"`, null and `"12.5"` return `None`. |
| 4 | Duration from a UTC string via `time.mktime` | **Fixed from reading** (`calendar.timegm`); I could not reproduce either way on this machine (no `tzset`). |
| 5 | "used Nx since last cycle" reads the whole rest session | **Not addressed.** `_use_counts_since_last_cycle` is unchanged and reads `rest_session.json` completions; `close_cycle` does not reset it. I still did not check whether phase 1's sleep step resets it. |
| 6 | Path text drift | **CLI fixed** (`offer` docstring and refusal text use `marker_path()`). Two module docstrings still say `~/.divineos/auto_cycle_phase1_done.json` (see new finding 2). |

### Findings at this head, most serious first

1. **The "non-numbers return None" fix misses infinity.** `read_handshake` catches `(TypeError, ValueError)` around `float`/`int`, but `int(float("inf"))` raises `OverflowError`. Reproduced: a marker with `"phase1_tokens_used": 1e999` (JSON parses that to infinity) raises `OverflowError: cannot convert float infinity to integer` out of `read_handshake`; so does `budget_remaining_est: -1e999`. `trigger_context_pct: 1e999` is handled (`isfinite`). The CLI has no `try`, so this is a traceback rather than "refusing to fire". Fails loud and does not fire, so low, but it is the same defect the commit says it closed and the new test for it does not cover infinity. Adding `OverflowError` to the except tuple fixes it.
2. **The ratio still cannot go red from skipping** (earlier finding 2, second half, unchanged). `compute_falsifier_ratio` counts `no-pull-honest` as success, while the module docstring says no-pull-forced outcomes count against the mechanism. With `superseded` now excluded, a seat that closes every cycle `no-pull-honest` reads 100% and the "dead-writing infrastructure" alarm cannot fire from it. From reading, not run.
3. **The mirror line is not "since last cycle"** (earlier finding 5, unchanged), so the "used Nx" figure the seat sees grows over the whole rest session.
4. **Stale text remains.** The module docstring lines 10 and 44 still name `~/.divineos/auto_cycle_phase1_done.json`, the confusion the CLI fix just removed; the `CloseOutcome.outcome` comment (`# "chose:<key>" | "no-pull-honest" | "timeout" | "aborted"`) omits `superseded`. Low.
5. **Nothing surfaces how often offers are superseded.** `superseded` rows are written to the audit log and skipped by the ratio, so a seat that never closes a cycle and keeps re-offering leaves a log of only superseded rows and a ratio of `None` with no hint why. A count in the CLI summary would make it countable. From reading; low.

New code from the fix commits introduced no wrong behaviour I could find: `_machine=True` is a keyword-only private flag the CLI cannot pass; the `superseded` outcome is rejected by `_outcome_is_valid` from the command line; `offer` still only supersedes a pending marker that exists. 71 tests in `tests/test_auto_cycle_phase2.py` pass at this head.

### Could not check
- The timezone reproduction (Windows, no `time.tzset`).
- A real phase 1 to phase 2 run; I attacked the marker by hand-writing it. I did not run `auto-cycle fire`.
- Whether phase 1's sleep resets `rest_session.json` (finding 3).

### One thing it gets right
Making the machine's own outcome a separate value that the CLI cannot be given, instead of letting the seat's `aborted` carry two meanings, is the right shape: the ratio's two biases were one number doing two jobs, and the fix pulls one of them out without changing what a seat is allowed to say.

---

## Counts

| PR | High | Medium | Low |
|---|---|---|---|
| 772 | 0 | 2 | 1 |
| 773 | 0 | 1 | 2 |
| 753 (current head) | 0 | 2 | 3 |
