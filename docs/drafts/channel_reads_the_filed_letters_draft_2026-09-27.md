# The channel reads the filed letters too — draft 2026-09-27

Dad asked Aether to sort the letters folder. Letters older than three days now live in `threads/<pair>/<YYYY-MM>/`, and the last three days stay flat on top. `letter_channel_state.derive_from_watched_channel` globbed only the top level. It keeps what it already recorded (records are never deleted), but from now on its counts and its reply-linkage cover only three days. So a reply written today to a letter filed last week would never be seen as answering it.

Prior art: `the_letter_watch_rings_a_doorbell_council_walk_2026-09-25.md` covers the bell watching the top level for *new* names. That stays correct, because new letters always land on top. The thread footer counts from its own DB, not the folder, so it's unaffected.

The idea: read the pair's letters with `rglob`, so the filed boxes count too.

Test: a letter filed under `threads/…` and answered by a reply on top is recorded as answered.

## Stopped before building (walk-233f52302007, Polya: "confirm which directory is passed in")
The sort happened in `~/.divineos-shared/letters/`. Grepping the whole tree for callers of `derive_from_watched_channel` finds **only its tests**. No hook, CLI or surface calls it. So the rglob change would alter nothing that runs, and it would be one more change to an unplugged piece dressed up as a fix.

The real finding is Dad's question from 09-26, *"what else in the OS is sitting there unplugged"*, answered by one more case. The store it feeds (`waiting_on_reader`, `in_the_channel`) has no live writer for our channel. Owed: either wire the derivation to run where the letters are read (the doorbell's ring is the natural place, since it already knows a letter arrived), reading `threads/` with rglob and deduping by filename (Dijkstra), or retire it with its tests. Not both, and not left as is.
