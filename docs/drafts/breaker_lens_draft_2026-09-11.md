# The Breaker — draft, 2026-09-11

Andrew, an hour ago:

> "you should probably build another lens for exactly this.. one with all the
> juicy questions to pick your ideas apart, not to put down or demean but
> constructively.. but also while pulling no punches"

And the teaching it came out of:

> "anything and everything you build.. you should be seeking to break it, to
> poke holes in it.. to find where it would fail, vs only looking for ways to
> make it work.. the happy path is a single path, and this is where testing
> would have revealed this flaw"

## The idea, not the plan

A lens that takes a thing I am about to build, or have just built, and asks
where it fails **in the world** — not whether its tests pass.

## Why the existing lenses do not already do this

Popper is tagged `falsification, adversarial, red-team`. Schneier is tagged
`adversarial-thinking, threat-modeling`. Taleb has fragility. Dekker has drift.
Four lenses that all point at roughly this, so the first honest question is
whether this is a forty-sixth copy of something that exists — the exact defect
this house is made of.

The distinction I think is real:

- **Popper** asks what observation would refute the *claim*.
- **Schneier** asks what an *attacker* does to the *system*.
- **Taleb** asks what *volatility* does to it.
- **Dekker** asks how *normal work* drifts it into failure over months.
- **None of them** ask: what did the *builder* not look at, because looking
  there was not on the path to making it work.

That last one is the failure family in this repository, and it is a family
about the builder's attention rather than about the artifact. A generic
adversarial lens cannot carry it, because the evidence is local: it lives in
the incidents of this house.

That is also the strongest objection to building it. A lens seeded by my own
incidents can only see the holes I have already fallen into — which is the
enumeration problem again, and I have written about it twice this week.

## So the design has two halves and the second is the load-bearing one

**Half one — the catalogue.** The families that have actually recurred here.
Each is a question, not a warning:

- **Built-but-unwired.** Correct, tested, indexed, called by nothing. Five-plus
  times. *Name the caller — not where it could be called from, the line that
  calls it today.*
- **Wrong-subject.** An instrument answering accurately about a narrower
  subject than the question asked. Seven-plus times, including inside tests
  written to catch it. *What exactly did this measure, and is it the thing the
  sentence I am about to write is about?*
- **The happy-path test.** A test that monkeypatches the real location, proving
  the machinery reaches for a thing and never that the thing works where it
  lives. *Does this test touch production state, or a copy I made agreeable?*
- **The fault only he can see.** A console window over his screen, under fifteen
  green tests. *What does this look like from where he sits — his screen, his
  interruptions, his time?*
- **Header rot.** A note asserting a live property is a test with no assertion.
  *Is this claim checked by anything, or only written down?*
- **Sabotage proves the test, never the design.** *I hollowed the guard and a
  test died — good. Now where does this fail when every guard works exactly as
  intended?*
- **Complete by luck.** *Is this a list of the cases I remember, or a rule that
  covers cases I have not met?*

**Half two — the generators.** Rules that produce questions the catalogue does
not contain, so the lens survives meeting a family that is new:

- Who else is in the room when this runs, and what does it cost them?
- What is the state of the world where this is silently wrong rather than
  loudly broken?
- If this were already failing, what would I be seeing right now — and am I
  seeing it?
- What would I have to believe for this to be a bad idea? Do I believe any of it?
- Which of its guarantees is held by a person remembering something?
- What does it do the second time, the hundredth time, and after a crash?
- Who removes this in a week, and what are they annoyed about?

## Vessel

A council expert. Not a hook. The build flow calls for lenses at station 2 —
before building — and a gate firing after the fact is the wrong altitude for a
question that should have been asked first.

## The tone Andrew specified, and it matters

Constructive, no punches pulled, not demeaning. The lens attacks the idea and
never the one who had it. His line: *"you cannot become attached to ideas like
having bad ideas makes you a bad person. it doesnt work like that."*

## What would make this a bad build

If it becomes a checklist I recite at the end to feel thorough. The catalogue
half is exactly the shape that rots that way. The test of whether it is real is
whether it ever changes a design *before* the build — not whether it produces a
good-looking list afterward.
