# Audit round: External-Review: install check_wiring_claims.py into commit-msg gate via setup-hooks.sh (Finding 1 last instance). diff-hash 225e9d282cef...

- **ID**: `round-55d1bba0fe69`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 13:04 UTC
- **Tier**: WEAK
- **Findings**: 2

## Findings

### Andrew CONFIRMS install

- **ID**: `find-67286e457f68`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Andrew CONFIRMS the install. Soft-warning shape; bash-only acceptable.

### Hook installer adds check_wiring_claims as 4th commit-msg gate; soft warning; PowerShell installer pre-existing gap (no commit-msg block at all) noted but out of scope

- **ID**: `find-cf0a3e23d8dc`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Pattern matches existing 3 gates (multi-party-review, closure-claim, root-cause-audit). Soft: '|| true' so always exits 0; never blocks commit. setup-hooks.ps1 has no commit-msg block to extend — pre-existing gap. Operators re-run setup-hooks.sh once to pick up new gate.

**Resolution**

Verified: setup/setup-hooks.sh:171 installs WIRING_CLAIMS gate referencing scripts/check_wiring_claims.py. Comment at line 199 cites 'Closes Aletheia Finding 1 wire-decision for check_wiring_claims.py.' Soft-warning pattern matches the other 3 commit-msg gates as described.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
