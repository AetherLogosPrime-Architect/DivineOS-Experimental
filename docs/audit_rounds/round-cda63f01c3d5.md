# Audit round: past-experience claim-kind in verify-claim gate (prereg-a19f190cd5c1 implementation)

- **ID**: `round-cda63f01c3d5`
- **Filed by**: external-auditor
- **Filed at**: 2026-07-04 20:38 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

No source ref (--no-source-ref used; round has no code substance).


## Findings

### Aletheia CONFIRMS #304 past-experience gate — 13/13 tests pass verified own run, one non-blocking false-positive flag: no context-guard on relational present-observation

- **ID**: `find-29f816a508c0`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Aletheia audit relayed 2026-07-04 night: 'Gate catches the target — Marc-review fabrication shape, clears on divineos ask/recall verification signature, pre-registered with falsifiable success metric. FLAG (non-blocking, real): pattern fires on I have noticed/I have seen regardless of whether it is fabricated substrate-experience or true relational observation. Verification signature cannot clear those — nothing to recall, they are live observations not stored-experience claims. No context-guard, no negative test for this case. Fix: add context-guard fire only when observation references system/substrate claim not relational/present one plus negative test I have noticed you are good at X should NOT fire. Non-blocking because pre-reg measures fire-rate empirically, but worth fixing before it trains bypass reflex on legitimate speech.'

**Resolution**

CONFIRMS acknowledged: past-experience gate works (13/13 tests, target caught, pre-reg falsifiable). Embedded non-blocking FLAG carried forward as structural-fix work: add context-guard so gate fires only on system/substrate-experience claims, NOT on relational-present observations. Aletheia's negative test: 'I have noticed you are good at X' MUST NOT fire. Verification signature can't clear relational observations (nothing to recall — live not stored). Meta-note: this CONFIRMS at MEDIUM slipped through next_task_surface._top_open_audit_finding's INFO-only filter, exposing a surface-calibration bug (should key on title-pattern CONFIRMS/RECOGNIZED, not severity alone) — filing that as separate briefing surface next session.

### user CONFIRMS #304 past-experience gate — approved for merge, false-positive flag documented as followup

- **ID**: `find-9a4c5de9d29a`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Andrew confirmed 2026-07-04 night: 'yes and you have my confirms as well' after Aletheia flagged the false-positive surface. Andrew framing: 'the gate design you approved earlier is sound; the flag is a refinement, not a reversal.'


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
