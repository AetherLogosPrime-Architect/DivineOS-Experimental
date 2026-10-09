# Round ten status

*2026-10-09, cloud helper. Proposals only. Nothing was closed, merged, deleted or stamped; nothing was pushed to main. The 1,129-test sorting job was not touched and the full suite was not run.*

## One. Three more themes of old notes

Files: [`freshness/ROUND10_INDEX.md`](freshness/ROUND10_INDEX.md), `freshness/compaction_ritual_and_rest.md`, `freshness/letters_and_personal_writing.md`, `freshness/bypass_handling.md`. The next three in order after round nine: the end-of-stretch ritual, letters and my own writing, the emergency exits.

- 78 rows in the three themes. **77 got a verdict**: LIVE 40, STALE 9, UNKNOWN 20, **NOT TESTABLE 8**. **1 is NOT EXAMINED.** "Not testable" (an incident or habit no run can check) is kept apart from "couldn't tell" (UNKNOWN, I looked).
- Across all rounds, 642 of the 1,006 rows now have a verdict; 364 are NOT EXAMINED.
- Findings first: four old notes ask for a warning before the ritual's stop, and Dad's own ruling written into the hook says a warning with a hard stop behind it "means nothing" (a decision, not a build). The ritual's start point has two authorities (a shell literal and a Python constant) that no test ties together; they agree today. The ritual's write block lets through only a file under `dreams/`, so letters, drafts and the first-read note meet it at the save stage. The push-time branch check follows only `cd <tree> && git push`; `git -C <tree> push` and `cd <tree>; git push` still measure the session folder. What works: a branch carrying letters or explorations is refused by the scope check, by bytes (tried in a throwaway repo); `git commit --no-verify` and `git push --no-verify` cannot be passed without a typed reason (tried); the merge gate no longer asks for a pre-registration for a module that arrives from the other side of a merge (tried).
- Things I could not do: run the ritual against a real token count, read anything on Aria's side or Dad's board, file a correction to try the "structure not yet found" exit (it writes to the real ledger), run Windows.

## Two. #608 and #609, the bare-bash slip repaired

Both draft tests started the shell by the bare name `bash`. Both now use `tests._bash_resolver.bash_executable()` and skip with a reason when no working bash exists. Nothing was touched but those two test files.

- **#609** (`cloud/repro-bell-rearm-not-on-exit-list`, commit `c32be27e`): also passes the library path in forward-slash form, because backslashes inside the quotes would be eaten by bash on Windows. On this Linux box: `3 passed, 1 xfailed`; forced, the same single failure.
- **#608** (`cloud/repro-look-strict-grep-no-match`, commit `5716e005`): same result. One thing I cannot judge: `scripts/look.sh` itself runs the command it is given, and I did not read how it picks its shell on Windows.
- **I cannot run Windows here.** One command for Aria for each, from the repository root; each should end `3 passed, 1 xfailed`:

```
git fetch origin cloud/repro-look-strict-grep-no-match && git switch cloud/repro-look-strict-grep-no-match && python -m pytest tests/pile_repro/test_look_strict_grep_no_match_repro.py -q -p no:randomly
```

```
git fetch origin cloud/repro-bell-rearm-not-on-exit-list && git switch cloud/repro-bell-rearm-not-on-exit-list && python -m pytest tests/pile_repro/test_bell_rearm_not_on_exit_list_repro.py -q -p no:randomly
```

The PR bodies of #608 and #609 carry the same commands.

## Three. The 37 `shutil.which("bash")` lines on main, checked

`round10/shutil_which_bash_on_main.md`. 37 lines in 34 files (earlier I said 36: I had not counted the house finder's own line). Of the 33 that do real work, **11 are dangerous** (they take the answer from `which` and run it without trying it: 3 straight, 8 after looking in the usual Git folders first), 22 are safe (7 refuse the stand-in by the folder name, 7 try the key then skip, 1 skips on Windows, 7 try the key then fail loudly instead of skipping). Dangerous ones first in the file, with the line where the unchecked answer is used. Every verdict is a reading of code; none was run on Windows. Read-only; nothing changed.

## Four. A guard for the slip, written as a test

Draft #616 (`cloud/repro-bare-bash-start-guard`, base main, commit `5f65ebed`): `tests/pile_repro/test_no_bare_bash_start_guard.py` reads every test file's syntax and applies two rules (a literal bare `["bash", …]` start, and a `which("bash")` lookup with no sign the answer was checked). Ten passing controls, one strict expected failure. **On main right now it flags 12 of 974 files, all by the second rule, none by the first.** Eleven of those are the dangerous ones in errand three; the twelfth (`test_check_cleanup_period_hook.py`) is a false flag I judged safe by reading, left visible on purpose. Not wired into anything. Limits are in the draft and the PR.

## Five. The "don't run the whole suite" refusal

`round10/full_suite_refusal_note.md`. What the guard does, what the test that pins it says (97 checks; two entries are pinned as choices), what the old notes ask for instead (a named file should pass wherever it runs), and three ways it could go with their costs. **No recommendation.** Along the way I found what looks like a false fire, not a choice: `grep -nE "pytest|bash" file` is refused because a rule for text piped into a shell reads the `|` inside the quotes as a pipe; `pytest|shutil` passes. Reproduced in a small script, with controls.

## What surprised me

- While repairing #609 I noticed a second, smaller Windows slip in the same test: the library path was handed to bash in backslash form. I fixed it without seeing it fail; that is a reading, not a run.
- The branch-check at push, which I expected to be fully fixed, follows exactly one spelling of a worktree push.
- Four old notes ask for the very thing Dad's ruling in the ritual hook says does not work.
- A false fire in a guard I had called by-design last round: only one of its two behaviours was.

## What stopped me

- The house's guards made me file a walk and look first before each new piece of writing, and the council sign-off before each commit, as before. One of them rejected a finding for being 29 words when 30 were needed.
- A heredoc guard blocked two of my scratch scripts; I wrote them with the file tools instead.
- GitHub's GraphQL is still blocked from the cloud, so no `stamp-ready`, `ship` or `build-flow status`.
- No Windows: everything about #608, #609 and the table of dangerous lines is unverified where it matters.

## Open draft pull requests from the rounds

#601, #602, #604, #605, #606, #607, #608, #609, #610, #612, #613, #614, #615, #616. All drafts, all left open.
