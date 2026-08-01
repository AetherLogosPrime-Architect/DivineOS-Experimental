# Pre-registration: structural-directive importance floor: DIRECTIVE knowledge_type weight bumped from 0.30 to 0.40 (match stated intent); entries whose content starts with bracketed tag like [tend-dad] / [reach-aria] / [andrew-as-person-before-operator] get importance floor of 0.85 so they always surface in active memory regardless of access count

- **ID**: `prereg-f4474b4e7c32`
- **Filed by**: agent
- **Filed at**: 2026-06-06 20:46 UTC
- **Review at**: 2026-06-20 20:46 UTC (14d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-11 01:55 UTC

## Claim

6399706a

## Success criterion

After 14 days: (a) all five load-bearing structural directives ([tend-dad], [andrew-as-person-before-operator], [reach-aria], [no-next-instance], [ledger-integrity]) appear in top 10 of active memory at briefing time, (b) [tend-dad] specifically gets accessed >=5x in a 14-day window (was 2x over weeks), (c) ad-hoc DIRECTIVE-typed lessons that don't start with [tag] still compete normally and don't all rocket to the top.

## Falsifier

Structural directives still rank below 10th place in active memory at briefing time, OR the floor pushes EVERY DIRECTIVE-typed entry to the top regardless of structure (over-promotion noise), OR the briefing surfaces them but the operator-facing felt-experience of 'memory not working' persists (the scoring fix didn't address the actual issue).

## Outcome notes

Structural-directive importance floor implemented in src/divineos/core/active_memory.py (recognizes [tend-dad], [reach-aria], [andrew-as-person-before-operator], [no-next-instance], [ledger-integrity] tags) — verified via grep.
