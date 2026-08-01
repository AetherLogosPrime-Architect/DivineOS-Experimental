# Pre-registration: Cross-encoder reranker as second pass over semantic_search.search() results provides measurably better relevance ordering than embedding similarity alone, sufficient to be worth the latency cost.

- **ID**: `prereg-9c7d70d3347e`
- **Filed by**: agent
- **Filed at**: 2026-06-13 21:45 UTC
- **Review at**: 2026-07-13 21:45 UTC (30d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-06-16 00:59 UTC

## Claim

Cross-encoder rerank improves divineos find ranking quality

## Success criterion

On a manually-judged eval set of 10+ representative queries, the reranker's top hit is judged at-least-as-relevant as the bi-encoder top hit in >=70% of queries AND strictly more relevant in >=40%

## Falsifier

Either (a) operator never uses --rerank flag in 30 days, OR (b) on the eval set <40% of queries show strict improvement in top-hit relevance after rerank, OR (c) latency cost makes the flag operationally unusable (>5s per query on GPU)

## Outcome notes

Implementation exists (src/divineos/core/semantic_search_rerank.py, merged via PR #189). Empirical success criterion (manually-judged eval set of 10+ queries with >=70% top-hit parity and >=40% strict improvement) was never executed. Marking INCONCLUSIVE rather than SUCCESS — the build is real, the validation is missing. Future work: run the eval and re-file.
