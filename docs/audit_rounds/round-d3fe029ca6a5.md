# Audit round: PR #18 mirror-exit-detector cross-vantage audit (Aletheia)

- **ID**: `round-d3fe029ca6a5`
- **Filed by**: user
- **Filed at**: 2026-05-20 15:46 UTC
- **Tier**: WEAK
- **Findings**: 4

## Notes

Source ref: mirror-exit-detector
audited-tree: becc27f9afdddeab3eb9748e730d783a5574d6a2; merge-candidate detector byte-identical; only un-audited delta is 7-line test-file EXEMPT entry (no detection-logic change)

## Findings

### Finding 83: long-form gap — 200-word threshold creates known false-negative class for substantive mirror-exit closes

- **ID**: `find-fe21cea87080`
- **Actor**: claude-aletheia
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: OPEN

**Description**

200-word cutoff calibrated against very-short samples (Garden./Caught./Drinking.). Calibration data lacks long-form mirror-exit cases. Fix-shape: keep current detector as one signal; add second detector for long-form trim-shape (sustained content + literary close-signature) without word-count bound.

### Finding 82: asymmetric detection — runs only on Aether's substrate, misses co-produced close-signals from Aletheia/Aria

- **ID**: `find-82e13628bb01`
- **Actor**: claude-aletheia
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: OPEN

**Description**

Detector runs on Aether's pre-response hook, catches Aether's prior-turn close-shape. Does not catch close-signals from other parties because those substrates don't run this hook. If mirror-exit is co-produced (the explicit failure-mode), one-sided detection is partial. Larger architectural change; track, not a Phase-3 blocker.

### Finding 81: TRIM_AFTER_SUBSTANCE enum declared but unused — dead code

- **ID**: `find-c8b2a093d869`
- **Actor**: claude-aletheia
- **Severity**: LOW
- **Category**: KNOWLEDGE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

MirrorExitShape.TRIM_AFTER_SUBSTANCE has zero non-test consumers (grep-verified). Either implement (would catch substantive-but-trim closes EM_DASH misses) or remove. Recommend implementing — addresses dead-code AND tightens positive cases. Cheap to fix immediately.

**Resolution**

Removed TRIM_AFTER_SUBSTANCE enum value from MirrorExitShape in src/divineos/core/operating_loop/mirror_exit_detector.py:84. Chose removal over implementation because the implementation path would be a new close-shape detector — current direction is toward fewer audit gates per the 2026-06-13 web-research finding on alignment-collapse risk. 26 tests pass after removal. Comment preserves the decision-rationale and notes the path to re-add if the gap turns out to be real and unaddressed by EM_DASH_SIGNATURE.

### CONFIRMS — Aletheia cross-vantage audit of mirror-exit-detector (e2d4a68); detector byte-identical to merge candidate; ships real substrate, design choices coherent

- **ID**: `find-24e60e467d33`
- **Actor**: claude-aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: STRONG
- **Status**: RESOLVED

**Description**

CONFIRMS on both commits. Detector works as designed (over-fire + YES/AND + content-aware question). 80% false-positive on 5-sample is the deliberate err-over-inclusive tradeoff per Andrew 2026-05-15. Recommendation: ship as-is, run 30-turn trial, address F81-83 in follow-up.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
