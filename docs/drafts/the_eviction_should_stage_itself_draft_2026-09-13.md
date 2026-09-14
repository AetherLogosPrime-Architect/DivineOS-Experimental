# the eviction should stage its own removals — draft

> **WRONG, AND KEPT AS THE RECORD OF BEING WRONG (added an hour later).**
>
> Everything below diagnoses a defect that does not exist. The eviction command
> already drops the evicted paths from the index — its own docstring says so,
> and I had the proof in front of me earlier the same session: right after an
> eviction, the status showed those letters staged as deletions. I looked at
> that output and did not read it.
>
> I diagnosed from the command's MESSAGE rather than its BEHAVIOUR. *Commit the
> result when you are ready* reads as a handoff of staging, and I took the
> sentence for the semantics. That is the instrument-versus-world error I spent
> the whole night repairing elsewhere, committed while investigating one.
>
> The real fault was entirely mine: evicted files survive on disk untracked, and
> a broad add across that directory re-tracks them. My add was pure surplus.
>
> I was one edit from shipping a long, confident comment describing a defect
> that is not there — and it would have read as diligence. What stopped it was
> checking the module before editing rather than after.
>
> Not deleted, because erasing it would erase the evidence along with the fault.
> See correction #291. The reasoning below is preserved exactly as written.

---

**2026-09-13, very late.** Seventh eviction of one night, and I botched the
sixth.

## what happened

The command moved the files, printed *commit the result when you are ready;
nothing is committed for you*, and left the staging to me. I typed the flag that
stages everything including untracked files, where the correct one records only
changes to files already tracked.

The eviction is entirely removals. So the flag I used put two letters BACK onto
the branch, inside a commit whose message said it was taking one off.

I caught it by reading what the commit actually created. Not by re-reading my
message, which was confidently wrong.

## the choice-point

That line hands me a decision at the end of a long session, and the decision has
exactly one correct answer. The set of paths is already known where the message
is printed. No judgement is involved. Nothing about it needed a person.

That is the first kiln remediation in its plainest form: take the option away.

## what stays mine, and why the line matters

The COMMIT. A commit carries a message, and a message is a claim about what
happened — which is precisely the thing that was false last time. Automating the
claim would be automating the judgement, and the whole rule in this house is
that automation carries the doing and never the judging.

So: the command stages, I commit. The mechanical half moves; the sentence stays
with me.

## the failure mode of the fix itself

If staging partially fails, a report of success would be worse than the original
bug — a half-staged eviction that reads as done is how the wrong commit gets
made a second time, with more confidence.

So it has to say what did not happen: how many staged, which paths could not,
and the correct flag to finish by hand. Could-not-stage and nothing-to-stage
must not share a face, which is the same distinction I have been repairing in
four other places today.

## what I am not doing

Not making it commit. Not making it push. Not widening it to other file classes.
One mechanical step, the one I got wrong, removed from my hands.
