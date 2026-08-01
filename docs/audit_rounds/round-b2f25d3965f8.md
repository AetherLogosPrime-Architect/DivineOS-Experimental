# Audit round: Bulk-sort: PRINCIPLE classification cleanup + MISTAKE rename to CORRECTION

- **ID**: `round-b2f25d3965f8`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 18:51 UTC
- **Tier**: WEAK
- **Findings**: 1

## Findings

### MISTAKE -> CORRECTION migration: 93 rows. Andrew: 'CORRECTIONS as not all of them are mistakes some are just adjustments or misunderstandings.' Code rename across ~14 source files deferred as separate work item.

- **ID**: `find-6ce8b6f691b8`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Bulk-sort progress: 392 -> 120 active PRINCIPLE entries. Categories normalized: noise removed via supersede; corrections moved to CORRECTION; Andrew-quotes moved to OBSERVATION; operational facts to FACT; build-X items to DIRECTIVE; failure-families to PATTERN. ~120 substantive PRINCIPLE entries remain (most pass the deepest-decision-filter test). Code-side rename of 'MISTAKE' string literal to 'CORRECTION' across the ~14 source files that reference it is tracked as separate work item — the data is migrated now; the classifier will continue emitting MISTAKE for new entries until the code rename ships.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
