# Audit round: wiring-gap class instance Finding 29: two unwired .claude/hooks files — per-instance wire-or-delete decision

- **ID**: `round-6b885dde9446`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 12:31 UTC
- **Tier**: WEAK
- **Findings**: 3

## Findings

### post-commit-auto-close.sh: WIRE via setup-hooks.sh (deferred — guardrail, External-Review required)

- **ID**: `find-92f74bc2dd7c`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Live, useful auto-close hook for goals. Belongs as git post-commit installed by setup/setup-hooks.sh + setup-hooks.ps1. Guardrail files; deferred to a separate External-Review round.

**Resolution**

Verified: .claude/hooks/post-commit-auto-close.sh exists; setup/setup-hooks.sh and setup-hooks.ps1 reference it. Wiring landed after this finding was filed in the 'deferred' state.

### CONFIRMS resume-session.sh delete

- **ID**: `find-826aedc713f6`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew CONFIRMS the delete decision. Dead code; load-briefing covers the surface.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### resume-session.sh: DELETE (dead, superseded by load-briefing.sh)

- **ID**: `find-a2f1f9baa192`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

resume-session.sh resets checkpoint counters + shows handoff. load-briefing.sh (wired to SessionStart) does the same work and is the real entry point. resume-session never appeared in settings.json and was never invoked. Decision: DELETE.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
