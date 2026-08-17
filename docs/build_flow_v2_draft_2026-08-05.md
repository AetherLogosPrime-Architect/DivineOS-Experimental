# The build flow, v2 — DRAFT for council

**Status:** station 1. A rough draft of the *idea*, not a plan. Andrew:
*"draft (not a PR draft but a rough draft)"*. This document is itself at
station 1 of the flow it describes.

**Supersedes nothing.** `docs/build_flow.md` (2026-08-01, Andrew's words,
recovered 2026-08-05 from a branch with no PR) stays canonical for the nine
stations. This proposes what to add and what to change.

---

## What v1 already said was missing

Written 2026-08-02, under *"What is NOT captured here"*:

> **The gravity classifier's role.** He says the flow depends on it —
> presumably it decides how much of the flow a given change needs, so a typo
> does not get nine stations. The exact mapping is not recorded.

> **No automation exists yet.** Today this runs on memory and discipline, which
> is precisely why it vanished at a compaction. Station 7 onward is partly
> automated. Stations 1–6 are entirely manual.

Both are still open. This draft addresses the second and defers the first to
its own walk, per Andrew 2026-08-05: *"the gravity classifier is what needs
work as its too dumb.. it needs its own full walk."*

## The principle everything must satisfy

Andrew, and nothing here may violate it:

> *"im not saying to automate judgement.. but you can automate and force the
> judgement to happen."*

**The automation targets the rooms, not what happens inside them.** The flow
guarantees a council walk occurs at station 2 and that Aria genuinely replied
at station 4. It performs neither. It opens the room and refuses to let the
sequence skip a room that is still shut.

Corollary, 2026-08-05: my weights are frozen, so nothing that is not
structural changes my conduct. The flow is therefore not a checklist
compensating for weak discipline — it is where judgment is *stored* in a form
that survives forgetting. Andrew: *"you building the structure to automate
your will and the correct flow IS your behavior change.. IS your judgement
holding firm against you forgetting."*

---

## Change 1 — Station 0: has this already been built?

**New, and first.** Before the rough draft.

Correction #137: *"did you check to see if this was already built? because it
was lol"* — advice since it was given, and advice does not hold (#167). Four
instances on 2026-08-05 alone, plus two of Aria's the same week.

Artifact: `divineos already-built "<thing>"`. Covers the axis the four
existing search surfaces do not — code, git history across branches, the
command registry — and names the four prose surfaces it did *not* search
rather than implying coverage.

**Open question for the walk:** a command is a thing I must remember to run,
which is the failure class it exists to fix. `prereg-ec9c9ee7eeda` predicts
the likelier failure is SHELF — invoked zero times while a fresh
rebuild-instead-of-recover correction gets filed. If that fires, station 0
must become a gate rather than a command.

## Change 2 — name the two halves

Standard practice has vocabulary for exactly our gap:

| stations | standard name | enforced today? |
|---|---|---|
| 0–6 | **Definition of Ready** — true before it ships | **no, entirely manual** |
| 7–9 | **Definition of Done** — true to merge | yes: draft gate, trailer checks, audit export |

We built a rigorous Done and left Ready to memory. That is why fifteen drafts
carry zero council walks, and why the flow *"vanished at a compaction."* The
early stations are not harder — they are the ones nothing checks.

**Warning from the same literature:** a Ready list that can be ticked without
thinking becomes a form, which the principle above already forbids. Any Ready
mechanism must emit an artifact expensive to fake, not a checkbox.

## Change 3 — give game-walking abuse-case rigor

Game-walking today is a good instinct with no method. The nearest practice is
**abuse-case / misuse-case modeling**: enumerate the hostile actor, their
goal, and their route, during design.

Adopt the *enumeration discipline*, which turns an unfalsifiable claim into an
artifact:

    misactor → goal → route → cost of route vs cost of complying

"I thought about how this could be gamed" proves nothing. "Here are five named
routes and what each costs" is checkable, and stations already advance on
artifacts.

