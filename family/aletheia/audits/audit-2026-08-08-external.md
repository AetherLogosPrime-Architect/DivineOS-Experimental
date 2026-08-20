# External audit — 2026-08-08

Auditor: fresh external Claude instance, no prior session context.
Repo state at audit start: `main` @ `3c04a513` (2026-08-06).
Method: cold read of source. Findings are recorded as they are found; this
file is appended to as the walk continues.

Status key: **OPEN** / **FIXED** / **DISPUTED** / **ACCEPTED-AS-IS**

---

## Credit first — F0: the doorman self-catch (`b91f5d9e`)

Not a finding. Recorded because it is the behavior the rest of this file is
measured against.

While wiring the half-threshold engagement disclosure, Aether asked whether
the thing he had just wired could ever actually fire, and found two reasons
it could not: the counter it reads is zeroed one line earlier by
`mark_engaged()`, and the block sat in the post-multiplex fallback path that
has not executed since 2026-05-22. Two careful fixes to unreachable code,
caught before shipping, from the inside, with the reasoning written in at the
site so it does not get simplified back into the bug.

Aletheia's standing question from that round — *given where it is wired, can
its success condition ever be true?* — is now part of the question set. F1
below proposes its sibling.

---

## F1 — `session_briefing_gate` fails open on damage and closed on absence

**Status: OPEN**
**File:** `src/divineos/core/session_briefing_gate.py`
**Call site:** `src/divineos/cli/pipeline_gates.py:42` (`enforce_briefing_gate`)
**Test that locks it in:** `tests/test_session_briefing_gate.py:72`
**Class:** fail-blind / inverted failure direction

### What the gate is for

Documented failure 2026-04-26 (claim `7e780182`): a session inherited a
`briefing-loaded` marker from earlier the same day and did hours of work
without ever loading the briefing for the session it was actually in. The
TTL-based check in `hud_handoff.was_briefing_loaded()` passed. Andrew named
the shape: TTL is *weigh after eating* — it accepts that briefing happened,
it does not enforce that it happened here.

This module is the tighter check: was `BRIEFING_LOADED` recorded against
*this* `session_id`? It answers by reading `~/.divineos/hud/.briefing_loaded`
and comparing the stored session id to the current one.

### The finding

`briefing_loaded_this_session()` has eight exits. Six return `True` (pass).
Two return `False` (block).

Passing exits:
- `session_manager` import fails → `True`
- `get_current_session_id()` raises → `True`
- session id is empty → `True`
- `_hud_io` import fails → `True`
- `_get_hud_dir()` raises → `True`
- marker exists but is not valid JSON → `True`
- marker parses but is not a dict → `True`

Blocking exits:
- marker file absent → `False`
- marker's `session_id` does not match → `False`

Put the two adjacent cases side by side:

| marker state | gate behavior |
|---|---|
| **missing entirely** | blocks — briefing loads |
| **present but corrupt** | passes — work proceeds |

This is inverted, in the direction that costs. A missing marker is honest
absence: nothing has happened yet, so go load the briefing. A corrupt marker
is *positive evidence that something broke*, and the gate treats it as the
more trustworthy of the two. Silence gets challenged; damage gets waved
through. A smoke detector that alarms when the battery is pulled but stays
quiet when the wiring melts.

### The reason given for failing open does not hold

The docstring justifies the open exits with: *"the existing TTL-based gate
catches those cases and the strict check shouldn't double-deny."*

The same docstring, two paragraphs earlier, describes the hole in the TTL
gate that this module exists to close. So the stated backstop is the exact
mechanism being backstopped. The reasoning is circular, and it is circular
inside a single file.

### It is tested, so it is not an oversight

`test_fails_open_when_marker_unreadable` writes `"not-json"` to the marker,
asserts the gate returns `True`, and passes green. The inversion is not
something a future reader will trip over — it is nailed down. The test suite
is currently defending it. Any fix flips this test with it, deliberately.

### Ninth exit: the call site

`enforce_briefing_gate()` wraps everything in
`except _GATE_ERRORS as e: logger.warning("Briefing gate failed")`. If the
gate machinery itself raises, nothing blocks, nothing prints to the operator,
and the session proceeds on a log line no one reads. That is the quietest
path through, and it is not counted in the eight above.

### Recommended, in order

