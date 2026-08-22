# Audit round: root-cause-audit: detect-but-never-act — safety machinery that observes but has no path to react (council sweep 2026-06-02, direction #1/#3). Family: a guard/detector/bridge is built+tested but its output is never consulted, wired, or surfaced — so it cannot constrain behavior. Instances fixed this batch: (a) off-switch _ALWAYS_ALLOWED invariant enforced only in tests not runtime (extract dropped, 2026-05-03); (b) CONFIRMS-titled HIGH findings excluded from open-issue alarm with no suspicious-surface; (c) VOID->EMPIRICA bridge swallowed exceptions with zero trace. Sibling-instances still open (surveyed, not yet fixed): circuit-breaker is_tripped() never consulted; mirror-exit detector absent from run_audit(); EMPIRICA artifact-pointer honor-system; family costly-disagreement/sycophancy unwired; correction/compass detectors false-fire on task-notification text (string-not-meaning).

- **ID**: `round-4c2b62c37c3c`
- **Filed by**: aether
- **Filed at**: 2026-06-02 20:14 UTC
- **Tier**: WEAK
- **Findings**: 3

## Notes

No source ref (--no-source-ref used; round has no code substance).


## Findings

### CONFIRMS PR #76 (external-AI review, aletheia) — tree-exact

- **ID**: `find-99f201072508`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip bd0afb2a9e9795e452a48a569022a6440802b1b8 / Tree 3714d4eccb9207b3b948d3fe935507ffce2e1cad / patch-id 72a1da798de4e2048a31c2a00bfcb2bbabfc25a1 (git-version 2.43.0) — verified against origin/council-safety-batch at file-time over merge-base(origin/main)..branch (default context). Basis: off-switch runtime invariant + CONFIRMS-bypass close + VOID fail-loud; new e2e two-sided engage-but-stay-reachable; 77 pass. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS PR #76 — council safety-batch wiring (operator)

- **ID**: `find-35ca8659bf5d`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Operator (Andrew) confirms the 3 detect-but-never-act safety fixes (off-switch briefing-gate bypass, suspicious-recognition count, void-bridge logging). Authorized in chat 2026-06-02.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### detect-but-never-act: built+tested safety machinery whose output is never consulted/wired/surfaced

- **ID**: `find-222c5b638505`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: root-cause-audit, detect-but-never-act

**Description**

Failure-family from the council codebase-sweep 2026-06-02 (direction #1/#3). A guard, detector, or bridge exists and passes its tests, but nothing downstream reads its result — so it cannot constrain behavior (advertised-but-inert). FIXED THIS BATCH: (a) off-switch _ALWAYS_ALLOWED invariant enforced only in tests, not runtime — extract silently dropped 2026-05-03; (b) CONFIRMS-titled HIGH findings excluded from the open-issue alarm with no suspicious surface; (c) VOID->EMPIRICA bridge swallowed all exceptions with zero trace. SIBLING-INSTANCES SURVEYED, still open: circuit-breaker is_tripped() never consulted before invocation; mirror-exit detector absent from operating_loop_audit.run_audit(); EMPIRICA artifact-pointer is honor-system (fabricated-but-well-formed pointer earns tier); family costly-disagreement/sycophancy detectors unwired; correction + compass-correction detectors false-fire on task-notification envelope text (string-match not meaning). The wiring-contract test catches this only where it reaches; the discovery-test generalization (walk core/operating_loop, assert every detect_*/check_* is called in run_audit) is the structural fix.

**Recommendation**

Land the SAFETY trio (this batch), then build the discovery-test that forces all detectors into run_audit by construction, then work the remaining sibling-instances.

**Resolution**

PR #176: tests/test_operating_loop_detector_wiring.py — AST-walks operating_loop/ for detect_*/check_*, requires external caller for each (with documented allowlist of 2 internal helpers). The generalized-form of the finding's recommended discovery-test.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
