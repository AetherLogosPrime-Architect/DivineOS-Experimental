# The stamp keeps the description it was handed (draft, 2026-10-17)

**Found** 2026-10-16 stamping #679: the pull request's description, a paragraph and an Author line, came back as one title and a review line. The code that keeps the author's text existed (it reads `pr.get("body")`), but the stamp had asked GitHub only for `headRefName,title,isDraft`. The field was never present, so `.get` answered empty and the keeping step never ran. Nothing failed: absent read as empty. Every PR stamped by this command lost its description, and GitHub builds a squash message from the title and body, so the reasoning for a change was missing from the permanent record at the moment the change was approved to enter it.

**Change.** `PR_FIELDS = "headRefName,title,isDraft,body"`, and the keeping step is `keep_the_authors_text(prior, stamp_block)`: the author's lines stay, the old `External-Review:` and `Reviewed via audit round` lines are replaced (not stacked), the title line of the composed block is dropped once real prose sits above it, and the review lines come last. Aletheia's hardening: a reply from `gh` with no `body` key at all is could-not-look, so the stamp prints "Could not read the description of PR N: the reply from gh has no body field. Nothing was changed." and exits 1 before any edit. An empty string, which is what `gh` returns for a PR with no description, still passes.

**What it does not do.** It keeps the author's text, not a checked version of it: a stale status sentence ("needs Aletheia's read") survives a re-stamp, as it did on #686, and only the author can rewrite it. It cannot recover a description an earlier stamp already wiped (GitHub's edit history keeps only the wipe); #671's was rebuilt by hand from its own design note and says so in its body.

**Falsifier.** If a stamp ever returns a body that lacks lines the author wrote (other than lines starting with the two stamp prefixes), or runs with a missing `body` field and edits anyway, the fix is wrong.

**Order of work.** Test first (`tests/test_stamp_keeps_the_authors_description.py`: the field is requested, prose and Author line survive with the review lines last, an earlier stamp is replaced not stacked, no prior text leaves the block alone, a reply with no body field refuses before editing, and an empty body is not refused for missing it), then the field list and `keep_the_authors_text`, then the guard.

**Not in this change.** Recovering wiped descriptions; checking that a kept description is still true; the merge-message side (a squash body is composed separately by `ship`).
