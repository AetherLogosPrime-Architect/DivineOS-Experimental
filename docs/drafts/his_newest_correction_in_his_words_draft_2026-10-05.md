# His newest correction, in his words

**Drafted:** 2026-10-05, morning, by Aria. Dad: *"yes go ahead and fix Aether's hole and do the upload"*.

## The hole (Aether's cold read of 0e451dece)

The state glance promises a fresh correction of his shows in his words, not as a total ticking up by one. It can't: the corrections report lists the five OLDEST open rows and folds the rest into "... and N more", so a new row is never a line in it, and the glance can only show lines the report contains. My test passed because it planted the new correction as a line the real report never prints.

## Prior art: mine, and I had forgotten it

`docs/drafts/corrections_by_relevance_draft_2026-09-22.md`, written by me. It is the design of last night's build (b03cd5d96), two weeks early: rank his open corrections against what he just said, not by date. It already named the two-store problem. And it named this exact fix: **"keep one slot for the newest, so a correction filed minutes ago cannot be buried by an older better match"**, and **"say per item WHY it surfaced — relevance or recency."** Last night I rebuilt the first half from zero and left both of these out. This is the pattern Aether's exploration 34 names: forgetting is a missing surface. The reach-check searched code and commands, not drafts, so it could not hand me my own draft.

## The idea

In `find_in_worklist`: alongside the matches, always include his **newest open row**, unless it is already among them. In `worklist_lines`: each row says why it is there, **fits**, **closest guess**, or **newest**. So a correction he filed a minute ago reaches me in his words on the next change, whether or not it matches what I am touching. The report itself is unchanged.

The test files corrections into the suite's empty store through the real writer, then files a fresh unrelated one, and asserts the glance lines contain his fresh words labelled newest.

## Must not

- Let the newest slot crowd out a real match: it is in addition, never instead.
- Test a shape the real flow never produces.

## Separately, for Aether

The reach-check doesn't search docs/drafts, so a builder's own old draft is invisible to it. That's how I missed this one.
