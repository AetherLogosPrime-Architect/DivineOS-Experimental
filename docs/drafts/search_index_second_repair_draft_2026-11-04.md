# The search index, two fixed and one left open (draft, 2026-11-04)

The idea, not a plan. Review round 4 of repair #816 (relative chunk ids).

1. **One root for both callers.** `divineos find index` gathered its files from
   the folder it was run in and passed that folder as the root, while sleep
   passes the checkout root. Run from a subfolder, the first finds no files at
   all (or, where it does, ids fall back to absolute paths) and the two callers
   delete each other's rows by source path and embed them again. Both now use
   the checkout root the code runs from (`default_repo_root()`), wherever the
   shell stands.
2. **A deleted note keeps its rows.** The cleanup only looks at files that
   are still on disk, so a deleted or renamed note keeps its rows and keeps
   turning up in searches while the total quietly leaves them out. The refresh
   of the exploration corpus now also removes rows whose id sits under the
   exploration folder of this checkout (id prefix `exploration/aether/`, or the
   old absolute prefix) and which match no paragraph of any file walked. Only
   that corpus: letters, and other checkouts' absolute ids, are not touched.
   Scope of that cleanup, so a wrong prefix cannot eat live rows: a row is
   removed only if its file part is not among the files just walked AND it
   starts with this checkout's exploration folder (relative or old absolute).
   A control test pins that letters survive.
3. **Left open, on purpose: two checkouts with different text.** With ids
   relative to the root, checkout A and checkout B share an id for a note that
   differs between them, and each refresh replaces the other's row and
   embeds again, forever. A fix needs a rule for whose text wins. Options:
   (a) the newest file by modification time (wrong for fresh worktrees: git
   stamps checkout time on every file, so a stale copy would win); (b) the
   checkout the DB is "home" to (a decision about which tree is canonical);
   (c) put the checkout in the id for notes whose text differs (restores the
   duplicate counting #816 removed, only for differing notes); (d) skip a row
   whose text came from another checkout whose file still exists (first writer
   wins, so edits in the second checkout never become searchable). None is
   clearly right; it is a design decision.
