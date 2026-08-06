# Pre-registration: Ship-side scope-discipline layer-3: supersession-check — surface when a branch's mechanism is already on main under different name

- **ID**: `prereg-90f462c4e98a`
- **Filed by**: agent
- **Filed at**: 2026-07-17 17:11 UTC
- **Review at**: 2026-08-16 17:11 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The two-layer scope-check (branch-diff + per-commit high-blast) catches worktree-orient sneaks but misses supersession-drift — a branch whose mechanism already shipped on main via a different-named PR. Aria's 2026-07-17 catch of #353's plasticity fix being already-live via #255 (June 22) surfaced this class. Layer-3 mechanism: for each substantive commit on a branch, check whether the primary function it touches already has an equivalent public-API implementation on main (via git log --follow + AST diff or LLM-summary compare). Signal not gate — surfaces the possibility, human/agent confirms real supersession vs coincidental function-name overlap.

## Success criterion

Over next 30 days: at least one branch that would have been shipped-and-redundant is caught by layer-3 before merge; no false-positive rate above 20% (layer-3 signals real supersession >=80% of the time when it fires); the check adds <=5s to safe_push runtime.

## Falsifier

If in 30 days: (a) any redundant-mechanism branch merges without layer-3 catching it (mechanism failed); OR (b) layer-3 fires with >20% false-positive rate (signal is noise); OR (c) the check adds >5s to safe_push (performance regression); OR (d) the check adds cognitive load without preventing any real supersession (theater); THEN the mechanism needs redesign or removal.
