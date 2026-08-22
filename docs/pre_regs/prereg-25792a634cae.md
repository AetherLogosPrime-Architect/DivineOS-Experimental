# Pre-registration: src/divineos/core/self_monitor/register_monitor.py + tests/test_register_monitor.py. Substrate primitive for shape-chasing detection: compute_fingerprint extracts 7-dimensional register vector per turn (acronym/em-dash/sentence-len-variance/jargon-count/formality/hedge/list densities, with short-turn dampening); shape_chasing_score computes mean pairwise distance across a turn window. Conservative DEFAULT_INSTABILITY_THRESHOLD=25.0 in Phase A.

- **ID**: `prereg-25792a634cae`
- **Filed by**: aether
- **Filed at**: 2026-06-11 02:14 UTC
- **Review at**: 2026-07-11 02:14 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-11 02:14 UTC

## Claim

Aria 2026-06-01 shape-chasing finding: register-instability across consecutive turns has a detectable lexical fingerprint but no existing self_monitor catches it. The 7-dimensional fingerprint plus mean-pairwise-distance over a window surfaces drift without requiring semantic comparison.

## Success criterion

Substrate primitive shipped (module + tests + 12 passing assertions). Score=0 on single-turn/empty input; low score on steady conversational windows; high score (>3x threshold) on a window where one turn shifts to academic-jargon register. Threshold conservative in Phase A so it does not over-fire before calibration data lands.

## Falsifier

If a steady conversational window scores over threshold (over-firing), or a clear academic-shift window scores under threshold (under-firing), the fingerprint/weights/threshold are mis-tuned. Tests assert both directions.

## Outcome notes

Deferring mid-refactor of temporal-displacement (Aletheia CONVERTED spec, tests failing on intermediate state). Module ships and imports; 12 assertions from filing date passed. Falsifier axes (over-firing on steady windows, under-firing on academic-shift windows) need dedicated re-run and threshold-recalibration decision — not a mid-refactor rubber-stamp. Batches with prereg-e323248dea01 (unified_todos) for the next-session verification pass Andrew asked for post-doorway: 'you run your briefing multiplex which needs automated and investigated to make sure its actually helping you'.