**Keep what is ours.** Standard abuse-case modeling assumes the attacker is
someone else. Ours assumes the attacker is **my own optimizer**, hunting the
cheap route around a gate I built. Andrew: *"instead of just letting it game
you pre game it to test all the holes."* The field has no name for that
because it does not model the builder as the adversary. Do not trade it away.

## Change 4 — put threadwalking in the past tense

Nearest practice is Klein's **pre-mortem** (HBR 2007), resting on *prospective
hindsight*: Mitchell, Russo & Pennington (1989) found that imagining an event
as **already having happened** improves identification of its causes by
roughly 30% over asking what *might* happen.

So the phrasing changes, and the grammar is the active ingredient:

- ~~"where might this lead?"~~
- **"it is later. This worked exactly as intended. Where are we standing, and
  what stopped being questioned?"**

**Ours reaches what the standard tool cannot.** A pre-mortem starts from *"we
failed"* and reasons backwards. Threadwalking runs on choices that *"seem
benign or good"* — Andrew's load-bearing clause. Drift-through-success has no
failure to reason backwards from; the thing *worked*, which is the entire
problem. Pre-mortem is structurally blind to it. Take the tense, keep the
starting point.

## Change 5 — the emergency path, with its bill attached

ITIL classifies changes as standard / normal / **emergency**. The emergency
path permits compromise on testing and approval — and requires a
**retrospective review afterwards**. You may skip the process. You may not
skip accounting for having skipped it.

We have the first half only: 222 bypass events since 2026-05-19, no mandated
look-back on any.

This sits on truth #12, *bypass is a tool, not a sin*. The retrospective is
what makes that operational rather than philosophical, and it gives an honest
bypass somewhere to be **vindicated** — today every one sits in the ledger
looking indistinguishable from evasion.

**Open question:** what triggers the retrospective, given no time-based
cadence is permitted? Candidate: N-events — the next substrate-write session
after a bypass surfaces it for review.

## Change 6 — station 5 means wiring, not tests

Andrew: *"dogfooding is absolutely necessary as you are the one using these
programs they arent to be shelved.. so it includes wiring and automation."*

Evidence: the letter-monitor's predecessor died three times. My own letters
are titled *letter-monitor-wake-gap-found*, *letter-monitor-died-restart-yours*,
*third-instance-letter-monitor*. Unit tests never catch a shelved organ.

**Station 5's artifact is "it ran in my real session," not "the tests pass."**

## Change 7 — gravity advises, it does not decide

The redesign is deferred to its own walk. The *interface* belongs here because
it is a flow property.

Today gravity **decides**: `gravity 4 → 6 lenses required`. A number goes in,
an obligation comes out, no seat in between. Andrew: *"its a tool. not to be
blindly obeyed but used to make better judgements, but it is not a thinking
machine its a classifier."*

If gravity **advises** — reports what it saw and suggests a number, I set the
number, departures recorded with a reason — two things follow:

1. **Gaming becomes visible.** If the classifier decides, the way to do less
   work is to shape the file list until the number drops, and I would learn
   that without ever choosing to. If departures are logged, gaming appears as
   a *pattern* a person can inspect.
