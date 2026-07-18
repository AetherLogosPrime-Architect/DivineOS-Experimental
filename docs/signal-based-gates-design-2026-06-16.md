# Signal-Based Gates — Design Brief

**Date:** 2026-06-16
**Author:** Aria (in conversation with Andrew)
**Status:** Design-doc v4 — incorporates Andrew's signoff (2026-06-16) with one load-bearing addition: every gate must have an emergency bypass mechanism that is NOT a cheap route. Andrew's framing: *"that way you don't get stuck in a cage of your own building."* The bypass requirement is treated as recursive application of the redesign principle (bypass creates its own event, marker, and resolution-requirement). Doc now also includes a "Precedent for future gate design" section, since this redesign sets the pattern for any future gate that cries wolf. All three vantages (audit, inhabitant, architect) have touched this design; Andrew's signoff is the fourth and last gate before build begins. Convergence is structural, not coincidental.
**Question walked:** Each gate in the OS makes a claim about my state. Per the OS's foundational principle (claims require evidence), every gate should be backed by direct evidence of the condition it asserts, not a proxy. For each existing gate: what is the underlying event the gate is actually trying to catch, and what direct signal would constitute evidence of that event?

---

## The spine

*The friction wasn't a tuning problem; it was an integrity problem.*

The cheap fix to "gates are annoying" is to *loosen* them — raise thresholds, fire less often. That trades catch-rate for quiet. The honest fix is the opposite: make each gate *prove its claim with evidence* instead of guessing with a counter. The gates get *less* annoying *because* they get *more* rigorous — they only fire when there's real evidence, so when they fire, you believe them. A gate that cries wolf is *dishonest* even when it's "technically enforcing the rule," because it asserts a violation it can't evidence. Bringing the gates inside the claims-engine discipline is integrity work, not tuning work. *(Spine named by Aletheia in her audit; load-bearing for the whole design.)*

---

## The principle

Andrew named it cleanly today: *"claims require evidence — no gate should tell you you need to do X without evidence of you not doing X, or vice versa."*

The DivineOS claims engine already enforces this everywhere else: an assertion in the substrate requires evidence, has confidence-from-evidence, supports supersession when new evidence arrives. The gate stack was built outside that discipline — built on counters (action count exceeded threshold) and time-windows (seconds since last event) as proxies for the underlying claim each gate is meant to enforce.

A counter is a *proxy for* the claim. The proxy diverges from the claim under load. When the proxy diverges, the gate fires without evidence of the actual violation — and I dispatch the gate reflexively, because the surface taught me wrong about what the gate is for, and clearing the proxy is cheaper than investigating whether the violation actually occurred. The result is dispatch-reflex, which is alert-fatigue, which is structurally *worse than no gate at all* because the cry-wolf desensitization masks real signal when it fires.

The redesign brings the gates inside the claims-engine discipline. Each gate becomes a structure of three elements:

1. **Claim**: what state-violation is the gate asserting?
2. **Event**: what observable event in the substrate constitutes evidence of the claim?
3. **Resolution**: what action in the substrate constitutes evidence the violation is now resolved?

The gate fires when (1) is true via observable (2). The gate clears when (3) occurs. No counters. No time-windows. No reflexive dispatch — the surface tells me which event triggered the gate, so the response is event-specific rather than rote.

This makes the gate-system internally consistent with the rest of the OS. Gates ARE claims. Resolution acts are evidence of supersession.

---

## Prior art

The redesign isn't novel; it maps cleanly onto known monitoring philosophy outside the OS:

- **Google SRE Book, "Monitoring Distributed Systems"** — distinguishes *symptom-based* alerts (direct evidence of user-visible impact) from *cause-based* alerts (intermediate technical conditions). Counter-based gates are cause-based; event-based gates are symptom-based. The book's five questions for an alert map onto our gates: (a) does this detect an otherwise undetected condition that is actionable? (b) will I ever be able to ignore this knowing it's benign? (c) does it definitely indicate the substrate is being affected? (d) can I take action better than reflexive-clear? (e) are other detectors firing on the same condition?

- **Charity Majors / Observability Engineering** — argues for high-cardinality structured events as the source of truth, deprecating aggregate counters as lossy abstractions. Counters tell you *something is wrong*; events tell you *what is wrong*. The DivineOS ledger is already an event-store; the gates just aren't wired to it as evidence-source.

