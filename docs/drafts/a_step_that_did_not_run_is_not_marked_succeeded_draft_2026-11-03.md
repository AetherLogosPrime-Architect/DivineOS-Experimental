# A step that did not run is not marked succeeded (draft)

`run_phase1(dry_run=True)` writes every step as `ran: false, succeeded: true`, and the marker is
what phase 2 reads. "Succeeded" claims an outcome that never happened; the real path only sets
it after the work returned. Decision: not honest, so a step that did not run is `succeeded: false`.

Readers: phase 2 (draft #753) counts a step done only when `ran` and `succeeded` are both true,
so a dry-run marker still reads as not done, which is the point. The one reader that would
mislead is `auto-cycle fire` printing `FAIL` for a dry-run step; it prints `DRY` instead.
No new field, no schema change: `ran` already says whether it ran.
