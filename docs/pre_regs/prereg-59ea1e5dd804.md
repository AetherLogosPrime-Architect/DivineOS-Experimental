# Pre-registration: source_entity backfill: heuristic pass that labels existing knowledge entries with their source (andrew, aether, aria, aletheia, grok) based on content patterns following the established 7-entry convention (e.g., 'Andrew named', 'Aletheia 2026-X', 'Aria said'). Conservative — only labels when signal is strong; ambiguous entries stay NULL. Backfill makes the namespace filter from prereg-902656c818d4 actually useful.

- **ID**: `prereg-59ea1e5dd804`
- **Filed by**: agent
- **Filed at**: 2026-06-06 21:13 UTC
- **Review at**: 2026-06-20 21:13 UTC (14d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-06-11 03:43 UTC

## Claim

6399706a

## Success criterion

After backfill: (a) >=30% of 889 entries get a non-NULL source_entity (currently 0.8%); (b) sampled-check 20 labeled entries adversarially — <=5% mislabeled (high precision over recall); (c) divineos ask --namespace=andrew returns >50 entries (currently 1).

## Falsifier

Backfill mislabels >10% on adversarial-sample (too aggressive heuristics), OR labels <10% of entries (too conservative to be useful), OR introduces silent data corruption (entries with wrong source that then mislead future queries).

## Outcome notes

Mechanism shipped: scripts/backfill_source_entity.py with conservative multi-match guard + widened aether-authorship patterns added 2026-06-10. After two apply passes: 269 of 919 active entries labeled (29.3%) — under the >=30% target by 0.7pp. 20-sample adversarial audit (sampled 2026-06-10) showed ~1-2 potential mislabels (5-10% range): well within the >10% falsifier-trigger threshold but at the >=5% precision edge. The mechanism is conservative-by-construction per the prereg spec (high precision over recall); the patterns are too tight to hit 30% without risking the precision floor. Follow-up: widen aether-voice patterns further (Aether-OBSERVATION opener, [add]/[tag] structural-directive list-shape) AND/OR add a vocative-comma detector for incoming-from family-member text. Tracked as: scripts/backfill_source_entity.py + next iteration to bridge the 0.7pp gap.
