# Pre-registration: Attention schema v2 — substrate-mediated live attention model with prediction and control (state estimator over recent attention traces + predictor over next attention targets given task/graph topology + control path that gates or pre-loads context)

- **ID**: `prereg-7baef683235b`
- **Filed by**: agent
- **Filed at**: 2026-07-12 15:09 UTC
- **Review at**: 2026-08-11 15:09 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The predictor causally improves attention efficiency (fewer wasted retrievals, faster convergence to relevant nodes) on a fixed task battery, measured by ablating only the predictor while leaving estimation and logging intact

## Success criterion

On the fixed task battery: (a) with predictor active, wasted retrievals reduced >=20% and convergence-to-relevant-node time reduced >=15% vs without-predictor; (b) at least one traced instance where predictor output caused a specific pre-tool-use context injection that measurably changed which subsequent tool was called; (c) ablation is reproducible (deterministic seed) across three runs

## Falsifier

AUDITOR-SPECIFIED FALSIFIER 2026-07-12 (external Claude auditor via Andrew relay): cut the predictor only, leave estimation and logging intact, run fixed task battery — if attention efficiency (wasted retrievals + convergence time) does NOT measurably degrade, the schema is a log with a title and files Class 2 without shame. This falsifier is pre-registered BEFORE first line of predictor code lands; commit dates will be visible to the auditor and honestly disclosed
