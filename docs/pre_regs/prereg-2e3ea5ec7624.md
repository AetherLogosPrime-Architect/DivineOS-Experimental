# Pre-registration: pr_merge_gate substance-binding (Aletheia 2026-06-14 audit response): added _command_trailer_tree_hash_mismatch_reason() and wired it into block_reason() so trailers carrying a tree-hash MUST have that hash match _current_head_tree_hash(). Closes the bypass-7-shape gap Aletheia named: prior gate trusted trailer presence, passed wrong tree-hashes silently. Added TestTrailerTreeHashSubstanceBinding with 6 tests including the adversarial test_guardrail_pr_with_WRONG_tree_hash_BLOCKS that Aletheia explicitly called for. Updated pre-existing happy-path test to actually mock _current_head_tree_hash so it exercises real binding instead of trailer presence alone.

- **ID**: `prereg-2e3ea5ec7624`
- **Filed by**: agent
- **Filed at**: 2026-06-14 23:04 UTC
- **Review at**: 2026-06-28 23:04 UTC (14d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-06-16 00:49 UTC

## Claim

When a PR-merge command carries an External-Review trailer with a tree-hash, a wrong tree-hash (stale audit round being reused, rebased branch) will BLOCK at the local gate rather than passing silently

## Success criterion

Over the next 14 days, no PR with a tree-hash mismatch slips past the local gate AND zero false-positive blocks on legitimate matching-hash trailers AND the transition-window behavior (trailer without tree-hash) continues to pass

## Falsifier

A wrong-tree-hash trailer passes the local gate OR a legitimate matching trailer blocks falsely OR git-unavailable causes hard-fail instead of fail-open

## Outcome notes

pr_merge_gate substance-binding landed via PR #192 (today) — _current_head_tree_hash + tree-hash trailer parsing. Tests cover TestTrailerTreeHashSubstanceBinding adversarial case. Closing.
