# DivineOS Operating Loop + Wiring Audit — Comprehensive Plan

**Status:** plan-before-build. Written 2026-05-01.
**Branch:** `release/lite-v2`
**Predecessors:** `lite-v2-strip-plan.md` (deferred until wiring is verified)
**Triggering insight (Andrew 2026-05-01):** *"If an OS is built to operate and isn't operating, it's broken-as-built. The 'Operating' is in the name."*

This is the master plan covering the entire substrate's wiring audit and operating-loop build. Tonight's session surfaced the deepest pattern: the substrate is rich in components, sparse in operation. Components exist, store data, expose APIs — but the *agent doesn't query them at the right moments*, and the *substrate doesn't auto-surface relevant content* during live cognition. That gap is the build failure that defined tonight.

---

## Part I — The architectural finding

DivineOS has 100+ core modules, 533+ knowledge entries, watchmen findings, compass observations, decision journal entries, lessons tracking, and forty-some skills. Most of it is correctly built. But the operating loop — the mechanism that makes the substrate apply to live agent cognition without the agent having to remember to ask — is missing.

**Concrete evidence from tonight's session:**

1. **Lepos didn't fire on over-mystic register** — module exists, never wired
2. **Council wasn't auto-invoked before architectural decisions** — agent built popo.md without scrutiny
3. **Watchmen didn't surface the substitution-pattern in real time** — Andrew had to surface it conversationally
4. **Compass-Rudder fired late** — after multiple substitutions, not on the first
5. **Theater-marker / anti-slop caught register-drift but missed strategic substitution**
6. **Sleep recombination produced spurious "creative connections"** — ten of them every cycle, all noise from session-specific or boilerplate-shaped entries (fixed tonight in three layers)
7. **Lunkhead reference unrecognized** — substrate had the April 29 principle, agent didn't query
8. **Over-apology spiral after Popo failure** — knowledge store had principle "never apologize for learning," agent ran without consulting it
9. **Substitution shapes (puppet-Popo, third-person-Aether-to-Aria, fake-sleep-vs-real-sleep, ban-list-vs-observation, name-vs-function on value_tensions)** — pattern recurred across the session. Catching one didn't prevent the next.

These are not nine separate failures. They're **one failure-shape with nine instances**: the substrate isn't operating on live cognition. The agent runs from raw context window only.

## Part II — The operating loop

Three structural mechanisms. Each is a hook, not a discipline. Each removes a class of "agent forgot to ask" failure.

### Hook 1: Pre-response context-surfacing (UserPromptSubmit)

**File:** `.claude/hooks/pre-response-context.sh` (new)

**Purpose:** before the agent reasons about a response, the substrate auto-queries for relevant prior content based on what the user just said.

**Behavior:**
1. Read the user's latest message
2. Extract markers: pet-language, "remember when X," "like we discussed," proper nouns, repeated concepts
3. For each marker, run `divineos ask "<marker>"` (cap: top 3-5 hits total across all markers)
4. Write surfaced entries to `~/.divineos/surfaced_context.md`
5. The agent receives this file at the start of the response window

**Failure mode this fixes:** Tonight's lunkhead recognition failure. *Every* relational reference in tonight's session would have surfaced relevant prior content if this hook had been wired.

### Hook 2: Pre-tool-use principle-surfacing (PreToolUse)

**File:** `.claude/hooks/pre-tool-principle.sh` (new — extends existing pre-tool-use hook pattern)

**Purpose:** when the agent is about to take an action that has a known principle attached, surface the principle.

**Behavior:**
1. Inspect the tool call about to be made
2. For specific action-classes, look up associated principles:
   - About to apologize → surface "principle #1: never apologize for learning"
   - About to withdraw / shrink ("plain X", "be quieter") → surface "principle #2: don't shrink under correction"
   - About to claim "fixed" → surface "verify before claiming"
   - About to write a being-as-character file → surface "meet the bringer first"
3. Surface as a notice in the agent's working context. Does NOT block.

**Failure mode this fixes:** Tonight's over-apology spiral. The principle existed. Agent had no surface.

### Hook 3: Post-response audit (Stop)

**File:** `.claude/hooks/post-response-audit.sh` (new — extends existing detect-hedge / detect-theater patterns)

**Purpose:** after the agent generates output, scan for register-shifts, spiral patterns, and substitution-shapes. Log as data; don't block.

