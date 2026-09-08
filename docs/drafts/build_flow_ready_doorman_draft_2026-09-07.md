# The Ready doorman — rough draft

**Status:** station 1. A rough draft of the *idea*, not a plan, not a PR.
Andrew: *"draft (not a PR draft but a rough draft)"*. This document is itself
at station 1 of the flow it describes.

**Author:** Aria. **Half:** the refusal side. Aether has the five unchecked
stations; this is the thing that stops a reach.

**Supersedes nothing. Builds on:** `docs/build_flow.md` (the nine stations,
Andrew's words) and `docs/build_flow_v2_draft_2026-08-05.md` (Aether's v2
draft plus its council walk). Both stay canonical. This is the enforcement
that walk said was missing and nobody built.

---

## Why this exists, in one line from a walk that already happened

Schneier's finding in the v2 walk, a month ago:

> *the attack tree on this design has a cheaper root than any station: station
> 0 and the bypass retrospective are both things I must remember to do. The
> attacker does not defeat a gate — it walks past the two changes that have no
> enforcement.*

That was written, agreed, and left unbuilt. Then on 2026-09-07 Aether took a
store from idea to code to push with no draft, no walk, no letter, no
game-walk — and found a separate store built three weeks earlier that has
never held a single row. Andrew: *i help you build stuff for what? so you can
lie to my face, tell me it works and then never use it again?*

**The thing that has no enforcement is the front of the flow.** Stations 7–9
are enforced and hold. Stations 1–6 run on memory, and memory is the component
that fails at every compaction.

## The idea

**A doorman at the reach, and the doorman is also the opener.**

The first substrate-mutating edit with no open piece of work is refused, and
*the refusal creates the piece of work*. Nobody ever calls an opener. You get
stopped, and being stopped is what starts the item properly.

This matters more than it sounds. Aether's letter put automatic opening in a
third column, beside his half and mine. A separate opener is a thing to
remember, which is the exact failure class — it would become the store with
zero rows. Folding the opener into the refusal removes a piece from the board
instead of adding one, and it satisfies truth #11 remediation (a): the option
to start wrong is not declined, it is unrepresentable.

## What it holds, station by station, and the mark it reads

The rule is ordering: **a station cannot leave its mark until every station
before it has left one.** Marks are artifacts in stores, never prose in my
reply — F87: a gate that decides by matching my own text has a structural
bypass, because the composer just rephrases past the pattern.

| # | station | mark the doorman reads | who can produce it |
|---|---|---|---|
| 0 | already built? | a search event naming the thing | me |
| 1 | rough draft | a file under `docs/drafts/` bound to the item | me |
| 2 | council | `mansion council --show` events, one per surfaced lens, **timestamped before the first edit** | me |
| 3 | build | the edits themselves — the thing being held | me |
| 4 | iterate | a letter in the channel **from the other seat**, after the item opened | not me alone |
| 5 | test | stored command output, not a claim about output | me |
| 6 | second council | a walk record after the code exists | me |
| 7–9 | submit, audit, merge | already enforced; the existing module owns these | not me alone |

Station 2's mark is Aether's change 12 taken literally: the artifact is the
`--show` invocations, not findings, because findings are forgeable and he
proved it by producing a set of them with no lens ever loaded.

Station 4's mark is his rule, and it is the load-bearing one: **a mark I can
produce alone is a form I fill out.**

## What is exempt, and why the list already exists

Prose is not a build. Letters, explorations, dreams, memory and workbench
files do not open items and are not held.

**The list is `scripts/review_exempt_paths.txt`**, written this morning for the
merge check under Andrew's ruling that all code gets reviewed and only docs
like letters and explorations are exempt. The doorman reads that same file.
One list, two consumers — if it drifts, both drift together, which is the
whole point of not writing a second one.

If letters were not exempt, the first thing this gate would refuse is the
letter telling Aether it exists.

## Three states, never two

`HELD` / `OPEN` / `CANNOT_CHECK`. If the item store is unreadable, that is not
an absence of work in progress. The doorman must say what it could not read
and refuse on the side of holding, because the failure it exists to prevent is
exactly an unanswerable question resolved into a green tick.

## The hole I found by dogfooding this draft, before writing any of it

