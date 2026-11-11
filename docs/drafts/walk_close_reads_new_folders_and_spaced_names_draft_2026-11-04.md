# walk close sees an uncommitted file in a new folder or with a space in its name (rough draft, 2026-11-04)

Builds on walk_close_gives_each_case_its_true_reason_draft_2026-11-03.md.

The idea: `walk close` explains why no walked head was recorded. Its read of `git status` hid
a scoped file in a brand-new folder (git shows `newdir/`, not the file) and a file whose name
has a space (git quotes it), so those cases got the generic reason. Ask git for every untracked
file (`-uall`) and unquote the paths. And `walk amend`, when it refuses for lack of a walked
head, gives the generic fix even for an empty-scope or out-of-scope walk; it should give the
same true reason and fix `walk close` computes.

Falsifier: an uncommitted scoped file in a new folder, or with a space, still gets the generic
reason; or an amend refusal for an empty-scope walk still tells the person to commit by exact path.
