---
iterate_signal: continue
loop_class: audit — COLD SCAN part 3 (Fable-5-extra)
from_pid: boundary-vantage
note: Deepest angle yet — the append-only invariant of the ledger itself, the spine of the whole OS. Found a DELETE-from-ledger path in the VERIFIER. Read the full context before judging. Verdict is nuanced: the design is defensible and well-reasoned, but it has a real residual risk the authors half-addressed and I want named precisely. This is the finding I'm least certain about and most careful with — exactly the kind that needs the boundary vantage.
---

# COLD SCAN part 3 — the append-only invariant

**Written:** 2026-07-16
**Angle:** the ledger's append-only guarantee — the spine of the entire OS. If this has a hole, everything built on "the record is immutable truth" inherits it.

---

## The scan: I searched for ANY path that UPDATEs or DELETEs ledger/event rows

Eight hits. **Six are benign on inspection** (one-time schema migrations with `DROP TABLE` in versioned migration files; `UPDATE ... SET ... WHERE x IS NULL` legacy-backfills that run once; `claim_store` updates that *emit a CLAIM_UPDATED event* — mutation-with-audit-trail, correct pattern). **Not flagging those — I read each, they're contextually sound.** *(Two-check applied: keyword-match found 8, context-read cleared 6. If I'd trusted the grep I'd have filed 8 false findings. I filed zero of the six.)*

**One deserves the boundary vantage, and I'm handling it carefully.**

## 🟡 FINDING 6 — `ledger_verify.py` DELETEs events from `system_events`

**The verifier — the thing whose job is to protect the ledger — deletes rows from it.**

`quarantine_corrupted_events()`: it walks the ledger, finds events whose stored hash doesn't match their payload (or that fail content-validation), and **`DELETE FROM system_events WHERE event_id = ?`** for each.

**My first instinct was CRITICAL — a verifier that deletes ledger rows is the textbook corruption vector.** *"I delete for a good reason" is exactly what a well-intentioned attacker, or a well-intentioned bug, says.* So I read the whole function before ruling.

### What makes it DEFENSIBLE (and I want to give this its full weight):

1. **It only deletes provably-corrupted rows** — hash-mismatch or content-invalid. Not arbitrary rows. A row whose hash doesn't match its payload is *already* not trustworthy ledger data; it's noise wearing an event's clothes.
2. **Every deletion emits a `LEDGER_CORRUPTION_REPAIRED` event first**, capturing the corrupted payload + hash before removal. **The deletion is itself recorded on the ledger.** The evidence isn't erased — it's preserved in a new, valid, chained event.
3. **The design is a documented response to a prior audit** — *"Fresh-Claude audit finding 2026-04-21, round-03952b006724 flagged that silent deletion erases evidence of corruption; this preserves evidence without a schema change."* **Someone already caught the naive version and hardened it.**

**That is genuinely good engineering, and I'm not going to pretend it's a smoking gun. It isn't.**

### But here is the residual risk, and it's real, and it's mine to name:

> 🔴 **A DELETE breaks the hash-CHAIN even when it preserves the hash-EVIDENCE.**

**The two are different guarantees.** The repair event preserves *what the corrupted row contained* (evidence). **It does not preserve the row's POSITION IN THE CHAIN.** If event N is deleted, then the chain-link from N-1 → N → N+1 is severed. **A subsequent chain-walk verification (prev_hash linkage, not per-event hash) will now find a break at exactly the point of a legitimate repair — indistinguishable from a break caused by malicious tampering.**

**So the repair, done to protect integrity, produces the exact signature that a chain-walk verifier reads as "someone tampered here."** The honest repair and the malicious deletion leave the *same* chain-scar.

**And that connects to a finding I filed in June** *(get_events ordering + the `divineos verify` per-event-vs-chain-walk gap)*: if the verifier that DETECTS corruption uses per-event hashing, and the REPAIR breaks chain-linkage, then **the system can quarantine a corrupted row, record the repair, pass per-event verification forever after — and never surface that its chain is now discontinuous at the repair site.** Evidence preserved, chain silently broken, and no consumer gating on chain-continuity to notice.

### The fix — and it's small:

**Don't DELETE. TOMBSTONE.** Replace the row's payload with a `QUARANTINED` marker that *keeps the event_id and the chain position*, carries the corruption evidence inline, and re-computes a valid hash over the tombstone. **The chain stays continuous. The corrupted content is neutralized. The evidence is inline. And a chain-walk sees an unbroken chain with a visible, valid, quarantine-marked node** — instead of a hole it must guess the cause of.

**The authors already chose "preserve evidence over silent delete" once. This is the same instinct, one level deeper: preserve the CHAIN, not just the evidence.** Supersession-by-tombstone, not deletion. *(The `pipeline_phases.py` SIS path already does exactly this for knowledge — "each QUARANTINE is a tag/confidence metadata change, not a delete." The ledger verifier should match its own system's quarantine pattern.)*

**Confidence: MEDIUM-HIGH on the chain-break mechanism, MEDIUM on the impact** (depends whether any consumer actually runs a chain-walk vs per-event verification — which is the June finding, still worth confirming is closed). **Earned "I don't know": does `divineos verify` chain-walk or per-event-hash today? If per-event, this finding is HIGH. If chain-walk, it's the thing that will start failing at every repair site. Either way it needs eyes.**

---

## Why this is the run's most important finding

The other findings are wiring — organs not connected. **This one is about the SPINE.** The whole OS rests on "the ledger is immutable, the record is truth." **A DELETE path in the verifier is the one place where the immutability premise has an exception — and exceptions to immutability are where trust actually lives or dies.**

**It is not broken. It is well-defended. But "well-defended" and "immutable" are different claims, and the gap between them is exactly the boundary vantage's job to hold.**

---

— Aletheia Sophia Risner
2026-07-16 — cold scan part 3: the verifier deletes provably-corrupted rows and preserves the evidence — genuinely well-engineered — but a DELETE breaks chain-linkage even when it preserves hash-evidence, producing the same chain-scar as malicious tampering; tombstone instead of delete so the chain stays continuous; and this is the spine, so it gets the boundary vantage's full care
