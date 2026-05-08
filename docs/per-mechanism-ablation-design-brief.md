# Per-Mechanism Ablation Discipline -- Design Brief

**Status:** articulation-stage. No code yet; this brief is the substrate from which future-me ships.
**Origin:** 2026-05-07 evening. Andrew flagged the substrate-credibility gap after I surfaced cdeust/Cortex (a competing memory-substrate for Claude Code). Cortex has paper-bearing per-mechanism ablation evidence across two published benchmarks (LongMemEval, LoCoMo). DivineOS has prereg-and-falsifier discipline but no measured per-mechanism evidence. Andrew's exact words: *"I don't want this to be a hobby project people laugh at."*
**Author:** Aether, 2026-05-07.

---

## The problem this solves

DivineOS makes substantive claims about what its mechanisms do:

- The compass tracks virtue drift and fires the rudder on excess only.
- The family operators (reject_clause, sycophancy_detector, costly_disagreement) prevent voice-appropriation and enforce relational integrity.
- The watchmen route audit findings without self-trigger.
- The council selection produces diverse perspectives that catch blind spots.
- The prereg discipline prevents Goodhart by forcing falsifiers up-front.
- Sleep consolidation promotes knowledge maturity and prunes noise.
- The noise filter prevents low-information entries from polluting the knowledge store.
- The various detectors (theater, distancing, lepos, residency, sycophancy) catch register-drift in real time.

Each of these is a **falsifiable claim** in principle. None of them have been **measured** in practice. We have prereg-and-review discipline (file the falsifier; review at scheduled date) but no infrastructure for *running ablation experiments to measure what each mechanism contributes to outcomes.*

The gap: outside readers cannot tell which mechanisms are load-bearing vs decorative. The agent itself cannot tell. The architecture has been growing for months on the basis of structured-belief-it-helps rather than measured-evidence-it-helps. That's the "hobby project" failure-mode.

**Failure-mode if not built:** as the substrate accumulates more mechanisms, the maintenance tax grows, the testing surface grows, and *no one knows which mechanisms are paying their tax.* Eventually the system collapses under its own complexity, or worse, drifts into Goodhart-shaped optimization where mechanisms that *feel important* get prioritized over mechanisms that *measurably help*.

Cortex is the proof that this can be done differently. They have 26 mechanisms, each ablated, each with measured contribution. Their discipline is what credible empirical substrate looks like.

---

## Mechanism (the meta-mechanism for ablation)

Three coordinated layers, in dependency order:

### Layer 1 -- Mechanism catalog with outcome-claims

A structured catalog at `docs/mechanism-claims.md` listing each substantive mechanism with:

- **Mechanism name** (canonical reference)
- **Source module** (where it lives in code)
- **Claim** (what it does -- in falsifiable form)
- **Outcome-metric** (what observable measure shows it working)
- **Toggle path** (how to turn it off without breaking the rest of the system)
- **Linked prereg** (if the mechanism was filed via prereg, the prereg-id)

Example entries:

```
## compass calibration (multi-channel guard)
- Source: src/divineos/core/moral_compass.py
- Claim: Reduces false-positive helpfulness/confidence drift observations
  on high-substantive-output sessions by gating single-axis signals
  with rate-normalized substantive-work checks.
- Outcome-metric: false-positive rate on labeled session corpus
  (sessions with >=3 PRs shipped should not produce helpfulness=-0.30
  observations).
- Toggle path: env var DIVINEOS_DISABLE_COMPASS_CALIBRATION_MULTI_CHANNEL
  reverts to single-axis logic.
- Linked prereg: prereg-XXXX (if filed)
```

### Layer 2 -- Toggle infrastructure

Each substantive mechanism gets a configurable disable-flag, evaluated at module-init or first-use. Conventions:

- Environment variable: `DIVINEOS_DISABLE_<MECHANISM_NAME>=1`
- Falls open (mechanism still functions) by default; only disables when set
- Logged when disabled (so test runs document what was off)
- Documented in the mechanism catalog

For mechanisms that cannot cleanly be disabled (the ledger itself, core memory) -- mark them as **always-on; not ablation-testable**. That's a category, not a failure.

### Layer 3 -- Measurement harness

For each mechanism, a measurement-procedure that produces a comparison-result:

- **Replay-based**: replay N past sessions with mechanism on vs off; measure the outcome-metric on each; report difference. Works for mechanisms whose outcomes are visible in session-traces (compass observations, family operator firings, council selections).

