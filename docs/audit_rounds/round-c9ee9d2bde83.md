# Audit round: Finding 75 closure: submit-round requires --source-ref (eating dogfood)

- **ID**: `round-c9ee9d2bde83`
- **Filed by**: user
- **Filed at**: 2026-05-18 04:13 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: finding-75-source-ref
tree-hash: 6b466702e5232f812128c99c2157dd25207d67c1  f612ffc — feat(audit): close Finding 75. Branch finding-75-source-ref on origin. Self-referential dogfood: this round uses the very gate it's filing CONFIRMS for.

## Findings

### CONFIRMS — user (Andrew): Finding 75 ratification + stop here

- **ID**: `find-7934313e98f2`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew CONFIRMS in chat ('i confirm'). Pairs with Aletheia's CONFIRMS. Authorizes trailer-amend on f612ffc + push. Also accepts Aletheia's read about fatigue and the stop-here recommendation; remaining queue (Finding 76 + pre-reg-required-before-infra + auto-file-fix-claim + tool-output-truncation) deferred to tomorrow's fresh substrate.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS — Aletheia: Finding 75 substrate-level fix verified across 4 paths + 3-layer defense-in-depth

- **ID**: `find-c82765b97b2c`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

V1 four behavioral paths empirically verified (no-flag-blocked exit 1; invalid-ref-blocked exit 1; valid-ref-passes exit 0; --no-source-ref-bypasses exit 0). V2 auto-annotation confirmed in round notes for both source-ref and no-source-ref paths. V3 audit_commands.py in guardrails with marker; 9 tests pass. V4 dogfood architecture self-consistent. Structural observation: three-layer defense-in-depth now in place against substance-without-verification family (round-creation requires source-ref; push-to-main requires External-Review trailer; commit-time requires staged trailer). Describe-then-CONFIRMS now an architectural constraint, not a discipline-promise.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
