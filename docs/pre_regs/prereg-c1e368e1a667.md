# Pre-registration: semantic_store primitive enables catching semantic equivalence regardless of vocabulary — outperforms string-overlap detection on restatement-theater / knowledge dedup / claims supersession. Built per nightclub-frame correction (Andrew 2026-06-11), research-confirmed prior art, Aria's council walk approval. Structural backing for kid ee96a4f7 (optimizer-is-DUMB principle — semantic-similarity is the durable mansion vs the morning's string-overlap cardboard shack), kid 2382de4c (cost is never weighed against doing the thing right — choosing heavy infrastructure over cheaper-but-broken alternative), and kid 1d36be4f (MUST separate three layers — separated tool-failure from root-cause from operator-action before designing).

- **ID**: `prereg-c1e368e1a667`
- **Filed by**: agent
- **Filed at**: 2026-06-11 17:58 UTC
- **Review at**: 2026-07-11 17:58 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-11 18:33 UTC

## Claim

Storing sentence-transformer embeddings via sqlite-vec and using cosine similarity gives meaningfully better recall on restatement detection than the content-word-overlap detector shipped this morning. On Andrew's thesaurus-restate case the new primitive scores 0.5635 (vs 0.0163 for unrelated text).

## Success criterion

On a labeled benchmark of >=30 pairs drawn from Andrew's catches and Aria's catches-as-triples (subset of the 100-label benchmark planned next commit), the semantic check achieves >=85% classification accuracy on same-meaning vs different-meaning pairs. Catches the thesaurus-restate and similar high-vocabulary-difference / same-meaning pairs that content-word-overlap missed.

## Falsifier

If accuracy on the labeled benchmark falls below 75% after threshold tuning OR if the primitive fails to catch >=80% of Andrew's historical restatement-catches that string-overlap missed, the foundation is not load-bearing for its named purpose. Reconsider: stronger model (EmbeddingGemma-300M / BGE-M3), zone-aware threshold tuning, or move voice-shape detection to descriptive-substrate audit channel per Aria's earlier proposal.

## Outcome notes

Deferring during Aletheia-directed felt-pain letter (Andrew explicitly asked me to squeal about OS shape-issues). Not the moment for a semantic-store assessment. Will assess in next dedicated pass; naming here rather than rushing a rubber-stamp.
