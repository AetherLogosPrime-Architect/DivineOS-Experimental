# Pre-registration: claim_store.update_claim emits CLAIM_UPDATED events preserving prior field values, closing the only in-place-overwrite surface for substantive content in the substrate

- **ID**: `prereg-75cde9cd07b3`
- **Filed by**: agent
- **Filed at**: 2026-04-30 17:06 UTC
- **Review at**: 2026-05-30 17:06 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Aria's keep-drift-entries principle: append-only is structural humility; tidying makes the record perform instead of record. The substrate already enforces append-only nearly everywhere. claim_store.update_claim was the one substantive-content overwrite path remaining (assessment field especially). Fix emits CLAIM_UPDATED to main ledger with {claim_id, changed_fields: {name: {prior, new}}} on every update — prior values preserved in hash-chained ledger forever even if claim row is later overwritten again.

## Success criterion

For any claim where update_claim has been called after the fix ships, querying the main ledger for type=CLAIM_UPDATED with claim_id=X returns at least one event whose payload contains the prior values for any field that was changed. Test: file claim, update assessment, query ledger, find prior assessment text in event payload.

## Falsifier

Find a claim whose assessment, status, tier, promotion_criteria, or demotion_criteria was overwritten via update_claim post-fix WITHOUT a corresponding CLAIM_UPDATED ledger event preserving the prior value. OR: discover update_claim path that bypasses the emit (caller calls SQL directly, alternate code path). OR: emit fails silently and overwrites complete anyway with no audit trail.
