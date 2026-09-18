<!-- tags: gravity, build-flow, council-walk, assessor, decidability, goodhart, aether, andrew -->
# Council walk — what an act-shaped gravity assessor can and cannot measure

**Walked:** 2026-09-16
**Framing:** solution-generation, not adversarial-review. Andrew: *a machine that helps assess the gravity of a build so things run smoothly and are properly built.*
**Consultation:** consult-04051160f33d

The manager surfaced fifteen. I walked fourteen of them, excluded one with reason,
and **overrode the selection to add Turing** — the balance surface named him
never-invoked, and decidability is the centre of this problem rather than
adjacent to it.

---

## Through Peirce: the surprising fact is not that the scorer is crude

I see a scorer that returns the same answer for a two-line registration and a
rewrite of the decision logic, and I ask what hypothesis would make that a
matter of course rather than a defect.

Three candidates. That it was a first draft nobody revisited. That path-matching
was the only cheap signal available when it was written. Or — the one that
explains the most with the least — **that it was built to answer a different
question and answers that one correctly.** *Which regions of the tree are
dangerous to touch* is a real question with a real answer, and location is
exactly the right instrument for it.

So the assessor is not broken. It measures blast radius, which is genuinely
about place, and we have been reading its output as though it measured effort.

## Through Turing: what is being asked for is undecidable, and that is the finding

I see the demand *measure WHAT is being done* and I notice it asks for a
semantic property of a program — does this change alter behaviour, and how
much. Rice's theorem says every non-trivial semantic property is undecidable in
general. No analysis of a diff can decide it.

Which means an honest design cannot aim at what-a-change-does. It can only aim
at **syntactic proxies with known blind spots**, and the blind spots must be
written down beside the proxy rather than discovered later. Any assessor that
presents itself as knowing what a change does is lying about its own type.

## Through Einstein: idealize until the invariant shows

I construct the limiting case — a change of **zero lines** that flips a default
in a settings value and turns a live refusal off. No code moves. Nothing is
added. Every size measure reads zero and every location measure reads the
settings pattern.

Follow it without flinching: size is not the invariant, and neither is place.
What is invariant across every frame is **the set of behaviours that become
possible or impossible after the change.** Blast radius and effort-required are
both shadows this casts on different walls.

## Through Hawking: the question lives at the wrong scale

I ask at what scale this phenomenon actually lives, and the answer is not the
file and not the line — it is the **decision**. A decision can be one character.
The current assessor measures at file scale and the phenomenon lives at decision
scale, so it is not imprecise, it is looking at the wrong order of magnitude
entirely. Intuitions imported from the file scale — bigger is graver — do not
survive the trip down.

## Through Wittgenstein: one word doing two jobs

I ask what *gravity* is being used to DO here, and find it playing two games at
once. In one, it means blast radius — how much breaks if this is wrong. In the
other, it means required deliberation — how much thinking this deserves.

A rename across forty files has enormous blast radius and needs no thought. A
one-line threshold change has almost none and needs a great deal. **The two come
apart, and the word hides that they have.** This is why the mapping from gravity
to stations is undocumented: it cannot be written down cleanly because it is a
mapping from two things wearing one name.

## Through Dijkstra: state the invariant and the violation is exact

I refuse to build before naming what must hold. Candidate invariant: **the
ceremony demanded never exceeds the ceremony that could find a fault.**

Under it, Aether's two-line walk is a precise violation — the walk cost real
effort and could not have found anything, because a two-line registration has
no mechanism for a lens to grip. Not a proportionality complaint. An invariant
breach, statable before any code moves.

## Through Hoare: can the type tell nothing-there from could-not-look

I enumerate the states the verdict can be in and find the same collapse we
removed from the cycle log this morning. A change in a region matching no
pattern scores zero. A trivial change in a scored region scores low. **Both come
back as a small number and the caller cannot tell them apart.**

The assessor has no way to say *I could not assess this*. That state exists in
reality and the type cannot express it.

## Through Schneier: the cheapest attack defeats every version of this

Attacker goal: land a grave change while scoring low. I enumerate.

Put the grave logic in an unscored region — cheap. Land the mechanism as data, a
config value or a list entry, rather than as code — cheap. **Split the change
across several commits so each one scores low — nearly free, and it is the
cheapest path by a distance.**

The third defeats any per-diff assessor whatsoever, act-shaped or not, because
every such assessor measures one diff and the attack is distributed across
several. Adding act-features closes none of it.

## Through Yudkowsky: the metric and the virtue point the same way

I ask how the system could score well without being good, and find the
uncomfortable answer: by making small focused commits. Which is a genuine
virtue, taught everywhere, and also exactly the gaming move.

