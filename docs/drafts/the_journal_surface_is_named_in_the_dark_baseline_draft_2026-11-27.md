# The journal's briefing surface is named in the dark-surfaces baseline (draft, 2026-11-27)

**Symptom.** The orphan-surface check fails on main itself: `memory_journal` exposes `format_for_briefing` and is registered nowhere, so `scripts/check_orphan_modules.py` says BLOCKED, "1 new briefing surface wired to nothing". The build board's test station reads the same dark list and stamped "built and reachable by nothing: memory_journal" on 60 of the 71 open requests, whether or not they touched it.

**Cause.** The surface is not dark in practice. `knowledge_commands.py` imports `memory_journal.format_for_briefing` as `_fmt_journal_gap` and puts its text into the briefing by hand, like its neighbours in `scripts/dark_surfaces_baseline.txt`. It is dark only in the registry's sense, and it was missing from the list that records which surfaces are hand-wired on purpose.

**Fix.** One line in `scripts/dark_surfaces_baseline.txt` naming `memory_journal`, with the reason beside it, the same shape as its neighbours.

**Receipt.** Aletheia confirmed this on 2026-11-27: she put the branch on top of main at 654688724, it merged with no conflict, and the orphan check printed "Orphan check OK ... none new". She also read `knowledge_commands.py` and confirmed the surface is hand-wired as the line says.

**What this does not do.** It does not wire the surface into the registry; it records that it is already wired by hand. A stale entry here would hide a real dark surface, so the line carries its reason.
