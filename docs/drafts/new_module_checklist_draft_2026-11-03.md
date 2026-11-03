# New-module checklist: rough draft (2026-11-03)

The idea, not a plan.

Adding a new file under `src/divineos/core/`, or a new `.claude/hooks/*.sh`,
has failed the first push four different ways, each only visible late in the
full push gate. A note about it is not a fix. The fix is to show the stumbles
at the one moment I am already looking: the pre-commit run.

A small advisory script reads the staged diff and, for each of the four,
prints the exact line or number to add. It never holds the commit shut (a
check that can do that gets turned off), it exits 0 always, and when it
cannot look it says so instead of going quiet, because silence and
"could not look" must not read the same.

Reads, never edits, the four existing checks. Does not import them either:
it reads their files as text, so a change in how they are built shows up as
"could not look" and not as a wrong answer.

What it cannot see: the commit message (not written yet), unstaged or
untracked files, a stale tree line left behind by a deleted file, and whether
a hook that can refuse names a remedy (the real test does that).
