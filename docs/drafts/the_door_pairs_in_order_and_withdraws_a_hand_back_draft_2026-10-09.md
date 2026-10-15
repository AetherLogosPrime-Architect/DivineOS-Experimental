# The door pairs identical replies in order, and withdraws a helper's hand-back (draft, 2026-10-09)

After #584 landed, Aether's replay of the 49 unmatched rows settled 43 and left six. Five were Dad's emoji saved garbled (closed at the source in #584). The sixth is not his words at all: a helper session's hand-back, kept as `<agent-message ...>`, whose record the harness stamps `peer` and wraps in its own sentence. Naming the tag was necessary and not enough (Aether's commit `a1daede60`, carried here): #584's equal-words test still failed against the record's extra prose.

## Two changes, one file

1. **A kept message with nothing of his in it fits a record of the same turn that is not stamped human.** Equal words is still tried first. The fallback needs the same prompt id and a non-`human` stamp, so a machine-only message never takes a record of his, even one on its own id. Measured 2026-10-09: all 38 records carrying an `<agent-message>` in 30 days across 257 transcripts are `peer`; none is `human`.
2. **Identical quick replies take their records in the order he sent them.** Aletheia's item owed since 10-03, measured by Aether on #584's head: two identical "yes" kept five seconds apart, each record written three or more seconds before its keep, swapped records, so each was filed against what we had said before the *other*. Taking the nearest record in either direction swaps them; Aether's one-line "nearest at or before" still swaps them on his own example (checked in a standalone script before any edit); "newest first" fixes that and breaks the slips written just after each keep. Pairing messages with the same words in order, choosing the smallest total gap, is right in all of them, and a lone message still gets its nearest record, so Aletheia's unkept-older-record case still holds.

Tests, written first: the swap (red on main), the control where each record comes after its keep (green both ways), the hand-back withdrawn (red on main), and the control that a machine-only message does not take a human-stamped record (green both ways). On the real stuck row (Aria's seat, 2026-10-04 15:33) the new rule fits.

## Said plainly, not tested

- **Named limit.** A hand-back stamped `human` would not fit and would stay unmatched, visibly. None of the 38 measured is stamped that way.
- `door_report.report` counts only `stamp == "human"` records as arrivals, so a `peer` hand-back is correctly not an arrival; whoever reads the denominator should know.
- The emoji test in #584 needs bash (`@needs_bash`), so on a seat without it that test is skipped and the real fix is unproven there; it ran on both seats here.
- `_fits` has a lower time bound and no upper one (a same-id record hours *after* the keep fits). It was so before #584, and the id and equal words still apply. Named, not changed.
