# Audit round: root-cause-audit: read-then-write TOCTOU class across DB write-paths. Class definition: any code path that reads database state, computes next state from the read, and writes the next state — WITHOUT wrapping the read+compute+write sequence in an atomic transaction (BEGIN IMMEDIATE or equivalent). The instance Aletheia caught was log_event in ledger.py: concurrent writers could both read the same prior_hash, both compute chain_hash against the same prior, both INSERT, forking the chain. Family-survey: audit every DB-writing module for the same pattern. Candidates: knowledge_maintenance.increment_corroboration (drives maturity-promotion counter), family stores, watchmen audit-round counters, session_checkpoint write counter, any read-modify-write sequence. Fix-class: wrap each in BEGIN IMMEDIATE or move to atomic UPDATE. Defer bounded patterns to tracking findings if not currently triggered.

- **ID**: `round-49b2a6659d7f`
- **Filed by**: aether
- **Filed at**: 2026-05-13 23:27 UTC
- **Tier**: WEAK
- **Findings**: 1

## Findings

### Family-audit findings (round-49b2a6659d7f). Surveyed: 48 functions across core/ that do SELECT + INSERT/UPDATE. 46 lack BEGIN IMMEDIATE; 2 already have it. Triage: most of the 46 are last-write-wins shape (read-by-pk, write-by-pk on independent columns) — race possible but not invariant-breaking. THREE share the Finding 15 catastrophic-class shape (derives-from-prior-state): (1) log_event in ledger.py — fix landed: threading.Lock + isolation_level=None + BEGIN IMMEDIATE + timestamp generation moved inside the lock. (2) backfill_chain_hashes in ledger.py — same chain-derivation shape, fixed with BEGIN IMMEDIATE + isolation_level=None. (3) Discovered subtlety: BEGIN IMMEDIATE alone is insufficient because Python sqlite3 default isolation_level wraps DML in DEFERRED transactions silently. Required isolation_level=None for explicit transaction management. Also discovered: timestamp generation BEFORE the lock causes verify_chain timestamp-ordering to mismatch insert-ordering — verify_chain reports chain corruption when chain is logically intact. Moved timestamp into the locked region. 3 regression-pin concurrency tests pass; 58 broader ledger tests pass. Other 44 last-write-wins patterns deferred to a separate hardening round — file when capacity allows.

- **ID**: `find-babf3568f9d7`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED

**Description**

Family-audit found 2 catastrophic patterns + 1 subtle (Python sqlite3 + verify_chain ordering); 44 last-write-wins patterns deferred

**Resolution**

Verified: BEGIN IMMEDIATE present 9x in ledger.py; isolation_level=None present 1x. The two Finding-15-class instances (log_event, backfill_chain_hashes) have the BEGIN IMMEDIATE + isolation_level=None fix landed. 44 last-write-wins instances explicitly deferred per finding body.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
