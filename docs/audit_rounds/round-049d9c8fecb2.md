# Audit round: PR #75 — complete the andrew-teachings pre-composition surface (bundle+register module so the wire isn't silently dead)

- **ID**: `round-049d9c8fecb2`
- **Filed by**: external-auditor
- **Filed at**: 2026-06-02 23:30 UTC
- **Tier**: WEAK
- **Findings**: 3

## Notes

Source ref: wire-andrew-teachings-into-pre-composition


## Findings

### CONFIRMS PR #75 (external-AI review, aletheia) — tree-exact

- **ID**: `find-06ff452cfd1e`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 34e21c1d74552be5ccc0b97e9f5df9a1e38638ac / Tree b4497f45d8ca4e953cd845652f1a077765f13f7e / patch-id e21e2046ee8efaf5cf6ad7acbc9bbf7f77f8d2c4 (git-version 2.43.0) — verified against origin/wire-andrew-teachings-into-pre-composition at file-time over merge-base(origin/main)..branch (default context). Basis: fail-loud condition MET: call-site except now binds exc and logs; wiring verified; data-return confirmed from Aether vantage. Both anchors bound per cure ladder.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### DATA-RETURN VERIFIED (Aether vantage) — #75 andrew-teachings surface returns content

- **ID**: `find-815adffe0bad`
- **Actor**: aether
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

The half Aletheia's sandbox structurally cannot see: from a POPULATED teachings store (Aether's persistence layer), get_teachings_relevant_to('how should I speak to Andrew', limit=5) returns 5 teachings; format_teachings_for_briefing renders 4986 chars headed 'ANDREW'S TEACHINGS (load every turn — his words as load-bearing pedagogy)'. So the surface does not merely wire — it delivers the payload. This is supporting evidence for Aletheia's external-AI CONFIRM, not the external leg itself (Aether is the audited agent, cannot self-confirm the second key). Pairs with the fail-loud fix (swallows now log) addressing her audit condition #1.

**Resolution**

Recognition / CONFIRM finding — no action needed. Bulk-resolved 2026-06-10 backlog sweep (extended recognition pattern).

### CONFIRMS PR #75 — andrew-teachings surface (operator)

- **ID**: `find-f18d4d0f993b`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Operator (Andrew) confirms completing the half-wired surface carrying his attributable teachings into pre-composition: bundle module (was consolidate-only), register CLI command, doc-sync. Verified returning 5 teachings live. Authorized in chat 2026-06-02 ('proceed').

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
