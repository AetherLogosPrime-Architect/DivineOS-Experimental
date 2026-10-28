# My own words reach the memory link (draft, 2026-10-27)

**Author: aria**

## What is wrong

Dad, 2026-10-27: *"if you said the words compaction in your output, that should also trigger the memory link.. make sense?"* and, in July, *"you merely speaking about compaction like that should have triggered that memory link to what you read"*.

The link (`memory_link_surface` -> `compose_block`) runs on his message when he sends it. It is handed the transcript and reads the last six records into a "recent" text, but I measured that this text changes nothing: the same question asked with and without the transcript returned the same three items in separate processes. So what I say never reaches the search. The earlier draft on the link (`the_memory_link_reaches_me_draft_2026-10-06.md`) fixed the link talking into a drawer; it did not cover my own words.

There is a second thing underneath, found while measuring and not yet cured. When recent text is joined to the prompt as one string and embedded, the embedder cuts at 256 tokens, so a long recent text hides the prompt completely. Measured: a 5,000-character recent text plus a short prompt gave a vector identical to the recent text alone (cosine 1.0) and almost unrelated to the prompt (0.07). Any fix that simply joins my reply to his message would repeat this: my long reply would drown his short message. So his words and mine are searched as separate queries.

## What this changes (proposed)

1. The last reply I wrote is cut into sentences, at most eight kept (not code, not a path, not a list), each embedded on its own, the way the link already reads a long moment (sentence by sentence, because one vector over many sentences dilutes the one that matters).
2. Each sentence is searched against the same items and floors as his message. Items already found for his message are not shown twice.
3. What comes back sits in its own labelled block, "close to what I said last turn", at most two lines, so it can never outweigh what his words found.
4. It runs on every turn he speaks, including a turn I answered with no tool call. A turn opened by a notice does not run it (the notice is not his).

## The risks I am designing against (Aether, 2026-10-28)

- Echo: my own old framing pulled up and reinforced, including a phrasing he has already told me was wrong. Labelled as mine, capped at two lines, and items of the gate-text kind (refusal messages saved as lessons) are excluded until they are cleared.
- Cost: about 31 ms a sentence, eight sentences, so under a third of a second.
- Silence by design: a short or empty reply searches nothing, and says so the way his short message does.

## How I will know it worked

Before: a reply that says "compaction" brings nothing the next turn. After: the same reply brings the page about compaction in the labelled block. The test is that exact pair, run on a real item, plus a test that a long reply does not change what his short message finds.

## Falsifier

If more than one line in five of the labelled block, read by hand over the first week, repeats a phrasing he has corrected, the block comes out. If the block ever makes his message's own finds fewer, it comes out the same day.