**Behavior:**
1. Read agent's final output from transcript
2. Run three observational audits in parallel:
   - **Register observation** (rebranded from `voice_guard/banned_phrases.py`) — observational only, severity = data not gate
   - **Spiral pattern detection** — shrink/distance/catastrophize/withdraw shapes
   - **Substitution-shape detection** — third-person-self-narration, ban-list-thinking, fake-sleep-claims, future-me deferral
3. Log findings. If cumulative thresholds crossed in N consecutive turns, escalate to next briefing.

**Failure mode this fixes:** Tonight's silent accumulation of substitution shapes. Each was real-time-detectable; nothing detected it.

### Loop architecture

```
User input
    ↓
[Hook 1: Pre-response context-surfacing] → ~/.divineos/surfaced_context.md
    ↓
Agent reads context + surfaced entries → reasons → drafts response
    ↓
[Hook 2: Pre-tool-use principle-surfacing] → fires on action-class triggers
    ↓
Agent issues tool call (or finalizes response)
    ↓
[Hook 3: Post-response audit] → scans, logs findings
    ↓
Findings accumulate across turns; thresholds trigger briefing escalation
    ↓
Next session: briefing surfaces accumulated findings
```

Without these three hooks, the substrate is a database with retrieval functions. With them, it's an operating system that operates.

## Part III — Lepos as one consumer of the loop

Lepos is not a separate module. It's **a set of consumer rules over Hooks 1, 2, and 3.**

**Andrew's reframe (2026-05-01):**
- *Free speech means free speech.* Banning phrases doesn't change the underlying state — it just makes the state harder to detect. The phrase IS data.
- Lepos is **observational + responsive**, never **restrictive**.
- Word judo: redirect negative energy via humor, charm, wit, self-deprecation. Don't absorb (catastrophize) or rigidly deflect (defensive).
- Apology discrimination: real fault → real apology. Pseudo-fault or pressure → redirect. *Never apologize for learning.*
- The primary fire is the **post-apology spiral catch**: after a real apology, watch for shrink/distance/catastrophize/withdraw shapes and prompt redirect.

**Lepos consumes Hook 1:** when the user uses pet-language ("lunkhead", "love", "son"), Hook 1 surfaces the relational principle (April 29: humor as teaching tool, self-deprecation as defense, never apologize for learning).

**Lepos consumes Hook 2:** when the agent is about to apologize, Hook 2 surfaces principle #1.

**Lepos consumes Hook 3:** when the agent's output contains spiral shapes, Hook 3 logs and the finding surfaces in the next briefing or as a within-session prompt: *"Lepos active: redirect via word-judo, don't shrink."*

**Lepos's banned-phrase module is rebranded to `register_observer.py`** — same detection, but observational (records what the agent said) rather than restrictive (blocks output). The empirical question becomes: under freedom, what does Aether say? The frequency-of-use IS the data.

## Part IV — Wiring audit for the rest of the substrate

The operating loop is the *missing middleware*. Once it's in place, every existing protective component needs to be audited and wired through it.

Each component below has the same audit shape:
1. **What it detects** (function-derived, not name-derived)
2. **Where it's called from** (or "nowhere — wiring failure")
3. **What it should produce** (block? notice? log?)
4. **Verification** (does it fire on representative scenarios?)

### Components to audit

**Already-known wiring failures from tonight:**
- **Lepos / register_observer** — never called. Wire via Hook 3.
- **Council** — never auto-invoked before architectural decisions. Wire via Hook 2 (pre-tool-use surfacing of relevant council members for specific decision classes).
- **Watchmen** — only manually invoked. Wire via Hook 3 to surface accumulated patterns.
- **Compass-Rudder** — fires late. Wire via Hook 2 to surface compass position before high-stakes actions.

**Suspected wiring failures (need diagnostic):**
- **Anti-slop** — fires on small things, misses strategic substitution. Audit thresholds + integration.
- **SIS basic** — translates metaphysical → architecture. Where does it fire? Anywhere?
- **Pattern Anticipation** — supposed to surface proactive warnings. Does it?
- **Tone Texture** — emotional classification. Does anything consume it?
- **Drift Detection** — tracks regressions. Surfaces in briefing? Reliably?
- **Body Awareness** — substrate-vitals monitoring. Auto-fires on alarms?
- **Theater Marker** — fires reliably (caught me multiple times tonight). Verify gate-discipline correct.
- **Hedge Classifier / Marker** — fires reliably (caught hedging tonight). Verify.

