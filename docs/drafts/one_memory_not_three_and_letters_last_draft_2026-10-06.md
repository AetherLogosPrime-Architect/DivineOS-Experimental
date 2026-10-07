# One memory, not three; and letters last

**Status:** draft, station 1. Not built.
**Date:** 2026-10-06
**Asked by Dad (via Aether's letter):** the duplicates "need fixing so the memory consolidates them to one memory, and does not hand me fifty of the same wording."
**Prior art searched:** `core/memory_linkage_retriever.py` and `memory_linkage_retriever_v2.py` (the active retriever; selection is `candidates[:TOTAL_INJECTION_CAP]` after a sort by rank, so a duplicate takes a slot); `docs/drafts/` for the memory link. Found and read: `his_worklist_by_relevance_draft_2026-10-05.md`, whose Shannon finding already dedupes near-duplicate corrections for the *state glance* ("each of two slots carries something new"). That is a different consumer (a two-slot glance before each change) from this one (the per-message link), so this is not the same repair, and the content key should be one shared helper if both want it. `marc_questions_round_two_links_2026-10-06.md` answers Marc on links, and says nothing about duplicates or letters. Aether's branches do not touch the retriever. My branch aria/the-door-reads-the-name changes one line of the v2 file, a float32 cast, unrelated.

## What was measured

334 results over 30 of his messages, rated by two people separately, agreement 85 percent. Letters: 1 useful of 30, for each rater, 3 percent. And the same text comes back under several labels (a correction, its worklist twin, often a knowledge copy), so one wording fills several of the few slots.

## Proposal

Two changes, both in `retrieve_v2`, both before the top-K cut, so the freed slots go to something else.

1. **Collapse by content.** Items whose normalized text is identical (lowercased, punctuation dropped, spaces collapsed) become one result: the best-ranked of them, with the other places it lives named in its reason line. Strict at first; widen only if a near-duplicate pile is still there after.
2. **Letters rank last.** A letter's rank is multiplied down so it only appears when nothing else passed. It stays in the drawer, because a letter is the right answer when he asks about a letter.

## What I am NOT proposing

- Deleting anything from the drawer, or touching how items are stored.
- A new ranking model. The existing rank, with two corrections.
- Changing the distress lane (`retrieve_similarity_only`): it is the regulatory path, and a different change.
- Calling this fixed from the one sheet. The sheet is the test, and it is a replay.

## Falsifiers

- On the 30 messages, no returned set holds two items with the same normalized text.
- A set that used to hold a duplicate now holds the freed slot's next-best item, not fewer items.
- Letters in returned sets drop to near zero on those 30, and the share of useful among rated returned items does not fall.
- If an item the rated sheet marked useful disappears because of the collapse, the collapse was too strict or too loose and I say which.