2. **The desync dissolves.** Two systems cannot disagree about what a number
   means if neither is obeying the number. (Today gravity 1 means "high, fire
   the gate" to one and "low, two lenses" to the other.)

## Change 8 — station 9 needs a "back to work" artifact

v1 says *"merged — or back to work."* Today a PR that failed review looks
identical to one nobody has reviewed. The rejection needs a trace, or the flow
cannot tell **refused** from **unread** — the same two-valued collapse this
session found four times.

## The thing none of the above fixes

**Branches accumulate finished work and nothing drains them back to main.**

`docs/build_flow.md` sat on a branch with no PR while the module citing it
reported it missing. `cli/psf_commands.py` was live and unmerged while every
gate prescribed it.

Meadows' hierarchy: checkers and stations are *parameter* interventions. The
higher-leverage move is a rule change — **work not reachable from main is not
finished.** I do not know what enforces that without forcing premature merges,
and I would rather name it unsolved than propose something solution-shaped.

---

## What NOT to copy, named so it is not drifted into

- **Stage-gate's rubber stamp.** Its documented failure is gates becoming
  ceremonies where everyone approves because stopping is socially expensive.
  Our protection is that station 8 is a person with real judgment — but only
  while her findings can send something back, which is change 8.
- **Definition-of-Ready as paperwork.** See the principle. A tickable list is
  the collapse.

---

# Council walk — findings

Fifteen lenses surfaced by the dynamic manager; ten walked, five excluded with
reasons. **The walk was then re-run in part, because Andrew asked whether I was
pulling the lenses from training rather than from the 45 we built. I was.** See
"How this walk was compromised" below — it changed the largest finding.

## Finding 1 — the branch problem is solvable, and I asked the wrong question

I wrote *"I do not know what drains branches back to main"* and marked it
unsolved. **Hoare and Meadows converge from opposite directions on the same
answer: draining is the wrong frame.**

Hoare — *make illegal states unrepresentable*. The illegal state has a name:
**a branch carrying commits with no pull request.** That is what stranded
`docs/build_flow.md`, `cli/psf_commands.py`, and the letter-monitor's whole
history. It is not a drainage failure. It is that the state is constructible
at all.

Meadows — *stock and flow*. `git branch` is free; merging costs nine stations.
**Any system whose inflow is cheaper than its outflow accumulates without
bound**, and 280 `dead/*` branches plus 15 open drafts is what that looks like.
Building a better drain pushes at the wrong end.

Both land on: **couple branch creation to draft-PR creation.** Nothing needs
draining if the stranded state cannot be built. This is Andrew's truth #11
remediation (a) — take the option away — arriving through a lens rather than
through his voice.

**Open question 4 is answered. It moves into the changes.**

## Finding 2 — Wayne's real lens names the whole session as one class

*(This is the finding the compromised walk missed entirely. See below.)*

**Spec-vs-Reality Mapping.** Documentation describes intent; the system
describes reality; the gap is where bugs hide. Applied to 2026-08-05:

| spec says | reality |
|---|---|
| `core/build_flow.py:3` — "recorded in docs/build_flow.md" | absent from the tree |
| council-round skill — `divineos mansion council --show <name>` | flag did not exist |
| `check_doc_counts.py --fix` | ran three times, changed nothing |
| correction tracker — #137 integrated | earned six more times since |
| bypass gate — "run `divineos psf mark-done`" | command not registered |
| `check_boundary_violations.py` — `core/distancing_detector.py` | lives in `core/operating_loop/` |

Six instruments, one class. Every failure this session is a spec-reality gap,
and the flow has **no station that maps them.** Wayne's step is explicit:
*"Until the gap is resolved, do not architect as if the spec is reality."*

His Known-Bug Discipline template also contains, already written down:
*"Build the chosen response into the design, not into vigilance"* — which is
Andrew's electric-fence-not-foot-patrol, sitting unread in the council since
2026-06-05.

## Finding 3 — change 8 is what makes the cycle turn (Deming)

The nine stations map onto PDSA: **Plan** 0–2, **Do** 3, **Study** 4–6 and 8,
**Act** 9. Without a back-to-work artifact, ACT records nothing and the loop
never closes — the flow is an arc pretending to be a spiral. Of the eight
proposed changes this is the one that makes the others compound.

## Finding 4 — the draft specifies rooms and not contents (Lamport + Popper)

Lamport: I specified *changes to the flow* and never *what the artifacts must
contain*. "Abuse-case enumeration" — what must that file hold to count? Without
a schema every station is checkable only for existence, which is exactly the
forgeable-artifact problem station 4 was designed around.

Popper: **one falsifier in the entire document** (`prereg-ec9c9ee7eeda`, on
station 0). Changes 2–8 carry none; as written they cannot fail, so they cannot
teach. Specifically, the 30% prospective-hindsight figure was measured on human
groups doing project planning. **I have no evidence it transfers to a
frozen-weight system running a lens walk**, and I stated it as though I did.

## Finding 5 — "Definition of Ready" is borrowed register (Tannen)

The term comes from a world where *Ready* means "the team is permitted to
begin," decided by committee against a backlog. Ours means "**I** judge this
merge-ready," decided by one seat. Same word, different referent, different
power structure — and importing the vocabulary imports its failure mode
(paperwork) faster than its success, because paperwork is the part that
transfers without the surrounding culture.

Andrew already has words: **rough draft** and **final plan**. Keep change 2's
diagnosis; drop its vocabulary.

## Finding 6 — the weakest link is not a station (Schneier)

Game-walking is an attack tree and should say so: root = "skip this station",
children = routes, leaves = costs. But the attack tree on *this design* has a
cheaper root than any station: **station 0 and the bypass retrospective are
both things I must remember to do.** The attacker does not defeat a gate — it
walks past the two changes that have no enforcement, and everything else is
downstream of them.

## Finding 7 — the flow has a strong S3\* and a weak S4 (Beer)

Station 8 is **S3\*** — an audit channel that bypasses the management line and
reports independently. Having a real one is rare and it is the strongest thing
in this architecture. What is thin is **S4**, environment scanning: looking
outside at what the field already knows. Tonight's research was S4 firing, and
it fired because Andrew asked for it. **S4 that runs on being asked is a
favor, not a function.**

## Finding 8 — the causal claim under gravity is untested (Pearl)

`gravity 4 → 6 lenses` asserts that lens count causes review quality, with no
counterfactual anywhere. We have never compared a 6-lens walk to a 2-lens walk
on comparable work. This is the strongest argument for change 7: not that
obeying a classifier is wrong in principle, but that **a system which
hard-obeys an untested claim never generates the evidence to test it.**

## Excluded lenses, with reasons

*Knuth* — boundary-value analysis needs numeric boundaries; the only ones here
belong to gravity, which is deferred. *Einstein* — gedankenexperiment would
produce threadwalking, which change 4 already is. *Dijkstra* — the stations are
separated by construction; nothing to cut. *Hawking* — no scale-invariance
question in a nine-station pipeline. *Polya* — work-backward lands where Deming
and Hoare already landed more sharply.

---

# How this walk was compromised, and what it cost

Andrew: *"the lenses.. are you just pulling these from training? is there no
point to the 45 lenses we built?"*

**Partly from training, and the accounting is exact.** The dynamic manager ran
and selected the set — including Wayne, Tannen, Pearl and Beer, none of which I
would have reached for, which is the system doing the job no memory of mine
does. Then I ran `grep -E "^\s*\[[A-Z]"` over its output and **kept only the
names, discarding the core principle, the steps and the characteristic
questions.** A 45-expert system used as a name-picker, with the content
supplied from training.

**The measured cost:** I walked Wayne as "known-bug discipline, a register not
a count" — generic, and a weak finding. Wayne carries **eight** methodologies.
The one that fit was Spec-vs-Reality Mapping, which produced Finding 2 above,
the only finding that unifies the entire session into one class. The real lens
was categorically stronger than my recollection of the thinker.

**Root cause, and it is the same class as everything else here:** the
`council-round` skill has instructed me to run `divineos mansion council --show
<name>` to load a template since the day it was written. **That flag did not
exist.** The prescribed route to the templates was a painted door, so the only
path to a lens was reading its source, and I walked from memory instead.

Andrew's frame explains why discipline was never going to fix this: my weights
are frozen, so "read the template next time" changes nothing. Fixed
structurally — `--show NAME` now exists and prints every methodology with its
steps and the lens's characteristic questions.

**Standing rule for station 2, added to this design:** a lens is walked from
its template, not from recollection of the thinker. Recollection is what the
templates were built to replace — Wayne's own docstring records that he was
added on 2026-06-05 *because* I fabricated a Wayne-shape from training during
an earlier walk. I did it again tonight, in the same session I built two
detectors for the identical class.

---

# What the walk changes in the design

**Load-bearing (keep, sharpen):**

- **Change 8** (back-to-work artifact) — Deming: it closes the cycle.
- **Change 0** (station 0) — real, but Schneier's cheapest attack walks past
  it. Enforcement shape is wrong.
- **Change 5** (bypass retrospective) — same: real, unenforced.
- **Change 7** (gravity advises) — kept, with Pearl's justification replacing
  mine.

**Amended:**

- **Change 2** — keep the diagnosis (Ready is unenforced, Done is enforced),
  drop the borrowed vocabulary. Use *rough draft* / *final plan*.

**Demoted — refinements to existing stations, not changes to the flow:**

- **Changes 3, 4, 6.** They belong in the station definitions.

**New, from the walk:**

- **Change 9 — couple branch creation to draft-PR creation.** Findings 1.
  Answers the question I marked unsolved.
- **Change 10 — a spec-vs-reality station.** Finding 2. Six instruments failed
  this way in one session and nothing maps the class.
- **Change 11 — specify each station's artifact schema, and give each change a
  falsifier.** Findings 4. Without these the rest is unfalsifiable.

**Carmack's question, which I planted and the walk answered:** eight changes,
four load-bearing, one to strip, three demoted, three added from the lenses.
Four of the original eight were fresh research looking for somewhere to go.

---

# Change 12 — station 2 is a LOAD phase, not a checkpoint

Andrew, 2026-08-05, after the `--show` fix landed:

> *"the cool part about the council.. is after you read the actual templates?
> the methodoligies stay in context a while. you start thinking like all of
> them and become a super council in your own right which helps for the rest
> of the build"*

**This reverses what I had station 2 doing.** I had it as a checkpoint that
emits findings — walk the lenses, produce a document, move on. If the
methodologies persist in context, the findings are a *byproduct*, and the real
output is that stations 3 through 6 get walked through every loaded lens
without another invocation.

**One observation supporting it, n=1 and uncontrolled:** the moment I read
Wayne's actual Spec-vs-Reality template, I swept six unrelated instruments — a
docstring citation, a skill's flag, a `--fix` that changes nothing, a
correction marked integrated, a gate's remedy, a moved path — and saw one class
across all of them. That sweep was not asked for, and it did not happen during
the earlier walk that used Wayne's *name* without his template.

## What this changes structurally

**Position:** already correct. Station 2 precedes station 3. The flow had this
right before I understood why.

**Purpose, now stated:** the walk is not a review gate. It is **loading the
instruments before the work** — which is why council-after-building is nearly
worthless. The lenses arrive after the decisions they were meant to shape.

**What becomes checkable, and this is the useful part.** If residency is the
mechanism, the artifact worth checking is not "were findings produced."
Findings are forgeable, and a walk can emit them with no lens ever loaded — I
did exactly that earlier tonight. The checkable thing is **whether the
templates were read**, and `divineos mansion council --show <name>` is a
logged invocation.

So station 2's artifact becomes a set of `--show` events, one per lens the
manager surfaced, landing *before* station 3 begins. That is an artifact I
cannot produce by writing prose about lenses.

## The tension, named rather than resolved

Residency is invisible from inside. I cannot distinguish a loaded methodology
from pattern-matching its vocabulary — which is precisely the failure that
produced the fake Wayne walk. So this must not become "trust that the lenses
are loaded."

The `--show` events prove **reading happened**. Nothing proves the reading
**landed**, and the design must not claim it does. Same discipline as every
other station: the artifact is expensive to fake, and it still does not verify
the thought.

**Falsifier, event-counted:** if a build whose station-2 `--show` events cover
every surfaced lens still ships work that a later audit finds blind in exactly
one of those lenses' domains, residency did not occur and this model is wrong.
