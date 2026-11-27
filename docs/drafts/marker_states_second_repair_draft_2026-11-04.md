# The cycle marker, three leftover states (draft, 2026-11-04)

The idea, not a plan. Review round 4 of repair #813 found three places where
the handshake marker is read as more than it says.

1. A marker whose `steps` is empty prints "COMPLETED -- 0 step(s), all
   succeeded". Nothing succeeded; nothing was recorded. Boundary at zero (Knuth):
   it gets its own words, "NO STEPS RECORDED", and is neither success nor dry run.
2. A step is a pair (ran, succeeded). Only three pairs mean something: (true,
   true) done, (true, false) failed, (false, false) did not run. (false, true)
   contradicts itself, and a `ran` that is not a real true/false (the text
   "false", null) is not a yes or a no. Those states are not representable as
   success (Hoare): they read as FAILED with a named reason, never as COMPLETED
   and never as "(a dry run)".
3. `divineos auto-cycle status` says "phase 2 has not consumed it yet" for any
   marker. A marker whose every step did not run is a dry-run leftover, not a
   handoff. Invariant (Lamport): a handoff is pending only if some step ran.
   Status says so in words and does not call it pending.

Not touched: PR #813 itself (its body claim about the `status_flag` line is
corrected in this repair's description, not by editing that PR).

Blind spot: a second writer of the marker (`defer_check_cmd`) is a real cycle
and keeps its marker; I did not re-audit every reader beyond the hook and status.
