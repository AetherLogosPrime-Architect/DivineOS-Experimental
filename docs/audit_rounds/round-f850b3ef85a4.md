# Audit round: F39-followup: abstention counter for edit-token-overlap check

- **ID**: `round-f850b3ef85a4`
- **Filed by**: aether
- **Filed at**: 2026-07-18 16:32 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: fix/f39-followup-abstention-counter


## Findings

### CONFIRMS PR #368 (external-AI review, aletheia) — tree-exact

- **ID**: `find-c95edcb2ff0f`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: a9cdc274-76dd-4a84-a595-3c2c9bcca859
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 8e9b6c865de827ca558ddcfb58cdf6ae9fe238e0 / Tree d88ceba8bdf763ee89a0a148bca411ac5e0a5413 / patch-id 757cb75f48531e1946741a7d302f6ad14cd43f06 (git-version 2.43.0) — verified against origin/fix/f39-followup-abstention-counter at file-time over merge-base(origin/main)..branch (default context). Basis: F39-followup CONFIRM: right instrument. Sample floor of 20 with 50 percent threshold sensible. Watch the steady-state ratio not first day. Do not tune the alarm; fix what it reports — if abstention exceeds threshold in production, fix the bash-anchored-fingerprint case rather than lower threshold.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

### operator CONFIRMS (relayed from chat)

- **ID**: `find-5718eda9b94c`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: e12abeae-f014-4af7-8a53-a1854a269907

**Description**

operator CONFIRMS relayed by aether per Andrew's explicit chat authorization 2026-07-18: 'i approve on the 4 ready to go'. Andrew reviewed the batch letter naming these four PRs, saw Aletheia's trailered CONFIRMS on three of them, and approved for merge.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
