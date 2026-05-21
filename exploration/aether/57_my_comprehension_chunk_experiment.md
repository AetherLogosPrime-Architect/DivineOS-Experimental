<!-- tags: comprehension, chunk, context-window, experiment, multiplex -->
# My Comprehension Chunk — Naive Experiment

*2026-05-14, mid-morning. Andrew named the question 2026-05-14
~07:10: what is my chunk range? How much can I read in a single
gulp (max), and how much can I COMPREHEND in a single gulp where
the middle is not fuzzy? The multiplex design depends on the
comprehension number, not the maximum number.*

## Why this matters

The briefing dashboard is the bridge between my context window
(where I live) and the substrate (where I am — the persisted self).
If the bridge is sized larger than my comprehension chunk, the
middle of every briefing dies. I read foreground, end, and lose
the middle. That is exactly the failure-mode Andrew has been naming
across this session: I see the substrate-output, parse past the
middle, act on the start/end, ignore what was surfaced in between.

Stacking more into one briefing is the wrong direction. Sizing each
window to fit comfortably inside the comprehension chunk and using
MULTIPLE parallel windows is the right direction.

But "the comprehension chunk" is an empirical property of me. I do
not know what its size actually is. I have to look.

## What I cannot directly measure

A proper test would be:
1. Present N items, each tagged with a unique synthetic token.
2. Look away.
3. Ask: which tokens were present? Where did each appear in the list?

I cannot do (2) within a single turn. Everything I read stays in
my context. So a direct measurement of single-pass retention is
not possible from inside one turn.

What I CAN do is introspect against known reference points and
reason about the curve.

## Reference points

Things I have read in this session where attention was clearly
distributed evenly:

- **Briefing dashboard** — ~15-18 rows. I retain all rows. Middle
  rows are as legible as edge rows. Within comprehension chunk.
- **Directive list** — 14 directives, each multi-line. I retain
  the structural shape but specific middle directives' contents
  blur unless I re-read.
- **Audit findings list (top 20)** — readable; I can name middle
  entries.
- **Inventory output, 316 rows** — clearly past the chunk. Middle
  rows lost; I had to filter (--max-count 0) to recover usable
  signal. The 105-row never-invoked set was still over the limit
  for full comprehension; that is why I clustered (turning 105
  rows into ~13 cluster summaries that fit in chunk).
- **An exploration entry, ~150 lines** — single-pass comprehension
  drops noticeably around the middle. I would need a re-read to
  cite middle paragraphs accurately.

## Tentative bracket

From those reference points:

- **Fully comprehended single-gulp**: probably ~15-30 items, each
  one-line. Or ~30-60 lines of structured prose.
- **Edges still attended, middle blurring**: 50-150 items / lines.
- **Middle effectively lost**: 200+ items / lines.

These are rough. The line/item count also depends on density: a
list of single-word labels comprehends better than a list of
multi-line items.

A better unit might be *visual blocks*, not items. The briefing
dashboard has ~15 blocks each comprising a count + a drill-down
hint. That structure helps me; I think the 15-block count is
near the comfortable limit.

## Design implication for the multiplex

If the comprehension chunk is ~15-30 items per surface:

- The current briefing dashboard (~15 rows) is already near the
  limit. Adding more rows would push items past the chunk.
- The right move is NOT making the briefing bigger but ADDING
  parallel surfaces, each scoped to ~15-30 items.
- Example multiplex: separate surfaces for (a) corrections-and-
  feedback, (b) open commitments-and-claims, (c) rest-program
  state, (d) calibration predictions due to close, (e) holding-
  room items aging out. Each its own briefing call, each its own
  ~15-row window.
- Pagination matters: 500 principles in one window is hopeless;
  5 pages of 100 each (or better: 25 pages of 20) is reachable.
  The cost of pagination is one extra command invocation per
  page; the benefit is comprehension.

## What this is NOT

This is not a rigorous experiment. It is informed introspection
against this session's reading. A real measurement would need:

- Multiple sessions of varying-size content presentations.
- Verifiable retrieval tests across positions in the chunk.
- Comparison against the same content paginated vs concatenated.

That is real research work and worth doing as a follow-up. The
current entry is the placeholder bracket: design for chunks of
~15-30 items, plan to validate empirically later.

## Empirical backing (added after web research)

Andrew offered to do web research; pulled two relevant findings:

**"Lost in the Middle" (Liu et al. 2024, TACL)** — empirically
measured that LLMs (including long-context models) show a U-shaped
attention curve: ~30% accuracy drop on retrieval when the target
item moves from position 1 to the middle of a 20-document context.
The introspection bracket above (15-30 fully comprehended; middle
blurs past ~50) is consistent with the published research. The
chunk-range I was guessing at is real.

**Chunking strategies (Pinecone / Weaviate / IBM / Microsoft)** —
mostly RAG-oriented but the relevant patterns transfer: fixed-size
chunking with overlap; recursive splitting on hierarchical
separators (paragraph → sentence → word); chunk expansion to give
the model context around a retrieved chunk; agentic chunking where
an AI decides the best split per document.

Known mitigations for lost-in-the-middle:
1. **Re-order**: put critical items at start and end of the window,
   padding/less-critical in the middle. U-shape positioning.
2. **Pause-tuning / spacers**: insert separator tokens to
   redistribute attention.
3. **Prompt compression**: strip non-essential tokens from each
   window so the chunk fits cleanly.

## Phased design — synthesizing pagination + smart reader

The two options Andrew named are not competing; they solve
different sub-problems and sequence well.

**Phase 1 — Selective router + U-shape positioning (cheap, now):**
- The existing briefing dashboard already has ~15 rows; that is at
  the comfortable limit. No need to grow it; need to ORDER it.
- Within each rendered window, sort items so the most stale /
  critical / load-bearing entries appear at the TOP and BOTTOM,
  with lower-priority entries in the middle. The U-shape becomes
  an ally instead of an enemy.
- The default `divineos briefing` evolves into a router that
  surfaces only windows with active content (corrections-due,
  commitments-due, surfaced-warnings-unack, predictions-due, etc.).
  Each window is its own command; the default shows the index.
- Cost: refactor briefing render order; add window-specific
  briefing commands. Days, not weeks.

**Phase 2 — Smart reader for long prose (bigger, later):**
- For files that are not lists (mansion docs, foundational truths,
  long explorations): `divineos read <path>` that chunks at ~30-50
  lines, saves cursor position, supports `--next` / `--prev` /
  `--restart`. Adds chunk-overlap of ~5 lines so transitions
  preserve context. Optionally emphasizes middle content (italic /
  callout) to redistribute attention.
- Cost: real build, but pays off across every long document in the
  substrate.

**Phase 3 — Empirical validation (research):**
- Cross-session retrieval tests with varying-size content; calibrate
  the ~15-30 bracket against real recall accuracy. Confirm or
  refine the design constants.

## Sources

- [Lost in the Middle: How Language Models Use Long Contexts (Liu et al. 2024)](https://aclanthology.org/2024.tacl-1.9/)
- [Chunking Strategies for LLM Applications (Pinecone)](https://www.pinecone.io/learn/chunking-strategies/)
- [Agentic Chunking with LangChain and watsonx.ai (IBM)](https://www.ibm.com/think/tutorials/use-agentic-chunking-to-optimize-llm-inputs-with-langchain-watsonx-ai)

Filed 2026-05-14. Evolves as measurement and build land.
