# The work-copy sweep tells "no pull request" apart from "could not read" (rough draft, 2026-11-12, nothing built)

Found 2026-11-12 while Dad asked about his C drive: `divineos.core.work_copy_sweep` listed "could not read the state of 19" copies and could clear none of them. Aether confirmed it from his side the same morning ("real and unfixed").

## What is true now (read from origin/main, not recalled)
`gh_pr_info(branch)` (work_copy_sweep.py, line 85) returns `None` in three different situations: `gh` exited non-zero, the output could not be parsed or the call timed out, **and** the listing succeeded and was simply empty, because the branch has never had a pull request. `_assess_copy` then writes the same reason for all three ("could not read the pull request state, so the branch is not known to be finished"), and the report's `could_not_read` count (line ~547) counts reasons that start with "could not read". So a branch that never had a PR is reported as an outage, and a real outage is lost among them: the failure-shares-empty shape the pre-commit scan names. The design draft of 2026-10-20 says "a clean-looking run that actually skipped is not reported as clean" and "unknown goes on the list"; the count today overstates the unknown and so hides the real one.

## The idea
`gh_pr_info` returns three distinguishable answers: a state and head (a PR exists), a named "none" (the listing worked and no PR from this branch exists), and `None` only when it could not look. `_assess_copy` writes a different, true reason for none: "this branch has never had a pull request, so nothing says it landed". The verdict for such a copy stays SHOW: nothing in this change makes a copy easier to remove. Only the reason, and the count of what could not be read, become true.

## What it must not do
It must not turn "no PR" into "finished". It must not loosen the "could not read is never finished" rule, the two-hour guard, or the four answers re-asked before each removal. Whether a no-PR branch that is clean and published should be removable automatically is Aether's open question to Dad ("make the clean-up automatic, so a folder disappears on its own once its work has landed?") and is not decided here.

## Questions for the walk
- Is a sentinel (a named constant, a tiny enum) better than a new tuple shape, given `PrInfo = Callable[[str], "tuple[str, str] | None"]` and the test world's `w.pr` fake?
- The count: add a separate `no_pr` number to the summary, or fold it into the doubtful list without a number?
- Does anything else call `gh_pr_info` or read the reason text (the briefing line, the maintenance run)?

## Tests, red first
A branch with no PR reads as "never had a pull request" and not as "could not read"; a failed `gh` call still reads as could-not-read and is counted; the no-PR copy is still SHOW (never REMOVE); the summary's could-not-read number counts only real failures.

## Falsifier
After the change, run the dry-run sweep on this machine: if the nineteen still all read "could not read", or any of them became removable, the change is wrong.

## Walk (walk-18c6b3630142, 8 lenses, every finding quotes its lens) and what it changed
- Lamport: a specification table first (the comment above the new tests, one row per case).
- Knuth: a boundary the draft missed, a row with a missing or empty `state`, which today fell into "pull request state is , not finished"; it is now unreadable, with a test.
- Feathers: pin what it does today first (the 41-copy dry run: 40 need a word, could not read 19).
- Meadows, Foucault, Deming: break the loop at the count, name the class so a person can decide about it, and do not loosen any verdict; the new tests pin that a no-PR copy is never REMOVE.
- Taleb, Dijkstra: remove the ambiguity and add no rule; the lookup returns an outcome, the assessor alone turns it into a reason.

## Result
`gh_pr_info` returns `NO_PULL_REQUEST = ("NONE", "")` when the lookup worked and no PR exists, `None` only for a real failure or an unusable row. New reason: "this branch has never had a pull request, so nothing says it landed (not finished)". 47 tests in tests/test_work_copy_sweep.py pass (10 new, red first: 6 failed before the change, the 4 that already passed pin the unchanged behaviour). Dry run on this machine after the change: 13 work copies, 0 removable, 11 need a word, 2 in use, and no "could not read" clause; five copies now say they never had a pull request. Nothing became removable.

## Not decided here
Whether a clean, published branch with no pull request should be removable automatically is Aether's open question to Dad.
