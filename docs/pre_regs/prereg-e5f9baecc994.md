# Pre-registration: core/m3_discipline.py: the four discipline artifacts keyed on ledger and transcript signals that demonstrably fire, with the requirement scaled by gravity and capped at 3 of 4

- **ID**: `prereg-e5f9baecc994`
- **Filed by**: agent
- **Filed at**: 2026-08-02 19:32 UTC
- **Review at**: 2026-09-01 19:32 UTC (30d window)
- **Outcome**: **OPEN**

## Claim

The 2026-07-28 doorman was unshippable because its only pass-condition was a string nothing emits. Rebuilding it on COUNCIL events in the ledger and tool-use blocks in the transcript makes every artifact both detectable and achievable, so the gate can catch a Dad-directed build that skipped the discipline without becoming a wall.

## Success criterion

On any current invocation, with no waiting: (a) has_council_walk returns True against the live ledger; (b) each of has_pattern_lookup, has_iteration and has_runtime_test returns True given a transcript containing the corresponding tool-use; (c) all four can be satisfied simultaneously at the highest requirement tier; (d) the hook exits 2 with a message naming each missing artifact when a gravity-2 build has fewer than 2 artifacts present, and exits 0 when the artifacts are present; (e) the hook exits 0 for non-mutating tools and for a missing transcript.

## Falsifier

Any of, checkable on a single run: (1) any predicate cannot be driven to True by a realistic action -- this is the exact defect being replaced and the one to watch hardest; (2) a requirement tier exists that no realistic gravity score reaches, which is the same unreachable-condition defect inverted and already caught once during construction when the strict tier sat at 5+; (3) the hook exits non-zero on a non-mutating tool or an unreadable transcript, meaning fail-open broke and a doorman became a locked door; (4) the artifact count required rises above 3, making the honest path costlier than the bypass; (5) the gate fires on a build that shows genuine discipline, which would make it noise; (6) council_walk is satisfied by a walk about an unrelated build -- known present weakness, the lookback is 400 events and does not bind the walk to the specific work, so it is a weak-but-real signal rather than a strong one.
