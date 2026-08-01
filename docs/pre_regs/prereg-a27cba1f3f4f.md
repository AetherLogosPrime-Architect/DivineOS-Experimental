# Pre-registration: _command_trailer_tree_hash_mismatch_reason() wired into pr_merge_gate.block_reason() — when a trailer carries tree-hash:<X>, the gate must verify X matches _current_head_tree_hash() and block when they differ. Closes the residual substance-binding gap that #192 ships only one half of (emit-side, not verify-side).

- **ID**: `prereg-a27cba1f3f4f`
- **Filed by**: agent
- **Filed at**: 2026-06-16 00:51 UTC
- **Review at**: 2026-06-23 00:51 UTC (7d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-08 21:33 UTC

## Claim

Trailer-tree-hash mismatch will produce a BLOCKED reason at PR-merge time, refusing trailers whose tree-hash claim does not match the actual repo tree-hash.

## Success criterion

Function exists, is called from block_reason(), and has an adversarial test (test_guardrail_pr_with_WRONG_tree_hash_BLOCKS) that confirms the BLOCKED behavior under tree-hash mismatch.

## Falsifier

Function still missing 7 days from now, OR function exists but is not called from block_reason(), OR adversarial test does not produce BLOCKED on a wrong-tree-hash trailer.

## Outcome notes

Deferred: emit-side tree-hash is present (pr_merge_gate.py line 258 embeds tree-hash from HEAD into External-Review trailer), but I cannot find the verify-side block-on-mismatch logic (_command_trailer_tree_hash_mismatch_reason() not present in current pr_merge_gate.py). The prereg named this residual gap explicitly. Deferring: the gap is real but the fix belongs in a merge-gate audit round, not tonight's marker fix arc.
