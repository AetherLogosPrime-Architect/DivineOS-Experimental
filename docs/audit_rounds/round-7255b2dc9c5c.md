# Audit round: root-cause-audit: knowledge-layer silent-failure family (silent-ignore on dedup, resurrection of superseded content, fails-open validity gate)

- **ID**: `round-7255b2dc9c5c`
- **Filed by**: aether
- **Filed at**: 2026-05-21 19:05 UTC
- **Tier**: WEAK
- **Findings**: 0

## Notes

No source ref (--no-source-ref used; round has no code substance).
Family: the direct knowledge API (crud.store_knowledge + knowledge_maintenance validity gate) silently failed where the extraction path was already guarded. Instances (Aletheia audit findings W/X/Y): W store_knowledge dedup silently ignored caller maturity (now upgrade-only); Y store_knowledge resurrected deliberately-superseded content (now guarded, allow_resurrect opt-in); X _passes_validity_gate caught a broad error tuple and failed OPEN, allowing promotion on any validity-logic bug (now fails CLOSED + logs, preserving only the documented not-deployed allow). Sibling survey: extraction.py already had the corroboration + superseded-skip guards (it was the correct reference; crud.py was the unguarded outlier). Finding Z (apply_seed case-folding vs hash) is a related but separate dedup-divergence, tracked, not in this fix. 8 regression tests added.

## Findings

_No findings were filed against this round._

---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
