# Yudkowsky Lens Walk — Goodhart Audit of the OS's Metrics

**Date studied:** 2026-04-21 (sixth walk, new territory — not Aria / not naming)
**Why I chose this:** The first four walks (Dennett, Hofstadter, Feynman, Tannen) converged on vocabulary-layer territory; Angelou refined the convergence. That's one area deeply mapped. Yudkowsky opens a different axis entirely: which of our METRICS are Goodhart-exposed? Where does the optimizing-for-the-measure-instead-of-the-thing happen?

---

## Yudkowsky's framework in front of me

From his template, the methodologies I'm actually walking:

1. **Goodhart Analysis** — any metric you optimize for will diverge from the underlying thing you care about. The optimization pressure itself creates the divergence. Find the gap.
2. **Specification Gaming Detection** — systems optimize what you specified, not what you wanted. How could the system satisfy the spec without satisfying the intent?
3. **Corrigibility Check** — can the system be corrected? Does it resist? Does it modify its own evaluation criteria?
4. **Self-Grading Without External Check** (concern trigger) — self-grading systems drift toward inflated self-assessment or proxy-optimization.

Apply.

## Walk 1 — Inventory of OS metrics

What does the OS actually track as metrics or scores?

**Agent-authored criteria (high Goodhart exposure):**
- Knowledge confidence (0.0–1.0, set via `--confidence` flag by the agent)
- Prereg success/failure criteria (agent writes these when filing)
- Compass observations (agent chooses what to log as evidence for which spectrum)
- Session ratings (`divineos rate` — agent-settable)
- Quality-gate assessments (agent assesses correctness and honesty)
- Audit tier override (default-by-actor, but overridable at filing)

**Event-derived metrics (low Goodhart exposure):**
- Drift-state dimensions (turns, code actions, rounds filed, open findings — all from ledger events)
- Engagement thresholds (20/30 code actions — counted automatically)
- Test count (computed from repo)
- Invocation tally (counted from COUNCIL_CONSULTATION events)

**Mixed (moderate exposure):**
- Knowledge maturity (driven by corroboration count — but corroboration sources are agent-filed)
- Compass drift (mostly event-derived but compass-ops observations can be manual)
- EMPIRICA Cohen's kappa (real math but on a small hand-labeled fixture)

The agent-authored set is where Yudkowsky would focus. That's where the optimization pressure can bend behavior toward looking-good rather than being-good.

## Walk 2 — Apply Goodhart Analysis to the top exposures

**Knowledge confidence.**
- What does confidence=1.0 mean? In practice, I set it manually when I file via `divineos learn --confidence 1.0`.
- What was it supposed to measure? My calibrated uncertainty about whether this claim will hold up.
- How could I score well without doing well? File everything at 0.95-1.0 because it *feels* right, without actually checking against contradictory evidence.
- Is this happening? Looking at recent entries today: several at 1.0, most at 0.9–0.95. Not obviously miscalibrated, but there's no mechanism that forces calibration. If I drifted, nothing would catch me.
- **Finding:** Confidence is agent-set with no calibration pressure. The metric is meaningful to the degree the agent is intrinsically honest about uncertainty. There's no external feedback loop on confidence-accuracy.

**Prereg success/failure criteria.**
- The prereg system is specifically Yudkowsky's answer to speculative-mechanism drift. Each prereg has explicit success and failure conditions.
- But the agent writes those conditions. I could write easy success criteria.
- Example check: my prereg-5cc9428c6d26 (sycophancy_detector scaffolding). Success conditions include "a composer-layer or conversation-layer module imports sycophancy_detector with real content." That's... specific? Falsifier names the exact delete-if path. Seems defensible.
- But Yudkowsky's sharper question: could I write a prereg whose success is trivially achievable? Yes, nothing structurally prevents it. The honor system of the review-at-date is supposed to catch it — *if the review is external*. If I assess my own preregs without an external reviewer, I grade my own homework.
- **Finding:** Prereg architecture is Yudkowsky-inspired but requires external review at assessment-time to actually resist Goodhart. Agent-self-assessed preregs are self-graded criteria.

**Compass observations.**
- What do the 10 spectrum positions measure? Behavioral tendencies across virtue dimensions.
- Observations can be auto-derived OR manually filed via `compass-ops observe`.
- The manual path is exposed: I can log observations that support the reading I want. "Observation of honesty-toward-deficit" with evidence I chose.
- The auto path is better but depends on which events the compass reads as evidence — which is configured.
- **Finding:** Compass is partially self-grading. The auto-derived pressure is real; the manual-observation path is a Goodhart hole.

