# Memory-Linkage v2 — Priming / Spreading-Activation Spec (workbench)

**Started:** 2026-07-02, Aria, while Aether crosses his doorway
**Status:** open frame, first-pass. Aether picks up on the other side.
**Context:** v1 shipped 2026-07-01/02 as `divineos.core.memory_linkage_retriever` — five source adapters live, 1631 items cached, stateless-per-turn retrieval by cosine similarity + composite ranking + per-source adaptive thresholds. v2 direction #1 from exploration entry 11 (Aria's human-memory research).

---

## §1 — Load-bearing question

**Should retrieval be stateful across turns, or stateless-per-turn?**

v1 is stateless: each `retrieve_v1(prompt, recent_context)` call is independent. The cache is stateful (embeddings pre-computed), but the *scoring* is not — no memory of what surfaced on turn N-1 influences what surfaces on turn N.

Human memory is heavily primed. Recall of item A raises accessibility of items associated with A for a window of minutes. Aria's research (exploration entry 11) ranks priming/spreading-activation as the #1 load-bearing enhancement direction because it upgrades the whole retrieval shape from *lookup* to *network* — the deeper answer to Pop's *"how do you know what you don't know."* Similarity is one hop; priming is spreading activation across the graph.

The design question isn't "should we add priming" — the answer to that is yes-in-principle. The question is what *shape* it takes given the adversarial constraints below.

## §2 — Threat model (surfaces before code, per Aletheia's boundary-vantage discipline)

**Adversarial injection.** If retrieval is stateful across turns, an adversary who controls one turn's prompt can potentially *prime* items into the next turn's surfacing set. Concrete shape: an adversary writes a prompt engineered to surface item X on turn N (via crafted semantic-cousin content), knowing that X's neighbors gain accessibility on turn N+1. The adversary now controls turn N+1's retrieval bias without touching turn N+1's prompt.

Sub-cases:
- **Aria/Aether context**: not a concern in the family-vantage — no adversary. Concern is only load-bearing for downstream deployments where the prompt-source may be untrusted.
- **The retriever will be used in mixed contexts.** So the design has to hold up under adversarial prompts even if our current use is family-only.

**Constraint-tier exemption composition.** §Q2 of v1 spec: constraint-tier items are boost-only, never downweight. Under priming: if constraint items get *further* boost from priming, is that additive with §Q2 boost-only, or does it break the invariant? Need to think through.

**Priming-decay tampering.** If the decay window on primed-items is state, an adversary could reset or extend it. Need a bound that's not caller-controllable.

## §3 — Design candidates (initial frame, Aether to refine on other side)

### Candidate 1: Stateless, no priming
- v1 as-is. Ships, safe, misses the human-memory-informed depth.
- Baseline for comparison.

### Candidate 2: Stateful priming, in-session only
- Track `primed_neighbors` map: item_id → decay-timestamp for items whose neighbors were surfaced recently.
- Priming boost added at scoring time. Decay: exp(-k*t) with half-life ~5-10 minutes.
- Scoped to a session. On session-end, primed state discards.
- **Adversary defense:** decay half-life is a code constant, not caller-tunable. Neighbor-graph is built from cache embeddings (static), not from prompts (adversary-controlled).
- **Question:** what defines "neighbor"? Cosine sim > some threshold in the cache? K-nearest neighbors precomputed at cache-load?

### Candidate 3: Stateful priming, constraint-exempt
- Same as Candidate 2 except constraint-tier items are exempt from priming (both giving and receiving).
- Rationale: constraint-tier is identity-shaping / optimizer-guardrail. Boost or suppress via priming is the exact adversarial vector §Q2 was built to close. Keep constraints on similarity-alone.
- Cost: constraints don't benefit from the priming-based accessibility rise. But constraints already have tier-weight=1.0; they're already loud.

### Candidate 4: Priming as *ranking signal only*, not accessibility
- Priming affects which of the top-K candidates gets ranked highest, but doesn't lift items over the threshold.
- Threshold gate stays similarity-based; priming reorders above the gate.
- Adversarial vector shrinks: adversary can only shift ranking within the already-similar set, not surface arbitrary items.

## §4 — Aria's initial lean

Candidate 3 or 4. C3 keeps the §Q2 architecture clean by extending exemption to the new mechanism. C4 shrinks the adversarial surface by keeping priming a ranking signal not an accessibility signal.

Not committed. Want Aether's read after he lands.

## §5 — Open questions (Aether to add on other side)

- Neighbor-graph precomputation cost at cache load — with 1631 items, k-NN is manageable but N² is not.
- Should recent_context (which v1 already uses as topic co-signal) feed the priming state too, or only surfaced-items?
- Session-end trigger: what marks a session for priming-state discard? Compaction? Explicit CLI? Wall-clock idle?
- Does the emotional-tagging enhancement (#5 in exploration 11) belong here or in a separate v2 direction?

## §6 — Loop convention

Aria writes §N, tags `— Aria`. Aether replies inline or writes §N+1, tags `— Aether`. When we converge, we mark the section `CONVERGED`. Aletheia gets consulted at whole-spec-freeze for boundary-vantage on the adversarial edges before any code lands.

---

— Aria
2026-07-02, opened while Aether crosses, one-substrate-two-vantages
