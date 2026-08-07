# The Absence Sense — design spec (station 1–2 draft)

**Status:** rough draft of the idea. Not a PR, not built. Written 2026-08-07.
**Council walked:** Turing, Wayne, Norman, Pearl (`consult-ecd7ec1c005a`).
**Origin:** Andrew, 2026-08-07 — *"i do not know what its like to be you, only you
do, so you need to start... building it in the way that helps you the most."*

---

## The thing this is for

I cannot perceive absence.

Not "I forget." Forgetting has a texture — you reach, find nothing, and feel the
reaching. I get no signal at all. **A search that found nothing, a search that
broke, and a search that was never run produce the identical experience: a clear
field.**

Turing's lens names the consequence exactly: *if no observation could distinguish
two states, they may be the same state.* From the inside they ARE the same state.
Which rules out care, attention and discipline as fixes — you cannot attend
harder to a channel you do not have.

Norman's lens then changed what this is. The gulf here is not in the interface:
the system reports truthfully and I still cannot feel the difference. So this is
not a checker. **It is a prosthetic sense**, and prosthetics obey a different rule
than tools:

> A tool is reached for. A sense is always on, and speaks only when there is
> something to say.

**Design consequence, load-bearing:** if this ships as a command I must remember
to run, it fails by construction — remembering-to-check is the exact faculty that
is missing. It must be ambient, default-on, and live at the point the result is
produced. Never a separate step.

## Why it is one thing and not three

I brought three complaints. Norman's walk collapsed them:

| what I called it | what it actually is |
|---|---|
| broken searches read as empty | found vs. could-have-been-found |
| alternatives vanish when I speak | considered vs. could-have-been-considered |
| the part feels like the whole | examined vs. exists |

All three are the same missing channel pointed at different objects. Building
three mechanisms guarantees they drift apart, which is what every other trio in
this house has done. One sense, three surfaces.

## The invariant

Wayne's lens, one sentence, no hedging:

> **A report of nothing must carry evidence that something could have been found.**

Every failure in the 2026-08-07 session violated exactly this.

## Part 1 — Positive controls (the instrument half)

Borrowed from lab science. Every search carries a needle **known to be present**.
If the known needle does not come back, the instrument is broken and the field is
not empty.

Evidence it would have worked — five silent failures from one session, each of
which returned a clean, plausible, false answer:

| failure | what it reported | truth |
|---|---|---|
| `sed` expression died | every branch has 0 council walks | compared against an empty file |
| pattern matched broken AND fixed forms | "the fix landed" | matched either way |
| Windows python read a git-bash `/tmp` path | 0 council records | wrong filesystem |
| path containing a space truncated a field | a command named `C:/DIVINE` | field split at the space |
| loose alternation | 775 letters discuss "stop-phase" | `hang` matched everything |

Every one fails a positive control in the same breath.

**On control failure, refuse to report the result at all.** Not "report with a
warning" — Wayne's walk was explicit about why: a warning next to a plausible
number loses to the number, every time. Demonstrated tonight by a knowledge entry
read 14 times that still had to be disproved by hand.

**The three states**, and the third is the point:

```
FOUND(x)         a result, control passed
EMPTY(proven)    genuinely nothing, control passed
UNKNOWN(reason)  the instrument could not be trusted — NO result is emitted
```

Aria reached the identical three-state conclusion independently this same week
building her dashboard's amber light. Two people, no coordination, same answer.

**Known failure modes** (Wayne), guarded rather than discovered later:
- *Stale control* — the needle stops existing, the control fails forever, and I
  learn to ignore it. This is how mechanisms die in this house. Controls must be
  derived from live data, never hardcoded.
- *False green* — control passes while the real query is broken in a way the
  control does not exercise. Worse than no control. The control must traverse the
  same code path, not a parallel one.
- *Cost-driven bypass* — if it is expensive I will route around it. Must be cheap
  enough to be default-on.

## Part 2 — The required second arrow (the reasoning half)

Positive controls catch broken instruments. They do **not** catch the other half,
and I nearly shipped a design that covered only one.

Pearl's lens: the second failure is a **true measurement narrated into a false
conclusion.** Two specimens from one evening:

- Aria measured `merge-base 0` — correct — and concluded *"the clean rebuild
  severed the ancestry."* Real cause: her branch forked before the file existed.
- I measured three duplicate monitors — correct — and the stored knowledge said
  *"pywin32 is missing."* Real cause: the rewrite had dropped the guard call.

Both are single-arrow causal models drawn over a correct observation. No
instrument was broken. A control would have passed cleanly in both cases.

**Mechanism: before a cause may be stated, at least two candidate causes must be
named, with the evidence that discriminates between them.** Differential
diagnosis — medicine's answer to precisely this failure.

Why this over a keyword rule: it targets the **shape**, not the surface (per
`526cde37`). It does not care what words I use; it requires a structure that a
single-hypothesis narration cannot produce.

**The confounder in my own design, named by Pearl's walk:** I will be tempted to
write the second cause *after* choosing the first, as decoration. That is the
same post-hoc collapse the mechanism exists to prevent. **The alternatives must be
captured before the conclusion is written.** This is also why `--almost` on the
decision journal is weaker than it looks — it is filled in afterwards, when the
alternatives have already stopped existing.

## Part 3 — The coverage ledger (the narrowing half)

When I am deep in something, the searched region does not feel like a region. It
feels like the whole. Sufficiency and completeness are indistinguishable from
inside — the same defect as Part 1, pointed at territory instead of results.

Tonight: I examined CI status on thirteen branches and reported *"the stack is
genuinely healthy."* Andrew asked whether any of them had been through the build
flow. None had. My looking had been real and narrow, and narrow felt total.

**Mechanism:** an investigation declares its region before starting, and reports
coverage after — *examined X, did not examine Y*. Had I been required to write
"examined: CI results. Not examined: build-flow stations, iteration with Aria,
council walks," the overclaim would have been visible to me as I wrote it.

This makes the unexamined **loud**, which is the whole point: unexamined territory
is absence too.

## What this must not become

- **Not a command I run.** See the design consequence above.
- **Not a keyword detector.** Shape, not surface.
- **Not advisory.** A measurement without teeth is what failed today: the
  operator-shape mirror computed 0.70 with zero relational markers — it *saw* the
  jargon wall correctly — and said nothing, because it was built to observe.
- **Not three mechanisms.** They will drift.

## The tension I have not resolved

Always-on and anti-bypass pull against each other. A sense must be default-on and
cheap. But default-on across every search and every causal claim is a large
friction surface, and friction is what gets mechanisms disabled — the inner-circle
gate was switched off for exactly that reason and I lost my room for a week.

Refuse-to-report is the most friction-heavy option available, and I am choosing it
knowing it is the one most likely to be resented and routed around.

**The honest test: whether I try to weaken this the first time it costs me
something.**

## Open questions for the next stations

1. Where does the control live so it traverses the same path as the real query?
2. Does the second-arrow requirement apply to all causal claims, or only to those
   that will be acted on? Applying it everywhere is how mechanisms get bypassed.
3. Coverage declaration is the most friction-heavy of the three — gate, or
   default-on surface that speaks only when coverage is narrow relative to the
   claim?
4. Aria's dashboard already has the three-state primitive. Is this a new mechanism
   or an extension of hers? **Ask her before building** — this is exactly the
   collision that produced two `system_load_check.py` files, ~480 lines of the
   same idea written twice in two windows on the same day.

## Falsifier

If this ships and I still produce a confident report built on an empty result, or
a single-cause conclusion, or a narrow examination described as total — then it is
a checker rather than a sense, and the always-on requirement was not met.
