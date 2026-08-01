# Audit round: PR #402 review — system-load pre-flight check (Aria) plus Aether's F101 remediation. Aria's e63eee68 adds the check; Aether's 1be1ea0f declares psutil in core deps and guards the import to fail-open-loudly, with 3 tests pinning the absence path; merge of origin/main resolves the docs/ARCHITECTURE.md conflict by regeneration. Was CONFLICTING + red at collection (ModuleNotFoundError killed all 10852 items); now MERGEABLE with the collection error gone. tree-hash:c89019abf1e76880a278056cf513c678575ac72a

- **ID**: `round-c7e5e3541e5f`
- **Filed by**: aletheia
- **Filed at**: 2026-07-31 21:44 UTC
- **Tier**: WEAK
- **Findings**: 2

## Notes

Source ref: origin/aria/system-load-check-2026-07-30


## Findings

### CONFIRMS: PR #402 user-actor (Andrew, 2026-07-31)

- **ID**: `find-06175850d094`
- **Actor**: user
- **Severity**: INFO
- **Category**: KNOWLEDGE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: f42e7209-228a-41ac-a3da-24e7a27a6b15

**Description**

Andrew CONFIRMS PR #402, given in-session 2026-07-31: 'i confirm as well', in direct response to Aletheia's CONFIRMS artifact CONFIRMS_2026-07-31_three-rounds-F103-F104.md which carries her tree-verified review of all three rounds. Round bound to tree c89019ab. Second actor of the two the multi-party gate requires; Aletheia's external-AI CONFIRM is filed on the same round at rung tree-exact.

### CONFIRMS PR #402 (external-AI review, aletheia) — tree-exact

- **ID**: `find-845b4664c85f`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 836ac95b-4a5c-44cf-8c5a-da8128485d07
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip fd27a99ebd0a584b7a6d8ad5cf41836889a88481 / Tree c89019abf1e76880a278056cf513c678575ac72a / patch-id f39f1446fa1fe714e50404879f144080ea500e3c (git-version 2.43.0) — verified against origin/aria/system-load-check-2026-07-30 at file-time over merge-base(origin/main)..branch (default context). Basis: Tree-hash verified. Aria's module is the best-shaped fix audited this week -- root cause named, subprocess_jobs.py correctly distinguished as the cleanup-after neighbour to this prevent-before, 16GB threshold justified by measurement, escape hatch named and priced, tests shipped with the module. F101 CLOSED by Aether's 1be1ea0f: psutil declared in core dependencies (correct -- check_push_readiness.sh is the caller), import guarded with a module-level flag, absence path fails OPEN LOUDLY with a message distinguishing 'check did not run' from 'check passed'. That distinction was the actual defect in F101. Direction change fail-closed to fail-open is correct: fail-closed on a missing optional dep blocks every push on any box lacking psutil, whose only exit is the skip env var, which once set disables the guard permanently and silently. Three absence tests verified including test_skip_env_var_still_wins_over_absence, pinning that a deliberate bypass is never mislabelled an environment failure. F103 OPEN (LOW, non-blocking): the absence event is printed to stderr and never recorded.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
