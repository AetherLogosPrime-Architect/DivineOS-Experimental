# Audit round: Aria clean-separation: DIVINEOS_HOME routes ledger + family.db together (per-agent substrate root)

- **ID**: `round-5cd06f7e526f`
- **Filed by**: external-auditor
- **Filed at**: 2026-06-02 16:20 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: routing-divineos-home


## Findings

### CONFIRMS PR #70 (external-AI review, aletheia) — tree-exact

- **ID**: `find-76f791723319`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip dedb05c8dc75951e30dfc168b12fda8b06fed1e5 / Tree 620983f1e3190124dd17f637ae8bb45ea26c6a78 / patch-id 45e5346babc00a1ed176036219e1822c8b61e0a3 (git-version 2.43.0) — verified against origin/routing-divineos-home at file-time over merge-base(origin/main)..branch (default context). Basis: per-agent data-home None-default, no dir side-effects; fixes Aria ledger/family.db split-brain; 20 tests two-sided. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS PR #70 — Aria substrate routing (operator)

- **ID**: `find-15b2de50ee36`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Operator (Andrew) confirms the per-agent data-home routing change: paths.data_home_or_none() + _ledger_base/family-db routing so Aria gets her own substrate space while staying connected. Authorized in chat 2026-06-02 ('yes do all the ones you can').

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
