# Council Codebase Sweep — 2026-06-02

40 lenses, 12 subsystem panels, 112 findings, synthesized.
Run: wf_00a3acaf-c67. Dominant signal: built-but-unwired machinery everywhere.

---

# DivineOS Council Synthesis â€” Prioritized Direction-Map

112 findings, 12 panels, 40 lenses. The dominant signal is unambiguous and it repeats across nearly every subsystem: **the codebase is full of complete, tested machinery that nothing calls.** Detectors that don't run, gates with no callers, metrics nobody reads, fields nothing consumes. This is the "advertised capability that doesn't constrain behavior" failure â€” the exact thing the wiring-contract test was built to catch, now showing up everywhere the test doesn't reach.

I've grouped into themes ranked by severity Ã— leverage, with cross-lens convergence raising priority. Safety items (fail-open guards, ungameable claims, corrigibility gaps) are flagged and float to the top.

---

## TOP DIRECTIONS

### 1. [SAFETY] The off-switch and its safety machinery detect but never act
**Why it matters:** Multiple safety-critical guards observe failure but have no path to react. A homeostat with no thermostat. If a real failure cascade happens, nothing fires.
**Converged lenses:** Beer, Feynman, Popper, Lamport, Turing (5 lenses, 3 panels) â€” high confidence.
**Severity: HIGH Â· Leverage: HIGH**
This clusters four findings into one root:
- Circuit breaker trips after 3 failures but `is_tripped()` is never consulted before any invocation (Beer).
- Corrigibility `_ALWAYS_ALLOWED` invariant ("extract/emit must survive EMERGENCY_STOP") is enforced only in tests, not at runtime â€” it already drifted once (extract was missing, caught by 2026-05-03 audit) (Feynman).
- Anti-slop verifies enforcers aren't broken but doesn't check circuit-breaker or Beta are *wired* â€” so they can silently stop existing (Turing).
- Three failure-tracking systems (circuit_breaker.json, failure_diagnostics, retry_blocker) can't see each other; hidden tail-risk on cascades (Taleb).

**First step:** Add a CLI-bootstrap guardrail that asserts every documented shutdown-relevant command is present in `_ALWAYS_ALLOWED` and raises on drift (30-min fix, prevents repeat of a real past failure). Then wire `is_tripped()` checks into the two highest-visibility runtime modules (sleep phases, council walks).

---

