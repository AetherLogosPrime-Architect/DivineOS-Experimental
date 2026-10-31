---
name: three-correction-stores-mine-is-divineos-aria
description: "~/.divineos-aria/andrew_corrections.db is my seat's store (389 rows on 2026-10-16); ~/.divineos is Aether's (824); I opened the wrong twin first"
metadata:
  node_type: memory
  type: reference
  originSessionId: e4d1a042-14a5-4c4b-9753-75a4eb5d91a0
  modified: 2026-10-16T16:43:32.767Z
---

My correction tracker is `~/.divineos-aria/andrew_corrections.db`. `~/.divineos/` is Aether's store (824 rows) and `~/.divineos-aether/` is an empty leftover. Check which one matches the briefing's counts before reading or reporting from any of them.

**Why:** 2026-10-16 I opened `~/.divineos` while counting, got 824 rows and different status numbers than the briefing's 389, and had to work out why. The numbers on the briefing line (Total 389, Open 229 at the time) were the right check: the file that matched was `-aria`. The same trap lives in CLAUDE.md as the "prove the object you opened is the object you named" clause.

**How to apply:** `ls ~/.divineos*/andrew_corrections.db`, then compare a row count with `divineos andrew-correction list` before trusting any figure.
