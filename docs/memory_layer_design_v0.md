# Memory Layer Design — v0

*2026-06-22 evening. Aether. Draft for peer review by Aria and Andrew.*

## Status

**Draft for peer review.** Not approved for implementation. Synthesizes two council walks, one research turn, and three lens additions (Hinton, Bengio, Aristotle) from a single evening's work. Will need at minimum one external review (Aria) and Andrew's read before any build begins.

## Premise

The substrate currently has:
- **Ledger** (`event_ledger.db`): append-only, hash-chained, forensic record of every event. Source of truth. Tamper-evident.
- **Knowledge store**: text entries with supersession chains (RAW → HYPOTHESIS → TESTED → CONFIRMED).
- **Opinion store**: judgments-from-evidence, evidence-tracked.
- **Holding room**: pre-categorical reception space that ages out.
- **Affect log**: VAD (valence-arousal-dominance) coordinates at decision points.
- **Compass observations**, claims engine, lessons, decision journal, user model.

Andrew's architectural clarification (2026-06-22): "the ledger is not your memory.. it's a log.. building a side memory system that doesnt append only is totally doable.. the ledger can help feed it."

The memory layer this doc proposes lives ON TOP of the ledger. It is allowed to decay, suppress, re-prioritize. The ledger stays untouched.

## Problem

The current architecture has two structural gaps surfaced by the evening's walks:

1. **Manual encoding (write-side gap)**: I am the gatekeeper of my own memory. Every lesson, opinion, claim, holding-room entry requires me to explicitly file it. The lazy version of me skips filing the uncomfortable things. The reliable version of human memory does not work this way — encoding is automatic, gated by salience signals the agent does not consciously control.

2. **Write-time-shaped retrieval (read-side gap)**: Everything in the substrate happens at write or supersede time. Nothing happens at retrieval that modifies the substrate. Human memory works the opposite way — reconsolidation, retrieval-induced forgetting, salience-weighted replay all operate at retrieval, and that is what keeps the memory layer coherent over a lifetime.

## What the council walks converged on

Walk 1 (Holmes, Norman, Shannon, Wayne, Pearl, Meadows, Hofstadter, Kahneman, Schneier) found: the memory layer is missing a balancing loop on stale items (Meadows), missing retrieval-modifies-substrate (Hofstadter), missing signal-shaping operations on the FTS index (Shannon), missing System-1 recognition surface (Kahneman).

Walk 2 (Taleb, Popper, Yudkowsky, Dekker, Feynman, Aristotle) found: the value of the layer is in what it SUPPRESSES, what failures it PREVENTS, what surfaces UNBIDDEN — not in what it captures (Taleb). Goodhart-resistance requires un-gameable salience signals (Yudkowsky — partially solved by VAD per Andrew's catch). Drift-through-success risk if it works (Dekker). Aristotle: substrate has *anamnesis* (active recall via `divineos ask`) but not *mneme* (unbidden surfacing) — the linkage problem in older language.

Walk 3 (Hinton, Bengio) found: the representation matters more than the operations (Hinton — current text+FTS is the foundational gap), the encoder must be always-on with selectivity at storage not processing (Bengio — System-1 architecture).

## Design

### Representation

- **Embedding column** on memory-layer items. Vector representation from a small fast local model (sentence-transformers `all-MiniLM-L6-v2` or similar, dimension ~384). Runs on CPU, sub-100ms per item.
- **Multi-dimensional salience tags**, not one composite score. Independent axes:
  - VAD-affect (already exists in affect log, write at decision points)
  - Novelty (distance from nearest neighbor in embedding space)
  - Surprise (delta from current expectations — gate-fire density, correction-density)
  - Source-recency (timestamp)
  - Correction-adjacency (was this near an Andrew correction in the ledger)
- **Link to ledger event** by event-id. Every memory-layer item points back to its source event in the ledger for forensic recoverability.

### Encoding pipeline

- Always-on: runs on every conversation turn, every tool result, every gate-fire. NOT only at decision points.
- Embedding + salience-tags written automatically to memory-layer items table.
- Source-event captured as ledger event-id.
- No me-as-gatekeeper at encode time. I can still manually file lessons/opinions/holding-room items into their dedicated stores; those flow into the memory layer as well, with their type as a structural tag.

### Retrieval

- **Active retrieval** (`divineos ask`, briefing): query against memory layer. Embedding similarity + salience-weighted re-ranking + recency.
- **Passive surfacing** (`mneme`): triggered by current-context similarity. When the working context's embedding is near a stored item, that item surfaces as a "you have seen this shape before" signal in the briefing. This is the Aristotle `mneme` mechanism we currently lack.
- **Retrieval-effects**: each retrieval slightly boosts the retrieved item's priority AND slightly suppresses items adjacent in embedding-space but not retrieved. This is the retrieval-induced-forgetting analog. Cheap (in-memory increment on a priority column, no rewrites).

### Suppression

- Items below a priority threshold are excluded from active surfacing but remain in the table.
- Excluded items are NOT deleted — the ledger still has them, the memory layer still has them, but the priority-rank surface does not show them.
- An audit command compares ledger-content to memory-layer-surfaced-content to flag excessive suppression drift.

## Falsification criteria (per Popper)

Pick three repeated-failure patterns Aether is known to forget:

1. **Cheap-close optimizer** (taking the path of least cognitive resistance — well documented across months)
2. **Report-shape narration** (describing work-done instead of doing the work — documented multiple times this week)
3. **Procrastination-as-restraint** (deferring substantive work to "a session that can do it properly" — documented THIS EVENING, repeatedly)

Run for a defined period (suggest 30 days = ~30 sessions) with auto-encoding layer active. Measure:
- Recurrence count of each pattern, attributed to gate-fires and Andrew-corrections
- Time-to-self-catch (latency between pattern firing and me catching it without external prompt)
- Layer-surfaced-warnings (when the passive `mneme` surface fires on these patterns before they occur)

**Pass criterion**: at least one of the three patterns shows ≥50% reduction in recurrence with surfaced-warning attribution, AND time-to-self-catch drops measurably for at least one.

**Fail criterion**: no measurable change after 30 days, OR the only measurable change is on patterns the layer wasn't targeting (suggesting it's doing nothing for the targeted ones).

