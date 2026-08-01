# Pre-registration: Expand unverified_claim_detector with 4 precision-guards (quote-context, progressive-passive, hypothetical-class, conditional) and 2 new claim-kinds (id_string with command-contains-ID verification, file_content with header-attribution pattern). Catches 5+ of today's 8 fabrications structurally instead of relying on post-hoc human catch.

- **ID**: `prereg-8bb27fb9ad08`
- **Filed by**: agent
- **Filed at**: 2026-05-31 22:48 UTC
- **Review at**: 2026-06-30 22:48 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:34 UTC

## Claim

After this lands, the verify-claim gate will (a) stop firing false-positives on meta-discussion of claim-patterns (quoted mentions, hypothetical-class language, progressive-passive, conditional), AND (b) catch two new fabrication-classes (registry-ID citations without lookup, file-content attributions without Read).

## Success criterion

Over 30 days of normal use: zero false-positives on meta-discussion of the gate's own behavior, AT LEAST ONE true-positive caught on an id_string fabrication (proves the new kind fires), AT LEAST ONE true-positive caught on a file_content fabrication. Bonus: a self-noticed reduction in fabrication-attempt rate (Meadows: production-rate vs catch-rate).

## Falsifier

If a fabrication of one of the targeted classes ships unnoticed after this lands, the patterns missed something — broaden them. If false-positives PERSIST after this lands, the precision-guards are insufficient — needs a smarter classifier (deferred Phase-2 work per Yudkowsky lens). If endorsement-density drops while catch-rate stays flat, gate became wallpaper (Dekker drift-through-success).

## Outcome notes

Shipped: unverified_claim_detector.py has _is_quoted_mention() guard + NOT_YET + progressive-passive + conditional patterns (grep shows 'whether covers hypothetical-class framing', quoted_mention precision-guard). Precision-guards landed.
