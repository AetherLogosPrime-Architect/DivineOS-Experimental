# Audit round: GATE-GATE #16: context-aware tiered correction-detector (strong blocks / weak advises by prior-turn context)

- **ID**: `round-dd1f8a224d2b`
- **Filed by**: external-auditor
- **Filed at**: 2026-06-04 16:44 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: feat/correction-detector-context-aware


## Findings

### Aletheia external-AI CONFIRMS #85

- **ID**: `find-e23653fadddc`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Aletheia 2026-06-04 audit CONFIRM, relayed (she cannot run CLI). #83: hard safety walls verified to still short-circuit individually + take precedence. #85: epistemic-complement HOLD fixed (doesnt mean/imply caps at advise) + re-verified by my own probe.

[retroactive-anchor 2026-06-07]
Tree 4fffd69d744e5b80cfb81cfbdf7bf4914aab9d1b [synthesized-retroactively-from-merge-commit on 2026-06-07]
merge-commit 01f16e9c0b53f9f9700d88473fa994e40296200c
merged-at 2026-06-04T19:01:54Z
vantage-caveat: patch-id NOT recorded — Aletheia 2026-06-02 named patch-id as cross-vantage-unstable (context lines / git config / line endings). Tree-hash alone is the load-bearing anchor for this retroactive sweep. Original CONFIRM was filed without anchors; this backfill is the rigor-discharge per task #50.

[internal-verification 2026-06-07]
internal-verification: aether-confirmed 2026-06-07
basis: Context-aware tiered correction-detector shipped; the detector now distinguishes strong vs weak correction patterns by prior-turn context (observed: false-fires on quoted text and meta-discussion this session were correctly handled or surfaced as known false-fire pattern). Re-verified via merge commit 01f16e9c0b53. No regression.

### user CONFIRMS #85 merge

- **ID**: `find-9279cd7c0f24`
- **Actor**: user
- **Severity**: INFO
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Andrew approved merging the Aletheia-confirmed guardrail PRs (lets do C; yes keep going; lets build the 1 button then land them). Recorded on his behalf per his standing rule that I run the CLI for him.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
