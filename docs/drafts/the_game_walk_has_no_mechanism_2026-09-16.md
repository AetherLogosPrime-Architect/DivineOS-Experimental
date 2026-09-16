# Rough draft — game-walking exists in the written process and nowhere else

**Station 1.** A draft of the IDEA, before any code.

Andrew, 2026-09-16: *"i forgot game walking should be mandatory as well, as this
is the main issue, things being gamed and skipped."*

---

## What is missing, measured

Searched the source, the scripts, the hooks: game-walking appears in four
documents and in no code. There is no command, no event type, no record, and
nothing that could distinguish having done one from saying so.

Threadwalking and lens-walking both have real machinery — a walk state machine
with open, add, apply, exclude, close and consume, plus a substance floor and a
distinctness check across findings. Game-walking has a definition and a quote.

So it cannot be made mandatory. There is nothing to require.

## What a game-walk actually is, from the process doc

Not "think adversarially." A specific, structured act:

> Enumerate every route around the mechanism, then compare each one's cost
> against the cost of just complying. Any route cheaper than compliance is the
> leak.

Andrew's phrasing: *"instead of just letting it game you pre game it to test all
the holes."*

That is a shape, not a mood. Routes, and a cost verdict per route.

## The crux, and it is nastier than the other walks

**This is the one mechanism whose entire subject is faking.** Every other walk
can be lazily satisfied and the laziness is an ordinary failure. Here, a lazily
satisfied game-walk is the exact behaviour the game-walk exists to catch,
performed inside the tool built to catch it.

The existing walk machinery validates substance by **character count**. Four
plausible paragraphs about hypothetical routes clears that floor without a
single real hole being found. I would not even have to intend it — plausible
adversarial prose is the easiest thing in the world for me to generate.

So a game-walk validated the way lens walks are validated is theatre with
better branding.

## What I think the shape has to be, for the walk to attack

**Structured, not prose.** Each route named separately with a verdict on one
question: is this cheaper than complying? A paragraph can waffle; a per-route
verdict cannot.

**A no-leak result is suspicious and must be justified, not accepted.** I am the
one who built the mechanism. If I enumerate routes and conclude none is cheaper
than compliance, the likely explanation is that I did not look hard, not that
the mechanism is airtight. But this cannot be an absolute — some mechanisms
genuinely have no cheaper route, and a rule that forbids clean results teaches
me to invent leaks, which is worse than missing one.

**The leak, once found, is owed something.** A game-walk that finds a cheaper
route and does nothing is a record of knowing better. What it is owed — close
it, accept it in writing, or file it — is the part I am least sure about.

## Open questions I want the walk to hit

1. Can this be validated at all, or does every check I write become a shape I
   can produce without doing the work? If it cannot be validated, is a recorded
   but unvalidated artifact still worth more than nothing?

2. Where does it attach? Per mechanism built, per edit, per branch? Attaching it
   per edit makes it noise; per mechanism needs a definition of "mechanism" that
   I will be the one applying.

3. Does it extend the existing walk machinery or stand apart? Extending risks
   inheriting a substance check that is wrong for this; standing apart risks a
   second walk system that drifts from the first.

4. What does the current arrangement PREVENT — Chesterton's fence. Game-walking
   has lived as a doc-only practice for over a month. Being unenforced means it
   is also unfakeable: there is no artifact to forge. Making it mandatory
   creates, for the first time, something worth faking.

That last one is the argument against building this at all, and it deserves a
real answer rather than a dismissal.