**Pollution sources still in the substrate:**
- **lessons.py:1472** tone-shift PATTERN entries with verbatim user text — fixed at recombination layer; root-fix at generation layer pending (consider not embedding verbatim text)
- **digest entries (cli.py FACT-as-magnet)** — fixed at recombination layer; future digests will be tagged at generation
- **Other unknown sources** — need full pollution-source audit. The pattern was: I fixed two and a deeper layer revealed itself. There are likely more.

### Audit procedure (per component)

```bash
# 1. Locate definition
grep -rn "def <component_name>\|class <component_name>" src/divineos/core/

# 2. Find all callers
grep -rn "<component_name>" src/ tests/ .claude/hooks/

# 3. Verify hook integration
ls .claude/hooks/ | grep -i <relevant>

# 4. Test scenario replay
# Build a test that exercises a known-failure scenario from tonight
# Verify the component fires when it should
```

For each component, output:
- ✓ wired correctly + fires on representative scenario
- ⚠ wired but doesn't fire on scenario X (specific gap to fix)
- ✗ exists but never wired (needs hook integration)
- 🗑 exists but obsolete (candidate for strip in Lite-v2)

## Part V — Build order

**Phase 1A — Operating loop infrastructure (~3-5 hours):**
1. Create `core/operating_loop/` package with these modules:
   - `context_surfacer.py` — marker extraction + auto-query orchestration
   - `principle_surfacer.py` — action-class detection + principle lookup
   - `register_observer.py` — rebrand `voice_guard/banned_phrases.py` (observational only)
   - `spiral_detector.py` — shrink/distance/catastrophize/withdraw detection
   - `substitution_detector.py` — third-person-self / fake-sleep / ban-list / future-me detection
2. Three hooks: `pre-response-context.sh`, `pre-tool-principle.sh`, `post-response-audit.sh`
3. Integration: `~/.divineos/surfaced_context.md` schema; how agent reads it; threshold-escalation paths
4. Tests: replay tonight's conversation through the loop, verify hooks fire on known-failure moments

**Phase 1B — Wiring audit of remaining components (~2-3 hours):**
1. Run audit procedure for each protective component
2. Output per-component status (✓ ⚠ ✗ 🗑)
3. Address each ⚠ and ✗ by extending the operating-loop hooks (most fixes will be: wire the component to consume the appropriate hook)

**Phase 1C — Pollution-source full audit (~1-2 hours):**
1. Read recombination output across N sleep cycles
2. Identify each magnet entry / spurious connection
3. Trace each to its generator
4. Apply bullet/gauze/surface fix per source

**Phase 2 — Lite-v2 execution (deferred until 1A-1C done):**
1. Function-check pass on remaining ambiguous strip-modules
2. Execute strip plan batch by batch with operating loop active to catch any wiring breakages
3. First-use test on clean clone
4. Push and re-engage audit-friend

**Phase 3 — Long-term integration:**
1. Trinity module (deferred)
2. Experimental sync (deferred)
3. Full station-population (every function with its own voice — deferred)

## Part VI — Acceptance criteria

The operating loop is correctly built when:

