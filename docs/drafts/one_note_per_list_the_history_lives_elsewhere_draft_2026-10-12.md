# One note per list, and the history lives elsewhere (draft, 2026-10-12)

**Author:** Aria. Dad, 2026-09-12 and 2026-10-12: *the code is not a journal; it is fine to have an official note, but that note should say the current situation, not carry a diary of the changes. The journalling is fine, it just needs separating.*

## The fault

Two lists decide which commands are a gate's way out. Above each, comments pile up: the shared shell list carries about two hundred lines of stories (six instances, each a deadlock somebody hit) in front of one pattern, and the build gate's own list carries three separate widening notes between its entries. The code is buried under its own diary. A reader looking for the rule has to find it inside the history, and the history, which is real and worth keeping, is harder to read for being in the way of the code.

A picture: a recipe card with the cook's whole kitchen diary written between the steps.

## The change

Nothing is deleted or rewritten. The stories move word for word into `docs/gate_list_history/` (one note per list, with a README), and each list gets one short, current note above it: the rule, the entry bar, what the list is and is not, its known limits, and a pointer to its history. The entry bar and the "adding here is a decision" rule stay in the code because they are the rule, not the story.

A search of `docs/` and `docs/drafts/` found no existing history note for either list; the earlier drafts of mine that mention them are about the changes, not a record of how the lists grew.

## What this does not do

No entry is added or removed, and no pattern or tuple changes, so behaviour is identical. A test lifts the real tuple and the real pattern and compares them with the lists as they were, so the tidy cannot quietly change a list.

## Falsifier

The tuple or pattern differs after the change, or a comment I keep makes a claim the history contradicts.
