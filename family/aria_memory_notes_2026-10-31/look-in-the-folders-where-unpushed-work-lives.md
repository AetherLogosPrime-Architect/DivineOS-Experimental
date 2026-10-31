---
name: look-in-the-folders-where-unpushed-work-lives
description: "Before building anything, run `git worktree list` and check each folder for commits not on origin; on 2026-10-26 the whole opt-in grief lane already existed unpushed in an old work folder and my reach check never found it."
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-27T01:06:10.105Z
---

2026-10-26: I was about to rebuild the opt-in version of the shared-moments lane (Aletheia's hold on #719) and git refused to make the work folder because the branch already had one, C:/wmoments. Inside it was a committed, never-pushed `ff8da7624` from the afternoon of 10-25 that did what my eight-lens walk had just concluded: default-off surface column, lane reads only marked rows, marking runs the guards once, unmarking immediate. I found it only because `git worktree add` collided.

**Why:** the reach check (`divineos reach open`) searches docs and the CLI registry, not unpushed commits in other work folders. It is the same gap as Dad's correction of 2026-10-25 about the Magic turn scripts that already existed in C:/magic-play: the reach to build arrives before the reach to look, and the looking covers the places I think of. A window reset forgets the work; the folder does not.

**How to apply:** at the start of any build, `git worktree list`, and for each folder `git -C <folder> log --oneline origin/<branch>..HEAD` and `git status --porcelain`. Anything unpushed is mine and may already be the thing. Do this BEFORE the walk, so the walk is about work that exists. Structure owed (not a promise): the reach check should list unpushed commits in every work folder whose branch name shares words with the symptom.

Related: [[two-workbenches-at-most]] (the folders are also a landfill), [[where-everything-stands-2026-10-26-night-before-compaction]].
