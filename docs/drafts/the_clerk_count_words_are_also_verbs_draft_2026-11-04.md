# The clerk's count words are also verbs — draft, 2026-11-04

## What Aria found (cold read of #832, head fdab5d4db)

#832 made `_names_pr` ignore a number followed by a count word (`commits files changes lines times
minutes hours days issues items`), so `pull 5 commits` would not name PR 5. But those words are also
verbs, and after `PR` they are far more likely to be one: `PR 7 changes the clerk warning`, `PR 7 files a
round`, `PR 7 issues a warning` all stopped naming PR 7. A round written like that was not found and the
clerk went quiet about it, which is the direction that hides.

## The fix

After `PR` or `pull request`, the number names the PR whatever word follows. The count exclusion stays only
for the bare git word `pull` (`pull 5 commits`, `pull 7 times`), where a count is the likelier reading.

One regex, three alternatives: `#7`; `PR` / `pull request` + separators + `7`; bare `pull` + separators +
`7` not followed by a count word. A GitHub URL (`/pull/7`, `/pull/7/files`) still matches through the bare
`pull` alternative because the exclusion needs whitespace before the count word.

## One decision I changed, said plainly

#832's own test said `pr 5 files` must NOT name PR 5. That is now the other side: after `PR` it names the
PR, because `PR 7 files a round` is the same shape and the two cannot be told apart by their words. The
cost is the other direction: a round saying `PR 5 files` as a count would be reported as naming PR 5, a
louder, visible mistake, where the hidden one is silent. Hiding is the worse error here.

## Known limit

Bare `pull` keeps the count exclusion, so `pull 7 lines up with the draft` is still not found. Wording like
that is rare; the stated lean is toward not hiding where the words give a clear signal (`PR`) and toward
the git reading where they do not (`pull`).

## Tests

Five new tests (all fail on #832's head, pass now), and `pr 5 files` moved from the must-not-name list to the
new test. 45 pass in `tests/test_landing_round_without_tree_line.py`; 21 in `tests/test_landing_homework.py`.

## Status

Draft, stacked on #832's branch (`claude/fix2-807-2026-11-04`). `landing_homework.py` is the clerk. Needs a
read by someone other than me (Aria found the defect and has read #832), then the round.
