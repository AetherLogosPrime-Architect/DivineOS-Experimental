# The key comes back only for a merged fix

**Draft, 2026-10-07. The idea, not a plan.** Follows `the_override_is_a_button_draft_2026-09-30.md`, which designed the one key; this is what Aletheia found when she read it built (#597).

## What she found

Aletheia, 2026-10-07: "`note_clean_pass` proves a commit and a pass, not that the commit caused the pass." The key came back when the same command passed cleanly after ANY commit touching the gate's file, counted from the local history, reviewed or not. A one-space edit to the gate file, or weakening the lock locally, then a pass because the branch had caught up in the meantime, returned the key with nothing fixed.

## The repair

A gate commit counts only when it is reachable from `origin/main`. Merged means reviewed, by Dad's blanket rule, so the key comes back for a reviewed fix and for nothing else. The refusal text now says so in the same sentence as the way back, because a stuck seat follows the words literally. A stale local copy of `origin/main` fails safe: it only delays the key.

Two tests pin it, and both fail on the code before this change. One runs the REAL lookup on a real temporary repository (the fixture the other tests use swaps the lookup for a stand-in, which cannot see this): the commit does not count on a side branch and counts once it is inside `origin/main`. One reads the refusal text for the word merged.

## What it will not do

Her second suggestion is not built: proving causation with the replay tool, so that the spent command is refused by the gate file at the fix's parent and allowed at the fix. That is stronger than merged-means-reviewed, and it is owed.

The key now waits for review and merge, so a deadlock lasts longer than before. The "ask Dad" route and the inquiry opened on a second deadlock stay as the release valve.

## Limits of the push-folder rule, named so a pass is never over-read

The merged helper `push_detection.push_cwd` (older than this branch, not regressions): `git -C /other push` names a tree without a `cd` and is not read, and in `cd A && git push; cd B && git push` only the first push's tree is read. Both fall back to the session's own tree.

## The five "pin today" tests

Five tests in `test_workshop_today_lets_the_cheap_shapes_through.py` pass on the code before the change on purpose: they describe what the draft door lets through today, before it is changed. They are labelled as describing behaviour and not testing a fix.
