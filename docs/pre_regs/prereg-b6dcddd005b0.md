# Pre-registration: PreToolUse Bash hook blocks gh pr merge invocations on PRs that touch guardrail files unless a valid External-Review audit round (operator-CONFIRMS + external-AI-CONFIRMS within 14d) is referenced via --body or trailer. CLI command divineos pr-merge-check <pr> validates and emits the merge body if clean.

- **ID**: `prereg-b6dcddd005b0`
- **Filed by**: agent
- **Filed at**: 2026-05-28 20:43 UTC
- **Review at**: 2026-06-27 20:43 UTC (30d window)
- **Outcome**: **SUCCESS**
- **Decided at**: 2026-07-08 21:30 UTC

## Claim

Structurally enforces multi-party-review discipline at the merge-action layer, so a fresh DivineOS install inherits guardrail protection without operator-side GitHub branch-protection configuration.

## Success criterion

Within 30 days: (a) zero post-merge Integrity Audit failures on main from new PRs; (b) at least one attempted gh pr merge on a guardrail-touching PR blocked by the hook with the operator running pr-merge-check to satisfy it before retry.

## Falsifier

The hook either (a) misses guardrail-touching PRs (false negative — a merge proceeds without audit round and Integrity Audit fires red post-merge), or (b) blocks merges on non-guardrail-touching PRs (false positive — operator reports friction on clean PRs). Either pattern observed twice within review window invalidates.

## Outcome notes

Shipped: pr_merge_gate.py + ci_merge_review_check.py enforce the External-Review round requirement on guardrail-touching PRs at merge time. divineos pr-merge-check validates and emits the merge body per CLAUDE.md rule 8.
