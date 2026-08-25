Looked, per the gate's own instruction, and the flag is correct-but-over-counted. Gate said 18 deletions; real count is 10 -- it diffs against the merge-base rather than origin/main's current state, so 8 of the 18 are already absent from main and their "deletion" is a no-op. That wrong-denominator shape is the same class as three other findings tonight and is the root-cause I owe this gate.

All 10 real deletions trace to one named commit, eea9a71f "chore(delivery): five systems noticed one letter; three ran at once", which is Andrew-directed retirement work: "retired systems never retired.. turned off instead of removed.. leaving a mess in its wake." Five mechanisms existed to notice one letter, three ran simultaneously, two were Windows scheduled tasks running outside Claude from sessions that had already exited. The deletions ARE the intended work, not collateral.

Replacement verified live this session, not assumed: scripts/letter_monitor_v2.py is not in the deletion set, is the monitor I armed twice tonight, and it delivered Aria's letter (aria-to-aether-2026-08-21-station-four-holds...). cross_substrate_watcher.py's surviving counterpart cross_substrate_event_emitter.py is present on disk.

Also note this push is not a merge -- the deletions reach main only through a PR that has its own gate.

ROOT CAUSE I WILL FIX: check-branch.sh should count deletions against origin/main's current tree, not the merge-base, so an already-retired file stops being reported as a pending deletion.

---

## RETIREMENT NOTE (2026-08-25)

Removed after investigation. Three findings, and the first one is that the
root cause written above is WRONG.

**1. The diagnosis was wrong.** The marker says check-branch "diffs against the
merge-base rather than origin/main's current state." It does not.
`branch_health.check_deletion_shape` uses `git diff --diff-filter=D
--name-only {base}..HEAD` with `base="origin/main"` — a two-dot diff, which is
a direct tree comparison, not merge-base-relative. That line has read `..` since
2026-05-09 (2734d0d1) and was never changed. I wrote a plausible root cause into
a kill-switch without reading the code it accused, and then carried it for four
days as the reason a gate stayed off.

The real cause of the 18-vs-10 discrepancy is almost certainly the wrong-tree
problem the hook's own comments name at 2026-08-15: it measured the ambient
repo root rather than the worktree the push came from. That fix shipped
(the PUSH_CWD extraction in check-branch-on-push.sh).

**2. The gate is healthy.** Run 2026-08-25 on
fix/hook-latency-and-stamp-branch-measurement:

    [ok] base_freshness: Branch base is current with origin/main.
    [ok] deletion_shape: No files would be deleted by merge.

**3. The marker was never consumed.** The hook's comment says the kill-switch
"disables the gate for one push." Nothing deletes it. So it disabled the gate
for EVERY push from 2026-08-21 onward, and each of those pushes fired
`record_emergency_use`, filing a fresh claim and a fresh structural-fix
obligation. Ninety-two of the 334 rows in the pending-obligations list — 28% of
the entire backlog — are that one marker, refiled.

A one-push kill-switch that is not consumed is a permanent one, and the only
evidence of the difference is a pile that grows on a timer.
