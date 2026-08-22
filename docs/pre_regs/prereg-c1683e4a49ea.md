# Pre-registration: Layer A rule-based self-admission detector correctly distinguishes USE from MENTION in MY output

- **ID**: `prereg-c1683e4a49ea`
- **Filed by**: aether
- **Filed at**: 2026-07-28 01:20 UTC
- **Review at**: 2026-08-11 01:20 UTC (14d window)
- **Outcome**: **OPEN**
- **Tags**: no-upstream-because

## Claim

Fires on real self-corrections, silent on discussions of correction

## Success criterion

Over 14-day review: catch-rate on true self-corrections >= 70%; false-positive-rate on discussion messages <= 5%

## Falsifier

If over 14-day review: (a) more than 5% fires are on discussion-shape messages, OR (b) real self-corrections missed at rate above 50%, Layer A is insufficient and Layer B semantic tiebreak MUST be built
