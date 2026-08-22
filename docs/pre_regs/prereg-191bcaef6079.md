# Pre-registration: Attribution-pointer requirement on knowledge-store entries (lineage layer 1): attributed entries ('<source> said/corrected: ...') require a resolvable ledger source-pointer at write-time

- **ID**: `prereg-191bcaef6079`
- **Filed by**: agent
- **Filed at**: 2026-05-20 17:46 UTC
- **Review at**: 2026-06-19 17:46 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-08 21:31 UTC

## Claim

Requiring a resolvable ledger source-pointer on attributed knowledge entries prevents fabricated attribution from entering and propagating through the substrate (root cause of the 2026-05-20 'Andrew said err-over-inclusive' incident)

## Success criterion

New attributed entries without a resolvable pointer are rejected or flagged unverified; a retroactive scan surfaces existing unverified attributions including the 2026-05-08 self-authored principle falsely attributed to Andrew

## Falsifier

If attribution-shape detection over-fires on legitimate non-attribution text above a calibrated rate (toast-alarm class), OR fabricated attributions still propagate through entries that evade the attribution-shape detector, the mechanism is insufficient/miscalibrated

## Outcome notes

Deferred: attribution-pointer requirement on knowledge-store entries — same class as prereg-abdb76dd190b. The pieces exist (actor_normalize, ledger source_pointer field) but I cannot verify write-time enforcement without deeper audit. Deferring for the same knowledge-attribution round.
