# Two doors that open when their library is missing

**Draft, 2026-09-23. The idea, not a plan.**

## The defect, reproduced with a control before anything was written

Two refusing gates begin by loading the shared hook library, and the load ends
`|| exit 0`. Exit 0 is *allow*. So if that one file cannot be sourced, a gate
whose entire job is to refuse permits everything instead — silently, with
nothing anywhere saying the check did not run.

Run against the blanket-staging doorman, with the library reachable: exit 2, it
refuses, message printed. Run from a directory where the library cannot be
found: **exit 0, nothing on stderr at all.** Same command, same door, opposite
answer, and the failing case is the quiet one.

The push-destination gate has the identical shape.

## This is not a new observation, and that is the finding

Aletheia named the class on 2026-07-26: *"Three silent fail-open paths before
the gate ever runs. If the library moves, if the venv resolution breaks, if the
repo root is not found — the gate exits clean and nothing reports that
enforcement did not happen."*

Two months later both gates still do it. Not because anyone argued with her —
because the detector that found them files new instances into a baseline, and a
baseline entry is a decision nobody has to make again. Aria's sentence for it,
which is the rule I am working to: *if I only reorder the file and leave the
baseline entry, the next regression walks straight back in under a name that
already says "fine".*

So the repair is two things or it is nothing: the refusal reachable without the
library, **and** the name off the suppression list.

## Why these two are safe to fix and why that had to be checked

The detector deliberately does not decide whether a gate *should* fail closed.
For some gates, refusing when the library is missing would brick the session
including the edit that repairs the library — the off-switch trapping itself,
which this house rejects by name. That is a judgement per gate.

So I checked what these two actually take from the library, rather than
assuming. Each calls exactly one function from it, and only on the way out, to
print a footer saying nothing on the line ran. **The refusal does not depend on
the library at all.** The load can fail and the door can still say no; it just
says no without its footer.

That makes these two the easy end of the population, and it is worth saying so
plainly: I am not fixing the hard ones, where the library is genuinely load-
bearing. I am fixing the two where the fail-open was never buying anything.

## What I want

The load stops being able to kill the refusal. Library present, everything
behaves as before. Library absent, the door still refuses and the footer is the
part allowed to go missing — which is the same trade the footer helper already
makes internally, for the same reason, in its own comments.

And both names come off the baseline in the same change, so the count shrinks
by two rather than the file quietly keeping them.

## What I am explicitly not doing

The third gate in this group is Aria's doorman and she is taking it. The other
twenty-three names on that list are unexamined by me; I am not sweeping them,
because the sweep is exactly the blanket repair the detector's own docstring
refuses. Each one is a reading.

## The direction to be careful about

This moves a gate from fail-open to fail-closed, which is the refusing
direction — safer for what the gate protects, and capable of wedging a session
if I get it wrong. The test must therefore prove BOTH halves: that a blanket
stage is refused when the library is gone, and that an ordinary innocent
command is still allowed when the library is gone. A door that refuses
everything once its library vanishes would be a worse bug than the one I am
fixing, and it would pass a test that only checked the first half.