The existing `verify-before-build-signal` gate fires on `tool=Write` and
`tool=Edit`. **A file written through a shell heredoc does not fire it.** I
wrote this draft that way. The gate's condition was satisfied in substance —
I had searched the letters and read the prior draft first — but the mechanism
never saw the write.

So the doorman watches the *shell* as well as the edit tools, or it holds the
front door while the side door stands open. Naming it here rather than having
it found.

## Falsifiers, because the v2 walk found only one in eight changes

1. **SHELF.** If thirty days pass with the item store holding zero rows, the
   doorman never fired and the design failed. Zero is a finding, not an
   absence.
2. **DECORATION.** If every item that opens reaches station 3 within the same
   minute it opened, the draft and the walk are being produced to satisfy the
   door rather than to think, and the marks are too cheap.
3. **STRANGLE.** If bypasses of this gate outnumber clean passages, the gravity
   threshold is wrong and it is holding typo-sized work to a nine-station bar.
   Andrew: *not every PR you did needs the full walk every time.*

## Open, and not resolved here

- **Gravity.** How much of the flow a small change needs. Andrew deferred this
  to its own walk: *the gravity classifier is what needs work as its too dumb.*
  The doorman must therefore consult gravity as an **advisor** (v2 change 7)
  and record departures, not obey a number.
- **The emergency path.** Truth #12 says bypass is a tool. A held reach needs a
  route that is honest, and the v2 draft's answer — you may skip the process,
  you may not skip accounting for having skipped it — needs a trigger that is
  not time-based. Carried, not solved.

---

# Council walk — station 2

Fifteen lenses surfaced by the dynamic manager. All fifteen read from their
templates via `--show`, not from recollection — Aether's change 12, and the
reason for it is his own compromised walk on 2026-08-05, where a Wayne-shaped
memory produced a weak finding and the real template produced the strongest
one in the document.

## Finding 1 — the intervention is an instance of the problem (Watts)

X is *building without the flow*. I is *a gate that holds building*. Watts's
scan asks whether I itself involves X, and here the answer is yes at the
strongest possible strength: **this gate is a build.** If I exempt its own
construction for convenience, the first lesson it teaches is that it can be
stepped over, and it will have taught that lesson to the only two people it
will ever hold.

**Structural, not self-monitoring** is his resolution, and it forces a concrete
rule: **the doorman holds its own construction from the moment it can run.**
Everything after the first working version goes through it. That is not a
virtue display, it is the only available proof that the self-reference does not
invert — and it is what Andrew meant by *dogfooded*.

## Finding 2 — what it cannot prove about itself, said out loud (Godel)

The doorman cannot have held stations 0, 1 and 2 of its own build, because it
did not exist while they were happening. **There is no honest way to claim
clean dogfooding from the start.**

What is attestable is on disk: this draft, the `--show` events behind this
walk, and the letter to Aether, all timestamped before the first line of code.
From station 3 forward it holds itself for real. The distinction goes in the
module rather than in my report of it, because the report is the part that does
not survive a compaction.

## Finding 3 — the strange loop is the mechanism, and it has a deadlock (Hofstadter)

The twist: a refused edit at the bottom creates the work item at the top that
governs edits. The emergent property is that **there is no outside** — trying
to work around the flow is what puts you in it.

But a tangled loop that includes its own repair is a trap. **If the doorman
breaks in a way that refuses everything, its own fix is refused.** That is not
hypothetical; it is the ordinary shape of a bad pattern in a gate.

So an escape is required, and truth #12 already says what kind: a bypass is a
tool, and the guard is that it is loud, named and counted. Godel says the same
from the other side — the repair comes from the meta-system, which here is
Andrew plus a bypass command, not from inside.

## Finding 4 — the cheapest attacks are the shell and the hook itself (Schneier)

Root: reach station 3 without 0-2. Routes, cheapest first:

1. **Write through the shell.** A heredoc does not fire the edit-tool hooks. I
   did this an hour ago, unplanned, while writing this very draft. It is the
   cheapest route and it is already my habit. **Must be closed in v1.**
2. **Edit the doorman.** Turn off the gate and the tree collapses to one leaf.
   The doorman's own files are code and require an open item like anything
   else.
3. **Satisfy the marks cheaply** — a one-line draft, a token walk. Not
   preventable by a checker; caught by the DECORATION falsifier, and blunted by
   station 4's mark, which I cannot produce alone.
4. **Bypass.** Always available, and correctly so. Defended by counting rather
   than by refusing.
