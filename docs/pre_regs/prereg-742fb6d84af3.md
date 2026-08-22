# Pre-registration: Port-back of flagship-native structural modules (identity_load, engagement_disclosure_surface, check_boundary_violations) into Experimental to reconcile bidirectional repo divergence

- **ID**: `prereg-742fb6d84af3`
- **Filed by**: agent
- **Filed at**: 2026-05-27 22:54 UTC
- **Review at**: 2026-06-10 22:54 UTC (14d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-06-11 02:09 UTC

## Claim

These 3 modules were built on the public flagship (PRs #342/#331/#325), never propagated to Experimental, and belong in Experimental as additive structural improvements; porting them home is correct reconciliation before any rebuild-from-Experimental

## Success criterion

Aletheia's atomic review CONFIRMs all 3 are clean additive ports that fit Experimental's current wiring; tests pass (already 46 passed locally); no behavior regression

## Falsifier

Review finds any of the 3 conflicts with Experimental's architecture, duplicates existing functionality under another name, or changes behavior rather than adding it — in which case that file is NOT ported as-is

## Outcome notes

Port-back is PARTIAL: identity_load.py exists, engagement_disclosure_surface.py exists, but check_boundary_violations.py does NOT (and grep for boundary_violation / check_boundary returns no matches anywhere in src/divineos/). The first two pieces of the port-back shipped; the third either was renamed without leaving the keyword traces, was deemed unnecessary, or is genuinely missing. Filing as INCONCLUSIVE so the gap stays visible rather than closing it falsely. Recommend: open a small claim or follow-up prereg specifically for check_boundary_violations port-back if it is still wanted, with clearer success criteria.