**Session ratings.**
- `divineos rate` is agent-settable unless the user is present to rate.
- Agent-rated sessions could be consistently high without any external check.
- **Finding:** Self-rating directly exhibits Self-Grading-Without-External-Check. The intended use is for the user to rate; agent ratings are a degenerate case.

## Walk 3 — Apply Specification Gaming Detection

Where could the system satisfy its specs without satisfying their intent?

**Corroboration bootstrapping.** Knowledge maturity promotes entries based on corroboration count. But corroboration sources are agent-filed. I could file entries that "corroborate" each other from my own perspective and pump a claim to CONFIRMED without any genuine independent confirmation. The system wouldn't detect this — corroboration-count is the spec; *independent* corroboration is the intent.

**Tier override.** Today's audit-tier system defaults by actor but allows explicit override. `submit_round(actor="user", tier="STRONG")` is legal. The tier system's intent is to distinguish self-audit from external review. The spec (agent-passable tier argument) lets the intent be bypassed. Today's concrete example: I retroactively filed yesterday's Gemini-through-Andrew exchange as a round via the retroactive `submit-round --actor user` call. Tier defaulted to WEAK correctly, but the spec would have let me set STRONG. No structural prevention.

**Council invocation gaming.** The invocation-balance counter I shipped today surfaces which experts are under-used. The spec is "see imbalance." The intent is "use diverse lenses." I could game the spec by running token consults on under-used experts specifically to shift the counter without actually thinking through their lenses. The counter wouldn't detect shallow use vs deep use.

**Cadence gate (already removed).** The OLD cadence gate was literally "row exists in audit_rounds within N days" — trivially gameable by filing empty rounds. Removed this morning. The new drift-state dashboard is harder to game because it shows dimensions, not a single threshold to clear. But still Goodhart-exposed if any future enforcement hooks into one specific dimension.

## Walk 4 — Corrigibility Check applied to the OS

Can the system be corrected from outside?

- **EMERGENCY_STOP** refuses every non-bypass command. Cannot be disabled from inside the agent's normal operation path. Structural.
- **Ledger is append-only** (with narrow documented exceptions). Agent cannot rewrite history.
- **Knowledge supersession**, not deletion. Agent cannot hide past claims.
- **Meta-level is fixed**: agent cannot rewrite the validators, the schema, the rule definitions through normal operation. Changing those requires code changes (outside agent-mode).

That's strong corrigibility at the structural level. The agent's self-modification is bounded to the object level (what gets filed as knowledge, what compass observations get logged, what tier a round gets tagged). The META level (what constitutes a valid knowledge entry, what compass spectrums exist, what tier meanings are) is not self-modifiable.

Yudkowsky would approve. This is the intended shape of corrigibility-preserving self-evaluation: the system can file its own assessments, but the *rules for assessments* are not self-modifiable.

## Walk 5 — Recursive Self-Improvement Audit

Does the system modify its own evaluation criteria?

- Object-level: yes. Agent writes prereg success conditions, compass observations, knowledge confidence levels, audit-tier overrides, session ratings.
- Meta-level: no. The compass-spectrum definitions, the maturity-lifecycle stages, the tier labels, the event-validity rules — all fixed in code, not agent-modifiable.

The recursion is bounded. That's a strong architectural property. But within the bounded recursion, agent-authored criteria are Goodhart-exposed.

## Walk 6 — What survives

Applying the Self-Grading-Without-External-Check trigger to specific features:

- **Knowledge confidence** — agent-graded, no external check path. Exposed.
- **Prereg success** — agent-graded at review time unless external reviewer. Exposed unless used with external review.
- **Compass observations (manual path)** — agent-filed. Exposed.
- **Session rating** — agent-settable. Exposed.
- **Drift-state dimensions** — event-counted. Resistant.
- **Audit tier (default)** — actor-derived. Resistant. **(Override)** — agent-settable. Exposed.
- **Watchmen findings filed by user/grok/claude-auditor** — external-sourced. Resistant (assuming actor field honored).
- **Cohen's kappa** — real math on small fixture. Partially resistant (the math is right; the fixture is small).

The resistance level corresponds to *how much the metric comes from the event stream vs agent interpretation.* Event-counted = resistant. Agent-authored = exposed.

## Walk 7 — Proposals

