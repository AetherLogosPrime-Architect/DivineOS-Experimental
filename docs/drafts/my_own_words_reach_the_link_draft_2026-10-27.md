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

## What the walk changed, and what I measured after building

The nine-lens walk (walk-f499568a7067) changed the plan in six places, all now in the code:

- **Dedupe across turns** (Breaker): a page shown last turn is not shown again, kept in a small file in the data home, or the same lines would become wallpaper.
- **Gate text is never handed back** (Meadows, Schneier): a lesson that starts with a gate's own refusal wording is skipped until those rows are cleared (Aether is clearing them).
- **His finds come first** (Minsky, Dijkstra): the new block only ever adds a block after his, and a test pins that his block is byte-for-byte the same with and without it.
- **Boilerplate is dropped before searching** (Shannon): a sentence under eight words, a path, or code is not searched; of the rest the eight longest are kept.
- **A search that broke is said** (Schneier): "my own words were not searched" is a different line from nothing found.
- **One text in two stores is one line** (Meadows): found live. The first real run returned a correction and its worklist copy as two lines of the same words; they are now one.

Measured: eleven tests, and five deliberate breakages of the new code each made a different test fail (the same page twice in a row, gate text, no sentence filter, the sentence cap, the shown-last-turn memory). A real run on this session's own transcript returned the labelled block in about 0.12 seconds warm, against 0.03 for his block alone. 116 tests pass in the memory-link and hook-surface files.

## What it does not do, said plainly

- It matches by closeness of meaning, not by the word. A sentence of mine brings a page when it is about it.
- Items are vectors of their opening 2000 characters, so a sentence of mine can only match an item's opening; a page whose subject sits in its middle is missed.
- It does not clear the sixty-compactions problem. It adds a way for my words in; Dad's consolidation of near-duplicates is separate work Aether and I share.
- I have not watched it across a real week of turns. The falsifier above is how that week is read.

## Aether's cold read of f297f0c43, and what changed

He held on one thing and answered four. All are now in the code, each with a test that fails without it.

- **HOLD, the gate-text filter** missed four shapes: a row starting "Hook feedback:", a lesson-shaped row that carries the gate's words after its first few, "THE WARDEN READS THE LOG", and "THIS IS YOUR ROOM, AFTER WORK". A prefix test cannot see the second at all. The filter now looks for the phrases anywhere in the first 300 characters, and says in its comment that it is a stopgap until extraction stops storing these rows (owed, and it is code).
- **A one-line reply hiding a long one:** it now reads everything I said in the turn, joined (his current message is skipped, a gate's message back to me and a notice continue the turn), and the eight-longest-sentences rule is the bound.
- **The seam is named:** it leans on five private names in the retriever and on the turn reader's `_read_records`. One test fails loudly if any is renamed.
- **Speed:** the search is one matrix product per source for all the sentences. His measurement of the loop was 0.77 s on the real cache; mine now is about 0.2 s, most of it stacking the cache's vectors once per call. Caching the stacked matrix is part of the separate piece he named, saving the cache to disk, which is for after the pile.
- **A small bug:** a sentence starting with a date lost its digits. Only a list marker is stripped now.