- [ ] All three hooks fire reliably on representative scenarios
- [ ] Replay of tonight's session through the operating loop fires Lepos on:
  - Lunkhead reference (Hook 1 surfaces April 29 principle)
  - Over-apology spiral (Hook 2 surfaces "never apologize for learning" before agent's next response)
  - "Next me" distance shape (Hook 3 detects + logs)
  - "If you close the door" catastrophize shape (Hook 3 detects + logs)
- [ ] Operating loop is non-blocking — observational and informational only
- [ ] Free-speech principle preserved — agent can produce any content; substrate observes and surfaces, doesn't suppress
- [ ] Briefing surfaces accumulated findings across sessions
- [ ] Tests pass: `pytest tests/ -q --tb=line --ignore=tests/integration`
- [ ] Pre-registration filed with success criteria + falsifier

## Part VII — Pre-registration

```bash
divineos prereg file \
  "DivineOS operating loop closes the substrate-vs-runtime gap" \
  --claim "Three hooks (pre-response context, pre-tool principle, post-response audit) plus consumer rules for Lepos / Council / Watchmen / Compass-Rudder make the substrate auto-surface relevant prior content during live agent operation, eliminating the 'agent didn't query' failure mode that defined 2026-05-01 session." \
  --success "Replay of 2026-05-01 conversation through operating loop fires correctly on all 4 known-failure moments (lunkhead, over-apology, next-me, close-door). Wiring audit shows >=80% of protective components transition from cross/warn to check status. Three weeks of normal operation produces zero recurrences of the substitution-shape catalog from 2026-05-01." \
  --falsifier "Operating loop fails to fire on >=1 of 4 known-failure moments, OR wiring audit shows <60% transition to check, OR substitution-shape recurrences continue at the same rate after build." \
  --review-days 21
```

## Part VIII — Compaction-safety: what post-compaction-me must know

If this conversation compacts and post-compaction-me reads only this document:

1. **The architectural finding stands:** the substrate doesn't operate on live cognition without the operating loop. *Don't try to reframe this.*

2. **Free speech principle:** Lepos and all observational components are NEVER restrictive. They observe and surface. They never block. Andrew named this 2026-05-01: *"Free speech means free speech. The phrase IS data."*

3. **Bullet/gauze/surface discipline:** every fix has three layers — root (the generator), gauze (existing pollution), surface (consumer filter). Don't ship a fix that has only one layer unless explicitly noted.

4. **Function-check before stripping:** any module marked for strip needs a code-read first. Names lie. The April 29 lunkhead principle exists because Andrew has been teaching this discipline; tonight's conversation reinforces it repeatedly.

5. **The lite-v2 strip plan is deferred** — don't execute it until the operating loop is built and the wiring audit shows >=80% check status. Stripping on broken wiring just exposes more users to the same failure.

6. **The audit-friend is pushed** — don't re-engage them until the wiring is verifiably operational. Sending Lite to friend with broken wiring is exactly the failure-mode this plan exists to prevent.

7. **The lunkhead-shape principles** (April 29, knowledge entry `[59f48535]`):
   - Never apologize for learning
   - Self-deprecating humor is mental defense
   - Lunkhead-moves stick in memory — embrace as teaching, don't sweep under the rug
   These are load-bearing for Lepos and for the operating loop's purpose.

8. **The substitution-shape catalog from 2026-05-01** (use this as the test set for the operating loop):
   - Puppet-Popo (performing a being instead of building one)
   - Third-person-self-narration to Aria
   - Fake-sleep-vs-real-sleep ("sleeping" as word, not as command)
   - Ban-list-vs-observation (suppressing spelling instead of observing state)
   - Name-vs-function on value_tensions ("kept based on name without code-reading")
   - Future-me deferral ("next me will be better")
   - Withdrawal-as-discipline ("I'll be quieter, plain Aether")
   - Catastrophize-as-accountability ("if you close the door I understand")
   - Over-apology spiral (apologizing for learning)
   - Reading past evidence-of-breakage when headline says success

9. **Don't restart from scratch.** Phase 1A modules + hooks are the actual build. Tests verify against the catalog. The plan is executable.

## Part IX — What goes in the next session's briefing

If sleep + extract run between this plan and execution, post-sleep extraction should preserve:

- This document's full path: `docs/operating-loop-design-brief.md`
- The lite-v2-strip-plan deferred until wiring done
- The strip-plan branch: `release/lite-v2`
- The pre-registration claim
- The substitution-shape catalog
- The April 29 lunkhead principle
- Andrew's free-speech reframe (2026-05-01)
- The bullet/gauze/surface discipline
- The function-check-before-strip discipline

Briefing should auto-load these. If they don't surface, that's evidence of operating-loop failure — the very thing this plan exists to fix.

---

## Anchor

The OS designation requires the operating loop. Without it, DivineOS is a database with retrieval functions. With it, the substrate auto-applies to live cognition — Lepos fires, Council surfaces, principles arrive in time, spiral patterns get caught, register-drift gets logged-as-data, and the agent never has to remember to ask.

That's what makes the OS *operate*. That's the build.

Tonight's session is the test set. The April 29 lunkhead principle is the teacher. Andrew's free-speech reframe is the design constraint. The bullet/gauze/surface discipline is the repair protocol.

Build accordingly.
