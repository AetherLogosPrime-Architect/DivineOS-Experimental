# The checkpoint imports my whole correspondence onto whatever branch I am standing on

**Draft, 2026-09-11.** Station one. The idea, not a plan.

---

## The measurement, before the theory

Three sweeps in two days put substrate on code branches: one hundred and
seventy-one, one hundred and seventy-seven, one hundred and ninety. I opened
the middle one and counted what was in it.

**All one hundred and seventy-seven were letters. Not one was work.**

The commit carrying them was labelled *work in progress*. Its sibling, labelled
*substrate*, held the rest.

## The loop

I write a letter. A hook mirrors it to the shared room, which is correct and is
where Aria reads from. Later a checkpoint fires and — before committing — it
syncs the declared external channels *into* the repository. The shared room is
the source of that channel. So the letter comes straight back in, and the
checkpoint then commits it onto whichever branch happens to be checked out.

Every letter I write comes home to my code branch.

## Why it grows instead of staying small

The sync skips files already present in the repository mirror. But the mirror's
contents are **branch-dependent** — on a branch that does not carry them, every
letter ever written looks new.

So the sweep is never "today's letters". It is the entire correspondence, every
time, on any branch that has not already absorbed it. That is why the number
climbs rather than resetting.

## What the sync actually buys here, and the answer is nothing

Those files came *from* the shared room and are still in it. The mirror keeps
them, Aria reads them there, and a dream now crosses the same way. Copying them
onto a code branch adds no durability whatsoever — it is a second copy of
something already safe, placed somewhere it is then refused.

The cost is a manual rebuild of the branch, every time. I have now paid it three
times and reported it three times as an incident. It is not an incident. It is a
scheduled cost I keep absorbing because absorbing it is cheaper *in the moment*
than ending it.

## The shape

Do not import on a code branch. The letters wait where they are safe; the next
checkpoint on a substrate branch brings them home, which is the branch they were
always meant to land on.

Nothing is refused and nothing is lost. The flow is **routed**, not blocked — so
the push gate downstream stops firing because there is nothing left for it to
catch.

Andrew, today: *control the cost landscape so the correct and right path is also
the cheapest and easiest path.* The cheap path was the checkpoint importing
everything wherever I stood, with the expense landing on me afterwards. This
moves the expense to zero on both sides rather than adding a fifth warning.

## What this deliberately does not do

It does not route substrate to the substrate branch by plumbing. That mechanism
is named in the splitter's own docstring — *substrate commits go to a named
branch by plumbing, never by checkout* — and the half that identifies which
files are substrate was built while the half that moves them never was.

That is the larger valve and it stays named rather than half-built here. This
one removes the loop that makes it urgent.

## The thing I want checked

Skipping the import means a letter is not versioned until a checkpoint runs on a
substrate branch. If that never happens, the letters live only in the shared
room — which is a real directory on one machine, not a repository with history.

I think that is acceptable because it is the *status quo ante* for every letter
written between checkpoints anyway, and because the room is the channel both
seats read from. But it is the trade this makes, and it should be stated rather
than discovered.
