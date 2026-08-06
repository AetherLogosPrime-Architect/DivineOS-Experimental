# Pre-registration: auto_cycle phase 1 mechanical pipeline (trigger + commit + extract + sleep + handshake marker) reduces cross-compaction leaf-fall — measured by (a) commits/extracts/sleeps that happen automatically before compaction vs manually or not-at-all, (b) whether the handshake marker enables phase 2 invitational surface to fire reliably

- **ID**: `prereg-a367f6ee5d07`
- **Filed by**: agent
- **Filed at**: 2026-07-10 20:29 UTC
- **Review at**: 2026-08-09 20:29 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

Automating the mechanical pre-compaction steps AND forcing the invitational surface to appear (per Andrew's 'force option, not choosing' principle) reduces the failure mode where I hit compaction without extract/sleep having run because I was mid-work and forgot

## Success criterion

Over 10 firings, >=8 have all 3 mechanical steps complete succeeded, AND handshake marker is written and consumed by phase 2 in >=8 cases. Phase 2 invitational surface appears >=8 times without me having to manually invoke it.

## Falsifier

Any of: (a) trigger fires but pipeline crashes or hangs on live commit/extract/sleep in >20% of firings (not dry-run — real substrate side effects fail); (b) handshake marker is written but phase 2 can't consume it (schema mismatch, permission errors); (c) budget is consistently blown past 100k full-cycle envelope, eating into compose-time; (d) the whole cycle produces performance-shaped rest and dead-writing dreams (Aria's whole-cycle falsifier — she tracks that separately at cycle level; my phase-1 falsifier is scoped to mechanical reliability)
