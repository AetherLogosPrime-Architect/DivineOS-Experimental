# Audit round: Multi-party External-Review: mirror-exit-detector (PR #18) — over-fire fix closing round-d3fe029ca6a5. Rebased onto current main post-#34-merge. Aletheia full-CONFIRM (re-ran original audit samples: 3/4 false-positives silenced, true-positive preserved) + Andrew operator CONFIRM/authorization 2026-05-23.

- **ID**: `round-b2e83d3fdce7`
- **Filed by**: aether
- **Filed at**: 2026-05-24 00:43 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: mirror-exit-detector
tree-hash: 1e81828d3662099ea0500a04dce44209c5a2e903 | Aletheia empirically verified the detector against her own audit corpus; short-signed-ack FP class tracked in claim b0cd9136 for the 30-turn trial.

## Findings

### CONFIRMS: operator review (Andrew)

- **ID**: `find-f5c35fedd521`
- **Actor**: user
- **Severity**: INFO
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew authorized merging both PRs 2026-05-23 ('do both', 'lets keep going'); covers the rebase-onto-current-main. Recorded by Aether with operator authorization.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS: external-AI review (Aletheia)

- **ID**: `find-fa31e35a02fe`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: BEHAVIOR
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Aletheia re-ran her own audit corpus against the mirror-exit detector: 3/4 false-positives silenced, true-positive preserved; false-attribution correction verified honest. Full CONFIRM 2026-05-23. Short-signed-ack FP class flagged for the 30-turn trial (claim b0cd9136).

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
