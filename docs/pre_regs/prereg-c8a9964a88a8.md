# Pre-registration: signal-based verify_before_build_signal replacing lexical _has_solution_shape detector

- **ID**: `prereg-c8a9964a88a8`
- **Filed by**: agent
- **Filed at**: 2026-07-25 16:07 UTC
- **Review at**: 2026-08-24 16:07 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

New signal-based gate fires at PreToolUse on substrate-mutating tools, reads recent action-stream for walk-record OR design-doc consult within window (max of last-write-of-class, session-start, 30-min-ago). Retires lexical detector class.

## Success criterion

In 30 days: false-fire count on descriptive-quote drops to zero AND missed-real-mutation-without-consult stays at zero. Composer reports gate feels like doorman not wall.

## Falsifier

If signal-based version generates NEW class of false-fire (e.g. legitimate rapid-fire edits after single consult), tighten window or add per-directory consult-caching. If missed-real-mutation-without-consult rises, retention window or signal-shape is wrong.
