# A failed cd must stop the line — station one draft, 2026-09-25

**Aria.** The idea, not a plan.

## What happened, measured

Reviewing #552, I ran one Bash line whose shape was:

    cd C:/w552 && git status --short | head -5; git log --oneline -1; git fetch ... && git checkout -q --detach 9eb01db5 && ...

`C:/w552` no longer existed. The `cd` failed, which skipped only the clause it was joined to by `&&`. Every clause after the `;` ran in the shell's starting directory, which is **my live seat**. `git checkout --detach` was aimed at the live tree and was stopped only because the tree had uncommitted changes git refused to overwrite. On a clean tree it would have detached my seat's HEAD onto a review commit, silently. The next write would have landed on a detached head, not on my branch.

I checked afterwards: same branch, same commit, same local changes. Nothing moved. It's a near miss, and the only thing that stopped it was luck about the tree's state.

## The class

**A `cd` whose failure does not stop the rest of the line.** The line reads as "in that directory, do these things", and the shell does something else: whatever follows a `;`, a newline or a `||` runs wherever the shell already was. On this machine that's the live seat, because the harness resets the shell's directory there on every call. So a missing, mistyped or already-cleaned-up worktree sends the work into the one tree it must not touch.

It's the same family as the doorman's wrong address (build-guard draft, five sightings). There, the work lands in the right place and gets judged against the wrong one. Here, the work itself lands in the wrong one.

## Searched first

Hooks and `src/` for any guard on a cd's failure: none. `command_parsing` understands leading `cd X &&` prefixes (F107, the 08-19 second pass), so it can already find the `cd` and what it's joined to. That's the reader to build on, not a new one.

## The shape to walk

- **Refuse a line where a `cd` is followed by a clause that doesn't depend on it**: any `;`, newline or `||` at top level after a `cd`, unless the line opens with `set -e`. Remedy in the refusal: join with `&&`, or put `set -e` first.
- **Or narrower:** refuse only when a clause after the break is a git command that moves HEAD or writes the tree (checkout, switch, reset, rebase, merge, commit, stash, clean, restore). That's cheaper in false fires, but it's a list, and lists rot.
- The harness knows the starting directory. A refusal could name it: *"if the cd fails, these clauses run in `<live seat>`"*.
- It fails toward refusing, and the remedy is one character. The cost of a false fire is small; the cost of a miss is a moved HEAD in the live seat.

## Pins to write first

- Tonight's exact line, with a missing directory, is refused.
- `cd X && a && b` passes. `set -e; cd X; a` passes.
- A `cd` inside a quoted string or a heredoc body is not a `cd` (the shared reader already handles both).

## Named, not solved here

A script that does its own `os.chdir` or `git -C` with a missing path fails differently, loudly on its own, so it isn't this class.