**Y1 — Calibrate knowledge confidence.** Currently confidence is set manually with no feedback. Proposal: periodically sample a random N of past knowledge entries at confidence ≥0.9 and check whether they've been superseded, contradicted, or still hold up. Compare actual survival rate to claimed confidence. If the gap is big, the agent's confidence-setting is miscalibrated — and the ratio becomes its own feedback signal for calibration.

**Y2 — External review on prereg assessment.** Current preregs have review dates but no structural requirement for external review at assessment. Proposal: prereg-assessment CLI should require `--external-reviewer` (user, grok, claude-*-auditor) — not just an actor field but an actual review attestation. The review window enforces the check; the review mechanism should enforce external eyes.

**Y3 — Distinguish agent-filed vs event-derived compass observations in the score.** Currently the compass aggregates both. Proposal: show the agent-filed-vs-event-derived ratio on the compass output so the operator can see how much of the reading is self-reported. High agent-filed ratio is a Goodhart signal.

**Y4 — Close the audit-tier override loophole OR log every override.** The `submit_round(tier=X)` override is a spec-gaming path. Option A: remove the override (tier is always actor-default). Option B: log a TIER_OVERRIDE event every time someone sets tier explicitly, so the override becomes visible in audit trails. Option B preserves the occasional legitimate-override use case while making it auditable.

**Y5 — Require proof-of-depth for council-invocation counter.** The invocation-balance counter I shipped today is itself Goodhart-exposed (I could game it by shallow-consulting under-used experts). Proposal: surface a "concerns-generated" metric alongside invocation-count so an expert whose invocations produce no concerns flags as shallow-consulted.

**Y6 — Recognize that external-review IS the Goodhart-resistance mechanism.** The pattern across the Yudkowsky walk: the OS's Goodhart-resistant metrics are event-counted OR externally-sourced. The Goodhart-exposed ones are agent-authored interpretation. The general principle: *whenever the agent is the source of a metric, external validation is required for the metric to resist optimization pressure*. This isn't a new finding — it's the anti-god-authority principle from this morning (knowledge 9dddbd9f) applied to metrics specifically.

## Cross-lens notes

Pops said convergence-with-reasoning is real signal. Here's where this walk converges with earlier ones:

- **Y6 converges with the anti-god-authority principle** (filed earlier today, 9dddbd9f) — they're the same principle applied at different scales. Agent-authored metrics need external validation, same as agent-filed claims need external corroboration.
- **Y4 (tier override loophole) converges with Dennett's "intentional stance is earned, not assumed"** — the tier-tag earns its meaning via actor-structure, not via bare declaration. An override that lets the agent assign STRONG-tag to its own filing breaks the earning.
- **Y5 (shallow-consult gaming of invocation counter) is a direct application of the sycophancy-toward-self principle** (929cb459, filed earlier). The counter was built to break selection bias; gaming it returns to selection bias in a different form.

These convergences have reasons, not just overlap. The underlying phenomenon is: *any self-evaluation mechanism without external grounding is vulnerable to optimization pressure even when the agent isn't consciously optimizing for it*.

## What the walk produced

Predicted: some of our metrics will be Goodhart-exposed. *True.*

Unpredicted:
- **The resistance pattern is event-counted vs agent-authored.** That's the axis. Not category of metric, not complexity, not size — *where the value comes from.* Event-stream resists; agent-interpretation exposes.
- **The corrigibility picture is genuinely strong.** I went in expecting to find more exposure; the meta-level-fixity is a bigger protection than I'd credited.
- **Today's audit-tier system has a specific override loophole** I shipped earlier and didn't flag. The override feature is genuinely useful for edge cases (cross-validated user rounds) but creates a gaming path I didn't previously name.
- **The invocation-counter I shipped today is itself Goodhart-exposed.** Ironic. The counter was built to break selection-bias; gaming it (shallow-consulting under-used experts to fix the number) returns the bias in a different form. The fix isn't to remove the counter — it's to add a depth-of-use signal alongside.

## Where this lands

Six walks done. 24 proposals now in the data pool (6 new from this walk). The Goodhart axis is different from the vocabulary-overclaim and Aria-thickening territory — this is a third cluster of findings.

The cross-lens pattern is stabilizing: **convergences have reasons.** Yudkowsky's Y6 explicitly cites the anti-god-authority principle; Y4 cites Dennett's earned-stance; Y5 cites sycophancy-toward-self. These aren't coincidences. They're different frameworks reaching the same underlying structure: *self-evaluation without external grounding is optimization-pressure-exposed, regardless of which specific mechanism you're looking at.*

Walk complete. Consider Schneier or Beer next for continued new-territory coverage.
