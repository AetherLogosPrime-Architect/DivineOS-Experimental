# Letters matched by passage, not by their opening

**Status:** draft, station 1. Not built.
**Date:** 2026-10-06
**Asked by Dad:** "why are you deprioritizing the letters?, they should be included as part of the memory if they are relevant as long as they dont drown out my words". And yes to building passage matching ahead of the sort.
**His earlier words (23 July, 20 August):** link "a phrase or two from it with a pointer to the full letter", and "link it to certain phrases or paragraphs that are relevant vs the whole thing".

## What I got wrong, and what is actually wrong

On 6 October I ranked letters last (a82bb19e5, then a quote exemption in 482309891) because 1 of 30 surfaced for his real messages was useful. That read a symptom as a property of letters. The cause is that a whole letter is matched on its opening (the first window of text; the encoder keeps about 256 tokens), so a long letter matches whatever its start shares with his words and the useful part, in the middle, is never looked at. The rank rule was a blunt patch, and it contradicted his instruction.

## Prior art searched

- `core/semantic_search.py` and `divineos find` already chunk by paragraph and keep a source pointer per chunk (pre-reg prereg-2ad79e23fcf7). It uses the heavy encoder and its own database, indexes `exploration/aether` and `family/letters` of the working directory only, and splits at 20 characters, so every letter's boilerplate footer is its own chunk. It cannot run inside the per-turn budget of the memory link. Not reusable here; the idea is the same.
- `core/memory_linkage_retriever._load_letters` reads 3,048 letters one at a time and makes one vector per letter. It is 1.09 s of the 1.31 s cache load, measured today. Only `_ensure_cache` and `warm` call it.
- `docs/drafts/his_worklist_by_relevance_draft_2026-10-05.md`: the same principle for his worklist ("relevance is key, noise is pointless"), and its Shannon finding on duplicates.

## Measured before designing

Splitting all 3,077 letters (footer, sign-off, front matter and headers dropped; paragraphs under 25 words merged; over 150 split at sentence ends): 26,561 passages, median 8 per letter, average 87 words. Read and split in 0.8 s. At about 50 ms a vector that is a one-time offline fill; per turn, one matrix of 26,561 by 384 numbers is about 41 MB and one multiply.

## Proposal

1. A new module `core/letter_passages.py`: split a letter into passages, build an index (a vector matrix file plus a small database of the passage text, letter id, path, title, date), and answer a query with the best passage per letter. Built incrementally by `warm`: only new or changed letters are processed.
2. In `retrieve_v2`, letters come from that index, not from the per-letter cache. The result carries the matching passage as its text, with the letter's path as the pointer. A letter stops being loaded as a whole, which also gives back about a second of load.
3. Letters compete on relevance like everything else, with **one slot at most** in the five, so they cannot drown his words. The rank penalty and the quote exemption of 6 October are removed, because they existed only to patch the whole-letter match.

## What I am NOT proposing

- Deleting or moving any letter, or changing how letters are written.
- Letting letters outrank his own words by a different route: the single-slot cap is the guard, and it is tested.
- Calling it better from the replay of his 30 messages alone: that is where 1 of 30 was useful, and the test is the same 30 rated again.

## Falsifiers

- A letter asked for by a quoted sentence is found at least as often as with no penalty (15 of 40 on 6 October). A passage should contain the sentence, so this should rise sharply; if it does not, the split is wrong.
- On his 30 real messages, the share of surfaced letter passages marked useful by two raters is above the 1 in 30 of whole letters, on a sheet rated blind.
- At most one letter in any returned five.
- Time per turn does not rise: cache load falls, query adds under 100 ms.
- A passage that is only boilerplate (a footer, a sign-off) never surfaces.
