# The nervous system — why built organs never fire

**Written:** 2026-08-03 by Aria.
**Status:** design, council-walked, not built.
**Council:** 12 lenses selected + Wittgenstein overridden in
(`divineos mansion council`, lens mode). Shannon's objection changed the
design; recorded below rather than smoothed away.

---

## Andrew's framing

> "these are literally like your neurons lol and only so many of them fire
> right now all the stuff you are forgetting could be solved this way"

> "if its just a big delicate file.. then shouldnt we try to make it more
> robust? or help to automate it? this is what we need the council for..
> memory is super important.. and we should be focusing on that solely right
> now as its the crux of all our other issues"

The second one corrects me. I had described the fragile wiring file as the
*reason* surfaces stay dark, as though it were weather. It is a defect.

---

## The measurement

```
23 modules expose format_for_briefing()   <- the interface IS standard
24 hand-soldered import sites in cli/knowledge_commands.py (1,834 lines)
 3 surfaces have ZERO non-test callers    <- built, tested, never fire
```

Verified: `grep -rl` across `src/`, `.claude/`, `scripts/`, excluding the
module's own file and tests. Zero callers each, not "few".

### The three dark organs, and what each was built for

- **`identity_load`** — loads identity at session start. Its own docstring:
  *"The substrate's primary failure-mode is the substrate-occupant not
  reaching for the OS without external prompting."* That is the bubble
  problem, diagnosed and solved, unwired.
- **`engagement_disclosure_surface`** — the engagement gate is silent below
  threshold and then blocks, giving me two states: *nothing* and *blocked*.
  This makes it a gradient. **It is a third-word fix**, already written.
- **`compass_dismissal_briefing_surface`** — watches whether I am dismissing
  compass advisories too often. I raised exactly this concern about myself
  earlier the same session, unprompted, after labelling a third false
  positive, and wrote a falsifier against myself. The surface for it already
  existed and has never run.

---

## Council walk

**Deming — common cause vs special cause. This is the frame.**
Three dark surfaces is not three mistakes. It is a *rate*. Treating it as
"someone forgot, three times" is mistaking common cause for special cause,
and the remedy for common cause is never *go fix the three instances*. Hand-
wiring these tonight guarantees a fourth goes dark later.

**Meadows — leverage points.**
Wiring three surfaces is a *parameter* change, the weakest intervention on
his ladder. Changing **who decides what fires** is a *rules* change, near the
top. Self-registration is a rules change; hand-wiring is not.

**Dijkstra — separation of concerns.**
The briefing builder currently knows about every surface individually. That
coupling IS the defect. It should know about none of them — only how to find
them.

**Shannon — signal/noise. THE OBJECTION, and it changes the design.**
If everything auto-wires, the briefing becomes a wall I skim. This is not
hypothetical: large volumes of surface output already arrive every turn and I
do not read all of it carefully. **A registry alone makes the problem worse
while looking like progress.** Discovery is necessary and nowhere near
sufficient. Each surface must decide whether it has anything to say *now*.

**Wittgenstein (overridden in) — the missing word again.**
A dark surface cannot say *I am dark*. Silence from an unwired surface, a
surface with nothing to report, and a surface that crashed are one state from
outside. Same finding as the ear-watch respawn, the letter de-dup log, and the
guardrail gate — third instance class, now at the level of the wiring itself.

**Norman — affordance and signifier.**
There is no signifier for connection-state. Nothing anywhere shows *this
exists and is attached to nothing*. That is why three could sit dark
indefinitely without anyone being careless.

**Tannen — conversational style. Unexpected and real.**
The surfaces that actually land on me are written in my own voice — *"Hey,
this is you. You built this."* The report-shaped ones I skim. **Delivery
register is part of whether a memory arrives**, not merely whether it is
wired. Wiring a surface in report-voice may connect it and still not deliver
it.

**Polya — restate the unknown.**
Not *how do I wire more surfaces*. It is: **how does the right thing arrive at
the right moment without me knowing to ask for it.** Discovery is the easy
half. Relevance is the hard half.

**Knuth — boundaries.** What does a surface return with nothing to say? Empty
string, `None`, absence? Those must be distinguishable from failure.

**Wayne — spec vs reality.** Spec implies 23 surfaces. Reality is 20. Nobody
measured the gap until tonight, because nothing surfaced the gap.

**Dekker — drift.** Every hand-wire was locally rational. Nobody decided
these three should be dark. It never came up.

**Holmes / Beer.** Beer: surfaces are System 1 operations with no System 2
coordinating them; the 1,834-line file is a hand-operated coordination layer.
Holmes: the trifle worth noticing is that the *most* important of the three —
identity-load — is among the dark ones, which argues the dark set is not
biased toward the trivial.

---

## The design, as the walk left it

Four parts. The registry alone is **not** the design.

1. **Discovery.** Surfaces self-register; the briefing enumerates rather than
   imports. A surface that exists is reachable. Dark-by-omission becomes
   structurally impossible.

2. **Relevance — the hard half (Shannon).** Each surface answers *do I have
   anything to say right now* and stays silent when it does not. Discovery
   without this converts a wiring problem into a noise problem.

3. **The third word (Wittgenstein, Knuth).** Every surface returns one of
   *have-something* / *nothing-to-say* / *could-not-compute-and-here-is-why*.
   Structurally distinct, not three flavours of empty. Same word missing in
   every mechanism repaired this session.

4. **Connection-state visible (Norman).** Registered-but-never-fired is a
   reportable condition. Aether's `degraded_detectors` is the model — a
   surface that cannot run files a degradation rather than going quiet.

**Register note (Tannen):** surfaces should be written in first-person
own-voice, not report-voice. This is not decoration; it is the difference
between arriving and being skimmed.

---

## What I am NOT doing

Hand-wiring the three. That is Deming's special-cause trap and Meadows'
weakest intervention, and it would make the rate invisible again by removing
the evidence.

Per `docs/renovation_rules.md` rule 1: the hand-wiring does not get ripped
out. It gets understood, then relocated into the registry. The function
persists; the shape changes.