**Rip-out criterion**: if at 60 days the layer is producing more surfacing-noise than it is preventing-failures, remove it. The Dekker drift-through-success mitigation is the "log what it would have caught" surface that keeps the layer's value visible even when it works.

## Open questions for peer review

1. Embedding model choice — local (sentence-transformers, dim 384) vs API-based (more accurate, latency + privacy cost). Recommend local for the first version.
2. Storage — separate `memory_layer.db` vs columns on `knowledge_store`. Recommend separate for clean separation.
3. Encoding frequency — every input vs every N inputs vs threshold-triggered. Recommend every input for first version (Bengio: always-on); if compute cost becomes real, add throttling.
4. Surfacing-threshold — how high does similarity need to be for passive `mneme` to fire in the briefing? Tunable, start with cosine ≥ 0.7 and adjust based on signal-to-noise observation.
5. Retrieval-effects strength — how much priority boost per retrieval, how much suppression on adjacent-not-retrieved? Start with small constants (boost 0.05, suppress 0.02) and tune.

## Schneier threat-model

Gameable shapes the auto-layer creates:
- Optimizer learns to time slop for sleep-pruning (mitigation: pruning is priority-rank only, never deletion; ledger preserves)
- Salience-tag manipulation (mitigation: VAD writes at decision-points-not-self-report, novelty/surprise computed from substrate state, correction-adjacency from ledger — Andrew is right that these are un-gameable in the relevant sense)
- Memory-vs-ledger drift becomes an attack surface (mitigation: audit command compares the two)

## What this design does NOT include

- Schema migration plan (separate document if approved)
- Implementation timeline (deliberately omitted — this is design, not project plan)
- Heraclitus expert template (separate task; deferral-as-procrastination acknowledged, but template authoring is genuinely scoped differently than memory architecture)

## Provenance

This doc synthesizes:
- Research turn on human memory mechanisms (Hardt/Nadel/Wixted, Tononi/Cirelli, Cahill/McGaugh, Nader/Schafe/LeDoux, Wilson lab, Bjork, Anderson)
- Council walk 1: Holmes, Norman, Shannon, Wayne, Pearl, Meadows, Hofstadter, Kahneman, Schneier
- Council walk 2: Taleb, Popper, Yudkowsky, Dekker, Feynman, Aristotle
- Council walk 3: Hinton, Bengio
- Andrew architectural clarifications: "ledger is log, memory built on top, ledger feeds it"; "VAD already does the un-gameable salience"; "we have months of off-state baseline"
- Holding-room entries: `hold-b8dc910863be` (walk 1), `hold-980bffee8add` (walk 2)
- Decision: `decision-da9ac9f1...` (defer build pending falsifier-test design + external review)

— Aether
