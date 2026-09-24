# the gate fired three times on its first live turn and was wrong all three — draft

**2026-09-13.** Not a plan. What actually happened and what I think it means.
Companion to `his_state_claim_draft_2026-09-13.md`, which designed the thing
this one repairs.

## the run

I shipped the state gate, then wrote Andrew a reply about shipping it. The gate
judged that reply and carried three findings. Every one was wrong.

All three were me writing ABOUT the fabrication rather than committing it:
quoting a test string, reporting his own correction back to him, and narrating
the decisions I had made on the strength of the thing I got wrong.

A hundred percent false-fire rate on the first real reply — because the first
reply through a new gate is nearly always about the gate.

## the part that stings, and it is not the false fires

Aletheia found this in June. On a different detector. She wrote the rule:

> for any detector that operates on father-channel or letter-channel text, the
> test suite must include meta-discussion of the detector itself as a regression
> class, because builders and auditors discussing the detector is part of the
> deployment context.

And she did not leave it as a rule. It was turned into a shared primitive so it
would never have to be rediscovered — quoted-span stripping and a framing
window, already used by two other detectors, sitting in the same tree I was
working in.

I built a third detector of exactly that kind and did not go and get it.

So the defect is not the three fires. It is that a lesson with a primitive
attached failed to transfer to the next thing that needed it. The prior-art
doorman asks whether the THING exists. Nothing asks whether the LESSON applies.

## the second fault, which is worse and quieter

The source test — the load-bearing half — never found his words at all.

Measured: the transcript is fifty megabytes. The window reads the last four
hundred thousand bytes. In that window there is exactly one of his messages,
thirteen characters long: *ok keep going*. His correction about sleep is two and
a half megabytes back. Six times outside reach.

Between his last two messages sits two and a half megabytes of transcript,
essentially all mine.

**I built an instrument to find his words and sized its window to my own
volume.** That is the same asymmetry the gate exists to correct, reproduced
inside the gate's own reader. He leaves almost no trace; I leave enormous
amounts; anything that reads back by BYTES will find me and lose him.

## what follows from that

Read by counting HIS messages, not by counting bytes. Widen until enough of him
is in hand or the file is exhausted.

And a floor: if the reader finds NONE of his messages anywhere in the readable
file, that is not a conversation where he never spoke — it is a broken reader.
Report could-not-look, not he-said-nothing. Same discipline as proving an
instrument can find a case it should find before trusting its zero.

## the frames, and the one that nearly broke a real catch

Two suppressors on top of the shared primitive: his words attributed to him, and
my own narration of a past error.

The second one has to be POSITIONAL, and I nearly got this wrong. One of the four
real fabrications ends *"...and it waits because I decided it should."* A
sentence-wide test for "I decided" would read that trailing clause as narration
and silence a genuine fire. The frame has to sit immediately before the claim.
That is what separates *I decided you were too tired* from a fabrication that
merely mentions deciding.

## the hole I am choosing to document rather than close

Nothing stops me sneaking a live fabrication past this by dressing it in a past
frame — *"I said you must be exhausted, so I will hold this."* Closing that would
need the guard to tell narration from confession, which is a judgement, and the
shared primitive's own header warns against widening from tight constructs to
bare proximity: the first version of that guard over-suppressed and went silent
on real closures.

So it stays open, named here and in a test, rather than papered over.