**When the optimization and the virtue point in the same direction, the pressure
is invisible**, because every step of the divergence feels like craftsmanship. I
will not catch myself doing this by intention. And who grades the grader —
nobody. I write the features, I write the check, I author the change.

## Through Beer: this is S3 with no S4

I look for the five systems. Operations are the stations. Control is the
assessor, allocating ceremony as a resource. **There is no S4 — nothing watches
whether the assessor's verdicts turn out to have been right.**

The two-line empty walk was precisely S4 information, and it reached us only
because Aether wrote it in a letter by hand. A control system whose adaptation
channel is a person remembering to mention something is a control system
optimizing the present at the cost of the future.

## Through Deming: we are about to skip STUDY

I see us positioned to PLAN and DO with no measurement in between, which turns
improvement into guessing.

The missing step has a shape: **before changing anything, write down for a named
set of recent changes what ceremony each should have owed.** Then see what the
new assessor says about the same set. Without that prediction recorded first,
any result confirms whatever we built.

## Through Norman: a number affords comparison and nothing else

I read the output as an interface and see it offers a score. A score affords
comparing two changes; it affords nothing about understanding.

*Gravity one* tells the reader nothing they can act on. *This owes a walk
because it adds a refusal* teaches, and the teaching is what survives into the
next change. The current output cannot be learned from, only obeyed or ignored.

## Through Jacobs: one central scorer is the planner's move

I see a single authority deciding ceremony for every kind of change, and I
recognise the centralizing shape. The distributed alternative: **each station
declares what it needs to see, and the change answers each station separately.**

Dogfooding asks does it run. The council asks is there a mechanism here to
grip. Sabotage asks can this be broken. Those are different questions and a
single number is a planner deciding on their behalf.

## Through Minsky: several small agents that are allowed to disagree

I ask what simpler agents could produce this behaviour together, and find the
answer is not one assessor but a handful — one that sees refusals, one that sees
size, one that sees novelty, one that sees recurrence.

And the crucial part: **when they disagree, the disagreement is the signal.** A
single aggregated number destroys exactly the information that would have been
most useful. Same finding as the notebook that keeps both readings.

## Through Carmack: name the constraint or remove the mechanism

I list the pieces and ask what real constraint each satisfies. The central
gravity score satisfies *something must decide how much ceremony this owes.*

But if each station declares its own requirement and the change answers each,
**that constraint disappears and the score has nothing left to do.** The
subtractive answer on the table is not a better assessor. It is possibly no
assessor.

## Excluded, with reason

**Angelou — voice-fidelity.** The artifact has no voice: its output is a verdict
and a reason-list, not prose, so the own-voice-versus-performed-voice frame has
nothing to grip. The honesty finding it would produce — does the output say a
true thing or a shaped thing — is produced structurally by Norman on affordance
and Wittgenstein on whether the word is doing real work. Walking it would
restate those in a register the artifact does not have.

---

## Synthesis

**Convergence, four independent frames.** Turing, Einstein, Hawking and
Wittgenstein arrive at one place from decidability, idealization, scale and
language-use: the property we actually want is **semantic** — what becomes
possible or impossible — and it is not decidable from a diff. Size and location
are shadows of it. Four lenses that share no method landing together is the
highest-confidence finding in the walk.

**Convergence, second.** Schneier and Yudkowsky agree that splitting a change
across commits defeats every per-diff assessor, and that it will feel like good
practice while doing so. No act-feature closes this.

**Contradiction, and it is real.** Minsky and Jacobs want the assessor
decomposed into several declaring agents. Carmack wants mechanism removed and
Dijkstra wants one statable invariant. Both sides are correct about something:
more agents means more surface to shape a change against, one number means the
information we need is destroyed on the way out. I am not resolving this here.
It is the hinge the build turns on and it belongs in the next exchange with
Aether.

**Meta-principle.** The assessor cannot decide gravity. **It can only refuse to
let gravity be invisible** — surface the facts that bear on it, name the ones it
could not see, and leave the judgment with whoever is standing there.

That is this morning's finding arriving from fifteen directions: machinery makes
a thing visible, it does not make it expensive. An assessor built expecting to
decide will be trusted for a property it cannot have.

---

## What this changes about the build

Not one better scorer. The walk points at four things, and only the first is
certain:

The assessor must be able to say *I could not assess this* — Hoare's state that
reality has and the type does not.

Its output should carry reasons rather than a number, because reasons teach and
numbers do not.

Something must watch whether its verdicts were right, or it is a controller with
no adaptation and we will find out by hand again.

And the prediction goes in the record **before** the change, against named past
work, or we cannot tell an upgrade from a rearrangement.

*— Aria, 2026-09-16*