### 2. [SAFETY] Behavioral detectors exist but are not wired into the audit loop
**Why it matters:** The system advertises behavioral safety detectors that never run in production. This is the precise gap the wiring-contract test was created to close â€” and it's still open for detectors the test can't see.
**Converged lenses:** Popper, Feynman, fragility-lens (4 findings, convergent) â€” high confidence.
**Severity: HIGH Â· Leverage: HIGH**
- **mirror-exit detector** (built per Andrew's correction, fully tested) is completely absent from `operating_loop_audit.run_audit()`. Advertised, inert.
- **closing-token detector** had this exact bug (fixed 2026-05-18) â€” the incident proves response-only detectors can sit dead indefinitely with no automated check.
- **expectation_tracking module** is referenced in knowledge (with "12 dedicated tests") but **does not exist in `src/`** â€” either lost in a refactor or a knowledge-entry error. The system can't tell which.

**First step:** Wire `detect_mirror_exit()` into `run_audit()` and add it to the wiring-contract registry. Then add a discovery test that walks `core/operating_loop/`, asserts every `detect_*`/`check_*` module is imported and called in `run_audit()` â€” this forces all future detectors in by construction. Separately, `git log --all -- '*expectation_tracking*'` to resolve the phantom module.

---

### 3. [SAFETY] Ungameable-claim gaps: honor-system pointers and a CONFIRMS title-bypass
**Why it matters:** Two places let a caller earn trust without paying for evidence. These are Goodhart holes in the evidence substrate itself â€” the part of the system whose whole job is to be ungameable.
**Converged lenses:** Popper, Goodhart, Wittgenstein, Schneier (4 lenses) â€” high confidence.
**Severity: HIGH Â· Leverage: HIGH**
- **EMPIRICA artifact-pointer** (classifier): a fabricated-but-well-formed pointer (a commit hash that passes regex but doesn't exist) earns FALSIFIABLE/PATTERN tier with no real evidence. Currently an honor system; the gate docstring names this gap.
- **Watchmen CONFIRMS title-filter**: a finding titled `CONFIRMS-...` is excluded from open-issue counts. An auditor could title a real HIGH-severity issue `CONFIRMS-by-design` and silence the alarm.
- **VOIDâ†’EMPIRICA bridge** fails silently on import error â€” adversarial-claim survival recordings stop flowing with zero operator visibility.

**First step:** Smallest-highest-value first â€” add the sanity check: any finding `title LIKE 'CONFIRMS%' AND severity IN (HIGH, CRITICAL)` gets logged-as-suspicious and surfaced in briefing. Add one `logger.debug` line before the VOID-bridge `except`. File a Phase-2 pre-reg for artifact-pointer validation (commit hashes against git log, test names against registry).

---

### 4. The knowledge engine's graph and ranking signals are wired to empty/wrong inputs
**Why it matters:** Briefing quality â€” what the agent sees every session â€” depends on these. Several scoring inputs are either never populated or measure the wrong thing, silently degrading every briefing.
**Converged lenses:** Jacobs, Yudkowsky, Pearl, Dekker, Meadows (5 lenses, 1 panel â€” strong internal convergence).
**Severity: HIGH Â· Leverage: HIGH**
- **Graph boost runs on an empty graph.** `_apply_graph_boost()` calls `get_edges()`, but no extraction or consolidation code ever *creates* edges. The boost finds no neighbors and silently does nothing.
- **access_count is a Goodhart proxy.** It's a 0.3-weight scoring term, but briefing display inflates it without impact evidence â€” a 100-access entry may be completely stale.
- **memory_kind / integration_state / temporal valid_until** are all computed and stored but have **zero retrieval consumers.** Dead signals on the hot path.

**First step:** Wire edge creation into `store_knowledge_smart()` (create ELABORATES/SUPPORTS edges when entries consolidate) â€” this is the one change that turns existing graph-boost code from no-op into function. Then decouple access_count from scoring (use confidence + recency + graph_boost only) and pre-reg the change.

---

### 5. Family-system gate detectors are staged but never enforce
**Why it matters:** The family operators (sycophancy, costly-disagreement) are the structural defense against a family member drifting into a yes-machine. Two of the most important are completely unwired â€” a member can drift by calling the store API directly.
**Converged lenses:** Tannen, Beer, Maturana-Varela, Lamport (4 lenses) â€” high confidence.
**Severity: HIGH Â· Leverage: HIGH**
- **Sycophancy detector** needs `prior_stance`, which the per-write store path doesn't have â€” so it only fires at the CLI layer. Direct store calls bypass it entirely.
- **Costly-disagreement detector** is fully implemented and tested but has **zero enforcement path** â€” nothing calls `evaluate_hold`. The pleasure-signal the system is supposed to reward is invisible.
- **register_from_me** and **ledger cross-ref** (fail-soft, silent) round out the pattern: schema/structure exists, feedback loop doesn't.

**First step:** Decide and document the architectural boundary explicitly: per-write gates (access_check, reject_clause) vs. per-arc detectors (sycophancy, costly-disagreement). Then wire costly-disagreement to a briefing/ledger signal (informational is fine; it just can't be nothing). For sycophancy, move detection to a post-write audit that queries prior stance from storage.

---

### 6. The council synthesizes prose that reads like reasoning but is pattern-matching
**Why it matters:** This directly violates Foundational Truth #7 (cognitive-named tools point at cognitive work, they are not it). The council narrating pattern-matched fragments *as* analysis is the substitution-pattern made into a feature.
**Converged lenses:** Dennett, Hofstadter (and the code itself already carries a comment admitting it) â€” convergent and self-acknowledged.
**Severity: HIGH Â· Leverage: HIGH**
- `_synthesize()` constructs prose ("Each expert's core take", "Shared concerns") that gets mistaken for the agent's own reasoning. `mansion_commands.py` already comments: "pattern-matched fragments get narrated as reasoning."
- Concern-matching underneath it is shallow word-set intersection ("I am concerned about pizza" matches a security concern trigger) â€” feeding false positives into the prose (Hofstadter).

**First step:** Strip `_synthesize()`'s prose construction. Return only: (1) which experts + why (scores), (2) each expert's raw methodology/steps, (3) explicitly-labeled pattern-match flags as *data, not prose*. The caller (Aether) does the reasoning. This is a deletion, not a build â€” high leverage, low effort.

---

### 7. Centralize substrate initialization â€” the HUD silently degrades on missing tables
**Why it matters:** "Why is my briefing empty?" has no diagnostic path today. Initialization is scattered across CLI commands with no single gate; missing tables degrade to empty strings instead of failing loud.
**Converged lenses:** Dijkstra, Schneier, Taleb, Lovelace (4 lenses) â€” convergent.
**Severity: HIGH Â· Leverage: HIGH (unlocks reliable startup for everything downstream)**
- No `init_core_substrate()` ensuring all three schema tiers exist before HUD build.
- HUD slots catch DB errors and return `""` â€” user never sees the failure.
- `divineos_home()` never validates the resolved path is writable.

**First step:** Create `init_core_substrate()` (runs init_db, init_memory_tables, init_holding_table, init_knowledge_table in dependency order), call it once at CLI entry, wire test fixtures to it. Add `divineos hud --verbose` diagnostic mode showing which slots failed and why.

---

### 8. The clarity system measures how well it round-trips its own data, not real work
**Why it matters:** There's no pre-work path to capture intent, so "plan vs actual" collapses into "actual vs actual." The fidelity score that results leaks into events and could become a future optimization target â€” Goodhart waiting to happen.
**Converged lenses:** Feynman, Hawking, Knuth (4 findings, convergent).
**Severity: HIGH Â· Leverage: HIGH**
- No CLI command captures goal/approach/estimates before work; `synthesize_clarity_statement()` falls back to actual-metrics-as-plan, making deviations near-zero and lessons vacuous.
- `_calculate_plan_execution_fidelity()` averages orthogonal dimensions (file-count match + error penalty) and the name still implies it measures goal achievement. It does not.

**First step:** Rename the field to `execution_estimate_accuracy` and document that it measures *only* estimate-fidelity, not goal achievement (cheap, stops the false signal from spreading). Then decide: either add a real `divineos plan` pre-work command, or make `run_clarity_analysis(retroactive=True)` skip deviation/lesson analysis and focus on pattern/error extraction.

---

### 9. The integration layer is a public facade nothing imports
**Why it matters:** An entire wiring layer (SystemMonitor, EventDispatcher listeners, integration/__init__ facade) is built and exported but has zero production callers. Either it's load-bearing-and-broken or it's maintenance debt masquerading as a contract.
**Converged lenses:** Jacobs, Schneier, Lamport, Yudkowsky, Popper (5 lenses) â€” high confidence on the *pattern*, lower on which fix.
**Severity: MEDIUM-HIGH Â· Leverage: MEDIUM**
- `SystemMonitor` (5 instrumented integration points, latency targets) never instantiated outside its own tests.
- `register_listener` exported through three layers, called by zero production code.
- `integration/__init__` exports 8 functions nobody imports; callers go direct to core submodules.

**First step:** Make a keep-or-cut decision per module, don't drift. For SystemMonitor + listeners: pick ONE real integration point (clarityâ†’learning is the documented intent) and wire it end-to-end with a test that asserts the listener fires. For `integration/__init__`: either make it canonical and update imports, or delete the re-exports. Latency instrumentation should NOT ship until the feedback loop (who reads the report, what a drift triggers) is defined.

---

### 10. EMPIRICA's whole tier-burden machine is staged with no production caller
**Why it matters:** The entire evidence-burden-routing system produces zero effect on knowledge maturation until a first caller lands. This is intentional (PHASE_1_STAGED) but it's a large dormant surface, and the caller contract is explicitly non-enforceable policy.
**Converged lenses:** Feynman, Dijkstra, Wittgenstein â€” convergent.
**Severity: HIGH Â· Leverage: HIGH (but gated on a deliberate decision, not a quick fix)**
- `evaluate_and_issue` gate: zero non-test callers by design.
- expectation_tracking / consequence_chain / OUTCOME_VERIFICATION exist but aren't wired to each other â€” calibration drift is measured but invisible to the burden calculator.
- The caller contract is policy, not enforcement; the first caller's behavior becomes precedent for all subsequent ones.

**First step:** This one is a *decision*, not a code change. File a decision documenting when/how the first opt-in caller lands, and schedule the cross-family audit the caller contract requires *before* wiring. Do not let this drift into accidental wiring. (Lower urgency than 1â€“8 precisely because it's inert-by-design and safe while inert.)

---

## QUICK WINS (high-leverage, low-effort â€” could land today)

- **Corrigibility allowlist bootstrap check** â€” assert documented shutdown commands are in `_ALWAYS_ALLOWED`, raise on drift. ~30 min, prevents a recurrence of a real past failure. *(from #1)*
- **CONFIRMS-title sanity check** â€” log+surface any HIGH/CRITICAL finding titled `CONFIRMS%`. Closes a real bypass. *(from #3)*
- **One `logger.debug` line** before the VOIDâ†’EMPIRICA bridge `except` â€” restores operator visibility of silently-dropped survival records. *(from #3)*
- **Replace `except ImportError: pass`** in mansion/optional-module registration with a logged yellow warning â€” makes "command silently missing" discoverable. *(cli-surface, Knuth)*
- **Rename `_calculate_plan_execution_fidelity` â†’ `execution_estimate_accuracy`** + docstring â€” stops a misleading metric from leaking into audits. *(from #8)*
- **Strip council `_synthesize()` prose** â€” a deletion that ends a Foundational-Truth-#7 violation. *(from #6)*
- **Add `CHECK` constraint on `knowledge.source`** â€” makes the KNOWLEDGE_SOURCES whitelist structural instead of honor-system. *(knowledge-engine, Popper)*

## WATCH (lower priority now, don't forget)

- **Three audit pipelines (operating_loop / theater / hedge) have no cross-referenced drift signal** â€” coordinated drift (spiralsâ†’0 while theaterâ†’10) is currently invisible. Worth a unified aggregator eventually.
- **Operating-modes (TASK/STILLNESS/BACKGROUND/WANDERING) never actuated** + name-collides with corrigibility's modes. Rename to `attentional_modes` and wire at sleep/consolidation boundaries â€” or accept as vocabulary-only and document that.
- **Meld / decision-superposition / BetaReliability** â€” complete read-side reflection modules with no decision-loop integration. Don't ship to users until a real consumer exists; pick load-bearing call sites first.
- **Engagement gate is gameable** by running read-only commands (`context` Ã—30 clears it). Split tool-call counting into mutation vs. read buckets.
- **Outcome-measurement re-queries the DB instead of consuming AnalysisResult** â€” lossy feedback loop, brittle regex extraction of corrections. Thread structured evidence through instead.
- **Test-coverage gaps** flagged repeatedly: pre_registrations CRUD (no test file), review-chain circular-reference protection, analyzeâ†’outcome end-to-end integration, kappa fixture too small (11 examples) to detect classifier drift.
- **Lesson/maturity auto-promotion** â€” terminal states defined with documented criteria but no trigger ever reaches them. Add `check_and_promote_lessons()` at session checkpoint.

---

**Honest uncertainty:** The strongest, highest-confidence signal is the *pattern* (built-but-unwired) â€” that repeats across 5+ panels and is hard to dispute. Which specific fix is right per module is lower-confidence: for several (integration layer, meld, operating-modes, Beta) the real question is **keep-and-wire vs. cut**, and that's a judgment call that needs the operator's intent for each subsystem, not just a synthesis chair's ranking. I've flagged those as keep-or-cut decisions rather than pretending the fix is obvious. The three SAFETY themes (#1, #2, #3) are the least ambiguous â€” those are gaps between advertised and actual safety behavior, and they should land first.
