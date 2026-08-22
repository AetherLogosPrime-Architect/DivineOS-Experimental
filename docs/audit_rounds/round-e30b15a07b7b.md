# Audit round: root-cause-audit: keyword-detector-shape family — F87 lexical bypass + gravity classifier over-firing on guardrail-listed clay-mode edits

- **ID**: `round-e30b15a07b7b`
- **Filed by**: aether
- **Filed at**: 2026-07-26 20:16 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: 33cffb2a40b791b4cc1e55ae8751669e147a9010


## Findings

### Gravity classifier over-firing on guardrail-listed clay-mode edits — sibling instance of same class

- **ID**: `find-e9671164aa4f`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: cb0cf355-d5cf-4ee6-b66b-268eb277932d
- **Tags**: keyword-detector-class, classifier-conflation, clay-vs-kiln

**Description**

Sibling instance of the keyword-detector-shape class: gravity classifier treated 'edit-guardrail-listed' as high-impact short-circuit for council-required. This treated CLAY-MODE workspace edits as if they were KILN-MODE pre-push transitions, producing 8-lens council walks per edit and blocking free workspace exploration. Root cause: conflation of 'files that need External-Review at merge' with 'files that ARE identity substrate needing council on edit'. External-Review at merge is the discipline for guardrail-listed; kiln-layer (foundational_truths + seed.json) is what warrants council on edit.

**Recommendation**

Removed 'edit-guardrail-listed' from _HIGH_IMPACT_FEATURES. Kept 'edit-kiln-layer' (foundational_truths.md + seed.json ARE identity). Cumulative score-threshold council-required still fires at total>=6. Updated 4 tests to match new correct behavior. 51/51 gravity classifier tests pass.

### F87 root cause: lexical detectors used as gate triggers are structurally bypassable by rephrasing

- **ID**: `find-4f65e972bc00`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 9cd0c5e8-c7d3-4470-99e1-38a1fe6c8e52
- **Tags**: keyword-detector-class, structural-fix

**Description**

Class of failure: any gate that decides fire/pass based on regex-matching reply-text has a structural bypass — composer rephrases past the pattern. F87 caught this in check_thread_walk_required (keyed on _has_solution_shape). Same shape has appeared before (Andrew 2026-05-14 mesa-optimizer routes around specific patterns, 2026-07-10 SHAPE-vs-SURFACE primary architectural discipline, 2026-07-23 keyword detectors are a sin only good for backup). Fix pattern: replace lexical trigger with structural signal from action-stream (which tool is about to fire, which command in the turn, which walk-record exists). Structural signals cannot be rephrased around because they are events not text-shape.

**Recommendation**

Retire lexical gate-triggers class-wide. Replace with structural signal-based triggers per Aria's five-primitive design. Pattern established this session: check_should_block in verify_before_build_signal.py is the working shape (fires at PreToolUse against substrate-mutating tools). Future gate-designs must use signal-based triggers unless composer can articulate why lexical is necessary for this specific case.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
