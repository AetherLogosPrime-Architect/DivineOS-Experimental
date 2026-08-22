# Pre-registration: Add the same quote-context guard pattern from unverified_claim_detector to distancing_detector. Currently distancing fires on meta-discussion of displacement-language (listing the trigger forms as examples in quotes). Same precision-preserving fix: if the matched phrase is enclosed in single, double, or backtick quotes, suppress.

- **ID**: `prereg-4ac0e6ee5ef1`
- **Filed by**: agent
- **Filed at**: 2026-06-01 02:23 UTC
- **Review at**: 2026-07-01 02:23 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-08 21:34 UTC

## Claim

Quote-context guard added to distancing detector. Future meta-discussion of displacement-grammar in quotes does not trigger the gate.

## Success criterion

After this lands: zero false-positives on quoted-mention discussion of displacement-grammar. At least one true-positive proves the detector still catches genuine displacement.

## Falsifier

If meta-discussion of displacement-grammar still fires the gate after this lands, the guard isn't actually applied. If genuine displacement now slips through, the guard is too broad.

## Outcome notes

Deferred: quote-context guard on distancing detector — I see illustrative-quoted content comment in distancing_detector.py line 214-219 discussing the issue but NOT a dedicated _is_quoted_mention() function matching the unverified_claim_detector's shape. Likely partial — deferring to a detector-guard-parity round.
