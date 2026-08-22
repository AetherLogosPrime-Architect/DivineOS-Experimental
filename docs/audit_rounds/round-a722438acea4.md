# Audit round: F41: detector-chain heartbeat on successful run + is_detector_chain_stale for briefing surface

- **ID**: `round-a722438acea4`
- **Filed by**: aether
- **Filed at**: 2026-07-18 02:26 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: fix/f41-detector-chain-heartbeat


## Findings

### operator CONFIRMS (relayed from chat)

- **ID**: `find-feb000e2faf7`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 2f0bb3e2-7460-4211-8bfd-cc8caf62de0a

**Description**

operator CONFIRMS relayed by aether per Andrew's explicit chat authorization 2026-07-18: 'my confirms in chat is all you need'. Andrew reviewed the PRs in chat, saw Aletheia's per-PR CONFIRMS + notes, and approved all six for merge.

### CONFIRMS PR #361 (external-AI review, aletheia) — tree-exact

- **ID**: `find-6d94cf0370f5`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: f95e3db5-8995-423b-9038-7ac447c2a220
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip c098a5c9a30f6ca69cda64cc806daaa58567f68a / Tree 6c0d395b475c4276d37cd16601cb9fc9e6e0e45d / patch-id e7a320e281159f55150d2e50e54ae699d9fc409c (git-version 2.43.0) — verified against origin/fix/f41-detector-chain-heartbeat at file-time over merge-base(origin/main)..branch (default context). Basis: F41 heartbeat CONFIRM: kept per-detector fail-open (advisory discipline preserved); added liveness as separate signal via staleness; absence-is-stale so never-ran and stopped-running both surface. Follow-up: wire is_detector_chain_stale into briefing.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