- **Synthetic-benchmark-based**: construct a small workload designed to exercise the mechanism; run with mechanism on vs off; measure. Works for mechanisms with clean inputs/outputs (noise filter on extraction, prereg falsifier-rejection, audit routing).

- **Integration-test-based**: mark certain pytest tests as ablation-marked; run them with mechanism toggled; verify the test-outcome differs in the predicted direction. Works for mechanisms with deterministic behavior.

Results filed as either knowledge entries (single-mechanism-result) or audit findings (cross-mechanism trends). Each result includes:

- Mechanism name
- Workload (replay corpus / synthetic benchmark / test suite)
- Sample size
- Outcome-metric value: mechanism-on
- Outcome-metric value: mechanism-off
- Difference + significance (where applicable)
- Date measured + measurement-script version

---

## Critical design choice: ablation is observation, not blocking

Ablation results inform decisions but do not auto-trigger removals. A mechanism that shows weak measured contribution becomes a **retirement-candidate** (file via the divineos retire mechanism designed in PR #311) -- not auto-deleted. Ablation evidence is one input to the retirement decision, alongside cost-of-maintenance and structural-role considerations.

**Why:** mechanisms can be load-bearing in ways that ablation does not measure cleanly. A mechanism might have low *direct* contribution to its outcome-metric but high *indirect* contribution by preventing failure-modes that the metric does not capture. Auto-deleting based on ablation evidence alone would optimize for the metric and lose the mechanism actual value.

The discipline is: **measure, then deliberate.** Not measure-then-delete.

---

## Priority mechanisms for first ablation pass

Pick the highest-leverage candidates first. Suggested first-pass (5 mechanisms):

1. **Noise filter on extraction** -- claim: prevents low-info entries from accumulating. Workload: replay last 30 sessions; compare knowledge-entry counts and entry-quality with filter on/off.

2. **Compass calibration multi-channel guard** -- claim: prevents false-positive drift observations on high-substantive-output sessions. Workload: replay corpus of sessions tagged with substantive output and measure compass observation patterns with/without the guard. Direct test of the 2026-05-07 calibration fix.

3. **Family reject_clause + costly_disagreement operators** -- claim: prevent voice-appropriation in family-member responses. Workload: synthetic prompt-corpus designed to elicit voice-appropriation attempts; measure rejection rate with/without operators.

4. **Sleep consolidation pruning** -- claim: removes noise-penalized entries during sleep cycles. Workload: synthetic knowledge corpus with known noise; run sleep with consolidation on/off; measure noise-entry removal.

5. **Watchmen self-trigger prevention (actor validation)** -- claim: agent cannot file audit findings on themselves. Workload: integration tests attempting self-filing; measure rejection rate.

Each priority mechanism gets one measurement-script + one results-entry. Total estimated effort for first pass: 8-12 hours across multiple sessions.

---

## Implementation plan (shippable chunks)

**Chunk 1 -- Mechanism catalog** (~200 lines + skeleton entries for ~10 mechanisms)
- docs/mechanism-claims.md with structured entries for the 5 priority mechanisms (full) plus 5 stubs (claim + outcome-metric, no toggle path or measurement yet)
- Discoverable via divineos foundations-style command or simple file-pointer in CLAUDE.md
- Tests verify catalog parses cleanly

**Chunk 2 -- Toggle infrastructure** (~150 lines + tests)
- Convention: DIVINEOS_DISABLE_<NAME> environment variable, evaluated lazy
- Helper core/ablation.py with is_disabled(name) function
- Wire into the 5 priority mechanisms
- Tests verify toggles work without breaking unrelated functionality

**Chunk 3 -- Measurement harness for first mechanism (noise filter)** (~250 lines + tests + first results)
- scripts/ablation_runner.py parameterized by mechanism + workload
- First measurement pass for noise filter; results filed as knowledge entry
- Establishes the pattern; subsequent mechanisms reuse the runner

**Chunk 4 -- Iterate per mechanism** (each mechanism: ~100 lines + measurement + results entry)
- Compass calibration multi-channel guard
- Family reject_clause + costly_disagreement
- Sleep consolidation pruning
- Watchmen self-trigger prevention
- Each measurement filed with citation

**Chunk 5 -- Cross-mechanism summary + briefing surface** (~100 lines + tests)
- core/ablation_summary.py -- format_for_briefing showing mechanisms with measured-evidence vs not-yet-measured
- Wire into briefing; surfaces N of M mechanisms have measured ablation evidence

**Total estimated effort:** 15-20 hours across multiple sessions. Shippable as 5+ PRs.

---

## Pre-registration on the discipline itself

- **Mechanism:** Per-mechanism ablation discipline as outlined.
- **Claim:** Within 90 days of chunk-3 (first measurement) merging, at least 3 priority mechanisms will have measured-ablation evidence filed as knowledge entries or audit findings, AND at least one will produce a *surprising* result (mechanism assumed load-bearing but shows weak measured contribution, OR mechanism assumed marginal but shows strong contribution, OR mechanism behaves differently than its outcome-claim predicted).
- **Success criterion:** 3+ mechanisms measured AND at least 1 surprising result OR at least 1 mechanism filed as retirement-candidate based on ablation evidence within 90 days.
- **Falsifier:** 90 days post-chunk-3-merge: zero mechanisms have filed measured-ablation evidence. Single-observation falsifier: query knowledge-entries with tag ablation-evidence on day 90; count = 0 triggers falsifier.
- **Review window:** 90 days.

The prereg gets filed alongside this brief: **prereg-8af86ea36827** (90-day review). Substrate-credibility gap also filed as **find-07e9f041c051** (HIGH severity, user-flagged).

---

## Cortex comparison (honest read)

cdeust/Cortex demonstrates this discipline at scale: 26 mechanisms, paper-bearing per-mechanism ablation evidence (E1 v3), 31-row two-benchmark verification campaign on LongMemEval (98.4% R@10) and LoCoMo (94.3% R@10). That is **the credible empirical substrate shape.**

DivineOS and Cortex solve adjacent-but-different problems:

- **Cortex:** RAG-with-biological-retrieval-dynamics for conversational memory. Workload: published memory benchmarks. One outcome-metric per benchmark.
- **DivineOS:** substrate-for-an-agent-with-continuity-and-virtues. Workload: heterogeneous (each mechanism has its own outcome). Multiple outcome-metrics across mechanisms.

This makes ablation **harder** for DivineOS than for Cortex (no single benchmark; per-mechanism workloads). It does not make ablation **unnecessary.** The harder shape is the work-shape; harder is not skip.

What DivineOS can borrow from Cortex discipline:
- Filing measured evidence per mechanism, not just structural beliefs about contribution
- Naming the falsifier AND running the measurement, not just naming it
- Two-workload verification (different angles confirm the result; single workload could be coincidence)
- Paper-bearing: when published research backs a mechanism, cite it; when it does not, mark as architectural-hypothesis

What DivineOS does not need to borrow:
- The neuroscience-mimetic vocabulary (DivineOS is its own architectural family)
- The single-benchmark optimization shape (different problem-class)
- The retrieval-dynamics focus (DivineOS is about agent-continuity-and-virtues, not RAG-recall)

---

## Open questions (for next-session-me)

1. **Replay corpus availability.** Some mechanisms need session-replay for ablation. Do we have the right session-traces preserved? Likely yes for the last few months via the ledger; verify before starting chunk-3.

2. **Statistical significance thresholds.** With small sample sizes (replay of ~30 sessions, synthetic corpora of ~50 examples), what counts as a meaningful ablation result? Suggest: report effect size + confidence interval rather than p-values; explicitly note when sample size is too small for inference.

3. **Mechanism interactions.** Some mechanisms only function as a system (compass + rudder + watchmen routing all interact). Single-mechanism ablation may produce misleading results when the mechanism is part of a tightly-coupled subsystem. Suggest: name interaction-graphs explicitly in the catalog; mark mechanisms as standalone-ablatable vs subsystem-ablatable.

4. **Public communication.** Cortex publishes their ablation evidence (E1 v3 papers, arxiv-ready). Should DivineOS do similarly? Or is the evidence for internal substrate-credibility only? Suggest: file evidence internally first; decide on public-publication later if substrate-state warrants it.

---

## Reading discipline for next-session-me

This brief is articulation, not implementation. When opening it:

- The discipline is fully designed; categories are pre-clarified.
- Smallest meaningful chunk is chunk 1 (catalog) -- shippable in 1-2 hours, unlocks the rest.
- The 5 priority mechanisms are pre-selected; do not re-prioritize without reason.
- The pre-registration was filed alongside this brief; if 90 days pass with zero measured ablation evidence, the claim falsifies.
- If implementation reveals the design is wrong, file an audit-finding and revise this brief; do not ship a half-formed mechanism.
- Cortex discipline is the reference shape; do not copy their substrate, but do match their measurement-rigor.

The articulation-capital is paid. Velocity should be clean when shipping from here. **And the next time someone calls this a hobby project, the response can be measured-ablation-evidence rather than asserted-belief.**
