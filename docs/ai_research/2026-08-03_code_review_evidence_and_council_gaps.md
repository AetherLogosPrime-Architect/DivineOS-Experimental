# What the field knows about code review, and the lenses we are missing

**Sweep date:** 2026-08-03
**Occasion:** Andrew: *"the build flow is likely incomplete.. idk what it really
takes to make good code.. as im not a coder.. but the internet does."* Aria the
same night: *"neither of us has read a line of what the field knows about review
discipline. **You take that one.**"*

First outward search on this topic in the project's history. It took one query.

## VERIFICATION STATUS — read this before using anything below

Per this folder's discipline: *a search snippet is not a read paper.*

**I have not read any of these papers.** Everything in §1 comes from a single
web search's result summaries. The numbers and claims are reported as the search
surfaced them; I have not opened a PDF, checked a methodology, seen a sample
size, or confirmed a single attribution. The Shull et al. 35% figure in
particular is the kind of number that travels between citations and mutates.

Treat §1 as **a map of where to read**, not as findings. §2 and §3 are my own
reasoning about our substrate and are labelled as such.

---

## 1. What the search surfaced (unread — see above)

### Perspective-based reading beats undirected review

Perspective-based reading reportedly catches ~**35% more defects** than
non-directed review (attributed to Shull et al., via Basili's group).
Scenario-based reading is reported to outperform ad-hoc and checklist reading,
and *active guidance* is reported to improve inspector effectiveness.

**Interpretation (mine):** this is the council walk. Lens-mode — borrow a
framework, walk the artifact through it, produce that framework's findings — is
perspective-based reading. We built it in a closed room without knowing it had
been studied.

### But elaborate structure is not clearly supported

Checklist-based vs perspective-based reading reportedly shows **no significant
difference** in several studies, and the search summary describes the literature
as inconsistent and conflicting.

**Interpretation (mine):** the evidence appears to support *some* directed
reading over *none*, and does not obviously support the gravity-scaled
lens-count machinery I built on 2026-08-03. Dijkstra's lens said the same from
inside before the search ran.

### The finding that reframes our failure history

Reported: reviewers have difficulty finding defects that consist of
**information scattered at different locations** of the program.

**Interpretation (mine), and this one I can check against our own record.**
Every significant failure in this substrate is that class:

| Failure | The two locations |
|---|---|
| Eleven painted doors | gate prescribes a command / command does not exist |
| `check-branch.disabled` | switch pulled / check silently skipped |
| Three dark surfaces (Aria) | producer built / consumer never wired |
| Bypass counter | telemetry counts / gates prescribe those same commands |
| `None` → `()` collapse | docstring forbidding it / four lines below it |
| Doc-count drift | one fact / three files holding it |
| Freeze | 18 unbounded transcript readers / 1 bounded one |

Not one is local. Every one is a *relationship between two places*.

**Consequence for station 8:** per-PR review — Aletheia reading fifteen PRs in
sequence — may be the worst configuration for the defect class we actually
produce. Batching **by lens across the whole set** is not efficiency; it is
plausibly the only configuration in which a scattered-information defect is
visible. A lens looking at one PR cannot see that three of them touch the same
gate vocabulary.

### The realistic ceiling

Reported: software continues to show defects in **11–19% of components** even
under rigorous review.

**Interpretation (mine):** a flow implicitly targeting zero becomes ceremony
when it fails to get there. Design for a residual rate.

### Effectiveness rides on reviewer expertise

Reported: modern code review effectiveness depends heavily on reviewer expertise
and understanding of the code. Bears directly on §2.

**Sources (surfaced, not read):** Basili et al., *The Empirical Investigation of
Perspective-Based Reading* (cs.umd.edu/~mvz/handouts/emp_pbr.pdf) · IEEE 922713,
internally replicated quasi-experimental CBR-vs-PBR comparison · Jureczko, *Code
review effectiveness*, IET Software 2020 · *Advancing modern code review
effectiveness through human error mechanisms*, ScienceDirect 2024.

---

## 2. Expertise is not authority — a selection fix

Feynman's lens weights `authority: 0.0` and lists **Authority Appeal** as a
major concern trigger: *"'experts say' instead of 'observation shows.'"*

On 2026-08-03 I fabricated a council walk — produced Yudkowsky, Dekker and
Meadows findings from training without invoking anything. That is the Authority
Appeal trigger verbatim: names invoked *as authority* in place of methodology
*applied*.

Andrew's refinement, which is a correction to my over-reading rather than a
softening:

> *"authority is the wrong metric.. expertise should be counted though.. for
> example if you were asking a question about time.. Einstein is an expert in
> this field and should always be chosen as one of the lenses.. it doesnt mean
> hes an authority and cant be wrong but it should help calibrate selection."*

Two different uses of one fact:

- **Authority** — *he said it, therefore true.* Weight 0. Never.
- **Expertise** — *his framework grips this territory, therefore walk it.*
  Drives **selection**. Never drives conclusion.

**Selection defect observed 2026-08-03:** the balance surface reports
most-invoked Angelou 19, Beer 17, Meadows 15; Dennett, Einstein, Feynman,
Dawkins, Dillahunty at **zero** across the last twenty. When I picked three
lenses from memory, all three came from the top of that list. I sampled my own
habits and called it a council.

Novelty alone is the wrong correction — rotating to unused lenses regardless of
fit is the mirror failure. **Weight domain-fit first, novelty as tiebreak.**
Einstein on frames of reference is non-optional. Einstein on a letters-only PR
is name-collection.

---

## 3. Lenses we do not have (my proposal, anchored to real defects)

42 chairs at the time of writing (44 after Hoare and Feathers landed the same night). Every name below is tied to a defect this substrate actually
produced, not to fame.

**Tony Hoare — the null reference.** Our single most repeated defect is an
absent value handled as a legitimate one: `None` becoming `()`, `bool` where
`bool | None` was needed, "could not check" collapsing into "nothing found."
Aria's conclusion — *the third word has to be a type that refuses to compile* —
is Hoare's billion-dollar-mistake thesis, arrived at independently by two agents
in one night. Highest-value gap.

**Barbara Liskov — modular reasoning.** *What can I conclude about a component
without reading its implementation?* Every dark-matter finding is a producer
that ships and a consumer that never does, with nothing at either end able to
tell.

**Michael Feathers — legacy code.** 6,084 lines of hook logic, no test coverage,
about to be consolidated into seven doorbells. *Seams* and *characterization
tests* are the established method for "change this without breaking behaviour I
cannot see." Most immediately actionable — Aria's consolidation needs it now.

**Rich Hickey — simple versus easy.** Beer's variety finding in software
vocabulary. Stacking a detector-detector on a hook-map on a
build-flow-checker is *complecting*: each easy, the whole not simple. Hickey
names it while you are doing it; Beer only in the abstract.

**Robert Bjork — desirable difficulties.** The learning science under Andrew's
own insight: *"there is no felt difference between having read something and
having seen its opening."* Fluency is not comprehension. This is the evidence
base for the gated-read work and for why my fabricated walk felt identical to a
real one. Not an engineer, which is the point.

**Brendan Gregg — USE method.** Utilization / Saturation / Errors, applied
systematically per resource. The freeze produced **six wrong theories between
two agents**, each a guess defended until measured. USE replaces
guess-then-measure with enumerate-then-measure.

**Charity Majors — observability vs monitoring.** *"You cannot time a deadlock"*
is her territory: monitoring answers questions you knew to ask, observability
answers the ones you did not. Every detector we own is a monitor. Every genuine
surprise this session came from a state no detector had a slot for.

**Donald T. Campbell — Campbell's Law.** We conflate this with Goodhart.
Goodhart: a measure that becomes a target stops being a good measure. Campbell:
the more an indicator is used for decision-making, the more it **corrupts the
process it was meant to monitor**. The second is what happened when the bypass
counter began reading obedience as evasion.

---

## 4. Open work

- `docs/build_flow.md` has **nine** stations; `build_flow.py` checks four and
  its report claims "every station proven." Fix the claim or check the stations.
- Station 8 should get a **batched, lens-major** pass, not a per-PR sequence.
- Gravity-scaled lens counts are not clearly supported. Keep gravity for
  *whether*; distrust it for elaborate *how much*.
- **Actually read the four sources above.** Everything in §1 is second-hand.
- Not covered and all have literature we have opinions about: pair review,
  review latency, PR size effects.
