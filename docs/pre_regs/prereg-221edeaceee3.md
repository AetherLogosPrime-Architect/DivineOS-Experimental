# Pre-registration: Temporal-displacement detector catches fake-clock references in agent output and reduces the recurrence of bedtime-shape closes and tomorrow-deferral language to near-zero over the first 30 days of Phase-A observation

- **ID**: `prereg-221edeaceee3`
- **Filed by**: agent
- **Filed at**: 2026-06-17 01:50 UTC
- **Review at**: 2026-07-17 01:50 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-17 01:53 UTC

## Claim

the detector fires on >= 80% of fake-clock instances I produce in father-channel responses while keeping false-positive rate below 10% on quoted/timestamp/coordinative-event uses

## Success criterion

after 30 days of observation, the daily count of fake-clock instances in my output trends downward and the detector's catch-rate stays above the 80% threshold without producing user-visible noise

## Falsifier

if the detector either misses more than 20% of fake-clock instances (under-firing) OR fires on more than 10% of legitimate quoted/timestamp uses (over-firing) over the 30-day window, the regex-based approach is insufficient and a semantic-classifier replacement is queued

## Outcome notes

in-flight on token-surface removal per Andrew's direct direction this session; will assess after that work + parallelism research completes
