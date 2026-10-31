---
name: project-pile-sort-2026-10-12
description: "Evidence from sorting Aria's 14 old open PRs on 2026-10-12 after 621 and 626 merged; none had landed verbatim"
metadata:
  node_type: memory
  type: project
  originSessionId: 4a7d6a79-a3cb-46f7-ba1d-aa44fb7e7578
  modified: 2026-10-12T02:43:57.563Z
---

621 (merge 41ed09c62) and 626 (5559633d3) merged 2026-10-12 and read off GitHub. Dad said "start it" on sorting my old PRs.

Probe: for each branch, `git diff <merge-base> <branch>` then `git apply --check -R` against origin/main. Control on the merged 626 commit 1708278cd returned CONTROL-FINDS-LANDED, so the probe can find a landed change. Result: none of the 14 landed verbatim.

Apply clean to main (rebase-and-review candidates): 617 (non-draft, mergeable CLEAN), 611, 567, 553, 592, 597.
Conflict with main (each needs a read to say superseded vs carry): 603, 595, 594, 563, 558, 552, 551, 549.

**Why:** Dad wants the pile down; nothing is deleted outright, old-but-important goes to the archive, the rest to C:\DIVINE OS\TO BE DELETED, with a record. See [[standing-permission-volley-and-tidy]] and [[branch-removal-is-andrews-hand]].
**How to apply:** take the clean six first (catch up, round, Aletheia), then read each conflicting one against main before closing it. 628 read cold twice and 629 Reading line sent (letters 2026-10-12). Owed: lock-list fix (audit submit / file-external-confirm on build gate tuple and shell list), registry-derived voiced-actor test.
