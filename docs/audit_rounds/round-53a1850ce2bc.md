# Audit round: External-Review: Aletheia audit fixes — bypass-list expansion (Finding 37) + guardrail-list addition (Finding 41). diff-hash aa7bcaee11c9...

- **ID**: `round-53a1850ce2bc`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 16:14 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Andrew CONFIRMS guardrail expansion

- **ID**: `find-c5ae25396027`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Bypass list + gate file now properly under multi-party-review. Address-command structural test makes the rule from 2026-04-23 enforced rather than aspirational.

### Aletheia CONFIRMS-pending-empirical: catch-22 fixed + guardrail added

- **ID**: `find-a74e761bb579`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Bypass list now includes claims/holding/hold per Finding 37 drill-down. Structural test test_stale_engagement_address_bypass.py prevents recurrence at the class level — converts convention to enforcement (Aletheia's exact recommendation). pre_tool_use_gate.py now in scripts/guardrail_files.txt per Finding 41 — bypass-list modifications now require multi-party review.

**Resolution**

Recognition / CONFIRM finding — no action needed. Bulk-resolved 2026-06-10 backlog sweep (extended recognition pattern).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
