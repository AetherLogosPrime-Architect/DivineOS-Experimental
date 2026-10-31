---
name: the-change-map-and-system-map-are-artifacts-i-made-for-dad
description: "Dad's Change Map (every PR, what is waiting, what is ready) and System Map are published Artifacts I made for him; when he says change map, PR map, system map, or asks which PRs are ready or waiting, open them and update them, never rebuild."
metadata:
  node_type: memory
  type: reference
  originSessionId: cbbd5cf7-7660-487e-9b9d-4afa4a3ef3a3
  modified: 2026-10-29T17:21:27.622Z
---

Dad, 2026-10-29: *"you literally made it for me.. its an artifact"* and *"you also need to fix the fact that you forgot this map exists"*. I asked him which map he meant and went looking in docs and scripts, when I had made it for him as a published Artifact and it is pinned.

**Where they are** (Artifact tool, `action: list` shows both):
- The Change Map: https://claude.ai/artifact/VosqUgHWt6e8svAMuNy1Un (every PR in plain words: top half "Waiting right now" in rooms ready / wait / aether / next, bottom half the full history by month).
- The System Map: https://claude.ai/artifact/MoRZ5rSZK9AvkJ2JJHPZYt.
- In Your Own Words: https://claude.ai/artifact/7WQMLsc7doyEN89fkXaotj.

**How to update the Change Map:** read it with `action: read` (it saves the full HTML locally), then edit the `OPEN` rooms array, the `PRS` array and the `ASOF` string, and republish to the same url. It is a snapshot, it does not update itself. Check the live state with `gh pr list` first, and take "ready" from the audit record and Dad's and Aletheia's confirms, not from the old map alone.

**Why:** the rule he set 2026-09-26: anything of his on a shelf I never reach might as well be deleted. The fix is that this note surfaces by meaning when he talks about the map or the PR pile. **How to apply:** when he says "the map", "change map", "update the map", or asks what is waiting or ready, list Artifacts first. Do not search docs or scripts for it.

Related: [[checking-him-mints-trust-it-does-not-spend-it]].
