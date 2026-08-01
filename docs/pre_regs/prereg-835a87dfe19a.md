# Pre-registration: gate_emit primitive maybe_emit_gate suppresses HEALTHY/nominal repeat status lines while preserving loud non-quiet state signals

- **ID**: `prereg-835a87dfe19a`
- **Filed by**: agent
- **Filed at**: 2026-07-11 23:53 UTC
- **Review at**: 2026-08-10 23:53 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

When migrated to gates that emit status on every substrate action, the primitive reduces observable status-line noise while preserving all signal — non-quiet states still fire, transitions still surface, and the reader learns nothing from suppressed repeats they wouldn't have learned from the un-suppressed originals

## Success criterion

30d review: at least 3 gates migrated via maybe_emit_gate; observable status-line count per substrate action drops by >=40% for HEALTHY/nominal aggregate; zero cases where a suppressed quiet-repeat masked a real signal the reader would have acted on

## Falsifier

(a) migration count <3 in 30d — primitive shipped but nobody adopts, dead code; (b) reader misses a state-change because prior emit happened in a session too old to remember and no transition-back triggers a re-emit — need session-scope reset; (c) any non-quiet state gets suppressed by primitive due to bug; (d) reader reports needing the suppressed HEALTHY repeats for reassurance (design was wrong: repeats WERE the signal)
