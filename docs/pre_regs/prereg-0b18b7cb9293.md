# Pre-registration: STATE_CHANGE_CLAIM detector catches perfective-claim-without-tool-call (saying-without-doing) via tool-call adjacency cross-reference

- **ID**: `prereg-0b18b7cb9293`
- **Filed by**: agent
- **Filed at**: 2026-05-02 19:04 UTC
- **Review at**: 2026-06-01 19:04 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

096adfec

## Success criterion

On a manually-labeled sample of 30 sessions post-deployment, the rate of state-change claims that lack a matching same-turn tool call is reduced by >=50% from a 10-session pre-deployment baseline. Detector emits drift events that the operator-loop surfaces, not just records.

## Falsifier

(a) saying-without-doing rate unchanged or worse; OR (b) detector flags >5% false positives on manually-labeled legitimate cognitive-naming; OR (c) doing-without-saying rate increases (Goodhart through silence — Yudkowsky lens)
