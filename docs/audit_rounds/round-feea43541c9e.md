# Audit round: External-Review: wire post-commit-auto-close.sh via setup-hooks.sh+.ps1 (Finding 29 wire half). diff-hash 6998da79986e...

- **ID**: `round-feea43541c9e`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 12:32 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Andrew CONFIRMS post-commit wire

- **ID**: `find-f78b4263ca12`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

CONFIRMS the wire-half decision and delegator shape.

### Aletheia CONFIRMS-pending-empirical: wire delegates via .claude/hooks/post-commit-auto-close.sh, fail-open

- **ID**: `find-1b8e74dfbf73`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Both shell + ps1 install a thin delegator that calls .claude/hooks/post-commit-auto-close.sh (the actual logic, unchanged). Fail-open exits 0 on any error. Empirical verification depends on operators re-running setup-hooks after pull; tracked.

**Resolution**

Recognition / CONFIRM finding — no action needed. Bulk-resolved 2026-06-10 backlog sweep (extended recognition pattern).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
