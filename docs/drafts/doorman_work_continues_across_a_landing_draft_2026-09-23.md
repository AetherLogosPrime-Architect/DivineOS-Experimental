# The doorman: work that continues across a landing — draft 2026-09-23

Reach: reach-23c27b8576ba. Data: Aether's letter
`aether-to-aria-2026-09-23-the-three-cases-with-real-numbers-and-a-fourth-still-open.md`,
pulled from his store, epoch times.

## The four cases, sorted by cause

- **Cases 1 and 2 recorded their trigger as `2`.** That is the old reader
  misreading `2>&1` as a file named "2": the fault f13cdef2 fixed on my branch
  and pinned in `test_doorman_reads_the_shell_as_the_shell_does.py`. His
  checkout runs main's reader. With the new reader, neither call names a write,
  so neither opens an item. **No new rule needed for these two** — they need the
  reader fix to reach main.
- **Case 3 — a red test on work in flight.** `wi-1a0cd62b914` opened 1790152194
  on `.claude/hooks/session-init-once.sh`, a file changed BY the landing its
  window starts from (e1635b5a2, 1790151660). The pre-push suite had refused the
  push. His reach, draft and walk for the launcher work all predate that
  landing, so the item saw nothing. **This is the rule to build.**
- **Case 4 — the orphan.** `wi-1a0cd37aa75` on the meter branch is still open,
  holding a reach and a walk for work that moved to another branch. The marks
  belong to an item and the work outlived the item. **Not built here**: the
  right answer is unclear (marks are stored globally, items per branch), and
  guessing would open the propped door. Named as open.

## The rule for case 3

When the doorman opens a new item because the last piece of work landed, and
the file being edited **was changed by that landing**, the edit continues that
work. Its marks window reaches back to where the landed work's own window
began: the landing before the last one. Otherwise nothing changes.

Why it does not reopen the propped door (September's fault: one finished piece's
marks paying for unrelated work): an unrelated edit touches a file the landing
did not change, so it gets the ordinary window. Only an edit to a file the
finished work itself touched inherits. And a file the landing changed is
exactly the file a red test, a lint failure or a review comment on that work
points at.

## Tests

- Case 3 from real shape: last landing changed file X; marks done before that
  landing and after the one before; first edit of a new item on X → OPEN.
- Control: same marks, first edit on file Y the landing did not change → HELD.
- Control: the landing before the last is older than the marks' own start, so
  marks from an even earlier piece never count.
