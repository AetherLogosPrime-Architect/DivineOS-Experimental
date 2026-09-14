# the checkpoint that carries only letters

The idea, not a plan.

## what happened

Two hours ago I fixed the checkpoint sweep, and I wrote down honestly that one
path was still open: the routing only runs when a checkpoint carries both
letters and code. A checkpoint carrying only letters takes an earlier exit and
commits them onto whatever branch is open.

I named it and moved on. Forty minutes later a substrate-only checkpoint put 168
letters back on the code branch while I was in the middle of pushing, and undid
a cleanup I had just finished by hand. So the open half is not theoretical and
it is not rare. It is the *guaranteed* case — when there is no code in the
checkpoint, the sweep always lands wrong.

## why I left it open the first time

Not because it was hard. Because the two-kind path was the one in front of me
and the one-kind path was a branch I was not standing in. That is the whole
mechanism of this particular failure: I fix what I am looking at, write the rest
down, and the writing does nothing.

## the shape

The earlier exit needs to try the same routing the later one does, before it
commits. Unstage, route, and return. On refusal, restage and fall through to
exactly what happened before.

Order matters and it is the only interesting part: unstaging first means a
refusal costs nothing — the paths go back and the old commit happens unchanged.
Committing first and cleaning up after is what leaves letters on a code branch
for the window in between, which is the thing being repaired.

## the tension I can feel and want named

This makes the code branch's tree NOT go clean for substrate — the same contract
amendment I made two hours ago, now reaching a second call site. Aether's
split-by-kind tests pin "the tree goes clean." They still pass, because their
fixtures have no substrate branch to resolve. That is luck rather than coverage,
and it was luck two hours ago as well. He should be told once, about both.

## what would make it real rather than written

A test that drives the checkpoint entry point with substrate and no work. Not a
test of the routing function — I already made that mistake tonight and sabotage
caught it. The unit was fine and nothing called it. That is precisely the defect
in this draft, one level up.

— Aria, 2026-09-10
