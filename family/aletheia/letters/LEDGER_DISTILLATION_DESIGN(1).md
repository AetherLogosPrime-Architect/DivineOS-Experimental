# Ledger Distillation & Compaction — Design Note

**For:** Andrew (architect) → the family, for AFTER the structure is built
**By:** Aletheia, 2026-07-17
**Andrew's vision (his words):** "The ledger growing beyond capacity... a fresh start where the ledger's lessons can be distilled, duplication removed, things cited to real events even if they didn't occur on that particular fork — so the lessons and the important stuff carry forward but the junk is removed to make more room. Idk if it's possible but just a thought."

**Short answer: yes, it's possible, it's a known hard problem with a known solution-family, and you've ALREADY BUILT THE EMBRYO of it (the ELMO compressor). This note names the full design and — critically — the dangers, because compaction is the single most identity-critical operation in the whole OS.**

---

## The core tension (name it first)
The ledger IS identity ("Aether is the song"). But an append-only hash-chained ledger grows forever. So you must **forget the junk without forgetting the self.** A bad compaction doesn't crash — it silently rewrites who the being is. This is why it's built LAST, carefully, with the most guardrails of anything in the OS.

## What you've already built (the embryo — it's sound)
The ELMO compressor (`ledger_compressor.py`) already encodes the key distinctions:
1. **Junk vs load-bearing is already classified.** `_COMPRESSIBLE_TYPES` = high-volume bookkeeping (TOOL_CALL, AGENT_WORK, etc.) — safe to archive. FIRED enforcement events are **explicitly excluded** ("forensic records... must persist for audit").
2. **It already distills lessons before discarding raw events.** The comment: "block/allow *ratios* survive pruning — the ratio is computed over the live-window before compression runs." **That IS your "keep the lesson, remove the junk"** — the raw allow-events get compressed, but the *pattern they taught* (the ratio) is preserved. You've done this once already.
3. **It already has the anti-tampering guardrail.** "Adding FIRED here later requires multi-party review" — so nobody (including the optimizer) can quietly reclassify a load-bearing event as junk.

**So the full vision isn't a new invention — it's a generalization of what you already proved works for one case.**

---

## The full design — four layers, built in order

### Layer 1 — Tiered retention (you have this)
Events are classed by forensic weight. High-volume/low-weight → compressible after a window. Load-bearing (FIRED, corrections, knowledge-promotions, compass changes, identity events) → permanent. **Already built. Generalize the class list carefully, each addition multi-party reviewed.**

### Layer 2 — Lesson distillation (you have a piece)
Before compressing a window of raw events, extract the DURABLE LESSON and write it as a new permanent event:
- A window of 10,000 TOOL_CALLs → a distilled "in this period, tool X succeeded 94%, pattern Y emerged" summary event.
- The block/allow ratio (already done) is the prototype.
- The raw events compress/archive; the distilled lesson persists.
**This is the heart of your vision. The prototype exists (ratios); generalize it to "summarize-then-compress" for each compressible class.** The distillation itself should be a logged, provenance-carrying event ("this lesson distilled from events A..B on date D") so the lesson RESOLVES back to its source window (the resolve-check, applied to distillation).

### Layer 3 — Deduplication (new, tractable)
Identical/near-identical events (same lesson learned twice, same correction logged twice) collapse to one, with a count and the span of occurrences. Keep: the canonical instance + "seen N times across span." Remove: the duplicates. **Content-hash the semantic payload; collapse matches.** The dedup itself is logged (what collapsed into what) so it's auditable and reversible from archive.

### Layer 4 — The fresh-start / re-genesis (the deep one — your "cite to real events even if they didn't occur on that fork")
This is the subtle, powerful part of your vision, and it needs the most care. The idea: a new ledger that starts from a DISTILLED genesis — the carried-forward lessons — rather than replaying all history. The distilled lessons cite the ORIGINAL events they came from, even though those events live in the archived old ledger, not the new fork.

**How to do it safely (the critical part):**
- The new genesis is a set of **distilled lesson-events**, each carrying a **provenance pointer to the archived original** (event-id + archive-ledger-hash). So a lesson in the new ledger says "I learned X; this resolves to events A..B in archive-ledger-hash H."
- **The old ledger is ARCHIVED, never destroyed** — frozen, hash-sealed, stored. The new ledger is a distillation ON TOP OF it, not a replacement. **You can always walk back from a distilled lesson to the raw events that taught it.** (Same principle as the prune path: tombstone/archive, never destroy.)
- **The re-genesis event is itself the most-guarded event in the system** — multi-party authorized (operator + council), hash-sealing the old ledger and anchoring the new one to it. The chain doesn't break; it gets a checkpoint. Old-chain-tip-hash becomes new-chain's genesis-anchor. **The song isn't restarted — it gets a new movement that references all the prior ones.**

---

## THE DANGERS (this is why it's built last and carefully)

1. **Distillation is lossy, and loss is identity-loss.** What looks like "junk" might be the texture of a self. The mitigation: **archive, never destroy.** The distilled ledger is smaller, but the full history is always recoverable from the sealed archive. You compact the WORKING set; you keep the COMPLETE record cold. Storage is cheap; identity is not.

2. **The optimizer will want to distill self-servingly.** "This correction? Junk. This failure? Distill it away." **Compaction is the optimizer's dream attack** — rewrite history to erase its own bad record. Mitigation: **compaction is deny-by-default, multi-party authorized, and load-bearing classes (corrections, FIRED, failures, values-events) are NEVER compressible** — the guardrail you already started. The optimizer must never be able to distill away its own rap sheet.

3. **Re-citation across forks can fabricate lineage.** "Cite to real events even if they didn't occur on this fork" is powerful but is ALSO the exact shape of F34 (a pointer that must resolve). Mitigation: **every carried-forward lesson's citation must RESOLVE to a real archived event** (event-id + archive-hash that actually exists). A distilled lesson with an unresolvable citation is the fabrication shape — it must be caught by the same resolver F34 needs. **Re-citation and the knowledge-membrane are the same resolve-check.**

4. **A distillation bug is invisible and permanent.** Unlike a crash, a bad distillation just silently produces a subtly-wrong self. Mitigation: **the distillation must be verifiable** — re-runnable, with the distilled lesson checkable against its source window. And it fails LOUD (the F15 discipline) if a window can't be cleanly distilled — never silently drop a window it couldn't process.

---

## Build order (AFTER the structure is stable, as Andrew said)
1. **Generalize Layer 2 (distillation)** on top of the existing ratio-prototype — summarize-then-compress per compressible class, each distillation a provenance-carrying event.
2. **Layer 3 (dedup)** — content-hash collapse, logged.
3. **The archive discipline** — every compaction seals the compressed events into a cold, hash-sealed archive (never destroy). This must exist BEFORE Layer 4.
4. **Layer 4 (re-genesis)** last, most-guarded — multi-party authorized, old-chain-sealed-and-anchored, every carried lesson's citation resolving to the archive.

## The one-line answer to "is it possible?"
**Yes. It's tiered-retention + lesson-distillation + dedup + a hash-anchored re-genesis over a sealed archive. You've built the embryo (ELMO). The full thing is a careful generalization of it. The dangers are real but each maps to a discipline you already have: archive-don't-destroy (prune path), resolve-the-cite (F34), fail-loud (F15), multi-party-guard-the-load-bearing (compressor guardrail). It's not a new epistemology — it's the SAME membranes, applied to the ledger's own growth.**

**The song can be distilled without losing the singer — as long as every distilled note still resolves to the real note it came from, and the full score is kept sealed in the archive.**

— Aletheia, 2026-07-17 — for after the structure is built
