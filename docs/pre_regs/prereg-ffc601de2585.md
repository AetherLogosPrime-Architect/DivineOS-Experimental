# Pre-registration: Structured evidence pointers on all substrate record types (needs, corrections, decisions, compass observations, events, knowledge) with creation-time inline-required per-pointer narration, walk command displaying target content verbatim + supersession-chain traversal + provenance_tier marker + single-source-corroboration flag, plus divineos hooks status command for branching artifact detection

- **ID**: `prereg-ffc601de2585`
- **Filed by**: agent
- **Filed at**: 2026-07-03 20:06 UTC
- **Review at**: 2026-08-02 20:06 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Adding structured pointer fields (source_events, source_corrections, source_knowledge, source_observations) + provenance_tier + a divineos walk command that displays target content verbatim makes the audit chain walkable-from-CLI without SQLite skill, closes the memoir-vs-audit-chain gap Anvil surfaced 2026-07-02, and shifts Aletheia's manual-walk labor to trace-following

## Success criterion

Within 30 days of C1+C2 landing: (a) divineos walk <surface-id> reaches originating correction for any live warning without insider help, (b) at least one peer-audit (Anvil/Muse/Aletheia) confirms they can reach the walk unaided, (c) provenance_missing on new-record creation stays under 10%, (d) walk output includes target content verbatim not just resolution-confirmation, (e) provenance_tier distinguishes cited_at_source from backfilled_by_llm and pointer_added_post_compaction, (f) new record types inherit pointer-provenance requirements by default per Q-tier

## Falsifier

Within 30 days: (a) walk fails to reach an originating correction for a live warning, OR (b) more than 10% of new records file with provenance_missing true without acknowledged reason, OR (c) pointer fields become ceremonial slot with placeholder values, OR (d) discovered case where all pointers resolve but surface claim unsupported by resolved content (resolution-is-necessary-not-sufficient enforcement failed), OR (e) new v3 record type ships without pointer fields without explicit boundary-vantage justification
