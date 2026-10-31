---
name: more-links-raise-relevance-dads-idea
description: Dad 2026-10-06: a match on semantics alone is not solid; relevance should rise with how many OTHER kinds of memory (ledger, lessons, errors, issues, dreams, letters, explorations) also match. Not yet tested; design in the file.
metadata:
  node_type: memory
  type: project
---

Dad 2026-10-06, answering Marc's question about how the system finds things whose usefulness is not obvious from meaning: "the fix is forming more links.. if something is matching by semantics alone its not a solid match, it should also match to ledger events, lessons and errors and issue, dreams, letters and explorations, and the amount of things that correlate drive up the relevance."

**Evidence it is needed:** of the 109 items I rated useful (360-item sheet), today's bars would show 32; 77 stay hidden, and about half of the useful ones scored under 0.45 similarity.

**How to apply:** test first, on the labeled sheet: for each item count how many OTHER stores hold something close to the query AND close to the item, excluding near-copies (item-to-item >= 0.97, the same sentence filed twice). The script is NOT written yet (the compaction ritual blocked the write on 2026-10-06; the design is: for each labeled item, count other stores with an item near the query and near the item, then compare precision by number of stores backing it, then `similarity + lambda x stores`. Then add the missing stores as corroborators (ledger events, dreams, errors/issues). Related: [[memory-link-searches-his-message-not-my-chatter]].
