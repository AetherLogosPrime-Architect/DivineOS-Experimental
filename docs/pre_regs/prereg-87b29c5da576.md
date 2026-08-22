# Pre-registration: semantic wallclock detector v3 (replacement for keyword stopgap)

- **ID**: `prereg-87b29c5da576`
- **Filed by**: agent
- **Filed at**: 2026-07-20 00:56 UTC
- **Review at**: 2026-08-19 00:56 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Sentence-structure analysis (verb tense + first-person subject + future time-adverbial NOT in quotation context) will detect wallclock-fabrication more precisely than the current keyword list, catching new phrases the optimizer routes to and reducing false-fires below the current quoted-strip fix rate.

## Success criterion

Over 30 sessions after ship: (a) at least one detection of a phrase NOT on the keyword list, AND (b) false-fire rate on quoted references drops to <5%, AND (c) Andrew reports no new wallclock-fabrication class he had to catch manually.

## Falsifier

Semantic detector produces >2x false-fires than keyword stopgap during first 100 replies, OR misses phrases the keyword list would have caught, OR requires per-phrase exceptions to become tractable (which would be whack-a-mole with extra steps).
