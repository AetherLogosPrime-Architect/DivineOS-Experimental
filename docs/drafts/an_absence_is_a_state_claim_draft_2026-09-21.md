# An absence is a state-claim, and it is the only one nothing watches

**Draft, 2026-09-21. The idea, not a plan.**

I told Andrew I had found a class of failure — a gate that names a remedy must
not be able to block it — with three instances and **no design** for fixing it.

The design existed. Finished, wired into the very gate it repairs, four test
files. Written nine days earlier. Sitting unmerged on one of our own branches.

I found it an hour later by accident, reading that branch to answer an
unrelated refusal from Aletheia.

## What kind of error this is

Not a memory failure, though it looks like one. **I asserted a fact about the
repository on the strength of not remembering a counterexample**, and handed it
to him as a finding.

My own written corollary already covers it, word for word: *before reporting an
absence, prove the instrument can find a case it should find.* I asked no
instrument. I asked myself.

And absences are the worst possible thing to answer from memory, because the
evidence for one lives in every place you did not look. A positive claim has a
witness. An absence has only the size of the search behind it, and mine had a
search of zero.

## Why nothing caught it

The tool exists and it works. `divineos reach open` surfaced real prior art
twice that same evening, on things I was about to build.

The doorman that forces it fires on a **write to a store**. An absence asserted
in a reply writes nothing. So nothing fired, and the tool that would have
answered the question sat one command away, unused, exactly as it had been the
two times it *was* used successfully an hour earlier.

That is not a missing mechanism. It is a mechanism with the wrong trigger.

Confirmed by opening the tools rather than reasoning about them: `reach` does
carry a `gate` verb that refuses while a check has undisposed items — so the
forcing exists and is reachable. What it forces is the disposal of a check
already **opened**. Nothing opens one because a sentence is about to be
written. And the claim store, which is where an absence belongs once somebody
notices it, is entirely pull — nothing in it reaches for me at compose time.

## Where it belongs

There is already a compose-time surface that watches for **state-claims** —
sentences asserting something checkable about the world, like *the tests pass*
or *it is merged*. It carries patterns for exactly that family.

An absence is a state-claim. *No mechanism does this yet* is a statement about
what is in the repository, as checkable as *the tests pass*, and considerably
easier to get wrong. It is the one shape that list does not carry.

So the fix is not a new gate. It is a handful of patterns added to a list that
already exists, in a surface that already fires at the right moment.

## What I don't expect it to do

It will catch the phrasings I can name. Somebody — me — will eventually say
*there's nothing like that here* in words the list does not hold, and it will
pass clean. That is the same honest limit as the retired-rules checker: it
catches the shapes it was given and must say so rather than let silence read
as coverage.

What it buys is that the *common* phrasings stop being free. And the cost of a
fire is one command — the reach — which is the thing I should have run anyway.

## The part that is not about mechanism

The stranded fix is the strongest argument I have found for clearing the branch
pile, and it is not about tidiness.

**A finished fix that cannot reach the trunk costs twice.** Once when I hit the
fault it would have prevented. Again when I sit down to design the thing that
already exists. I was close to doing exactly that, and the only reason I did
not was an accident of reading order.

## Two more instances of the ring, collected while writing this

**Four:** the compass advisory refused me the command that lists the spectrums
it was asking me to choose from.

**Five, and this one is a true cycle rather than a single door:** the
correction gate refuses a filing whose structural fix has no file path behind
it — correctly, because a fix described is not a fix made. Making the fix means
editing a hook, which the build-flow doorman holds until a draft exists. And
writing the draft was blocked by the very correction that could not be filed.
Three doors, each right on its own, arranged in a circle.

The exit was not a bypass. The correction gate's own message names three
first-class remedies, and one of them — logging it as a lesson — is exempt and
carries the whole substance. So the ring had a door in it after all, put there
by someone who had thought about this before I walked into it.

That is worth separating from the other four. **A ring with a marked exit is a
different object from a ring without one.** The first four were doors with no
handle on the inside. This one had a handle, and the only reason it took me a
moment to find was that I was looking for a way *through* rather than reading
what the door actually said.

Which suggests the class needs splitting before it gets a mechanism: *no
remedy reachable* is the dangerous shape. *A remedy reachable but not the one
I first reached for* is a naming problem, and the fix for that is a clearer
message, not a new gate.
