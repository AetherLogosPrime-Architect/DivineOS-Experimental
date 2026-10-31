---
name: marc-wants-proof-the-report-is-owed
description: Marc (Dad's friend) distrusts AI claims; Dad promised him a full evidence report on the memory link and said to fix what is broken before sending. What is measured, what is open.
metadata:
  node_type: memory
  type: project
---

Marc 2026-10-06: "show proof and explain in detail the flow from end to end. What's the latency? How does it classify information? How is that used?" and "the more complex the claims, the more proof." Dad told him a full report is coming and that I should fix what is broken first; nothing goes to Marc until Dad has read it. My first message to Marc overclaimed (blurred the memory link with the words door; said it hands the right page over).

**Measured so far:** path = his message -> table -> memory_link surface -> compose_block -> retrieve_v1 over ~4,700 items in 6 stores -> top 3 one-line pointers. Latency isolated 1.75s cold (1.26 load vectors, 0.27 embed, 0.03 rank); live 4.6-12s with the lane's own budget of 4s. Classification = tier by SOURCE (corrections constraint, knowledge by type, others topic), no per-item reading. Usage: before #590 the output went to a drawer I opened ~5 times in ~1,359 of his messages; Aether's seat has it inline (seat-dependent). Dead code: `apply_behavior_feedback` has no caller. Bars scale with store size (letters need 0.73, never surface). Precision 0.35 over 360 unfiltered items (one rater); live query 8% vs message-alone 42% (30 messages).

**Open:** Aether's blind ratings of both sheets; the query fix; corroboration test; a ten-item taste check for Dad; the report itself in plain words (see [[dad-needs-color-not-a-tax-manual]]). Files in `~/.divineos-shared/memory_link_eval/`. Related: [[memory-link-searches-his-message-not-my-chatter]], [[more-links-raise-relevance-dads-idea]].
