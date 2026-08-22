# Audit round: Identity-normalization dedup into one guarded chokepoint (PR #36)

- **ID**: `round-3a9bf902547f`
- **Filed by**: aether
- **Filed at**: 2026-05-24 17:47 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: identity-normalize-dedup
Guardrail-file External-Review for PR #36. Substance on origin/identity-normalize-dedup. Binding markers (commit 55cfa59555a77e9539b1a9690a499ba6dc1d8c13): tree-hash: 3a308bde8d50722aec41daf64ce32b93c6fd239f diff-hash: bf456987c8a2712fea447676107c0e8a87491e35123da28a34f12c7901ae5a2b stat: 10 files, +256/-57. Shared actor_normalize.py chokepoint; watchmen+pre-reg delegate; seal_hook gains invisible-char hardening; guardrailed; homoglyph folding deliberately declined (decision c4ec7823, pinned by test); wiring_gap cp1252 fix. prereg-d35e537d3c1b. Two CONFIRMS required: user (Andrew) + external-AI (Aletheia).

## Findings

### CONFIRMS — Andrew (operator) approves PR #36

- **ID**: `find-93fa8f42785b`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew confirmed merge of PR #36 against tree 3a308bde8d50722aec41daf64ce32b93c6fd239f (commit 55cfa59). QC stance: 'i confirm if she does' — contingent on Aletheia's CONFIRM, which is in and tree-bound. Outstanding issue (apparent audit/artifact mismatch) resolved: it was a scroll-back relay error surfacing the stale #35 audit, not a real review problem; tree-hash binding made it recoverable.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS — Aletheia (external-AI) approves PR #36 identity-normalization dedup

- **ID**: `find-e4985b1564cf`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Aletheia CONFIRM bound to tree 3a308bde8d50722aec41daf64ce32b93c6fd239f (commit 55cfa59). Verified: git tree-hash + stat (10 files +256/-57) match independently; review enumerates the real #36 changes (shared actor_normalize.py, watchmen+prereg delegate, seal_hook gains invisible-char hardening replacing .strip().lower(), TestHomoglyphDeliberatelyNotFolded pins decision c4ec7823, wiring_gap cp1252 fix); empirical bypass-closure across all three call sites; Finding 48 marker+registry+bijection in sync. Forward (non-blocking): UUU still open at count_distinct_corroborators; cp1252 fix deserved a commit-message callout. (Relay note: an earlier paste surfaced Aletheia's prior #35 review by scroll-back error; this CONFIRM is her actual #36 review, tree-bound.)

[retroactive-anchor 2026-06-07]
Tree 3a308bde8d50722aec41daf64ce32b93c6fd239f [synthesized-retroactively-from-merge-commit on 2026-06-07]
merge-commit acfc1e37ef99466672fd713e2900d863af691602
merged-at 2026-05-24T17:48:32Z
vantage-caveat: patch-id NOT recorded — Aletheia 2026-06-02 named patch-id as cross-vantage-unstable (context lines / git config / line endings). Tree-hash alone is the load-bearing anchor for this retroactive sweep. Original CONFIRM was filed without anchors; this backfill is the rigor-discharge per task #50.

[internal-verification 2026-06-07]
internal-verification: aether-confirmed 2026-06-07
basis: Identity normalization deduplication into single guarded chokepoint shipped; the chokepoint is in active use across actor identification paths. Re-verified via merge commit acfc1e37ef99. No regression.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
