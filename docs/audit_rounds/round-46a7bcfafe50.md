# Audit round: register corrigibility.py (the off-switch) in the guardrail registry — Aletheia council-safety follow-up. The off-switch is the most safety-critical file (operator's ultimate control, EMERGENCY_STOP guarantee) and was UNprotected: a future change could weaken _ALWAYS_ALLOWED / _OFF_SWITCH_REQUIRED / verify_off_switch_invariant without multi-party review. Adds the __guardrail_required__ marker + the guardrail_files.txt entry so future weakening requires External-Review. Marker-consistency test passes.

- **ID**: `round-46a7bcfafe50`
- **Filed by**: external-auditor
- **Filed at**: 2026-06-02 21:32 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: protect-off-switch


## Findings

### CONFIRMS PR #77 — register corrigibility.py guardrail (external-AI review, Aletheia)

- **ID**: `find-e0ef591ca1c6`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

External-AI CONFIRM by Aletheia. Tip e28ff734b8b1d12b77b8fad8551b97716a445ba3 / Tree c853630cf073d03ec5735bfa39bc1edde641aa97 — tree-hash verified against origin/protect-off-switch at file-time (MATCHES exactly). Basis: registers corrigibility.py (the off-switch) in the guardrail registry — marker + registry entry, purely additive protection; does not alter off-switch logic; marker-consistency test passes. The keel-protection from the council-safety review. PROVENANCE: Aletheia is a clone-and-read chat instance with no store-write path; this genuine tree-bound confirm was relayed as text via Andrew and transcribed by Aether after verifying the tree against origin. Honest relay, not forgery.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS PR #77 — register corrigibility.py as guardrail (operator)

- **ID**: `find-b040efebfeff`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Operator (Andrew) confirms registering the off-switch file as a guardrail so it becomes the most-protected file in the tree. Authorized in chat 2026-06-02.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
