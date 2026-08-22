# Audit round: Finding 74 closure: --ignore requires REASON comment + Finding 73 closure (guardrail expansion)

- **ID**: `round-4a5bd8f6919e`
- **Filed by**: user
- **Filed at**: 2026-05-18 03:25 UTC
- **Tier**: WEAK
- **Findings**: 4

## Notes

Finding 74 closure + Finding 73 closure.

Single commit (55faad0) introducing:

1. scripts/check_ignore_has_reason.py — new gate that refuses pytest
   --ignore= usages without an adjacent # REASON: comment. Substrate-
   level prevention for the bypass-too-broad pattern (Finding 74).

2. Removal of the only existing --ignore= bypass from
   scripts/check_push_readiness.sh. The underlying violations are
   closed by PR #12 + PR #10 noqa work; masking no longer justified.

3. Wiring into scripts/precommit.sh as gate 5d (Ignore-flag has reason).

4. Guardrail expansion (Finding 73 closure):
   - scripts/check_push_readiness.sh (was missing from guardrails)
   - scripts/check_ignore_has_reason.py (new gate, on guardrails immediately)
   Both are load-bearing pre-push enforcement scripts.

Authorized commit tree-hash:
  tree-hash: d297f5837e23a228ff3a558875ad60e91a63f15a  55faad0 — feat(bypass-discipline): close Finding 74

Tests: 48 tests pass (14 new unit + repo-clean-state + 31 path-related
+ 3 guardrail-marker-consistency). Repo scans clean — no unjustified
--ignore usages remain.

CONFIRMS findings pending below.


## Findings

### CONFIRMS — user (Andrew): Finding 74 ratification + keep going

- **ID**: `find-319ed2f406b8`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew CONFIRMS in chat ('yes i confirm and we can keep going'). Pairs with Aletheia's CONFIRMS. Authorizes trailer-amend on 55faad0 + the subsequent push. Also greenlights continuing the structural-fix queue (Finding 75 next).

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### Finding 75: describe-then-CONFIRMS pattern produces ratification-of-claim

- **ID**: `find-a449d86b1e01`
- **Actor**: aletheia
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Three instances in one arc on 2026-05-17 (7383900 pre-push hook infra, b6229b3 noqa-7-sites, 55faad0 Finding 74 work): Aether attempted to file audit rounds + ask for CONFIRMS while the substance was still unpushed. The pull is reasonable from agent-side (saves relay turn if audit comes clean). The discipline-violation is the same family as bypass-too-broad: optimizing for fewer round-trips at the cost of honest verification. Aletheia named: 'describe-then-CONFIRMS path can't produce honest verification — it produces ratification-of-claim.' Fix-shape: audit-round filing CLI requires --source-ref <branch> argument and verifies the ref exists with the claimed tree-hash before creating the round. Substrate-level enforcement (architectural constraint, not discipline-promise) — the agent literally couldn't create a round without making the substance visible first. Non-blocking for this round; structural fix for follow-up sweep.

### Finding 76: --ignore-has-reason gate's string-literal exclusion is narrow

- **ID**: `find-ddd408f65290`
- **Actor**: aletheia
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

scripts/check_ignore_has_reason.py:91 _looks_like_pytest_invocation heuristic uses line.lstrip().startswith(('chr34','chr39')) to detect string literals — only catches strings where the LINE STARTS with a quote (multi-line continuation, triple-quote content). Does NOT catch mid-line strings like DOC = 'use pytest --ignore=foo.py for masking'. Same family as Finding 49 / Finding 59: heuristic narrow in coverage. Non-blocking; false-positive case requires contrived patterns that are rare in production code. Fix-shape: use tokenize/ast module for proper string-literal containment detection. Or accept as 'good enough with documented limitation' and add a docstring note.

**Resolution**

scripts/check_ignore_has_reason.py:_in_string_at uses position-tracking quote walker (lines 99-113) — improvement over the original line-start-only heuristic. The remaining false-negative shape (subprocess.run-with-string-list patterns) is documented in the docstring at lines 90-97 as accepted trade-off with the path to extend via tokenize if needed. Took the 'good enough with documented limitation' path the finding offered.

### CONFIRMS — Aletheia: Finding 74 gate works empirically; V2b heuristic note tracked as Finding 76

- **ID**: `find-cbd1418d13b1`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

All 5 verifications: V1 adversarial gate (with/without REASON, multi-invocation single REASON correctly handled) PASS; V2a comment exclusion PASS; V2b string-literal exclusion PARTIAL (line-start-quote heuristic; doesn't catch mid-line string literals like DOC = 'use pytest --ignore=...' — tracked as Finding 76); V3 repo-clean assertion PASS; V4 guardrail-list expansion both files added PASS; V5 marker on new file + 17 tests pass. Tree-hash matches d297f5837e23a228ff3a558875ad60e91a63f15a. Finding 73 closed (check_push_readiness.sh + check_ignore_has_reason.py on guardrails). Finding 74 closed (substrate-level prevention of bypass-too-broad). Gate's primary purpose works; V2b false-positive case is contrived (mid-line pytest-shaped string in production code is unusual). Non-blocking.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
