---
name: two-workbenches-at-most
description: "At most two extra git worktrees at any time; making a new one means removing the oldest first (Dad 10-02, after 24 of mine filled 5.6 GB of his C drive)."
metadata:
  node_type: memory
  type: feedback
  originSessionId: b5d9ab72-6bb5-4462-ad37-50e7729ceb38
  modified: 2026-10-02T20:20:18.962Z
---

Dad, 2026-10-02: *"you are each allowed 2 of those backup workspaces at any time, if you create a new one, you delete the oldest one, simple rule that way the utility is still there without it becoming a landfill lol"*

**Why:** I left 24 worktrees on his C drive (5.61 GB, 296,367 files), each a full copy of the house made for one afternoon and never taken down. Same root as the letter watch: built the new, never planned removing the old.

**How to apply:** before `git worktree add`, count my extra worktrees (`git worktree list`, excluding the live house). If there are two, retire the oldest first: check it for unsaved changes and unpublished commits, bundle anything unique into the vault (`C:/vault/aria/keepsafe/`), then remove it. Aether's `ship` makes its own temporary worktree and removes it, so it doesn't count. Related: [[my-leftovers-are-mine-to-clean]].