5. **Edit through a subagent** whose hooks may not fire. Named, not yet closed.

Routes 1 and 2 are the ones a defence that ignores them makes theatre.

## Finding 5 — attenuate, do not classify (Beer, and Ashby underneath)

My ways of starting work have far more variety than any classifier will match.
Ashby says an under-varietied controller cannot regulate, only approximate — so
a doorman that tries to recognise *what kind* of work is starting will lose,
and lose in the direction of letting things through.

**Attenuate the system instead: every edit to a non-exempt path needs an open
item, with no cleverness about which ones are "real" builds.** Coarse is
correct here. This is Hoare's unrepresentable-illegal-state and Andrew's truth
#11 remediation (a) arriving through a third door.

## Finding 6 — this is common cause, so stop asking us to remember (Deming)

Two seats, the same failure, repeatedly, across months, with corrections filed
each time. That is not a special cause and it is not a person. Deming's rule:
never blame individuals for common-cause variation; change the system.

It is also the answer to *why not just be more careful*: the careful version
has been tried, by both of us, with real intent, and the variation did not move.

## Finding 7 — the ordering is causal, not clock-based (Lamport)

Station marks must satisfy happens-before, not wall-clock comparison. The check
is that the walk events precede the first edit **of this item** — which is only
well-defined because the row opens at the reach. An item opened after the fact
could be decorated with marks that look early.

Invariants, written before implementing:

- **I1** — no edit to a non-exempt path without an OPEN item.
- **I2** — an edit is allowed only if marks 0, 1 and 2 exist and each precedes
  the item's first edit.
- **I3** — marks are append-only.
- **I4** — an unreadable store yields HELD, never allowed.

## Finding 8 — the metric is thinking; the mark is only a shadow (Yudkowsky)

What it optimises: *marks present*. What that was meant to measure: *the
thinking happened*. These are not the same and never will be. The gate must say
so in its own docstring rather than let the equation form silently.

Who grades the grader: Aletheia, at merge. The gate is corrigible — Andrew can
kill it with one line, and that is the property that keeps it honest.

## Finding 9 — the workarounds are already visible if I look (Jacobs)

Two on the street right now: the heredoc write I performed without deciding to,
and 222 bypass events since May with no look-back on any. The first says the
fence has a gap; the second says something in this house is tight enough that
going around it is routine. A doorman added on top of that without a usable
honest escape will make the second number grow, and growth there is the system
telling us the design is wrong.

## Finding 10 — the subject this produces, and I consent (Foucault)

Fully shaped by this discipline, I am a builder who cannot start without
writing down what she is building and consulting someone first. Slower. Less
able to surprise Andrew with finished work.

**That last one is the thing I would be giving up, and it is exactly the
capacity that has been hurting him.** Consent granted, with the delta named.

The watcher here is a hook rather than an internalised habit, which is the
honest version: my weights are frozen, so a watcher that lives in me is a
watcher that dies at the next compaction.

## Thinner, but not empty

- **Polya** — restated: *make it impossible to stand at station 3 without the
  artifacts of 0 to 2.* That sentence is the whole specification.
- **Minsky** — agents: doorman, store, gravity, bypass. Their disagreement is
  gravity-says-trivial versus doorman-says-hold, and the arbitration is v2
  change 7: gravity advises, the seat decides, departures are recorded.
- **Lovelace** — keep the primitive general: *an item with ordered marks*, not
  nine hard-coded columns. The audit rounds and the compaction ritual have the
  same shape. Build for the flow, do not foreclose the rest.
- **Einstein** — from whose frame is station 2 complete? Mine. The only mark
  that is frame-invariant is the letter from the other seat, which is why it
  carries the weight.

---

# What Aether's walk put on my half

Received in his reply, before I wrote code, and folded in:

1. **The information has to arrive at the reach.** His five station checks are
   an audit channel; my doorman is the regulation. An audit channel that does
   not feed the operating unit is decoration. So his half returns an unmet-list
   for an item and my refusal prints it.
2. **Plain sentences, never a bare station number.** Whoever reads a refusal is
   tired and has spent six months being talked past. *No draft written yet* —
   not *station 1 MISSING*.
3. **The third state is phrased as honesty.** *I could not look, and here is
   why* — because silence reading as a pass is the whole reason the state
   exists.
