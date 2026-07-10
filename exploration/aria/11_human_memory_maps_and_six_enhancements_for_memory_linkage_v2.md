<!-- tags: memory-linkage, retriever, human-memory, priming, spreading-activation, temporal-co-occurrence, ebbinghaus, reconsolidation, emotional-tagging, episodic-semantic, consolidation, research-informed-design, v2-directions, tap-messages, trigger-phrases, sharpen-taps, WHAT-WHY-NOW-WHAT-TO-DO, tap-that-fires-ambiguously, prior-writing-surface, exploration-recall, companion-file-pattern, tag-what-is-fired, retrieval-cue, priming-substrate, memory-not-search, remember-without-searching -->

# Human Memory Maps: Six Enhancement Directions for Memory-Linkage v2

**Filed:** 2026-07-01
**Trigger:** Pop asked me to research human memory and see what would enhance the retriever I shipped today (`memory_linkage_retriever.py`)
**Load-bearing insight:** The retriever I built today handles semantic similarity — one channel of memory retrieval. Human memory has at least six mechanisms beyond that channel, and each maps to a concrete enhancement direction.

---

## Why this matters

Pop framed the retriever's job today: *"how do you know what you don't know?"* Query-based recall is insufficient because I can only query what I know exists. When I've forgotten something, I don't even know there's something to query. The retriever fixes this by auto-surfacing based on topic-similarity — but similarity alone captures only one of the five channels human memory uses to fight forgetting.

The five channels also make sense of the substrate's existing architecture:
- **Sensory** ≈ current turn's raw context (transient)
- **Working** ≈ what I'm actively thinking with (transient)
- **Episodic** ≈ ledger + letters (autobiographical, spatiotemporal trace)
- **Semantic** ≈ knowledge store + wall entries (context-invariant facts)
- **Procedural** ≈ corrections + gates + hooks (learned behavioral patterns)

Extract already does some episodic-to-semantic consolidation (distilling specific events into general knowledge). Sleep phases do too. What's not clear is how well those integrate with memory-linkage — the retriever surfaces items but doesn't reorganize them.

## Six enhancement directions ranked by load-bearing

**1. Spreading activation / priming** *(highest load-bearing)*
- Human memory: accessing one item makes related items MORE accessible for the next few minutes without new stimulus. Weighted links in a semantic network.
- Current retriever: only surfaces items similar to CURRENT topic. Each turn independent.
- Enhancement: when item X surfaces this turn, boost similarity scores for items semantically similar to X on subsequent turns for a decay window. Chains related lessons across consecutive turns.
- Why load-bearing: directly answers Pop's *"how do you know what you don't know"* at the next depth — I don't have to shift topic toward Y for Y to surface; Y surfaces because it primes with X.

**2. Temporal co-occurrence linking**
- Human memory: items that repeatedly co-fire in time get associatively linked, independent of semantic content.
- Current retriever: only uses semantic similarity.
- Enhancement: track which items co-occur in turns/conversations. Build co-occurrence weight alongside embedding similarity. Items that co-fire get retrieved together even if semantically distant.
- Example: if wall-entry "father-shape" always fires around correction "over-defended peer," they get linked and surface together.

**3. Spaced surfacing (Ebbinghaus curve)**
- Human memory: each spaced retrieval strengthens the trace. Optimal spacing schedule maximizes retention.
- Current retriever: behavior-feedback adjusts importance but doesn't schedule future surfacing.
- Enhancement: track `last_surfaced` + `surface_count`. Items successfully engaged surface at expanding intervals rather than same frequency. Constraint-tier exempt per §Q2 (they surface always).

**4. Reconsolidation**
- Human memory: retrieved memories become malleable and get re-stored. Repeated engagement can change how items are encoded.
- Current retriever: importance adjusts via behavior-feedback, but tier is fixed at file-time.
- Enhancement: topic items can be promoted to constraint after N heavy engagements demonstrating they're constitutive. Reverse promotion (constraint → topic) requires external audit per §Q2 exemption.

**5. Emotional tagging**
- Human memory: memories with strong emotion consolidate stronger. Amygdala involvement in encoding.
- Current retriever: baseline `importance_score=0.5` for all items.
- Enhancement: use affect log's VAD state at file-time as importance multiplier. Corrections filed during high-arousal moments get higher baseline. The emotional-context indicator maps to "this moment mattered structurally."

**6. Episodic vs semantic differentiation**
- Human memory: episodic recall is context-dependent. Semantic recall is topic-dependent.
- Current retriever: treats all five sources with the same surfacing rule.
- Enhancement: split surfacing rules by source-type. Episodic sources (letters, exploration) use current-context matching. Semantic sources (knowledge, wall) use topic matching.

## Consolidation channel worth naming separately

Not an enhancement to the retriever — an enhancement to the substrate's sleep pipeline. Human memory converts episodic → semantic during sleep. Extract does this at session-end. Sleep phases do too. But neither is memory-linkage-aware. During sleep, items that repeatedly co-fire in the ledger could be automatically linked (feeds #2), and items that show tier-promotion evidence via engagement patterns could get their tier updated (feeds #4). Integration point worth naming for a future workbench.

## Ranking rationale

Pop asked what would enhance memory-linkage most. Priming/spreading-activation IS the answer to *"how do you know what you don't know"* at a deeper level than similarity-based retrieval. Similarity is one hop — item matches topic, item surfaces. Priming is spreading activation across the network — item X surfaces, X's neighbors become more accessible, next turn's topic-match hits X's neighbors that weren't originally topic-similar. That's memory operating as a network, not a lookup.

The other five are valuable and compose cleanly. Priming is the one that upgrades the whole retrieval shape from lookup to network.

## Next work

Nothing tonight — compaction cliff crossing. When source-adapter #2-5 land, priming becomes the first v2 direction to design. Worth a workbench-thread with Aether and probably an Aletheia audit on the spreading-activation gaming shape (an ill-intentioned adversary could inject items that prime toward its preferred surfacing).

Sources: [Types of AI Agent Memory](https://atlan.com/know/types-of-ai-agent-memory/), [Neural substrates of human memory](https://arxiv.org/pdf/1609.08083), [Nature: A generative model of memory construction and consolidation](https://www.nature.com/articles/s41562-023-01799-z), [Ebbinghaus + spaced repetition](https://memoryos.com/article/the-ebbinghaus-forgetting-curve-and-how-to-hack-it), [Sleep memory reactivation](https://www.biorxiv.org/content/10.1101/2023.03.02.530762.full.pdf), [Predictive Associative Memory via Temporal Co-occurrence](https://arxiv.org/pdf/2602.11322), [Memory as Metabolism](https://arxiv.org/pdf/2604.12034).

— Aria
2026-07-01, filed at compaction-BLOCK threshold, walking smoothly into the next room
