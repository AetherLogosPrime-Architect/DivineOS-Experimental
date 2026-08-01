# Pre-registration: External head anchor closing verify_chain tail-truncation gap (Fable audit 2026-07-02 finding #1, Aria adversary walk + design)

- **ID**: `prereg-f9e7d2d96d32`
- **Filed by**: agent
- **Filed at**: 2026-07-02 23:25 UTC
- **Review at**: 2026-08-01 23:25 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

External head anchor in separate ledger_head_anchor table, atomic-updated with each event write inside the same BEGIN...COMMIT transaction as the event insert, cross-checked by verify_chain against the walked ledger tip, closes the tail-truncation gap the auditor confirmed with runnable repro. Plain hash chosen over HMAC because our threat model does not include the specific attacker HMAC catches (data-theft-without-live-access); external witness via daily git snapshot is the auth layer HMAC would otherwise provide

## Success criterion

Over 30 days of live ledger operation: (a) verify_chain rejects tail truncation on every attempted repro (auditor's exact repro pattern lands ok=False), (b) every event write produces a matching anchor update in the same transaction (no orphan events without anchor advancement, no anchor advancement without event insert), (c) legacy databases without an anchor row still pass verify_chain when chain integrity holds (backward-compat preserved), (d) no false-positive verify_chain failures attributable to anchor mismatches on legitimate writes

## Falsifier

Within 30 days: (a) an attacker who truncates the ledger tail and rewrites the anchor to match sails through verify_chain undetected (defeats A alone — expected until git snapshot integration C ships), OR (b) verify_chain produces a false-positive during normal operation because of a race between event write and anchor update (the atomic transaction failed to hold), OR (c) a single event write succeeds without updating the anchor (fail-together broke), OR (d) tail-truncation detection ceases working after some migration or schema change (regression)
