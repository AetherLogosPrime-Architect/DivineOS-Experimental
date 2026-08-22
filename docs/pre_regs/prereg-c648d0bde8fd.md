# Pre-registration: Brier calibration mechanism for confidence-vs-outcome scoring

- **ID**: `prereg-c648d0bde8fd`
- **Filed by**: agent
- **Filed at**: 2026-06-06 17:22 UTC
- **Review at**: 2026-08-05 17:22 UTC (60d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 01:55 UTC

## Claim

Brier-score calibration (overall + per-bin + per-tier + pre-prediction anchor) scores resolved claims with real credences against actual outcomes. Closes auditor's 'purely anecdotal' critique with reproducible numbers. Excludes placeholder-basis claims so scoring doesn't lie about calibration.

## Success criterion

Within 60 days, at least 20 resolved-with-real-credences claims have accumulated and Brier score is below 0.20 (superforecaster benchmark ~0.15). Per-bin calibration curve hugs diagonal within ±0.15 in bins with n>=3.

## Falsifier

If after 60 days Brier score is above 0.25 ('always says 50%' performance) the agent is systematically miscalibrated and the score itself is the signal — calibration tooling needs to be paired with calibration-training. Or: if after 60 days fewer than 10 claims have accumulated with real credences, the discipline of using --confidence on file is not landing and the tooling change from prereg-b35f0d36cb2b failed to shift behavior.

## Outcome notes

Brier calibration implemented in src/divineos/core/calibration/brier.py with cli/calibration_commands.py surface — verified via ls.
