# The gate says RED when it means I COULD NOT LOOK

**2026-09-22.** Rough. The idea, not a plan.

## What happened

Andrew closed his game to free memory so I could archive the oldest branch on
the server. The push failed anyway, with:

```
No module named divineos.core.subprocess_jobs
[push-readiness] BLOCKED — tests failing (exit 10).
[push-readiness] Fix locally, then push. Do NOT push red.
```

The tests are not failing. The module exists, imports fine under the project
python, and is on main. The gate copies the branch being pushed into a scratch
worktree and runs the suite THERE — and the branch is from 16 June, while the
runner module was added to main on 12 July.

So the branch does not contain the tool the gate needs to examine it.

## The class

**Could-not-look reported as found-a-fault.** This house has a name for it and
a three-valued answer everywhere else: HELD / OPEN / CANNOT_CHECK. The work-item
doorman says it outright — *an unreadable store is not an absence of work in
progress.* The push gate has two values where it needs three.

And the failure direction is the expensive one. A false RED does not merely
annoy: it says *fix it locally and do not push red* about a branch with nothing
wrong, and the honest reader obeys.

## What it has cost, and this is the part I did not expect

Every branch older than 12 July is unpushable from here and reads as broken.
That is not a hypothetical: there are branches in the pile from June and early
July, and the pile is the thing Andrew asked me to clear today. A fraction of
seventy-four may have been sitting behind a gate saying FAILING when it meant
CANNOT RUN — for two months, with nobody reading past the word.

I cannot yet say how many. That is a measurement I owe, not a claim.

## The idea

Before running the suite in the scratch worktree, check whether that worktree
contains what the runner needs. If it does not, do not run and do not say red.
Say CANNOT_CHECK, name the missing piece and the date it entered main, and let
the caller decide.

Then the archive path has an honest answer available: a branch too old to test
is not a branch that failed, and archiving it does not require pretending the
suite passed.

## What I am unsure about

**Does CANNOT_CHECK block or allow?** Blocking keeps the old branches stuck,
which is the whole problem. Allowing means a push with no test evidence, which
is what the gate exists to prevent.

My instinct is that it depends on the DESTINATION: pushing an old branch to
`archive/` touches nothing anyone runs, while merging one to main is exactly
where the suite must have run. That is a distinction the gate does not
currently draw and I am not certain it can draw it safely.

That is the question for the walk.

## What I expect to be wrong about

That the module is the only such dependency. If the gate needs three things
from the branch and I only check one, the next old branch fails differently and
I will have moved the false RED rather than removed it.
