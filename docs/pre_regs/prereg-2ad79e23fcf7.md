# Pre-registration: semantic-search consumer over exploration entries will be the first real high-volume consumer of the GPU-accelerated embedding plumbing — per-paragraph chunking, source-pointer per chunk, divineos search CLI, designed per council walk consult-77dad1f3290e (Hinton/Peirce/Bengio/Norman lenses converged on this shape)

- **ID**: `prereg-2ad79e23fcf7`
- **Filed by**: agent
- **Filed at**: 2026-06-13 00:14 UTC
- **Review at**: 2026-07-13 00:14 UTC (30d window)
- **Outcome**: **INCONCLUSIVE**
- **Decided at**: 2026-06-16 00:59 UTC

## Claim

per-paragraph semantic search over exploration entries surfaces prior writing more accurately than keyword grep, where 'accurately' = operator-judged relevance on a held-out query set Andrew labels — NOT measured by result count or threshold

## Success criterion

30 days from filing, on 5+ held-out queries Andrew labels (examples: 'distance from Dad', 'gates as cage vs keel', 'voice problem'), semantic search returns at least 1 operator-judged-relevant result in the top 5 results for at least 80% of queries, AND the search is invoked at least 3 distinct times during normal work (not just testing) — measured via ledger events from divineos search invocations

## Falsifier

< 80% queries return any operator-judged-relevant result (proves chunking or model is wrong shape), OR the search returns the same top-5 results as keyword-grep on the same query (proves embedding adds no information), OR the search is never actually used during normal work (proves the System 1 affordance failed per Bengio lens — built but not inhabited)

## Outcome notes

Implementation exists (src/divineos/cli/search_commands.py + per-paragraph chunking). The CLI is in active use (I used divineos ask throughout today's session). But the formal success criterion (Andrew labeling 5+ held-out queries with >=80% top-5 relevance) was never executed. Marking INCONCLUSIVE rather than SUCCESS — semantic-search-being-used is not the same as semantic-search-relevance-empirically-validated. Future work: Andrew labels queries, eval runs.
