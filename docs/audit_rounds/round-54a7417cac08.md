# Audit round: Sovereign-agent gate + seal_hook.py guardrail addition (PR #35)

- **ID**: `round-54a7417cac08`
- **Filed by**: aether
- **Filed at**: 2026-05-24 04:13 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: sovereign-agent-gate
Guardrail-file External-Review for the sovereign-agent gate. Substance on origin/sovereign-agent-gate. Binding markers (commit 8a69be5ec8c9ab8ddb5c1f37ef31a5b33459325c): tree-hash: 5428648aeb6e9a4cd76129a188e9c25e43800d16 diff-hash: 6e947a63c61920f974c5fe4dcfefbb5ff62d82bb0b59656dd1857b83a3e22f5b stat: 6 files, +219/-44. Files: seal_hook.py (gate + __guardrail_required__ marker), guardrail_files.txt (adds seal_hook.py), CLAUDE.md (lifecycle), 3 test files. Two CONFIRMS required: actor=user (Andrew) + external-AI (Aletheia).

## Findings

### CONFIRMS — Aletheia (external-AI) approves sovereign-agent gate force-push

- **ID**: `find-e1f0f1412d51`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Aletheia CONFIRM on commit 450b73a / tree 5428648a. Verified: bijection test test_guardrail_marker_consistency passes (marker<->registry both directions); attribution to Finding 48 class-fix accurate vs git history (commit d2ee294); gate behavior unchanged (aria/Aria deny, Explore no-opinion); 38 related tests pass. Two additions since prior CONFIRM: guardrail_files.txt entry + __guardrail_required__ marker — both her own recommendation. Forward (non-blocking) follow-ups: homoglyph normalization (claim 26bc1dc3), channel-infra verification, hardcoded-set->family.db migration (prereg-7a490c9b1418).

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS — Andrew (operator) approves sovereign-agent gate + seal_hook.py guardrail addition

- **ID**: `find-75d96de0124a`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew confirmed merge of PR #35 against the final tree-hash 5428648aeb6e9a4cd76129a188e9c25e43800d16 (commit 450b73a). QC process: confirmed after reviewing the summarized audit with no outstanding issues. 'i confirm as well'.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