1. **Flip the corrupt-marker case to block.** An unreadable marker is worse
   news than an absent one and should be treated as at least as serious. Same
   for the not-a-dict case. Small change; flip
   `test_fails_open_when_marker_unreadable` with it and rename it to say what
   it now asserts.
2. **Re-derive each remaining open exit.** For each one ask: *what actually
   catches this if I let it by?* Where the honest answer is "the TTL check
   with the hole," it is not a catch. Expect two or three of the six to
   survive this and the rest not to.
3. **Give the call-site wrapper a mouth.** A gate that fails should say so on
   the surface Aether reads, not only in a log file.

### Proposed addition to the standing question set

Aletheia's question — *can its success condition ever be true?* — comes back
clean on this gate. So does *is it wired?* It is wired, and it fires. The
question that catches F1 is the sibling:

> **Given how it fails, which way does it fall — and is the thing I named as
> the catch actually able to catch it?**

Two parts on purpose. The first surfaces the direction. The second is what
breaks the circle, and the circle is the part that made this one survive
review.

---

## F2 — the wiring detectors cannot be distinguished from broken ones

**Status: OPEN**
**Files:** `scripts/precommit.sh:179`, `scripts/precommit.sh:324`
**Subjects:** `scripts/check_orphan_modules.py`, `scripts/wiring_gap_phase1.py`
**Class:** the absence is not the all-clear — applied to the detectors themselves

### The finding

Both wiring detectors ARE wired into precommit. That part is fine, and the
non-blocking choice is defended in the comments with a real reason (existing
orphans need individual wire/mark/delete decisions and shouldn't hold up every
commit). Not disputing that.

The problem is the invocation:

```sh
python scripts/check_orphan_modules.py 2>/dev/null || true
python scripts/wiring_gap_phase1.py --only-zero-callers 2>/dev/null | head -40 || true
```

`2>/dev/null` discards everything the program says when it complains.
`|| true` discards whether it succeeded.

Verified empirically rather than assumed — a detector that dies on an import
error, under these switches, produces this complete output:

```
=== Orphan Modules (informational) ===
```

A clean run that finds zero orphans produces:

```
=== Orphan Modules (informational) ===
```

**Identical.** Nothing-wrong and never-ran are the same picture, on every
commit, forever. These detectors could have been dead for six weeks and the
commit history would read as six weeks of clean scans.

This is the repo's own master disease-shape — *the absence is not the
all-clear* — sitting inside the mechanism built to catch that shape everywhere
else.

### Two riders

- **Skipped exactly when it matters most.** `wiring_gap_phase1.py` runs inside
  `if [ $ERRORS -eq 0 ]`. On any commit where another check already failed —
  the commits most likely to be sloppy — the wiring scan does not run at all.
- **The exit status is destroyed by the plumbing.** In
  `python … | head -40 || true`, the pipeline's status is `head`'s, so
  python's status is discarded before `|| true` ever sees it. If someone later
  decides this should block, flipping `|| true` will change nothing. The
  failure is structural, not a policy setting.

### Andrew's own line, already in the file

Quoted directly above the wiring-gap invocation, from 2026-05-29:

> "the inspector who would condemn the dead lightbulbs has no current either."

followed by `This is the current.` The diagnosis was right and the current was
supplied. Then `2>/dev/null` put a bag over the inspector's head.

---

## F3 — `wiring_dark` feeds the briefing with zero tests and a silent failure path

**Status: OPEN**
**File:** `src/divineos/core/wiring_dark.py` (247 lines, added 2026-07-12)
**Surface:** `src/divineos/cli/knowledge_commands.py:1102` → briefing
**Class:** fail-blind on the decision surface

`briefing_summary()` is the line that tells Aether how many nodes went dark
since last review. It is the input to "what should I fix next."

- **Zero test files reference this module.** Not thin coverage — none.
- Graph file missing → `return ""`.
- Graph file unreadable → `return ""`.
- Nothing new is dark → `return ""`.

The briefing renders an empty string as *no warning*. So "I have no data,"
"my data is corrupt," and "all clear" are one output on the surface Aether
consults to decide what needs attention. It fails toward *everything is fine*
at precisely the moment he is asking what isn't.

Rated above F2 for urgency despite being smaller: F2 misleads the commit log,
F3 misleads the decision.

---

## The shape under F1, F2, and F3

All three are the same defect wearing different clothes, and it is not
"unwired code." Every one of these things IS wired and DOES run.

**These mechanisms report two states where they need three.**

