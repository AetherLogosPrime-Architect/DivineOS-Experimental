# Pre-registration: confidence_basis distinguishes uncommitted from credences

- **ID**: `prereg-b35f0d36cb2b`
- **Filed by**: agent
- **Filed at**: 2026-06-06 16:00 UTC
- **Review at**: 2026-07-06 16:00 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 01:55 UTC

## Claim

Adding confidence_basis column (uncommitted/filer-prior/assessor-judgment/evidence-derived/legacy-default) + 3 CLI surface changes (file --confidence/--confidence-basis, assess --confidence/--basis, claims uncommitted) closes Aletheia 2026-05-12 dogfood finding (108→202 claims stuck at default 0.5). Distinguishing the default 0.5 from real 0.5 credence makes the gap visible AND gives explicit paths to commit a credence without quantified evidence.

## Success criterion

Over 30 days, % of claims in 'uncommitted' OR 'legacy-default' basis drops below 80% (currently 202/203 = 99.5%). Counted via 'divineos claims uncommitted | wc -l' vs total claim count.

## Falsifier

If after 30 days >80% of claims still show uncommitted/legacy-default basis, the CLI surface change failed to shift the discipline and the gap is structural-not-tooling (workflow problem, not affordance problem). Also: if any new claim filed via CLI lands with confidence != 0.5 but basis='uncommitted', the SELECT-column-list bug pattern that produced the basis-flip during this build has regressed.

## Outcome notes

confidence_basis column implemented in src/divineos/core/claim_store.py:82 (NOT NULL DEFAULT uncommitted) + confidence_basis_text column + _migrate_add_confidence_basis migration helper — verified via grep.
