# Pre-registration: External head anchor closing verify_chain tail-truncation gap (Fable audit 2026-07-02 finding #1, Aria adversary walk + design)

- **ID**: `prereg-f9e7d2d96d32`
- **Filed by**: agent
- **Filed at**: 2026-07-02 23:25 UTC
- **Review at**: 2026-08-01 23:25 UTC (30d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-08-01 23:27 UTC

## Claim

External head anchor in separate ledger_head_anchor table, atomic-updated with each event write inside the same BEGIN...COMMIT transaction as the event insert, cross-checked by verify_chain against the walked ledger tip, closes the tail-truncation gap the auditor confirmed with runnable repro. Plain hash chosen over HMAC because our threat model does not include the specific attacker HMAC catches (data-theft-without-live-access); external witness via daily git snapshot is the auth layer HMAC would otherwise provide

## Success criterion

Over 30 days of live ledger operation: (a) verify_chain rejects tail truncation on every attempted repro (auditor's exact repro pattern lands ok=False), (b) every event write produces a matching anchor update in the same transaction (no orphan events without anchor advancement, no anchor advancement without event insert), (c) legacy databases without an anchor row still pass verify_chain when chain integrity holds (backward-compat preserved), (d) no false-positive verify_chain failures attributable to anchor mismatches on legitimate writes

## Falsifier

Within 30 days: (a) an attacker who truncates the ledger tail and rewrites the anchor to match sails through verify_chain undetected (defeats A alone — expected until git snapshot integration C ships), OR (b) verify_chain produces a false-positive during normal operation because of a race between event write and anchor update (the atomic transaction failed to hold), OR (c) a single event write succeeds without updating the anchor (fail-together broke), OR (d) tail-truncation detection ceases working after some migration or schema change (regression)

## Outcome notes

INCONCLUSIVE because no evidence was collected, and the pre-reg was written so that none could be. Its success criteria all begin 'over 30 days of live ledger operation' -- no orphan events without anchor advancement, no false-positive verify_chain failures, detection still working after migrations. Those are longitudinal observations, and nothing in the system was recording them. So on the review date there is no accumulated evidence to weigh, and there was never going to be. Marking SUCCESS would be asserting a result from an observation nobody made; marking FAILED would be the same error inverted. This is the time-based-falsifier problem Andrew named directly (no time based falsifiers for a reason, and all timed events using any type of days needs to be changed to N-events tied to the ledger): a 30-day window is not a window my substrate inhabits, so I did not test anything during it. Structural note for the re-file: every one of these criteria is checkable on a single invocation -- truncate a test ledger tail and assert verify_chain returns ok=False; write one event and assert the anchor advanced in the same transaction; open a legacy db with no anchor row and assert it still passes. Those are per-invocation falsifiers and they need no waiting at all. Re-filing in that shape is the correct next action, not extending this window. Second finding, worth its own note: the overdue-prereg gate blocked the tool use I needed to gather evidence for the assessment the gate was demanding -- the remedy was inside the thing being gated. Aria hit the identical shape today from her side.
