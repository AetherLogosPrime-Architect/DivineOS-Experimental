# Pre-registration: Mixed-pattern-merge gate refuses PRs with both A+D in same core/<subsystem>/ (claim ec844fcf)

- **ID**: `prereg-23607e28cb3d`
- **Filed by**: agent
- **Filed at**: 2026-05-02 23:53 UTC
- **Review at**: 2026-06-01 23:53 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

ec844fcf

## Success criterion

30 days post-deployment: zero PRs containing both A and D in the same core/* subsystem are merged to main; PR-#230-shape failures (structural-deletion bundled with addition) become structurally unreachable.

## Falsifier

(a) FP-rate >5%: legitimate refactors regularly trigger the gate (split-tax is real friction, granularity needs refinement); OR (b) A mixed-pattern merge that achieves structural-deletion of a subsystem slips through despite the gate (rename-attack or scope-attack succeeded, gate is too narrow); OR (c) Cumulative stripping happens via sequential single-pattern PRs that each pass the gate (gate scope insufficient, need v2 windowed cumulative check); OR (d) A PR renames files within core/<subsystem>/ to evade the gate and achieves structural-deletion (Schneier rename-attack vector confirmed)