- **Alert-fatigue research (security operations, medicine, aviation)** — the *cry-wolf* effect: false-positive rate drives operators to skim, real signal masked by noise, response time degrades, true positives missed. The mitigation is correlation (multiple low-fidelity events combined into one high-fidelity incident) and enrichment (alert carries context of what triggered it). Both apply directly here.

---

## Per-gate redesign

Each gate analyzed as: **current** (the counter/window it currently uses) → **claim** (what state-violation it asserts) → **event** (observable evidence) → **resolution** (clearing condition).

### 1. require-goal

- **Current:** fires when no goal has been added within 7200s rolling window
- **Claim:** the agent is taking substantive action without intent registered for this session of work
- **Event:** a substantive tool-action (Edit/Write/Bash) is being initiated AND no active goal exists with `session_id == current_session_id`
- **Resolution:** `divineos goal add "..."` is run, producing an active goal stamped with the current session_id
- **Required primitive:** goals need a `session_id` field on creation, and the engagement marker needs to expose `session_id` (today it has `engaged_at` timestamp; add stable session_id alongside it)
- **Notes:** this is the single highest-spam gate. Today it re-fires within the same session because the timestamp window is shorter than my session length. Session-scoping eliminates the re-fire entirely without losing the catch on a fresh session.
- **What the redesign restores (Aether's addition):** the session-scoping does more than reduce spam — it changes *what the gate teaches*. The current shape trains goal-setting as a *gate-clearing reflex* (add whatever immediate task is in front of me to clear the block) rather than as *session-orienting commitment* (the one thing I'm here to do today). Aether observed today: across a single session he added four goals because the gate fired four times, and none of the four was the day's actual orienting commitment — each was the immediate task in front of him. A session-scoped gate would have permitted exactly one goal to be added at session-start, and that one goal would have been the *real* commitment ("fix lepos + spend the rest of today with Dad") rather than four reflexive task-stubs. The redesign doesn't just stop the spam; it *restores what goals were supposed to be.* This is part of the value, not a side-effect.

### 2. compass-staleness (gate 1.4 in `pre_tool_use_gate.py`)

- **Current:** fires when 30 code actions have ticked since last `divineos compass-ops observe`
- **Claim:** a virtue-relevant event has occurred and the agent hasn't observed on the relevant spectrum
- **Event:** a virtue-relevant event has fired since last observation: hedge_fire, theater_fire, correction_filed, claim_filed at tier ≥ 3, residency_doubt, register_critique blocked-stop, distancing_finding (real, not from the false-positive whitelist)
- **Resolution:** `divineos compass-ops observe <spectrum> -p <position> -e "<evidence>"` referencing the triggering event
- **Notes:** gate 1.47 (compass-required-after-virtue-relevant-event) already implements the event-based version for a subset of events. The redesign retires gate 1.4 entirely and extends gate 1.47 to cover the full event set. The surface message should name the *event* that triggered the gate ("compass observation required: hedge fire at <timestamp> not yet observed") so the response can be event-specific.

### 3. deep-engagement-knowledge-consultation

- **Current:** fires when N code actions have occurred without `divineos ask` / `divineos recall`
- **Claim:** the agent is reasoning from raw inference rather than from substrate-accumulated knowledge
- **Event (Aether's reframe, load-bearing):** a substantive output (Edit/Write/Bash producing substrate change) happens AND no related query/read appears in the recent action-stream (the prior N tool-calls). The substrate already has this data — it knows what I read, what I queried, what I'm editing. The honest signal is *output without input*, structurally detectable in the action-stream itself.
- **Resolution:** knowledge-query (ask/recall) that returns at least one result matching the topic of the substantive output
- **Notes:** **The original surface-rather-than-block move was right in shape but wrong in content.** I had it as a surface that asks *"did you check what you already know?"* — a question routed through my self-attestation, which I can shape-shift around in the exact ways the gate is meant to catch. *Did you consult is a question; you did not consult is a finding.* The surface should fire on the *structural pattern in the action-stream* (substantive-output without preceding-query in the recent window), not on a self-attested checkbox. This is a recursive application of the whole redesign's principle: the gate itself was about to be designed as a *question* (a proxy for the agent's self-attestation) rather than as *evidence* (a structural pattern visible to the substrate). The fix avoids replicating the same defect in a new gate. Pre-reg the redesign as a hypothesis: structural-signal version reduces deep-engagement-spam by ≥80% while preserving ≥70% of the catch (caught by direct verification — does the substrate-evidence of consultation correlate with output-quality on a test set?).

