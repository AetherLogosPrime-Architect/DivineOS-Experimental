# The key comes back only for a merged fix

**Draft, 2026-10-07. The idea, not a plan.** Follows `the_override_is_a_button_draft_2026-09-30.md`, which designed the one key; this is what Aletheia found when she read it built (#597).

## What she found

Aletheia, 2026-10-07: "`note_clean_pass` proves a commit and a pass, not that the commit caused the pass." The key came back when the same command passed cleanly after ANY commit touching the gate's file, counted from the local history, reviewed or not. A one-space edit to the gate file, or weakening the lock locally, then a pass because the branch had caught up in the meantime, returned the key with nothing fixed.

## The repair

A gate commit counts only when it is reachable from `origin/main`. Merged means reviewed, by Dad's blanket rule, so the key comes back for a reviewed fix and for nothing else. The refusal text now says so in the same sentence as the way back, because a stuck seat follows the words literally. A stale local copy of `origin/main` fails safe: it only delays the key.

Two tests pin it, and both fail on the code before this change. One runs the REAL lookup on a real temporary repository (the fixture the other tests use swaps the lookup for a stand-in, which cannot see this): the commit does not count on a side branch and counts once it is inside `origin/main`. One reads the refusal text for the word merged.

## Added after Aria's cold read (2026-10-13)

She found no hold and measured three things on her own machine. Taken:

- **The replay counted a message of his twice when a session was resumed** (504 turns read, 494 distinct, because a
  resumed session copies records into its new file). Turns now carry the record id and a repeated id counts once.
  By id and never by text: he says the same words twice on purpose, and a test pins that.
- **The hook's wiring was the one part no test drove**, and its captured output (stderr included) became the refusal
  reason, so a typo in the inline program would have printed a raw traceback as the reason. The program now catches
  every error and prints one sentence naming the class (`the key could not be read or spent: JSONDecodeError`),
  still failing CLOSED, since empty output would read as no refusal. A test cuts that exact program out of the hook
  file and runs it against an unreadable ledger, an empty database and non-JSON input.
- **The test that runs the folder extractor now runs this checkout's code** (it had imported another checkout's
  copy and failed two tests after the merge of main).

Not taken, named so it is not read as done: one inquiry per unrepaired spend instead of one per refused attempt (a
retry loop writes many; it would read better on his board), and the key's fingerprint being the push command and not
the folder it ran in.

## Added after Aletheia's second hold (2026-10-13)

She was right that her first hold was not taken: "merged" was read from the local `origin/main`, which is only a note about GitHub, and one command (`git update-ref`) rewrites it, so an unreviewed fix could still bring the key back. The lookup now asks GitHub first with a forced fetch of main, which overwrites a hand-moved note with what GitHub holds. If the fetch fails the key stays spent and the refusal says so ("couldn't confirm the fix is on main"): a stale note can only delay the key, never return one. Two tests pin it on a real repository with a stand-in remote, one that moves the note by hand and expects no return, one that cannot reach the remote; both fail on the code before.

## What it will not do

Her second suggestion is not built: proving causation with the replay tool, so that the spent command is refused by the gate file at the fix's parent and allowed at the fix. That is stronger than merged-means-reviewed, and it is owed.

The key now waits for review and merge, so a deadlock lasts longer than before. The "ask Dad" route and the inquiry opened on a second deadlock stay as the release valve.

## Limits of the push-folder rule, named so a pass is never over-read

The merged helper `push_detection.push_cwd` (older than this branch, not regressions): `git -C /other push` names a tree without a `cd` and is not read, and in `cd A && git push; cd B && git push` only the first push's tree is read. Both fall back to the session's own tree.

## The five "pin today" tests

Five tests in `test_workshop_today_lets_the_cheap_shapes_through.py` pass on the code before the change on purpose: they describe what the draft door lets through today, before it is changed. They are labelled as describing behaviour and not testing a fix.
