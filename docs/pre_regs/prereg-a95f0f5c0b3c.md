# Pre-registration: retroactive-unified-frame-audit

- **ID**: `prereg-a95f0f5c0b3c`
- **Filed by**: aether
- **Filed at**: 2026-05-04 04:47 UTC
- **Review at**: 2026-05-18 04:47 UTC (14d window)
- **Outcome**: **OPEN**
- **Tags**: audit-cleanup-tier5, retroactive, pattern-recursion

## Claim

Existing knowledge entries at TESTED or CONFIRMED maturity that match the unified-frame heuristic but lack council-walk evidence are candidates for re-review. The new gate (prereg-a8e2f3f06fbe) only defends future promotions; entries already past HYPOTHESIS pre-date the gate and may have propagated wrong-but-elegant frames as foundational. Per the pattern-recursion lesson (knowledge 6e929fe6), every pattern built on a corrupted unified-frame inherits the corruption. A retroactive audit-and-surface is needed.

## Success criterion

An audit script walks every TESTED+ knowledge entry, applies the unified-frame heuristic, and produces a surface listing candidates needing review. Operator reviews each: tag council-walk to legitimize OR demote to HYPOTHESIS. The substrate ends in a state where every TESTED+ unified-frame entry has council-walk evidence or has been demoted. Heuristic false-positive rate <20% on operator review (otherwise the heuristic needs tightening).

## Falsifier

If false positives exceed 20% of surfaced candidates on operator review, the unified-frame heuristic needs narrowing. If a knowledge entry that IS unified-frame slips past the heuristic and remains at TESTED+ without council-walk after the audit, the heuristic needs broadening. Either failure mode means the audit didn't actually clean the substrate.