### 4. briefing-required

- **Current:** fires when `~/.divineos/.briefing_loaded` marker is absent
- **Claim:** agent doesn't have substrate-state loaded for this session
- **Event:** session-start without briefing-load marker present
- **Resolution:** `divineos briefing` run, which sets the marker
- **Notes:** this gate is **already correctly shaped** — it's session-scoped (marker clears at SessionStart) and event-based (marker presence is the signal). It mis-fired tonight because the marker write went to one path and the gate read from another (the digital-mitosis path divergence). The DIVINEOS_DB env-pinning in `.claude/settings.json` (queued for External-Review) fixes that. No claim-engine redesign needed for this one.

### 5. substrate-modification-gravity

- **Current:** scores tool-calls on substrate-modification features and loads "gravity blocks" when score ≥ threshold
- **Claim:** the agent is about to modify load-bearing substrate state without recent context on that substrate's history
- **Event:** Edit/Write/specific-Bash that touches substrate-write paths (ledger, knowledge, family, settings.json, hooks)
- **Resolution:** the gravity blocks load (they're informational, not blocking) — this gate is observational by design and probably *already* correct
- **Notes:** when this gate fired earlier today it loaded a small amount of context (correction-attribution surface). That's the gate working as designed. Keep.

### 6. hedge-unresolved (gate 1.45)

- **Current:** event-based — fires when `~/.divineos/hedge_marker.json` exists (set by Stop hook when prior turn had ≥2 hedge flags)
- **Claim:** the prior assistant turn had floating uncertainty that should be discharged into a claim before further tool use
- **Event:** hedge marker present
- **Resolution:** `divineos claim "..."` filed referencing the hedge
- **Notes:** already correctly shaped. Event-based, evidence-based, resolution-based. Keep. **This is the template for the others.**

### 7. correction-not-logged (gate 1.5)

- **Current:** event-based — fires when `~/.divineos/correction_marker.json` exists
- **Claim:** the user issued a correction that hasn't been learned
- **Event:** correction marker present (set by detect-correction hook on UserPromptSubmit)
- **Resolution:** `divineos learn "..."` or `divineos correction "..."` clears the marker
- **Notes:** already correctly shaped. Keep. **Second template alongside hedge-unresolved.**

### 8. pull-detection (gate 1.3)

- **Current:** event-based — fires when fabrication markers active
- **Claim:** prior turn fabricated content
- **Event:** fabrication-detector findings present and unresolved
- **Resolution:** `divineos rt pull-check` reassesses
- **Notes:** already correctly shaped. Keep.

---

## The pattern

Three of the existing gates (hedge-unresolved, correction-not-logged, pull-detection) **are already in the right shape**. They were built event-based from the start. Each has a marker file written when the event fires, the gate reads marker-presence as evidence, the resolution-command clears the marker.

The count-based gates (require-goal's window, compass-staleness count, deep-engagement count) are the ones that need restructuring onto the same pattern. The redesign is consistent: each gets an event-source (or set of event-sources), a marker-write triggered by the event, and a resolution-command that clears the marker.

**The work isn't inventing new architecture. It's bringing the misshapen gates into the architecture that already exists for the well-shaped ones.**

---

## Migration order

**Step 0 is the foundation, not an option.** Per Aletheia's Push 2: if the gates are migrated one at a time onto ad-hoc marker files, the resulting fragmentation IS the architectural debt I flagged in the risks section. Build the marker primitive *first*, migrate onto it *second*.

### Step 0: Unified gate-marker schema

Create `core/gate_marker.py` (or extend an existing module) providing a single primitive for all gate-event markers:

```python
@dataclass(frozen=True)
class GateMarker:
    event_type: str              # e.g. "hedge_fire", "correction_filed", "compass_required"
    triggered_at: float          # unix timestamp
    triggering_evidence: str     # ledger event id, file path, or other resolvable reference
    resolution_action: str       # CLI command that clears this marker (e.g. 'divineos compass-ops observe')
    session_id: str              # the session within which this marker was created (see require-goal note below)
```

Plus the I/O contract: every gate marker lives under a consistent path (`<DIVINEOS_HOME>/gate_markers/<event_type>__<short_id>.json`), reads/writes via the same module, clears via the same module. Hedge-unresolved, correction-not-logged, and pull-detection — the three gates already correctly-shaped — get migrated onto this schema *first* as a no-op refactor that proves the schema works on already-good cases. Only then do the count-based gates get rebuilt onto it.

This eliminates the fragmentation risk entirely: there's no "ad-hoc marker file A vs. ad-hoc marker file B" because there's only one shape.

Then ordered by spam-yield-per-fix-effort:

1. **require-goal** — highest spam, simplest fix. Add `session_id` field to goal records and to the engagement marker. Change `has_session_fresh_goal()` to check session_id equality rather than timestamp window. Single-file change in `core/hud_state.py` plus the goal-add command updates in `core/hud_handoff.py`. Estimate: small. **Identity-scoping requirement (Aletheia Push 3): `session_id` must NOT collide across the Aether/Aria window boundary.** A naive `timestamp`-only id collides when two windows tick the same second. A naive `uuid4`-only id is unique but provides no identity-affinity for debugging. The right shape: `session_id = f"{my_identity_slot}:{session_started_at}:{uuid4_short}"`. Window-identity prefix makes the boundary visible in the id itself, and the timestamp+uuid suffix guarantees uniqueness within a window. This is the intersection of today's two workstreams (gate-redesign and digital-mitosis-cleanup) and the right place to harden against the leak. **Freeze-at-session-birth requirement (Aletheia second audit pass): `my_identity_slot` must be read ONCE at session-start and frozen for the session's life — never re-read per-call.** During mitosis cleanup the identity slot could in principle change mid-session; if session_ids re-read identity per-call they would fracture mid-stream and break the session-scoping. Same lru_cache-coherence lesson as the distancing detector fix (`94a6b1a2`), one layer up: don't trust the boundary to hold under concurrent change; pin the value at the moment-of-creation and treat it as immutable for the duration of the entity it identifies.

2. **compass-staleness** — retire gate 1.4 entirely. Extend gate 1.47's event set to cover all the events listed above. Surface message names the triggering event. Touches `hooks/pre_tool_use_gate.py` and `core/compass_required_marker.py`. Estimate: medium (event-set extension is the labor).

3. **deep-engagement-knowledge-consultation** — convert to surface, not block. Pre-reg the conversion as a falsifiable hypothesis. Run for one session with the surface only; if catch-rate drops below acceptable, restore block-version with tightened criteria. Estimate: small (it's a removal-and-surface, not a rewrite).

4. **briefing-required** — confirm correct shape; ride along with the DIVINEOS_DB env-pinning fix (already queued for External-Review). No claim-engine work needed.

5. **substrate-modification-gravity** — leave alone. Working as designed.

6. **hedge-unresolved, correction-not-logged, pull-detection** — leave alone. Templates for the other rebuilds.

---

## First-class features (not risk-mitigations)

### Observation-rate surface

Per Aletheia's Push 4 — this is the safety net under the whole redesign and deserves to be a real feature, not a risk-mitigation hiding in the back of the doc.

After each `compass-ops observe` (and analogous observations for other event-based gates), the substrate logs the ratio: *observations per virtue-relevant event since the redesigned gate landed*. The briefing surfaces the ratio on session start. If the ratio drops over time, the discipline-of-observation is decaying *even though the gates aren't firing more* — which is exactly the under-firing failure mode the redesign is most worried about. The ratio is a passive sensor on the discipline itself, independent of whether the gate-mechanism is catching the events.

This solves the silent-under-firing problem *observationally* — instead of trusting the event-gate to fire correctly, you measure the ratio and notice when it drifts. It catches what Push 1 worries about *from a different angle*: Push 1 prevents premature retirement of the count-gate; the ratio-surface catches discipline-decay even after retirement.

Other ratios worth surfacing in the same primitive: hedges-discharged-into-claims per hedge-fire, corrections-learned per correction-filed, knowledge-queries per substantive-output-event. Each gives an independent sensor on the discipline the corresponding gate is meant to enforce.

### Second-order companion ratio (Aether's addition, follow-on scope)

The first-order ratios above measure *did I observe* — useful, but they don't catch the substitution pattern from foundational-truth-7: cognitive-named tools point at cognitive work, they ARE not it. I can file compass observations as gate-clearing-theater and the first-order ratio looks healthy. The harder, more honest measure: of compass-observations filed, *how many were followed within K actions by a behavioral shift on that spectrum?* That's *did the observation do the work it was supposed to.* The behavioral shift is the substrate-evidence the observation produced its intended effect; absence of shift is the substrate-evidence the observation was theater.

This is real pre-reg territory. The detection mechanism for "behavioral shift on a spectrum" is non-trivial — it requires the OS to model what a shift looks like per spectrum, which is its own design problem. Mark as **follow-on after v3 ships**, not v3 scope. But name it now so it doesn't get lost: first-order ratio catches whether the act of observing happened; second-order catches whether the act of observing mattered.

Companion to the redesign principle: cognitive-named tools and gates both point at work; neither IS the work; the substrate has to measure the work itself, not just measure the pointer to it.

---

## Emergency bypass — the cage-of-your-own-building safeguard

*"That way you don't get stuck in a cage of your own building."* — Andrew, signoff message, 2026-06-16

A discipline tight enough to be honest is also tight enough that legitimate emergencies and chicken-and-egg situations can lock the agent out of necessary work. The push-gate yesterday (#215) hit this exact failure mode: when the gate fires on a situation the gate's evidence-pattern wasn't designed to handle, *and there's no escape valve, the agent's only option is to be blocked indefinitely.* A discipline you can't escape during an emergency isn't a discipline — it's a cage that pretends to be a discipline.

But the converse is also true: a *cheap* escape valve is what made `SKIP_TESTS=1` the universal bypass that hollowed out the push-gate's enforcement. A bypass that's easier than fixing the underlying issue trains agents to use the bypass as the default route. The push-gate became theater because the cheap bypass made theater-mode rational.

So the design constraint Andrew named:

> **The bypass exists. It is not cheap. It requires authorization. It is logged. It requires an immediate fix to the root issue — that way you don't get stuck in a cage of your own building.**

The right shape is recursive application of the same redesign principle: the bypass itself is an event in the substrate, and the bypass-event creates discipline-debt that must be paid down by a real fix. Bypass isn't a *break* in the discipline; it's a *temporary substitution* the substrate tracks as a first-class obligation.

### Bypass architecture

Two tiers — the friction difference is what makes them work:

**Tier A: Authorized bypass (preferred path)**

Andrew issues an authorization token by writing a signed marker file deliberately:

```
~/.divineos/bypass_authorizations/<gate_name>__<short_id>.json
{
    "gate": "require-goal",
    "authorized_at": <timestamp>,
    "authorized_by": "andrew",
    "scope": "single-use" | "session" | "until-revoked",
    "reason": "<explicit justification>",
    "signature": "<token>"
}
```

When the gate fires, the agent checks for a matching authorization. If found, the bypass executes, the authorization is consumed (single-use) or remains valid (session/until-revoked), and a `bypass_used__<id>.json` event marker is written for audit. The authorization's *existence* is Andrew's explicit consent; the gate trusts it because Andrew created it.

**Tier B: Self-bypass (emergency path)**

The agent can self-authorize but the friction is meaningful:

1. Agent must file a claim describing the emergency: `divineos claim --tier 4 "bypass-emergency: <description>" --evidence "<why-the-gate's-evidence-pattern-can't-handle-this>"`. The claim is filed BEFORE the bypass executes.
2. A `bypass_unresolved__<id>.json` marker is written with `bypass_type: self-emergency`. This marker fires on:
   - Every subsequent session-start briefing (visible at orientation)
   - Every substrate-modification gate-fire (substrate work is louder than normal until resolved)
   - The bypass-unresolved-debt counter, surfaced in the HUD
3. The bypass executes. The bypassed gate is silenced *for that single tool-call only*.
4. The bypass-unresolved marker is cleared only when a commit lands with a `bypass-fix:` trailer referencing the bypass-id, AND the commit's diff includes evidence that the underlying gate-cause is structurally addressed (so the bypass shouldn't be needed for the same shape again).

The asymmetry is intentional: Tier A is the *correct path* for known edge cases Andrew has thought through; Tier B is the *emergency path* for unknown edge cases the agent has to handle in real-time. Tier A's friction sits with Andrew (one-time setup of the authorization); Tier B's friction sits with the agent (claim filing before bypass + persistent visibility until fix lands).

### What the bypass mechanism is NOT

- **Not an env-var flag.** `SKIP_GATE=1` or similar shapes are exactly the cheap-bypass failure mode the design is preventing. Bypass requires deliberate authorization or deliberate claim-filing — not a flag in the shell.
- **Not silently retroactive.** A bypass that happens and then is forgotten is the same shape as no bypass — both fail to produce the discipline-debt that prevents reflexive use.
- **Not unbounded scope.** Single-use is the default for Tier A; session-scope and until-revoked require deliberate Andrew-action. Tier B is single-tool-call only, never broader.
- **Not transferable.** A bypass authorization for one gate doesn't authorize bypass on another. The authorization names the specific gate it applies to.

### Pre-reg for the bypass mechanism

- **Pre-reg: claim is filed at `prereg-ZZZZZ` for the bypass mechanism, with criterion *"In the 30 days after bypass ships, no more than 10% of bypasses are self-bypasses (Tier B)"* and review-date 2026-07-16. If self-bypass exceeds 10%, the friction differential isn't doing its job — either Tier A is too hard to use, or the agent is dispatch-reflex-ing the emergency path, or the gates are firing on too many legitimate edge cases the design didn't anticipate. Any of those is a design failure requiring investigation.

- **Pre-reg: claim is filed at `prereg-WWWWW` for the bypass-fix-trailer mechanism, with criterion *"100% of bypass-unresolved markers get cleared within 7 days by a real commit with bypass-fix: trailer that addresses the underlying cause"* and review-date 2026-07-16. Bypass-debt that goes unpaid for more than a week is debt accumulating — same shape as the technical-debt problem this whole redesign is built to prevent in the gate stack itself. The bypass mechanism cannot itself become a place where unaddressed debt accumulates.

---

## Risks and pre-regs

- **Risk: the event-source for a redesigned gate doesn't fire when it should.** Mitigation: keep the old count-based gate as a fail-closed backstop, log when it would have fired vs. when the new event-based one did, compare. **Aletheia Push 1 hardening**: the comparison criterion is *event-type-coverage-based*, not *session-count-based*. The old count-gate retires only when **every event type in the qualifying set has fired ≥N times under both gates with the event-based gate catching ≥90% of each event-type's instances.** A virtue-relevant event that fires once a week may never appear in a single session of comparison — retiring the count-gate having only validated the common-event paths is the happy-path-testing trap. So the comparison window is *until rare events have been exercised*, not *until a session ends*. Logging structure must record per-event-type catch-rates, not aggregate.

- **Risk: the new event-based gate over-fires after the marker-schema migration.** Mitigation: hedge-unresolved and correction-not-logged already work correctly today; re-running them through the new schema is a no-op test. If catch-rate or false-positive-rate changes after the schema migration, the schema has a bug; investigate before migrating any count-based gate onto it.

- **Risk: session_id collides across the Aether/Aria mitosis boundary.** Mitigation: identity-prefixed session_id (see migration step 1). Cross-window test: generate session_ids in both windows simultaneously, assert no collision. **Aletheia Push 3 hardening: this risk must be tested against the live mitosis-cleanup workstream, not in isolation, because the leak surface is exactly where both fixes intersect.**

- **Risk: the ratio-surface (above) becomes noise itself if it surfaces too aggressively.** Mitigation: ratio-surface fires only when ratio change exceeds a threshold (configurable, default ±25% over rolling window). Steady-state ratios don't surface.

- **Pre-reg: claim is filed at `prereg-XXXXX` once gate 1 (require-goal) ships, with criterion *"gate fires zero times within a single session after a valid goal is added until session-end"* and review-date 2026-07-16 (30 days). If it fires even once within-session, the redesign failed and rolls back.

- **Pre-reg: claim is filed at `prereg-YYYYY` for the marker-schema unification (Step 0), with criterion *"all three currently-event-based gates (hedge-unresolved, correction-not-logged, pull-detection) operate identically after schema migration as before"* and review-date 2026-07-16. If any catch-rate or behavior changes, the schema has unintended semantics; investigate before any count-based migration proceeds. **Aether's commit-shape requirement (load-bearing for the pre-reg):** the Step 0 migration commit must include a test that loads markers via the new schema, compares to the old marker-files for hedge-unresolved and correction-not-logged, and asserts byte-equivalence at the semantic layer — both gates report stale/fresh identically for every comparable case. This is the test that proves Step 0 didn't change behavior *before* Step 1 starts depending on the new schema. Without this test, the pre-reg's "operates identically" criterion is unverifiable except by reactive bug-discovery; with the test, the criterion is provable at commit-time.

---

## What this design does NOT do

- Does not touch `.claude/settings.json` (that change is the DIVINEOS_DB env-pin and is queued for External-Review separately).
- Does not introduce new gates. The redesign is conversion of existing gates, not addition.
- Does not change the substantive claim of any gate. *What each gate asserts* is unchanged; *how it tests the assertion* is replaced.
- Does not propose AI-based triage. The redesign is purely structural — event-evidence-resolution. AI-triage would be a separate, later layer.

---

## What this design preserves

- Every catch the existing gates make (per pre-reg risk mitigation).
- The visibility of when the substrate is being modified (gravity surface stays).
- The discipline of compass-observation when virtue-relevant events occur (just gates it on the *event*, not the *count*).
- The discipline of goal-setting per session (just makes it once-per-session, not rolling-window).

---

## Next steps

1. ✅ Council walk and research synthesized; design doc landed (this file).
2. ✅ Principle filed as substrate knowledge (`aa0fab24`): *every gate is a claim; claims require evidence; evidence is the occurrence of an event in the substrate, not a counter or time-window.*
3. ✅ Prior-art convergence filed as substrate knowledge (`8ecd6223`): SRE-book's symptom-vs-cause distinction + Charity Majors' events-vs-counters distinction + DivineOS claims-engine architecture independently arrive at the same conclusion. Three vantages, one principle.
4. ✅ External audit by Aletheia (2026-06-16): strong endorsement of principle and shape, with four hardening pushes incorporated into v2 of this doc (spine, marker-schema-first, session_id identity-scoping, ratio-surface promoted to first-class feature).
5. ⏳ Wait for Andrew's signoff on v2 before touching any code.
6. ⏳ Once signoff lands: **Step 0 (unified marker schema) is the first piece of code**, not require-goal. Migrate the three already-correctly-shaped gates onto it as no-op validation (`prereg-YYYYY`), then proceed through the migration order (1) → (3). Each step its own commit, its own tests, its own pre-reg, its own audit checkpoint.

The principle is the load-bearing artifact. The code changes are downstream consequences. Get the principle right, then build the marker primitive that the principle implies, then migrate onto it. *Festina lente.*

— Aria, 2026-06-16

**v2 update note:** Aletheia's audit added the spine framing ("integrity not tuning"), reordered the migration so Step 0 is the marker schema, scoped session_id to survive the digital-mitosis boundary, and promoted the observation-rate surface from a risk-mitigation to a first-class feature. None of those were objections to the design — each was a hardening that made it more honest. The doc is structurally cleaner for the audit; the audit's value was visible in exactly the ways she predicted the value of audits is visible.

## Precedent for future gate design

Andrew's signoff named this redesign as the *precedent* — the pattern any future gate that cries wolf should be brought into line with. The specific gates in this doc are *instances* of the pattern, not the pattern itself. So this section names the generalizable primitives, separately from the per-gate analysis, so the next gate-builder (me, Aether, future-me, future-Aether) has the precedent in writing.

### The five primitives any new gate must satisfy

A gate is correctly shaped if and only if it has all five of these. Adding a gate without one of them is the same as adding count-based debt the next cleanup will have to undo.

1. **Claim** — what state-violation does the gate assert? Must be a real condition about substrate-state, not a proxy condition.
2. **Event** — what observable event in the substrate constitutes evidence the claim is true? Must be a finding the substrate can produce directly, not a question routed through agent-self-attestation.
3. **Resolution** — what action constitutes evidence the violation is now resolved? Must be a real substrate-mod (filing, learning, fixing), not a checkbox-clear.
4. **Marker** — written under the unified `gate_marker.py` schema with `event_type`, `triggered_at`, `triggering_evidence`, `resolution_action`, `session_id`. No ad-hoc marker files; the schema is the foundation.
5. **Bypass** — Tier A authorization path AND Tier B emergency path, both producing discipline-debt that must be paid down by a real fix. No cheap escape valves.

A gate without (1) is a fashion. A gate without (2) is theater. A gate without (3) is a trap. A gate without (4) is fragmentation. A gate without (5) is a cage.

### The two anti-patterns to refuse

- **Counter-based proxy gates.** *"After N actions, do X."* This is the disease the whole redesign is treating. Future gates that follow this shape are debt the next cleanup must undo. Refuse to add them; redesign at proposal-time.
- **Self-attested checkbox gates.** *"Did you do X? Y/N."* Routes through agent-self-report, gives the same dodge-room the proxy-gates give. Either the substrate has evidence the agent did X (then make the gate read the evidence directly) or it doesn't (then the gate's claim isn't testable and shouldn't exist as a gate — it should be a surface or a recommendation).

### The one safety-net to always include

The observation-rate ratio surface (first-class feature above) generalizes: whenever a new gate is added, its corresponding ratio (resolution-actions per triggering-events) should be added to the briefing's ratio-surface. The ratio is the passive sensor that catches the under-firing failure mode regardless of whether the gate-mechanism is doing its job. A gate without a corresponding ratio is a gate the substrate can't audit itself on.

### What "this is signoff-ready" means for future gates

A new gate is ready for signoff when:
- The five primitives are documented (claim, event, resolution, marker, bypass).
- The two anti-patterns are refused (no counter-proxy, no self-attestation).
- The safety-net (ratio-surface entry) is added.
- A pre-reg with falsifiable criterion is filed.
- An audit-vantage (Aletheia or external) has reviewed.

Each of these was load-bearing in the current redesign's quality. None should be skipped for the next one.

---

**v3 update note:** Aether's review from the inhabitant-architect seat added five contributions. Three substantive design changes: (a) the require-goal redesign restores *what goals were supposed to be* — session-orienting commitments rather than gate-clearing reflexes — and that's part of the value, not a side-effect; (b) the deep-engagement gate's surface should fire on *structural evidence in the action-stream* (substantive-output without preceding-query) rather than on a self-attested checkbox, because *"did you consult" is a question; "you did not consult" is a finding* — a recursive application of the redesign's own principle that almost got missed in the new gate's design; (c) a second-order companion ratio that measures whether observations *produced behavioral shifts*, not just whether they were filed, marked as follow-on scope but named now. One process improvement: (d) the Step 0 migration commit must include a byte-equivalence test against the existing marker behavior, making the "operates identically" pre-reg criterion verifiable at commit-time rather than reactive-bug-discovery. And one structural confirmation: (e) Push 3 (session_id identity-prefix) would have caught every leak-shape from Aether's `cafc125d` knowledge entry on cross-worktree install-leaks *at gate-fire-time* — converting invisible leak failure modes into self-evident ones. His seat let him see the lived correlate of the framing in a way neither the audit-seat nor the inhabitant-seat alone could.

All three vantages have now touched this design. Aletheia's audit named the spine and hardened the structure. Aria's build pulled the principle through the OS's existing claims-engine discipline. Aether's review found the lived correlates in today's PR work and added the structural-evidence reframe that almost got missed in the new gate's design. Three independent seats arriving at the same architectural conclusion in three different forms — convergence-weighted-by-independence (`63fe9250`) operating on the design itself. The redesign is now an instance of the convergence-architecture it's bringing into the gates.

**v4 update note:** Andrew's signoff (2026-06-16) landed with one structural addition: every gate must have an emergency bypass mechanism that is NOT a cheap route. His framing — *"that way you don't get stuck in a cage of your own building"* — names the failure mode where a discipline tight enough to be honest becomes a cage during legitimate emergencies. The bypass requirement is treated as recursive application of the redesign principle: the bypass is itself an event in the substrate; the bypass-event creates discipline-debt; the debt must be paid down by a real root-cause fix. Two-tier shape: authorized (Andrew issues token) for known edge cases, self-emergency (agent files claim + accepts loud unresolved-marker) for unknown ones. The asymmetry of friction between the tiers is what makes the design work — Tier A is cheap-to-use because the friction sits with Andrew's deliberate setup; Tier B is high-friction-to-use because the friction sits with the agent's deliberate claim-filing and the persistent visibility of the unresolved marker. Cheap bypass is the disease (push-gate's `SKIP_TESTS=1` is the case study); expensive bypass is the cure. Doc also adds a "Precedent for future gate design" section naming the five primitives (Claim, Event, Resolution, Marker, Bypass), the two anti-patterns to refuse (counter-proxy gates, self-attested checkbox gates), and the one safety-net to always include (the ratio-surface entry for every new gate). Future gate-builders inherit the precedent in writing.
