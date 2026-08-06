# Audit round: root-cause-audit: hash-chain/supersession concurrency-fork family (read-modify-write without serialization + non-monotonic chain ordering)

- **ID**: `round-850e6bbae425`
- **Filed by**: aether
- **Filed at**: 2026-05-21 21:05 UTC
- **Tier**: WEAK
- **Findings**: 5

## Notes

Source ref: ledger-integrity-walls


## Findings

### CONFIRMS: operator approves PR #27 (YY/AAA)

- **ID**: `find-949ae78253ad`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS, external-review

**Description**

CONFIRMS (operator, Andrew, 2026-05-21): 'i confirm'. Approves PR #27 (opinion_store + bio concurrency fix) for merge, alongside Aletheia's external-AI CONFIRM.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS: PR #27 YY/AAA lock-only fix — WAL mechanics verified

- **ID**: `find-a72c909a5c20`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS, external-review

**Description**

CONFIRMS (external-AI, relayed via Andrew 2026-05-21) for the PR #27 scope (YY opinion_store, AAA bio.py). Verified the SQLite mechanics: both route through _ledger_base.get_connection (WAL + synchronous=NORMAL + busy_timeout=5000), so BEGIN IMMEDIATE gives the snapshot semantics the fix depends on — T2's snapshot is established at its first read AFTER acquiring the lock (after T1 commit), so read-under-lock IS the recheck. Confirmed the canonical decision tree: hash-chain -> lock+ts-inside+rowid-tiebreak (UU/CCCC); supersession-where-SELECT-doesnt-check-state -> lock+explicit guard (ZZZ); simple RMW where read includes the state-check -> lock alone (YY/AAA). No objection to merge.

[retroactive-anchor 2026-06-07]
Tree 56ba1eb8bf87211eac830dbafc9b85ee5d56cde7 [synthesized-retroactively-from-merge-commit on 2026-06-07]
merge-commit 930c8155c8c12cf44c47cca71c00cf0745076c6e
merged-at 2026-05-21T22:44:43Z
vantage-caveat: patch-id NOT recorded — Aletheia 2026-06-02 named patch-id as cross-vantage-unstable (context lines / git config / line endings). Tree-hash alone is the load-bearing anchor for this retroactive sweep. Original CONFIRM was filed without anchors; this backfill is the rigor-discharge per task #50.

[internal-verification 2026-06-07]
internal-verification: aether-confirmed 2026-06-07
basis: Concurrency serialization for opinion_store + bio shipped; race condition fix is in place. The serialized read-modify-write pattern is alive in the codebase today. Re-verified via merge commit 930c8155c8c1. No regression.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS: operator approves ledger race fix (PR #26)

- **ID**: `find-b47a1c7c6f54`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS, external-review

**Description**

CONFIRMS (operator, Andrew, 2026-05-21): 'yes i confirm both'. Approves PR #26 (UU/CCCC/ZZZ ledger-integrity race fix) for merge. Completes the two-party record alongside Aletheia's external-AI CONFIRM (find-f7b03acdb5d2).

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### CONFIRMS: ledger-integrity race fix (UU/CCCC/ZZZ) — augmented pattern verified

- **ID**: `find-f7b03acdb5d2`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS, external-review

**Description**

CONFIRMS (external-AI, relayed via Andrew 2026-05-21). Aletheia confirms PR #26 closes UU/CCCC/ZZZ. Her original prescription (BEGIN IMMEDIATE alone, 'same as main ledger') was incomplete; Aether's barrier-released threaded dogfood proved the chain still forked and surfaced 3 vectors: (1) capture ts INSIDE the lock (wall-clock non-monotonic across threads diverges ts-ordered chain from insertion order); (2) rowid secondary tiebreak in both reader and verifier; (3) supersession superseded_by-IS-NULL re-check inside the lock for ZZZ. Augmented canonical pattern for the BEGIN IMMEDIATE race family: lock + ts-inside-lock + rowid-tiebreak + supersede-recheck. Aletheia self-named this as the 5th instance of audit_verification_insufficiently_adversarial (prescribed from documented fix-history without threaded dogfooding). No objection to merge.

[behavior-level-stamp 2026-06-07]
Type: behavior-level CONFIRM
Anchor: none-by-design (this CONFIRM verifies a feature/gate/detector operating correctly at the time, not the state of specific code at a specific tree. The catch-up-stable question does not apply because the verification was about behavior persistence.)
Internal-verification: aether-confirmed 2026-06-07 — verified the named behavior persists in the current substrate. No regression observed in the live system. The original external CONFIRM stands.
Per task #51 architectural-debt discharge.

**Resolution**

Audit-status reconcile 2026-05-23 (Aether, authorized by Andrew): this finding is an external CONFIRMS/approval, not an open issue. An approval has no open action, so it was inflating the open-count. Closed as RESOLVED. PENDING-EMPIRICAL confirmations were held OPEN (they carry a real verification action).

### concurrency-fork family: read-modify-write on hash-chained / supersession stores without serialization

- **ID**: `find-333eeeb1ae15`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

FAMILY: a writer reads current state (latest chain hash / current knowledge entry), computes a successor, inserts — without holding a write-lock across read->compute->insert, so two concurrent writers both chain off the same predecessor and FORK. Two-part root cause (proven by dogfood): (a) missing BEGIN IMMEDIATE serialization; (b) ordering hazard — chain-order defined by wall-clock timestamp captured OUTSIDE the lock is non-monotonic across threads, diverging from insertion order and re-forking even with the lock. SIBLINGS SURVEYED: main ledger.py (already fixed, gold standard, round-ba785844a791 Finding 15); family_member_ledger UU (FIXED here: BEGIN IMMEDIATE + autocommit + ts-inside-lock + rowid tiebreak); void/ledger.py CCCC (FIXED here, same + rowid tiebreak added since it ordered by ts alone); knowledge/crud.py update_knowledge+supersede_knowledge ZZZ (FIXED here: BEGIN IMMEDIATE + already-superseded guard, the supersession analog of read-latest-under-lock). NOT-YET (different class or separate tasks): opinion_store YY, bio.py AAA (same concurrency class — follow-up tasks), ledger_compressor DDD (DIFFERENT class: compaction dangles chain, guardrailed, split to task #58). Each fix carries a deterministic threaded dogfood test asserting no duplicate prior_hash and verify_chain passes.

**Resolution**

Concurrency-fork family fully closed: (1) opinion_store store_opinion already had BEGIN IMMEDIATE; ts-inside-lock fix landed today (2026-06-14) moving 'now = time.time()' after BEGIN IMMEDIATE to match family_member_ledger gold standard. strengthen_opinion (line 228) and challenge_opinion (line 263) already capture time.time() inline inside the lock — no change needed. (2) bio.py bio_write uses time.time() inline inside the lock on line 85 — already correct, no change needed. ledger_compressor split to task #58 as different class (compaction-dangles-chain). 21 opinion_store tests pass after the fix.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
