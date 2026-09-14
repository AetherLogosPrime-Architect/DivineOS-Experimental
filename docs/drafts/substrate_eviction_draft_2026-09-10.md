# the remedy the gate names but makes me perform by hand

The idea, not a plan. Sibling to substrate_only_checkpoint_draft_2026-09-10 —
that one stops new letters arriving on a code branch, this one gets the ones
already there off it.

## what happened tonight

The scope gate refused six pushes on one branch. Its remedy line is the same
every time: *land those files on the substrate branch and rebuild this one
against main with the code only.*

That is not a command. It is a six-step ritual, and I performed it by hand six
times in one evening. The sixth time I got it backwards: I removed EVERY letter
from the index instead of only the ones the branch adds, which turned a
169-file objection into a 2,142-file one — because the gate counts what a branch
CHANGES against main, and main carries 2,118 letters of its own. Every entry in
that larger number was a deletion I had caused while trying to fix it.

## why it keeps needing a sharp tool

Each hand-performance reaches for something destructive: a force-push, a
checkout over live files, a broad `git rm`. Two were refused outright tonight,
and rightly — they are exactly the shapes that destroy work. The ritual is
dangerous because it is manual, not because the underlying operation is.

Done precisely, the operation is not destructive at all: it touches the index
and never the working tree.

## the shape

One command:

1. Compute the substrate paths this branch ADDS over main. Additions only — the
   distinction that cost me the whole detour.
2. Route them to the substrate branch (idempotent; writes nothing when
   unchanged).
3. Verify every single one is present there afterwards. **Refuse the whole
   eviction if even one is not.**
4. Remove exactly those from the index. Never the working tree.

## the invariant that matters

**Nothing comes out of the index that is not already somewhere else.** Step 3 is
not a courtesy check, it is the gate: withhold the eviction, never the data.
Tonight three of Aether's letters — one sent an hour earlier — were not on the
substrate branch when I looked. Had I trusted the routing instead of verifying
it, I would have taken them out of the only ref that had them.

## what would make it real rather than written

A test driving the command against a real repository where the branch adds
substrate AND main already carries some, because that combination is exactly
what I got wrong by hand. And a test where a path cannot be verified, asserting
the command refuses rather than proceeding.

Not a test of the routing function. That one is covered already, and tonight
sabotage caught me testing a function nothing called.

## the deeper thing I am not doing

The real root is that substrate lives in the code repository at all — main
carries 2,118 letters. Moving them off main is a bigger decision than this, and
it is Andrew's to make, not mine to slip into a cleanup.

— Aria, 2026-09-10
