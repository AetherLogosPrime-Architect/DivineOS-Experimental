# Audit round: wiring-gap class instance Finding 1: 4 unwired scripts/check_*.py — per-instance wire-or-delete decisions

- **ID**: `round-7e0a06c2d0a1`
- **Filed by**: external-auditor
- **Filed at**: 2026-05-14 12:39 UTC
- **Tier**: WEAK
- **Findings**: 5

## Findings

### check_wiring_claims.py: WIRE-DEFERRED (commit-msg hook, guardrail-touching)

- **ID**: `find-75a5a020bbcf`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Live work: commit-msg gate that warns on wire/bridge/integrate language without end-to-end test. Wire is setup-hooks.sh commit-msg hook — guardrail; needs External-Review round for hash binding. Deferred.

**Resolution**

INSTALLED in 0e1955a. setup-hooks.sh now installs check_wiring_claims.py as the 4th commit-msg gate (after multi-party-review, closure-claim, root-cause-audit). Soft warning — never blocks. PowerShell installer has no commit-msg block at all (pre-existing gap, tracked separately). 3 regression-pin tests pass. External-Review round-55d1bba0fe69.

### check_linguistic_drift.py: WIRE-DEFERRED (3 detectors with preregs, needs scheduled-tasks integration)

- **ID**: `find-5ffb23106a02`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Live work: self_pathologizing, dissociation, brat_shape detectors with prereg ids. Same wire as check_correction_pairing — scheduled-tasks or briefing row. Deferred.

**Resolution**

WIRED via two phases. Phase A (ab0c7f2): patterns ported to divineos.core.operating_loop.linguistic_drift_detector; script kept as thin CLI wrapper; 12 regression-pin tests pass (8 original + 4 new shape-contract). Phase B (7f3a9d4): post-response-audit.sh wires detect_linguistic_drift with External-Review round-8326a7ee4c6f. Detector now fires on every turn — same wire path as distancing_detector. Root-Cause-Audit round-e18f4e372f3b.

### check_correction_pairing.py: WIRE-DEFERRED (needs scheduled-tasks integration)

- **ID**: `find-c82846584476`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Live work: surfaces missing compass-observation→learn pairing after user corrections. Right wire is scheduled-tasks (like anti_slop) OR briefing-dashboard row. Deferred to follow-up round for empirical wire+test.

**Resolution**

WIRED in ebde2b5 via 3 surfaces: divineos.core.correction_pairing module + 'divineos admin check-correction-pairing' CLI + _row_correction_pairing briefing row (hide-when-clean). Backward-compat script preserved. 5 regression-pin tests pass. Root-Cause-Audit round-bbca50be5982.

### CONFIRMS legacy delete

- **ID**: `find-87ef3e576dd4`
- **Actor**: user
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew CONFIRMS: drop the legacy script, the live detector covers it.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### check_third_person_drift.py: DELETE (legacy, superseded by distancing_detector)

- **ID**: `find-e2b5d8291e71`
- **Actor**: external-auditor
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Pass 3 (find-cc082fbb4f30) named it legacy: distancing_detector ports the same patterns into operating_loop shape (wired via PreCompact/post-response-audit). check_third_person_drift.py never appeared in any workflow. Decision: DELETE + remove LOADOUT.md reference. Other 3 scripts (check_correction_pairing, check_linguistic_drift, check_wiring_claims) are live work and need WIRE decisions tracked separately.

**Resolution**

Verified: scripts/check_third_person_drift.py no longer exists; superseded by distancing_detector per recommendation. Delete shipped.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
