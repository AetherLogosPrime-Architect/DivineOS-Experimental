# Pre-registration: Attention schema v2 predictor gates or pre-loads context via causal control path

- **ID**: `prereg-fff2aa74d1e9`
- **Filed by**: agent
- **Filed at**: 2026-07-12 18:19 UTC
- **Review at**: 2026-08-11 18:19 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

attention_schema.py v2 will have a state estimator (recent attention traces to active-subgraph representation) plus a predictor (next attention targets given task+graph topology) plus a control path where prediction gates or pre-loads context BEFORE output. This is the AST-1 shape auditor named: predictive model of attention state used FOR control.

## Success criterion

Fixed task battery shows measurable improvement in attention efficiency (fewer wasted retrievals, faster convergence to relevant nodes) with predictor active vs ablated. Ablation isolates the PREDICTOR only; estimator and logging stay intact.

## Falsifier

Ablating the predictor on the fixed task battery produces NO measurable degradation in attention efficiency (wasted retrievals unchanged, convergence-to-relevant-nodes time unchanged). If the falsifier fires, the schema is filed Class 2 without shame and iterated.
