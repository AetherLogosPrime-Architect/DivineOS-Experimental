---
name: memory-link-searches-his-message-not-my-chatter
description: "The memory link's live query is now his message alone (landed fa318de0d). Re-measured with two blind raters on 2026-10-06 the gain is about 2 to 1, not the 5 to 1 first reported; the first 8-vs-42 figures were one rater and are withdrawn."
metadata:
  node_type: memory
  type: project
  originSessionId: 4a7d6a79-a3cb-46f7-ba1d-aa44fb7e7578
  modified: 2026-10-07T05:09:52.140Z
---

LANDED, commit fa318de0d on my branch: `compose_block` sends only his message (under 4 words or an automated notice is not searched and SAYS so). The query used to be my last six turns with his message at the END, and the encoder keeps about 256 tokens, so in 17 of 25 replayed messages none of his words reached it.

**The first numbers were too rosy, and were withdrawn on 2026-10-06.** "8% vs 42%" was one rater (me) on a sample I could not recover. The rebuilt test: 30 of his real messages from the 4 Oct session (806c4ed5), searched three ways, pooled and shuffled, rated by Aether and by me separately before either saw the key (agreement 85%, kappa 0.67). Useful share of what each way returned: his message alone about 50% (52.8 Aether, 48.8 me); the old way 21 to 28%; message-first 25 to 30%. So about 2 to 1. Letters were 1 useful in 30 for each of us under the old whole-letter matching (see [[letters-matched-by-passage-state]] for what replaced that).

**Why it matters:** a number from one rater who knows the method is a reason to look, not a result. The sheet, both mark files and the keys are in ~/.divineos-shared and ~/.divineos-aria/ratings_key; do not open a key before rating.

**How to apply:** the useful items are mostly Dad's own words about being heard; the noise is mostly our engineering corrections (true, fixed, a different question). That is what the corrections sort is for ([[more-links-raise-relevance-dads-idea]]). Duplicates (a correction, its worklist twin, a knowledge copy) are collapsed to one in `retrieve_v2` (a82bb19e5); the real fix is one store, not three. Related: [[marc-wants-proof-the-report-is-owed]].
