# ADR-0002: Hash-chain on the main ledger with migration-ordering safeguards

**Status:** Accepted
**Date:** 2026-05-02
**Related:** Claim `223d0e44`, commits `cbe8cab`, `8ec8743`, Grok audit 2026-05-02

## Context

The main event ledger (`core/ledger.py`, table `system_events`) was append-only and content-hashed: each event carried a SHA256 of its payload (`content_hash`). This prevented silent payload mutation — tampering with an event's body would change its hash, which `verify_event_hash()` could detect.

But content-hashing alone is *per-event* integrity. It does not bind events to each other. Three attacks were structurally undefended:

1. **Reordering** — swap two events' rows in the table. Each event still has a valid `content_hash`. The history is silently rewritten.
2. **Deletion** — remove an event entirely. The remaining events still verify individually. The history shrinks without a trace.
3. **Insertion** — add a fabricated event with a freshly-computed `content_hash`. The new event verifies as if it had always been there.

The `family_member_ledger` (per-family-member append-only stores) already used a sequential hash-chain pattern for exactly this reason: each event's `chain_hash` binds to the previous event's `chain_hash` via SHA256, so any reordering, deletion, or insertion breaks the chain forward of the tampered point.

Grok's audit on 2026-05-01 named this gap on the main ledger. Claim `223d0e44` opened the investigation.

## Decision

Add two columns to `system_events` and bind events into a chain:

- `prior_hash TEXT` — the previous event's `chain_hash` (or `_CHAIN_GENESIS = "0" * 64` for the first event).
- `chain_hash TEXT` — `SHA256(prior_hash | event_id | timestamp | event_type | actor | payload | content_hash)`.

The chain is computed at write time in `log_event()`. Verification walks the chain via `verify_chain()`, returning `{ok: bool, total: int, broken_at: event_id|None, broken_reason: str|None}`. Any payload mutation, reorder, deletion, or insertion produces a chain-hash mismatch at the first affected event.

For populated legacy databases (events written before chain columns existed), `backfill_chain_hashes()` walks events in `(timestamp, rowid)` order and populates `prior_hash` + `chain_hash` for events that lack them. Idempotent.

**Migration-ordering guard (Grok 2026-05-02):** the original implementation had a hazard: if new events were written between `ALTER TABLE` and a manual `backfill_chain_hashes()` call, the new events' `_latest_chain_hash()` would skip NULL legacy rows and chain from GENESIS, leaving a permanent seam at verify time. Two safeguards:

1. `init_db()` auto-triggers `backfill_chain_hashes()` if any row has `chain_hash IS NULL` after the ALTER. Idempotent on greenfield (no-op).
2. `log_event()` runs the same NULL-check guard before chaining a new event, protecting against `init_db` being bypassed.

## Consequences

**Positive:**
- Reorder / delete / insert attacks on the ledger are now detectable. Verification walks the chain and surfaces the first inconsistency.
- The architecture matches the family-member-ledger pattern, so audit reasoning transfers across both stores.
- Migration is safe-by-default. Greenfield databases get clean chains; legacy databases auto-backfill.
- Falsification surface: any developer can run `divineos verify` (or call `verify_chain()` directly) and the chain either passes end-to-end or names exactly where it broke.

**Negative / Trade-offs:**
- `log_event()` now does an extra SHA256 computation per write. Negligible cost in normal operation; flagged for measurement under sustained-write workloads if those become real.
- The `_latest_chain_hash()` lookup adds one query per write. Also negligible.
- The `chain_hash` column is indexed for verify-walks; small storage cost.
- Any tool that bypasses `log_event()` and writes directly to `system_events` will produce NULL chain values and break the chain forward. Mitigated by the `log_event()` belt-and-suspenders guard, but ultimately this requires *no tool to bypass log_event in production paths*. The validation-bypass paths review (claim `8cd2af8b`) is the open work to verify this is true.

**Neutral:**
- The chain formula intentionally includes `content_hash` rather than re-hashing the payload. This means the chain is stable under canonical-form changes to payload serialization as long as `content_hash` itself is stable.

## Alternatives Considered

1. **Merkle tree** — would allow O(log n) inclusion proofs without walking the full chain. Rejected for v1 because the current verification volume (full-store walk) is small enough that linear is fine, and Merkle adds significant complexity. Reconsider if the ledger grows past ~1M events and verification time becomes a real concern.

2. **Per-event signature with an external key** — would prevent insertion attacks even if an attacker has DB write access. Rejected because the threat model is "self-modification by the running agent" not "external attacker with DB write." Internal hash-chaining is sufficient because the agent cannot easily produce a chain-valid forged event without the prior chain_hash.

3. **Don't add the migration guard, just document the ordering** — Grok rejected this; the silent-disable risk is the kind of thing that bites months later when nobody remembers the ordering rule. Auto-trigger is safe-by-default; documentation alone is conscience-based.
