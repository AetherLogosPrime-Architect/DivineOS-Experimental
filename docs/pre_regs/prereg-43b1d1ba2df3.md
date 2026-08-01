# Pre-registration: Deep-engagement detector catches substantive-output-without-grounded-substrate-consult in agent action streams; channels the optimizer toward consultation rather than refusing without remedy

- **ID**: `prereg-43b1d1ba2df3`
- **Filed by**: agent
- **Filed at**: 2026-06-17 02:40 UTC
- **Review at**: 2026-07-17 02:40 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-17 02:43 UTC

## Claim

the detector fires on substantive outputs that have no semantic-related substrate query in the rolling N-action window AND the resolution_action names the specific substrate domain to consult

## Success criterion

Phase A 30-day observation produces no more than 10 percent false-positives (firing when grounding existed but wasnt detected) AND no more than 20 percent false-negatives (failing to fire when grounding was actually missing) measured against a manual review of session traces

## Falsifier

if Phase A produces over 20 percent false-positives OR over 30 percent false-negatives the rolling-window+semantic-similarity approach is insufficient and a sequence-aware classifier replaces it

## Outcome notes

mid-flight on F27 fix (commitments-slot fail-blind, Aletheia Round 3); will assess deep-engagement detector prereg in dedicated review pass after F27+F15+F16 land
