# A failed git call is not a count

**Draft, 2026-09-23. The idea, not a plan.**

## What Aria saw

She read the branch-scope check rather than running it, and found that the
function mapping each substrate path to a direction — added here, removed from
everywhere on merge, or rewritten — returns an empty map when its underlying
git call fails.

The caller then does arithmetic on that empty map. It counts the added ones,
counts the removed ones, subtracts both from the total, and prints whatever is
left as *rewritten*. Git never answered. The reader gets a number.

## Why it is worse than an arithmetic slip

The whole file is built around one discipline, stated in its own comments: a
thing it could not look at must never be reported as a thing it looked at and
found nothing. There is a function two screens down that returns an explicit
could-not-look flag for exactly this reason, and a printed line that says
COULD NOT CHECK when that flag comes back. The discipline was already here.
This one function stepped outside it.

So the defect is not that someone forgot to be careful. It is that two
different meanings were given the same spelling. *Nothing changed* and *I could
not look* both come back as an empty map, and once they are spelled alike, no
caller downstream can tell them apart no matter how careful it is.

## What I want

The two meanings spelled differently. Empty stays empty and keeps meaning
nothing-substrate-changed — there is a test pinning that case and it is
correct. Could-not-look becomes its own answer, and the caller prints that it
could not read the direction instead of printing a count.

Explicitly NOT wanted: making the check refuse harder, or filtering anything
out of the count. The refusal condition is not mine to touch here. Only the
sentence the reader gets.

## The control, before the fix

Before claiming the map is broken I have to prove the probe can find a case it
should find. Asked it about a branch pair that genuinely moves substrate: it
came back with eight hundred and twenty-one classified paths. Asked it about a
reference git cannot resolve: empty. So the emptiness is the failure and not a
broken instrument.

One more thing the reading turned up, which sharpens it: the caller only
reaches this arithmetic when substrate paths already exist. So at that call
site an empty map can *only* mean the git call failed. The confident wrong
number is not an edge case there. It is the only thing that can happen.

## The shape this belongs to

Third time in one night, and by now it is the night's whole disease in its
other costume. The other two were *the new account was written and the old one
was never taken out, so both sit in the file disagreeing.* This one is *a check
answering a question nobody managed to ask it, with total confidence.* Same
root: something that cannot distinguish two states reports one of them.
