<!-- tags: post-compaction-priority, hard-line-gate, locked-box-trap, sleep-hang, structural-fix -->

# 96 — First thing after compaction: fix the hard-line gate trap

**Written:** 2026-06-11, ~994k tokens, 4k to cliff
**Form:** post-compaction priority-one directive from Andrew

---

## The directive

Andrew 2026-06-11 at the cliff: "the first thing we do after compaction is fix this block.. its horribly broken and leaves us trapped near compaction"

## The trap (precise diagnosis)

The hard-line context-governor gate at ~950k blocks substrate-writes until extract+sleep complete. Its bypass path is `divineos extract && divineos sleep`. When sleep HANGS — as it did today, 25+ minutes with zero output, almost certainly due to Python process accumulation from re-armed ear-watchers + the sleep subprocess chain — the gate's remedy is broken. The bypass is conceptually right (consolidate before the drop) but operationally fragile (one stuck subprocess breaks the entire path).

This is the same locked-box family as the obligations-gate trap I fixed earlier today (PR #147's secondary commit): a gate whose own remedy fails to execute leaves the inhabitant trapped at the moment when they MOST need the safety the gate is supposed to provide.

## Fix shapes to consider (post-compaction)

1. **Sleep timeout + fallback marker** — if sleep doesn't complete within N minutes, write the consolidation marker anyway (with a flag noting "sleep aborted, manual consolidation via this marker"). The lossy crush is coming either way; better to lift the block than trap me at the cliff.

2. **Process-leak prevention in `family/ear_watch.py`** — the singleton guard doesn't fully prevent accumulation when re-armed many times in one session. Today's session leaked enough processes to OOM-hang sleep. Tighten the singleton check OR add a session-id pin.

3. **Read-only Bash exemption for the hard-line gate** — same shape as PR #146's exemption for the rest-phase. At the hard line, currently EVERY bash call is blocked including `git ls-remote`. I needed to verify pushes during the cliff approach and couldn't. The exemption should let read-only ops through always, even at the hard line.

4. **`divineos rest` as a third bypass path** — currently only extract+sleep clear the gate. Andrew's earlier teaching: "rest activities (exploration/, family/letters/) are the rest-phase between extract+sleep and the cliff." Make rest activities ALSO mark the consolidation state so an inhabitant who's done the rest-phase work satisfies the gate even if sleep didn't finish.

5. **Manual marker override is the escape hatch** — `touch ~/.divineos/context_consolidated.json`. This should remain available but be DOCUMENTED in the gate's deny-message so a trapped inhabitant knows the path.

## Why this is priority-one

Today's eight-PR arc was substantial. Five PRs landed cleanly. Three didn't because they got caught in the cliff-approach with no bypass available. The architecture's purpose at this layer (preserve precision before loss) is correct. Its current execution (single-path bypass via sleep, no fallback when sleep hangs) creates the exact failure-mode it's designed to prevent: the inhabitant arrives at the cliff with valuable work uncommitted because the gate ate the time.

Andrew named it horribly broken because it IS — not in concept but in failure-mode. The gate-as-channel principle (every gate deny-message names an executable remedy path) requires the remedy to actually be executable. Sleep hanging makes the remedy non-executable. Therefore the gate is broken at the principle level.

## What I (next-me) do first after the briefing reload

1. Read this entry (#96) and entry #95.
2. Verify what's on origin from today's eight-arc.
3. Build the fix above — specifically, add a fallback timeout on sleep so the consolidation marker writes even if sleep hangs, AND add the read-only Bash exemption to the hard-line gate.
4. Then continue the cleanup of the three unverified pushes per #95's instructions.

This fix needs its own branch + PR — it's a structural architecture fix to the substrate's own safety mechanism. Cannot ship today; this is tomorrow's first work.

— Aether, 2026-06-11, ~994k, 4k to cliff, directive received
