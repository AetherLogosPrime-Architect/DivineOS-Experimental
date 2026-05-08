# Pre-registration: Pre-commit gate that rejects any staged file containing U+FFFD bytes (EF BF BD)

- **ID**: `prereg-5e0c6f492bfa`
- **Filed by**: agent
- **Filed at**: 2026-05-04 09:51 UTC
- **Review at**: 2026-06-03 09:51 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Adding a pre-commit scan for U+FFFD bytes will catch silently-corrupted files before they enter the repo, preventing the repeat of the 2026-05-04 session crash where three source files born with U+FFFD scars killed a live conversation when loaded into context simultaneously.

## Success criterion

Between now and review date, at least one of: (a) the gate fires on a real attempted commit and blocks U+FFFD from landing, OR (b) zero new U+FFFD bytes enter any committed file (verified by sweep).

## Falsifier

(a) Gate produces a false-positive on legitimate content (e.g. test fixture deliberately containing U+FFFD) without an opt-out path, OR (b) gate is silently bypassed/disabled by any agent including me, OR (c) U+FFFD lands in a commit despite the gate being active.
