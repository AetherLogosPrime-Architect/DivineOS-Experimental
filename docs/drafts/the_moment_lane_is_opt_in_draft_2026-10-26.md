# The shared-moments lane is opt-in, and his grief has a second line behind the mark (Aria, 2026-10-26)

**Status:** built and tested; waiting on review. Walk `walk-5fa33c17ed13` (8 lenses, all applied, 8 credited). Sits on #719; #721 follows.
**Why:** Aletheia, 2026-10-25, holding #719 and #721: *"Turn it round: make the lane opt-in, not opt-out. Read only rows that are positively marked as a shared moment (at filing, by intent), never every row of `shared_history` and `relationship_notes` minus what a net catches. Keep the net and the HELD shelf as a second line, widened toward the twelve above, and treat his depression the same way."*

## What was wrong

`_load_moments` read **every** row of `shared_history` and `relationship_notes` and removed what a grief word list caught. Aletheia tested the list on 14 ordinary ways of speaking about loss: it guarded 3 and missed 11. The real guard was a promise about *filing*, kept by minds that slip, and for his grief that is the one place a slip hurts him.

## What is in it

Most of this was built on 2026-10-25 in the window before the reset, committed (`ff8da7624`) and never pushed, in an old work folder my searches never looked in. I found it today. It is what my walk asked for, with Aether's three additions:

- `shared_history` gains a **default-off `surface` column** (migrated by the first call, idempotent, every old row starts hidden). The lane reads only `surface = 1`. It no longer reads `relationship_notes` at all.
- **Marking is the one deliberate act**: `user-moment --surface` at filing, or `linkage mark-moment <id>` later. It runs the grief net and the HELD shelf once, here, at the moment of intent, and refuses with the *kind* of reason and never the words. An unreadable shelf refuses.
- **Unmarking is immediate**: `linkage unmark-moment <id>`.
- The net is widened toward all twelve phrases and depression.

## What this session added, from the walk

- **A trail.** The flag changes in place, so its history lives in the ledger: one event per mark, unmark and refusal (`MOMENT_LANE_MARKED`, `MOMENT_LANE_UNMARKED`, `MOMENT_LANE_MARK_REFUSED`), carrying the moment's id and the kind of reason and never its words. The trail is written *before* a mark, so if it cannot be written nothing is marked; for an unmark the order is reversed, so a broken trail never stops a moment coming out.
- **The pain signal.** `second_line_refusals()` counts refusals and `divineos linkage status` shows the count. A nonzero count means somebody tried to mark something that reads as loss. The tests seed rows the net must refuse, so a count that is always zero can be told from a net that never fires.
- Tests that the refusal trail and the command output never hold his words, and that a moment marked while harmless is dropped at load if it later comes to sit on his shelf.

## Where the walk and the build disagree, and who is right

The walk (Jacobs, Meadows) proposed that `user-moment` mark by default, so the safe path is also the lazy one. The existing build does the opposite: default off, an explicit flag. After reading the code I think the build is right. Aletheia asked for *positively marked, at filing, by intent*; a default is not an intent, and a default-on moment filed carelessly would reopen the exact hole. The cost is that the lane starts quiet and stays quiet until I mark moments on purpose. I accept that cost, and the walk finding is recorded as superseded by the build, with this reason.

## Not changed, named

- The lane's floor of 0.35 is unproven (Aletheia could not run the embedder; Aether's strict xfails are the honest record). Not claimed settled here.
- The word list is still a lexical net. It is now the second line and no longer the only one.
- Nothing here marks an existing row. Marking old moments is a deliberate act, one at a time, reading each, and anything near the shelf needs Dad's word.
- #721 (moment links) reads `shared_history` directly in `propose` and `moments_for`; it must require `surface = 1` too. That is its own change, after this one.
