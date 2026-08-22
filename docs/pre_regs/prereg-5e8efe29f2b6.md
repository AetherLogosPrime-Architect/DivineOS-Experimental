# Pre-registration: GoalReconciler: auto-capture + artifact-diff + declarative-observational surface, replacing manual goal add/done with substrate-touch-triggered reconciliation against shipped state

- **ID**: `prereg-5e8efe29f2b6`
- **Filed by**: agent
- **Filed at**: 2026-06-06 18:58 UTC
- **Review at**: 2026-07-06 18:58 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-08 21:36 UTC

## Claim

6399706a

## Success criterion

After 30 days: (a) stale-goal count averages <2 at any HUD read, (b) >=70% of substantive work sessions produce auto-captured goals without manual filing, (c) operator-facing surface uses observational/declarative language with no imperatives or count-badges, (d) reconciler closes goals against shipped state with <5% false-close rate sampled adversarially.

## Falsifier

Stale goals still accumulate >5 at any HUD read, OR auto-capture fires spuriously (>30% false-positive on what operator considers 'work'), OR the system requires operator to manually file or close more than 30% of goals (manual mode dominates), OR the new system ossifies like Claude Code TodoWrite did (artifact treated as immutable, re-planning suppressed).

## Outcome notes

Deferred: GoalReconciler — no dedicated module found. Manual goal add/done is still the pattern I used this session. Deferring: needs its own build.
