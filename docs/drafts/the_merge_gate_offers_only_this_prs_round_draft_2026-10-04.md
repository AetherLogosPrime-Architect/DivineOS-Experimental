# The merge gate offers only this PR's own round (draft, written 2026-10-04, carried onto the branch 2026-10-08)

## The idea

When #588 was merged, the gate's ready-to-paste merge command offered #582's round, the newest valid one in the store, and the tree of the live checkout. A round that reviewed a different pull request, and a tree that was not the pull request's, were handed out as if they belonged to it.

## What changes

- A round is usable for a pull request only if its confirms are titled with that pull request's number (`CONFIRMS: #<n>`), so one approval can never quietly stand in for another.
- The tree-hash in the handed-out trailer comes from the PR head on GitHub, not from whichever checkout the command ran in. The local-tree lookup is removed.

## How we would know

Four new tests fail against the old gate and pass against this one; the walks that thought it through are `walk-9e7c75ada432` and `walk-a11532238e5a`.

## Open question, named on 2026-10-08

Whether handing out a tree-hash at all is right for a squash merge. A squash commit's tree is main plus the branch, which cannot equal the PR head's tree once main has moved: #582 went red on exactly that. Aletheia's ruling (2026-10-08) is that this branch's binding stays, and the audit changes to compare the trailer with the PR head GitHub recorded at merge time rather than with the squashed result. This branch should merge after that audit change, and until then `ship` composes the round only.
