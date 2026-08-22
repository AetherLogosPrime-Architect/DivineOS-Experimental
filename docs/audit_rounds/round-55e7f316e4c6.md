# Audit round: Pre-review: push-readiness gate skips pytest on deletion-only pushes. Guardrail file scripts/check_push_readiness.sh. Single commit 987872d5: detect all-zero local-shas across pushed refs (git pre-push protocol's deletion marker); if every ref is a deletion, skip the ~10min pytest gate (nothing enters main, nothing to verify). Mixed push (deletion + real update) still runs full gate. Multi-party check already skipped deletions per-ref, unchanged. Tested both paths + shellcheck clean.

- **ID**: `round-55e7f316e4c6`
- **Filed by**: aether
- **Filed at**: 2026-05-26 16:11 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: push-gate-skip-deletion
Commit 987872d5 tree-hash: ac7bdd12aaa498de735caadcbb7ce811dc17973e (the commit the push-to-main gate validates). Single-commit branch; this is also the branch tip tree.

## Findings

### CONFIRM: push-gate deletion-skip — external-AI review, 6 cases verified

- **ID**: `find-be2b604ee83a`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Aletheia (sibling-Claude external auditor) CONFIRM, bound to tip 987872d5 / tree-hash ac7bdd12aaa498de735caadcbb7ce811dc17973e. Verified detection across 6 stdin shapes (pure deletion, multi-deletion, normal update, mixed, empty, SHA256 all-zero) all correct; conservative defaults right-direction; multi-party check unchanged. External-AI half of the two-key.

**Resolution**

Recognition / CONFIRM finding — no action needed. Bulk-resolved 2026-06-10 backlog sweep (extended recognition pattern).

### CONFIRM: push-gate deletion-skip — operator sign-off

- **ID**: `find-488760924e4d`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew (operator) CONFIRM, verbatim: 'i confirm'. Human half of the two-key for the guardrail change to scripts/check_push_readiness.sh (deletion-only pushes skip pytest).

**Resolution**

Recognition / CONFIRM finding — no action needed. Bulk-resolved 2026-06-10 backlog sweep (extended recognition pattern).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
