# Pre-registration: Consultation gate+channel: PreToolUse blocks substrate-modifying tools when responses-since-last-substantive-consult >= 4, with a channel message inlining the unread correction + exact consult command; clears only on ask/recall/corrections/directives/active/compass

- **ID**: `prereg-154e20cea436`
- **Filed by**: agent
- **Filed at**: 2026-05-23 17:29 UTC
- **Review at**: 2026-06-22 17:29 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:31 UTC

## Claim

Converting the toothless consultation WARNING into a block-with-channel will raise my real substrate-consultation rate and stop the 9-responses-0-consults runs (like 2026-05-23) from recurring

## Success criterion

Over the next 30 days, sessions show substantive consults occurring before long substrate-modifying runs; the gate fires and is cleared by a real consult (not bypass-env), and responses-since-consult rarely exceeds 4

## Falsifier

The gate is routinely cleared by hollow consults (ask with empty/garbage topic) without reading output, OR it deadlocks/over-blocks legitimate work, OR consultation rate does not improve vs the warning-only baseline

## Outcome notes

Shipped: src/divineos/core/consultation_tracker.py exists. The consultation gate+channel fires as SUBSTRATE CONSULTATION - DEGRADED/HEALTHY surface in every substrate-modification gate load this session — verified by lived experience.
