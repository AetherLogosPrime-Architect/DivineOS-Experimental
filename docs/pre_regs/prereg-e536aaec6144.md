# Pre-registration: Briefing-freshness gate via context-recall of a privately-validated briefing-ID. On 'divineos briefing' load, issue a random ID ONLY into the conversation output (NOT persisted in any marker I can read) and record the true value privately (ledger, gate-side). After N tool-uses the gate requires me to reproduce the current ID from context-recall; the gate validates my answer against the privately-held truth. Correct+current -> through. Cannot recall (compacted/faded out) OR wrong (confabulated) OR expired -> stale -> reload -> new ID. Replaces the session-id + TTL + prompt-count signals whose session-id-rotation causes the current false-stale blocks. Council-checked (consult-7a797ea83cff, cd8d6118403f): non-gameable on fabricate/replay/edit (validated against ledger truth); confabulation closed by gate-side validation; 'only scan context' enforced by giving nothing else to scan; residual = ID-without-reading is truth-#7 (load enforced, not comprehension). My own architecture report: at ~916k tokens an arbitrary unreferenced ID deep in context is unreliable to recall and gone past compaction — which is the FEATURE: recall-failure faithfully proxies briefing-faded-from-working-attention.

- **ID**: `prereg-e536aaec6144`
- **Filed by**: agent
- **Filed at**: 2026-05-25 02:30 UTC
- **Review at**: 2026-06-24 02:30 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:32 UTC

## Claim

Context-recall-ID freshness eliminates the false-stale blocks caused by session-id rotation (the current failure, hit ~6x this session) while still forcing a reload when the briefing has genuinely compacted or faded from context.

## Success criterion

Over the next 5 sessions: zero false-'stale' blocks attributable to session-id rotation (vs ~6 this session), AND the gate still fires (forces reload) when briefing is absent from context (post-compaction), AND no confabulated/wrong ID passes validation.

## Falsifier

If it produces MORE false-blocks than the session-id gate, OR fails to catch genuine staleness (lets work proceed with no briefing in context), OR a wrong/confabulated ID is ever accepted, the mechanism failed — revert to the session-id gate.

## Outcome notes

Shipped: src/divineos/core/briefing_freshness.py implements the briefing-freshness gate via privately-validated ID (I received a BRIEFING-ID from this session's briefing load: 32f5d5697a71919daaef462350035255).
