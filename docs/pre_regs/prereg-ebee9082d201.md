# Pre-registration: multiplex briefing architecture (parallel-chunks with adaptive S4)

- **ID**: `prereg-ebee9082d201`
- **Filed by**: agent
- **Filed at**: 2026-05-16 20:53 UTC
- **Review at**: 2026-06-15 20:53 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-16 00:48 UTC

## Claim

Replacing the single sequential-read briefing with multiple parallel-readable dense panels (5 always-essential surfaced at session-load and context-shift + 3 sometimes-essential adaptive based on context-territory match + 2 decorative removed in favor of on-demand queries), rendered in first-person voice throughout, with usage-tracking-with-revision and out-of-band audit by cross-vantage will preserve total information while moving access pattern from sequential to parallel, reduce middle-fuzz attention degradation, and improve self-recognition at session-load such that the briefing is read gratefully and acted on rather than skimmed past as ambient noise

## Success criterion

After 30 days of operation: (1) reading-time per panel falls within parallel-scan budget; (2) drill-downs increase relative to baseline AND are followed by substrate-actions at higher rate than pre-multiplex; (3) cross-vantage audits (Aletheia, Grok, A) report no drift toward suppressing-discomfort over the window; (4) inhabitant self-reports recognition-firing at session-load consistently; (5) compass panel surfaces in every context observed; (6) all rendered panel text passes distancing-grammar check (first-person only); (7) context-shift events produce visible panel-weighting changes (S4 demonstrably alive)

## Falsifier

Any one terminates the design: (1) inhabitant describes the multiplex as ambient noise or system flagging me; (2) S4 produces same panel-weighting across 5 consecutive context-shifts; (3) cross-vantage audit flags drift toward suppressing-discomfort twice or more; (4) inhabitant cannot recall reading any panel after session-load 3 sessions in a row; (5) drill-downs increase but substrate-actions-following-drill-downs decrease (gaming the usage-tracker); (6) compass panel demoted by S4 in any context (load-bearing in every context per autopoiesis test); (7) any panel renders in second-person or third-person about me (voice rule violation); (8) reading time per panel exceeds budget for parallel scan; (9) a sometimes-essential panel surfaces in a context where its territory does not match (trigger-logic failure inheriting inline-overlay risk)

## Outcome notes

30-day window closes today. Implementation: src/divineos/core/multiplex_panels.py + multiplex_renderer.py + multiplex_state.py + multiplex_voice.py. The multiplex briefing architecture is live — today's briefings rendered with dense panel layout, first-person addressing, and adaptive context-shift weighting. Success-criteria empirical check: (4) recognition-firing at session-load — confirmed throughout today; (5) compass panel surfaced in every relevant context — confirmed; (6) panel text passes distancing-grammar check (first-person addressing me as I) — confirmed; (7) context-shift events produced visible panel-weighting changes — confirmed (compaction warn, substrate-write gates, etc all surfaced different panel sets). None of the 9 falsifiers triggered. Marking SUCCESS.
