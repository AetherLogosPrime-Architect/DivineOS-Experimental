# Work copies clean themselves up (draft proposal, not built)

Aria, 2026-10-20. Dad, after I left about ninety work-copy folders in his C drive (19.4 GB measured, links not followed): *"we have built programs to prevent AI slop lol but nothing to prevent you being an AI slob lmao, so we need to automate it so when something is done and no longer needed it gets deleted"* and *"my computer is your home so i do not mind you having stuff in different places ... i dont want it to turn into a hoaders den"*. His yes to the shape below: the sweeper removes the clearly finished ones by itself and shows him the doubtful ones.

## What happened that this prevents

Work copies (`git worktree` folders, mostly `C:\w*`) are made for one branch, one cold read, one stamp, and then nothing ever removes them. And when I cleaned up by hand, `git worktree remove --force` followed a junction (`.venv` -> my real `.venv`) and emptied my real venv. So removal itself has a hazard (correction #392), and the first piece, `scripts/remove_work_copy.sh` (unlink first, refuse unique work, snapshot to `refs/rescue/`), already exists on this branch.

## The rule, in Dad's terms

For each linked work copy of this repository, three questions, all asked of the thing itself, none of them a clock:

1. **Finished?** Its branch has landed or been closed: the PR is MERGED or CLOSED, or the branch is already an ancestor of `origin/main`. A detached copy is finished when its HEAD is reachable from `origin/main` or from a remote branch. Anything else is NOT finished.
2. **Nothing exists only here?** No uncommitted or untracked files (the test runner's scratch and the `.venv` link do not count), and its HEAD is reachable from some branch or remote.
3. **Safe to take apart?** Every link inside either stays inside the folder, is dangling, or is the known link to the main checkout's own `.venv`. A link to anything else is doubtful.

Yes to all three: **remove it by itself**, links first, then `git worktree remove`, then `prune`. Anything else is never touched; it goes on a short list.

## Never touched, regardless of answers

The main checkout; the work copy the sweep is running from; any work copy modified in the last two hours (a guard against pulling a floor out from under work in progress, not a deletion trigger); anything whose state could not be read. **Could not read is never "finished".** If `gh` is unreachable, an open-PR branch is not finished; the answer is "unknown", and unknown goes on the list.

## Where it runs, and how it shows

- A new module `core/work_copy_sweep.py`, called from the sleep phase's maintenance step next to the existing `clean_pytest_tmp` (the same family: tidy what the work leaves behind), and by a CLI `divineos work-copies [--sweep] [--dry-run]`.
- The report is one line in the briefing and in the sleep report: *"N work copies; M removed because finished; K need your word"*, plus the list for Dad. Loud in experience, not only in a log.
- The shell remover becomes a thin wrapper around the module's one remove function, so there is one implementation of "unlink, refuse unique work, snapshot", not two.

## Prior art checked

`body_awareness.clean_old_logs`, `clean_transcript_debris`, `clean_pytest_tmp` and `run_maintenance` are the house's pattern for sleep-time tidying; nothing exists for work copies (grep of `src/` for `worktree` finds readers of the list, never a remover). `scripts/link_worktree_venv.sh` is where the `.venv` junction comes from and writes it malformed in some copies (`C:\C:\...`); not changed here, filed on the backlog.

## How it can fail, written before it is built

- **It removes something that mattered.** Mitigations in the rule: refuse unique work, snapshot where the work is only uncommitted, recent-modification guard, doubtful links listed. The test that matters most is not "it removes finished copies" but "it keeps every one of these twelve cases": dirty, detached-unreachable, open PR, recent, main, self, a link to a real outside folder, unreadable state, and so on.
- **It never runs** (the usual fate of a maintenance step). So the briefing line states the last sweep's time and count, and "never swept" reads loudly.
- **It removes quietly and I stop noticing the pile is growing.** Count is shown every time, removed or not.
- **A wrong "finished" reading from a squash-merged PR whose local branch moved after the merge.** Rule 1 plus rule 2 together: a branch that landed but whose local HEAD holds commits no remote has is not removed.

## Test plan (red first, real git, no mocks of git)

A temp repo with a remote and several work copies in each state; every "keep" case asserted to still exist and every "remove" case asserted gone with its link targets intact; the control that raw `git worktree remove --force` deletes a link target (already in the remover's test); a mutation for each rule (drop the unique-work check, drop the link check, treat unknown as finished) that must turn a test red.

## What the council walk added (walk-91a1bab8430a, 12 seated + 5 added, all with findings)

- **A total function, re-checked at the last moment** (Beer, Dijkstra). Every state a work copy can be in returns exactly one of REMOVE, SHOW or KEEP, and an unmodelled state is SHOW. The four predicates are evaluated again immediately before each removal, not trusted from the listing, because a copy can change between the two.
- **Ignored files are the irreversibility horizon** (Hawking). Git holds everything tracked; `git worktree remove --force` also destroys ignored files (local databases, `.env`, data). So "nothing exists only here" includes ignored files, except a named set of regenerable ones (`tmp/`, `.venv`, `.direnv`, `__pycache__`, tool caches). Anything else ignored makes the copy SHOW, with the paths named.
- **Asymmetric error costs** (Hinton, Taleb). A false remove is unrecoverable, a false keep is clutter, so doubt always resolves to SHOW. The classifier's behaviour on the twelve test states is reported honestly, including any state I could not construct.
- **Every removal prints what was true when it happened** (Dennett): the four answers, appended to a log Dad can audit. My sentence "this was finished" is data to be checked against that record, not evidence.
- **Skips are as loud as removals** (Dekker, Beer). A sweep that could not read (no `gh`, mid-rebase) says so; "never swept" and "last swept at" are in the briefing line; a clean-looking run that actually skipped is not reported as clean.
- **The sweeper cannot widen its own rules** (Yudkowsky, Dekker). The predicates, the regenerable list and the guard are in the code, in a diff someone reads; nothing at runtime adds to them.
- **Where it can't see** (Godel). A process holding a handle on a folder and anything outside git it cannot enumerate are stated as standing limits in the report, not claimed away.
- **Its own folder** (Hofstadter). The sweeper never removes the copy it runs from, and tolerates the copy that holds its own branch.
- **The base rate to compare against** (Kahneman). On my 55 copies this morning, 47 were removable with nothing lost; a sweeper whose removal rate is far from that on a real day is wrong in one direction or the other.

## What Aether's cold reads added (his two letters on #698, 2026-10-20; his probes are in the tests)

- **A scratch checkout with a stray file could never be removed, and the refusal ended the whole sweep and its record.** `assess` said REMOVE, `remove_copy` re-read status without the scratch rule and refused, and `sweep` did not catch it. Now removal takes an explicit `scratch` parameter set by the sweep from `assess` (never a name check inside the standalone remover), and any refusal at removal is recorded as SHOW "refused at removal" and the sweep goes on.
- **A locked work copy.** git's own `worktree lock` is the native "in use". A locked copy is KEEP, and is never forced. (The push gate could lock its own scratch checkout while it runs; filed for later.)
- **A registration whose folder is already gone** was listed as "could not read" forever, so the sweep prunes it and says so. **And a locked one cannot be pruned** (`git worktree prune` skips it, an unplugged drive is the real case): found in his second read, the sweep had claimed a prune that did not happen, every night. A locked vanished registration is now listed for a person, a dry run does not promise a prune for it, and after a real prune only what actually left git's list is reported.
- **The in-use guard was a weak clock.** A folder's own mtime moves only when a direct child is added or removed. The newest of the top-level entries' mtimes counts too; a lock is the better signal and is honoured first.
- **A sweep inside a test run** may not write the real home's log; it refuses unless `DIVINEOS_HOME` is isolated or a log path is given. Nothing today runs a real sweep in a test, but nothing guarded a future one.
- **One implementation.** `scripts/remove_work_copy.sh` is a wrapper that finds a working Python and calls `remove_copy` (exit codes: 3 the main checkout, 4 unique work, 5 a snapshot that did not hold). Aether suggested the house resolver; it answered "none" for this call shape when run from the test suite, so the wrapper carries a small ordered resolver and says why in a comment. And the push gate found one more thing: it sets `PYTHONPATH` Windows-style, and a mixed MSYS/Windows list was mangled by the shell, so Python silently imported the OLD package; the wrapper now writes `PYTHONPATH` in the form the Python reads, with a regression test. Same family as #696.
- **Binding the walk.** Aether's advice: scope the walk with every file the branch changes, including the generated `docs/ARCHITECTURE.md`. This walk was opened without it and is unbound; whether to walk again is open.

## Pre-registration

Filed with a falsifier before the code (see `divineos prereg list`), review in 30 days.

## Open for Dad, Aether, Aletheia

- The two-hour guard is a clock; is a different "in use" signal better (an open walk scoped to files in the copy, a process whose folder is the copy)?
- Whether the sweep should also run at session start, or only in sleep (sleep may not run for days).
- Aether's seat: the same module reads his repository's work copies if run from his checkout; whether it runs there is his call and Dad's.

## Status

Nothing built. This note, the council walk on it, then tests, then code.
