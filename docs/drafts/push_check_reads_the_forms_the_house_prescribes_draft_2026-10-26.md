# The push check reads the folder forms the house prescribes (Aria, 2026-10-26)

**Status:** built and tested; waiting on review. Walk `walk-fb1339722adc` (8 lenses, all applied).
**Why:** Dad, 2026-10-26, when my gate fix could not be pushed: *"fix the check first, then push the gate fix through it properly"*.

## What happened

I pushed from a clean worktree, written the way the house's own cd-drift doorman tells me to (`( cd <folder> && ... )`). The push check measured my *session* folder, which really is ten commits behind main, instead of the worktree I was pushing, which was level, and blocked an up-to-date branch. The only visible exit was the kill-switch, which the app's own safety layer correctly refused to let me use. This is the third time for this function (2026-08-15, 2026-09-24/30, now), and each time the cause was a shell spelling it did not read.

## Root cause (read from the code, not guessed)

Two correct gates, composed, made a worktree push measure the wrong tree:

- The **cd-drift doorman** refuses a top-level `cd` and prescribes `( cd <folder> && <command> )` or `git -C <folder> <command>`.
- The **push check** (`check-branch-on-push.sh` with `push_detection.py`) found the pushed tree only from a `cd` after `;`, `&&`, `||` or a pipe, never after a bracket, and only recognised a push when the words `git push` *opened* a segment, so `git -C dir push` was not seen as a push at all (the check never fired).

A third defect was found while writing the walk: the matcher split on `;` and `&&` *inside quoted text*, so a note that merely mentioned a semicolon followed by the push words was judged a real push.

## What changed

1. `push_detection.py`: the matcher works on the command with quoted arguments blanked (the house's existing `blank_quoted_spans`, same length so offsets still index the original). A push may sit after a bracket and may carry `git -C <folder>`. The pushed tree is the last `cd` whose bracket still encloses the push (a `cd` inside brackets does not reach a push after the closing bracket), or the `-C` folder. A folder that was **named but is not a git tree** says so on stderr; naming no folder stays quiet.
2. `check-branch-on-push.sh`: the block now begins with `Measured tree: <folder>` (or says it was the session folder and that the command named no other), and the extraction's stderr is kept so the not-a-tree sentence reaches the screen instead of dying in `2>/dev/null`.
3. Tests: `test_push_check_reads_the_forms_the_house_prescribes.py` cuts its cases **from the cd-drift doorman's own refusal text**, so a spelling the house recommends cannot be left unread; plus the quoted-text cases, bracket scope, `git -C`, and the real hook run against a real branch 13 commits behind (a number no session folder shares, because the check only complains from ten). `test_push_check_reads_the_pushed_tree.py`: one regex widened to match the new redirect.

## The control

The same test file run against the **old** code: 16 of 20 fail (including the real hook measuring the wrong tree against the real stale branch), 4 pass as they should (the cases that were already correct). On the new code all pass, with two skipped (an unquoted folder containing a space is not valid shell).

## Walk 1, in short (all applied; full text on the walk record)

Wayne: the test must be the doorman's own prescribed forms. Dijkstra: two questions (is it a push, which tree) share one tool; and the quoted-text splitting. Hofstadter: the check that polices pushes is pushed through itself, so the fix has to be in the tree the hook runs from before it can protect its own push. Aristotle: scope, a `cd` in brackets lives only inside them. Lovelace: the alarm must name the folder it measured. Hoare: none-named and named-but-not-a-tree are different states and must not look the same. Dekker: third fix of the same function; derive cases from the doorman's text so there is no fourth. Watts: a detector that mismeasures trains the bypass; show the subject, read the prescribed forms.

## Honest bookkeeping

- I closed the walk before crediting the lenses that changed the build (credit only works while a walk is open). Same slip as on the voice gate branch earlier today, so it is a pattern, not luck, and worth a structure: the walk-close command could refuse while findings exist that were never credited or declared uncredited.
- `pushes_only_tags` still reads the old anchored pattern, deliberately: a `git -C dir push --tags` or a tag push inside brackets is read as "not tag-only", so the branch check runs. That is the safe direction (more checking, never less) and is left as is.
- Not changed: the "full suite by hand" doorman refuses a single-file pytest written inside a bracketed `cd`, for the same reason (it cannot see a path inside brackets). A fourth gate with the same blind spot; named here, not fixed here.
