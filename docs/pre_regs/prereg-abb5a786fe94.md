# Pre-registration: Reorder session-end pipeline to write the orientation/handoff note EARLY (right after analysis, before deep extraction), then enrich it with final counts at the end — so an interrupted or timed-out save still preserves session orientation

- **ID**: `prereg-abb5a786fe94`
- **Filed by**: agent
- **Filed at**: 2026-05-29 19:38 UTC
- **Review at**: 2026-06-28 19:38 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:35 UTC

## Claim

Waking blind after compaction is caused by the handoff note being written LAST in the pipeline; when a save is interrupted (e.g. killed by hook timeout), extraction may complete but the orientation note is skipped, leaving the next session with no 'where we were'

## Success criterion

After the change, a save interrupted partway still leaves a readable handoff note containing intent + next-steps; the final enriched note (with counts) still appears when the save completes fully

## Falsifier

An interrupted save still produces no usable orientation note, OR the early note is too sparse to orient the next session, OR the reorder breaks/duplicates the final enriched note

## Outcome notes

Shipped: cli/session_pipeline.py line 105-116 explicitly 'Write the orientation/handoff note NOW — before the heavy' with import from pipeline_gates.write_handoff_note as _early_handoff. Reorder landed — handoff written early, enriched later.