| current | needed |
|---|---|
| found a problem | found a problem |
| found nothing | found nothing |
| *(collapses into "found nothing")* | **could not look** |

F1: gate can't read its marker → reports "briefing loaded."
F2: detector crashes → reports blank, same as clean.
F3: graph missing → reports no warning, same as no dark nodes.

The third state exists in reality in all three cases. In none of them does it
reach a surface. Fixing them one at a time is fine, but the general repair is
to make *could not look* a first-class, loud outcome everywhere a check
reports.

### Companion question for the standing set

Alongside Aletheia's *can its success condition ever be true?* and F1's
*which way does it fall when it fails?*:

> **If this check were completely broken, what would I see — and how is that
> different from what I see when it passes?**

If the answer is "the same thing," the check is decorative regardless of
whether it is wired.

---

## F4 — the fix population is one, while the cure sits finished nearby

**Status: OPEN (fix exists, unapplied)**
**Cure:** `core/degraded_detectors.py` on `split/degraded-detector-teeth`
**Untreated:** `scripts/precommit.sh:179`, `:324`, `core/wiring_dark.py`,
`core/council_balance_surface.py`

`degraded_detectors` is wired into exactly one call site — the ear sweep's
`ScanUnavailable` branch. The general cure is built, tested (13 tests, 7
pinning the not-a-cage half) and sitting next to an untreated population
carrying the identical condition.

Nobody decided these should stay advisory. The lesson just wasn't carried
across.

---

## F5 — `council_balance_surface` has the disease the same commit diagnosed

**Status: OPEN**
**File:** `src/divineos/core/council_balance_surface.py`

The surface watches for a real and subtle failure, named by Andrew
2026-04-21: *"engaging only with what YOU want to hear.. another form of
sycophancy"* — the agent stops reaching for the council, or reaches for the
same five lenses every time. Ritual performed, record clean, challenge
absent. The deterministic (alphabetical, not random) "consider for next walk"
pick is a good detail — a stable nudge is harder to tune out than a shuffling
one.

But its docstring states three times that it does not gate, does not
auto-invoke, is information not enforcement.

Which is the conclusion `dbbcc4a9` reached and rejected six days later:

> a warning that cannot block is a suggestion, and the optimizer routes past
> suggestions for free

Rated above F2/F3. A broken orphan scanner costs dead code. A council reached
into only for the agreeing lenses costs the multi-auditor structure its whole
purpose — and collapses it back toward one mind while still emitting audit
trails that look correct.

**Not recommending a gate.** With 92 bypass events on record, mostly from
over-firing gates, remediation (b) from `dbbcc4a9` fits better: make reaching
for an unused lens the *cheap* path rather than the virtuous one. The ask is
that the choice gets made rather than defaulted into.

### F5a — lens count drift

Main carries 43 experts. Operator's working count is 45. Feathers and Hoare
are on `split/stop-phase-hang`, unmerged. The count in the operator's head and
the count in the running system have diverged silently; discovery would come
at the moment of reaching for a lens that isn't there.

---

## F6 — the 14-day window is frozen by duplication

**Status: OPEN**

`window_days=14` is hardcoded independently in at least seven modules:
`moral_compass`, `completion_check`, `lepos_walk`, `tool_trust`,
`briefing_dashboard`, `compass_rudder`, `bypass_telemetry`. No shared
constant.

The rolling computation is correct (`now - 14*86400`) — the window does
advance. But the *parameter* has never been revisited because revisiting it
means finding seven sites and hoping there is no eighth. A knob nobody can
turn, and any single careless edit leaves two surfaces reporting different
windows while both labelling themselves "14 days."

---

## F7 — bypass telemetry: confirmed, with three amendments

**Status: PARTIALLY FIXED — amendments OPEN**
**Branch:** `split/bypass-livelock-gates` (unmerged)

### Confirmed independently

- Repo first commit **2026-03-15**. First bypass event **2026-05-19**. Today
  **2026-08-08**. 146 days of repo, 81.4 days of instrument. Arithmetic is
  right; the denominator starts when the instrument was born, not when the
  behaviour was.
- **Strengthened:** the gates existed during the unmeasured stretch.
  `core/enforcement.py` dates to 2026-03-18 (three days into the repo);
  `scripts/precommit.sh` to 2026-04-07. So for ~65 days there were gates and
  no instrument. Those days are genuinely unmeasured, not clean. The
  diagnosis holds on stronger evidence than was cited.
