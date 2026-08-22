# Audit round: root-cause-audit: gate-blocks-its-own-remedy (catch-22 family) — a gate that names a remedy command the bypass set does not include, so it blocks the very command meant to clear it. Instances: Gate 1.48 stale-engagement (Finding 37, fixed prior); Gate 3 pull-detection naming 'divineos rt pull-check' with rt un-bypassed (fixed 43bf22ca). Survey: all pre_tool_use_gate.py deny messages naming a 'divineos <subcmd>' remedy, verify each subcmd is bypass-listed.

- **ID**: `round-75bc0b0ca922`
- **Filed by**: aether
- **Filed at**: 2026-05-27 16:09 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: consult-gate-wisdom-reads


## Findings

### Gate 1.45 hedge names 'divineos claim' (singular) remedy but only 'claims' (plural) was bypassed

- **ID**: `find-76bb54ec5e70`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Hedge gate names 'Run: divineos claim ...' to discharge an unresolved hedge, but only 'claims' (plural browse cmd) was bypassed; 'claim' (singular, the filing cmd) was not — so the hedge gate blocked its own remedy. Found by surveying all gate remedies against the bypass set. Fixed: added 'claim'.

**Resolution**

Verified fix: scripts/hook_bypass_commands.txt:85 has 'divineos claim' (singular) and line 82 has 'divineos claims' (plural). Both gate-remedy commands now in bypass list. Finding description already named the fix; just needed status sync.

### Gate 3 pull-detection names 'divineos rt pull-check' remedy but rt was un-bypassed

- **ID**: `find-ae6f9e553352`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Gate 3's deny message says 'Run: divineos rt pull-check to reassess', but 'rt' was absent from _BYPASS_DIVINEOS_SUBCOMMANDS, so when a pull/fabrication marker fired the gate blocked the command meant to clear it. Fixed: added 'rt' (whole namespace is inspection/state, no code-gen).

**Resolution**

Verified fix: scripts/hook_bypass_commands.txt:92 has 'divineos rt' in bypass list. Gate 3 pull-detection remedy now bypassable. Finding already documented the fix; status sync.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
