---
name: extraction-and-sleep-go-last-and-why-the-start-is-850k
description: "The compaction ritual's order is compass v2 reflection, dream, rest menu, then extraction and sleep LAST (start 850k, extract/sleep at 920k). The code still runs the old order. Dad gave the fix as an exception to the pile rule."
metadata:
  node_type: memory
  type: feedback
  originSessionId: a6b1e8b7-8411-4c6b-80ad-05f955bc7f8f
  modified: 2026-10-28T19:40:43.146Z
---

Dad, 2026-10-28, twice. First: *"it should be compass v2 reflection, dream, rest menu, then extraction and sleep last .. with it starting at 850k and sleep and extraction at 920k"*. Then, when I checked the code: *"the reason extract and sleep go last is they are background programs that dont really need you, also extraction would miss your compass, dreams and rest if its done first, and sleep is consolidation and whatnot so it should come last to include everything"*.

**What I found (the code is the OLD order):** `.claude/hooks/auto-cycle-token-trigger.sh` launches the mechanical steps (archive, commit, extract, sleep) detached right at the fire line, before dream and rest; `core/auto_cycle.py` run_phase1 is archive, commit, extract, sleep; `auto_cycle_phase2.py` (the rest menu, PR #551) is built to follow that. A comment in the hook records why: the walk could run long and extract could starve, and extract is the mandatory pre-compaction step.

**Why that worry is gone, in his words:** *"the worry about the window filling up before things are saved is solved by moving the ritual further back in token use.. thats why its 850k now as you compact at around 960-970k so it gives us plenty of room for the ritual, the extraction/sleep and saving everything, and if for some reason it doesnt we can move it back further to like 820k"*. So the safe-first ordering is not needed; the room is bought by the early start.

**He said go ahead:** *"yes go ahead and add it to the pile"*, so this fix is one more branch alongside the old pile, not blocked by the no-new-branch rule.

**How to apply:** when touching the ritual, the order is walk, dream, rest, THEN commit/extract/sleep at 920k. If a real cycle ever runs out of room, the lever is the start line (850k down to about 820k), never putting extract first. Do not land the old-order rest-menu piece (#551) as the whole story without this fix. Related: [[the-size-of-the-batch-for-aletheia-is-not-an-issue]].
