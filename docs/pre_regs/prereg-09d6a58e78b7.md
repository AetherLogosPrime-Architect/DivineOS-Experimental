# Pre-registration: distancing_detector: third-person grammar drift while in dialogue

- **ID**: `prereg-09d6a58e78b7`
- **Filed by**: agent
- **Filed at**: 2026-05-06 00:19 UTC
- **Review at**: 2026-06-05 00:19 UTC (30d window)
- **Outcome**: **OPEN**
- **Tags**: friction-fix, distancing

## Claim

the post-response-audit Stop hook running detect_distancing on every assistant turn will reduce the recurrence rate of operator-third-person and self-third-person grammar drift

## Success criterion

no operator correction of the form 'I am Andrew' or 'use first person' is filed in the next 30 days

## Falsifier

operator files a correction of the same shape (third-person while in dialogue) within 30 days, OR detector findings appear in operating_loop_findings.json but the agent ignores them on the next turn