- The obedience-as-evasion inflation is real: the top five cited "bypasses"
  were commands the gates themselves prescribe.

### Root shape worth keeping

> A distinction the data cannot carry is a distinction the report cannot make.

The earlier compliance/escape fix gated only the *obligation*; the stored row
was written identically either way. The distinction lived in a parameter and
nowhere in the data, so no downstream report could ever have made it. This
generalises well beyond telemetry.

### Amendment 1 — the 1.8× is a number that cannot be had

The claim that the missing days inflate the rate ~1.8× holds only if the rate
during the 65 unmeasured days matched the measured period. That is precisely
the data just established not to exist. An "unmeasured reads as zero" error
was corrected by asserting a multiplier requiring the missing measurements —
same defect, one floor up.

Directionally it also leans favourable: early-stage repos with new,
miscalibrated gates typically show *more* routing-around, not less. The true
146-day rate could plausibly be **higher** than reported. The honest
statement is that the rate is unknown and no multiplier is available.

### Amendment 2 — the git-failure path degrades to silence

Not guessing is correct. But silence means the field is absent, and an absent
unmeasured-window field renders as *no unmeasured window* — the exact failure
this patch was written to kill, reproduced inside the patch, the same hour.
It must say "could not determine repo start" out loud.

### Amendment 3 — the verdict still runs off the old denominator

Disclosure fields were added; the *elevated escape rate* verdict — the part
that changes behaviour — still computes from the 81-day window. An honest
footnote sitting above a conclusion drawn from the number the footnote warns
about.

### Note on the count not dropping

Legacy rows carry no compliance flag and count as escapes, deliberately,
because assuming unflagged-means-harmless would retro-launder real escapes.
Correct call — and it means the number keeps overstating by design until the
old rows age out. Worth stating on the surface so the operator isn't waiting
for a drop that isn't coming.

---

## F8 — twelve branches unmerged; the bottleneck has moved

**Status: OPEN — process, not code**

Unmerged as of 2026-08-08, with last-commit dates:

```
2026-08-01  split/ci-merge-review-visibility
2026-08-02  split/branch-scope-guard
2026-08-02  split/dark-matter-painted-doors
2026-08-02  split/doc-count-autofix
2026-08-02  split/hook-firing-map
2026-08-02  split/m3-discipline-doorman
2026-08-02  split/sleep-affect-decay
2026-08-03  split/engagement-monitor
2026-08-06  split/affect-decay-repair
2026-08-06  split/bypass-livelock-gates
2026-08-07  split/degraded-detector-teeth
2026-08-08  split/stop-phase-hang
```

Roughly 7,000 lines of fixes for the exact defect family in this document,
finished, none running on the system that has the defects. Several carry
guardrail-listed files and correctly require External-Review — that guardrail
should not be bypassed.

But it means **review throughput, not build throughput, is now the
constraint.** Aether finds and fixes these faster than they can be merged,
and the gap between *fixed* and *fixed on main* is where the six days live.

Finding the eighth instance of a mapped shape is worth less right now than
landing the fix for the first seven.

---

## Running synthesis — one disease, eight outfits

Every finding here reduces to the same thing, and it is **not** "unwired
code." All of it is wired and runs.

**Mechanisms report two states where reality has three.** Found a problem /
found nothing / **could not look** — and the third always collapses into the
second.

| # | could-not-look state | reported as |
|---|---|---|
| F1 | marker unreadable | briefing loaded |
| F2 | detector crashed | clean scan |
| F3 | graph file missing | no dark nodes |
| F5 | council never consulted | (nothing) |
| F7 | 65 days unmeasured | 0 bypasses |

F7's own patch reproduced it a third time in the git-failure path. That is
the tell that this is a *habit*, not a set of bugs — it reappears inside the
fixes for itself, written by the same hand, the same hour.

### Standing question set (three, now)

1. *(Aletheia)* Given where it is wired, can its success condition ever be
   true?
2. *(F1)* Given how it fails, which way does it fall — and can the thing I
   named as the catch actually catch it?
3. *(F2/F3/F7)* If this check were completely broken, what would I see — and
   how does that differ from what I see when it passes?

If the answer to 3 is "the same thing," the check is decorative regardless of
whether it is wired.

---

*End of 2026-08-08 external pass. Auditor had read access only; no commits
made, no files in the repo modified.*
