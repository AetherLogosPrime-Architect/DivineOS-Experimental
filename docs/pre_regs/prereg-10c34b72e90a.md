# Pre-registration: Spaced-repetition lesson surfacing: rank lessons by combined occurrences + regressions + recency rather than pure recency, so frequently-failed patterns surface more often than freshly-acknowledged ones

- **ID**: `prereg-10c34b72e90a`
- **Filed by**: agent
- **Filed at**: 2026-05-04 22:50 UTC
- **Review at**: 2026-06-03 22:50 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Replacing pure-recency ranking with SM-2-style spaced-repetition scoring will increase the surfacing frequency of high-regression lessons (the ones I keep failing) and decrease the surfacing of one-time lessons that have stuck. The 'stuff that stings is the stuff that sticks' seed-knowledge gets operationalized: lessons that recur surface MORE, lessons that don't recur fade out the briefing.

## Success criterion

(a) High-regression lessons (regressions >= 2) appear in the top-N briefing surface measurably more often than under recency-only ranking when measured across N sessions, OR (b) Low-occurrence stuck lessons fade out of the briefing within 30d of last occurrence rather than persisting indefinitely.

## Falsifier

(a) Lessons with regressions=0 surface less often than they should (i.e., I lose track of valid principles), OR (b) The new ranking causes briefing churn — same lessons rotating in/out across sessions in a way that's noisier than the old recency ranking, OR (c) Performance regression: lesson surfacing query becomes measurably slower.
