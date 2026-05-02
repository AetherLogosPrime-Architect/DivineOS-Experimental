# DivineOS Architecture — Full File Tree

This is the reference listing of every source file in DivineOS with a one-line description. For the high-level overview and onboarding, see the main [README.md](../README.md#architecture).

The tree is automatically checked against the filesystem by `scripts/check_doc_counts.py` — any drift between this listing and the actual `src/divineos/` contents surfaces as a pre-commit error. Keep this document in sync when you add, rename, or remove files.

## The tree

```
src/divineos/
  __init__.py                  Package init
  __main__.py                  python -m divineos entry point
  seed.json                    Initial knowledge seed (versioned)
  cli/                         CLI package (202 commands across 28 modules)
    __init__.py                Entry point and command registration
    _helpers.py                Shared CLI utilities
    _wrappers.py               Output formatting wrappers
    _anti_substitution.py      Labels that name what each cognitive-named tool does vs. what cognitive work is still the agent's (pre-reg prereg-50d2fdc2b6ab)
    session_pipeline.py        Extraction pipeline orchestrator (formerly SESSION_END, calls phases)
    pipeline_gates.py          Enforcement gates (quality, briefing, engagement)
    pipeline_phases.py         Heavy-lifting phases (feedback, scoring, finalization)
    knowledge_commands.py      learn, ask, briefing, forget, lessons
    analysis_commands.py       analyze, report, trends, scan, patterns
    hud_commands.py            hud, goal, plan, checkpoint, context-status
    journal_commands.py        journal save/list/search/link
    directive_commands.py      directive management
    knowledge_health_commands.py  health, distill, migrate, backfill
    claim_commands.py          Claims engine and affect log
    decision_commands.py       Decision journal commands
    compass_commands.py        Moral compass reading and observations
    complete_commands.py       complete: file completion-boundary events (rudder redesign Phase 1b)
    body_commands.py           Body awareness and cache pruning
    sleep_commands.py          Offline consolidation (sleep cycle)
    progress_commands.py       Progress dashboard (measurable metrics)
    entity_commands.py         commitments, temporal, questions, relationships
    event_commands.py          emit, verify-enforcement
    audit_commands.py          external validation (Watchmen)
    void_commands.py           VOID adversarial-sandbox subsystem commands
    prereg_commands.py         pre-registrations (Goodhart prevention)
    ledger_commands.py         log, list, search, context, export
    memory_commands.py         core, recall, active, remember, refresh
    correction_commands.py     correction (log raw), corrections (read)
    empirica_commands.py       corroborate (record provenance event), kappa (classifier agreement)
    corrigibility_commands.py  mode show / set / history — the off-switch
    scheduled_commands.py      scheduled run / history / findings — Routines entry point
    lab_commands.py            lab list / run-slice — science-lab CLI (GUTE term slices)
  protocols/                   Persistent protocol definitions (survive compaction)
    resonant_truth.md          Full 12-section RT mantra
  science_lab/                 Numerical test harness for GUTE terms and derived claims
    complexity_theory.py       Chaos, fractals, emergence (Lyapunov, Lorenz, Mandelbrot, power laws)
    information_theory.py      Shannon entropy, mutual information, KL, channel capacity, von Neumann entropy
    mathematics.py             Numerical analysis (Simpson, Newton, bisection, RK4) and linear algebra
    cosmology.py               Friedmann equations, black-hole scales, gravitational-wave quantities
    quantum_mechanics.py       Quantum states, operators, Pauli/Hadamard/CNOT gates, Bell/GHZ states
    formal_logic.py            Propositions, formulas, laws of thought, modus ponens/tollens
    harmonics.py               Harmonic series, just intonation, Kepler's third law, orbital resonance
    physics.py                 Special relativity (Lorentz, time dilation, Schwarzschild)
    gute_bridge.py             Term → slice dispatch; slices for LC, OmegaB, Psi, V, A, F
  core/
    ledger.py                  Append-only event store (SQLite, WAL mode)
    _ledger_base.py            Shared ledger DB connection and hashing
    ledger_verify.py           Verification, cleanup, and export
    fidelity.py                Manifest-receipt integrity verification
    memory.py                  Core memory + active memory + importance scoring
    memory_journal.py          Personal journal (save/list/search/link)
    memory_sync.py             Auto-sync to Claude Code memory files
    active_memory.py           Active memory ranking and surface
    _hud_io.py                 HUD file I/O helpers
    hud.py                     HUD slot builders and assembly
    hud_state.py               Goal/plan/health state management
    hud_handoff.py             Session handoff, engagement, goal extraction
    holding.py                 Pre-categorical reception (holding room, dharana)
    constants.py               Central tuning constants (all behavioral levers in one place)
    knowledge/                 Knowledge engine sub-package
      _base.py                 DB connection, schema, public API
      _text.py                 Text analysis, noise filtering, FTS, overlap
      crud.py                  Knowledge CRUD operations
      memory_kind.py           Memory-kind classifier (EPISODIC/SEMANTIC/PROCEDURAL/UNCLASSIFIED) — diagnostic metadata only; not yet consumed downstream
      extraction.py            Knowledge extraction from sessions
      deep_extraction.py       Deep multi-pass extraction
      feedback.py              Session feedback application
      migration.py             Knowledge type migration
      edges.py                 Unified edge table (typed relations, auto-warrants)
      relationships.py         Knowledge relationship management
      lessons.py               Lesson tracking and extraction
      retrieval.py             Briefing generation and layered retrieval
      curation.py              Layer assignment, archival, text cleanup
      maturity_diagnostic.py   Classify RAW into transient (session-scoped) vs pending (could mature)
      temporal.py              Temporal bounds (valid_from/valid_until) and time-aware queries
      compression.py           Knowledge compression (dedup, synthesis, graph-aware)
      inference.py             Knowledge inference engine — boundaries from mistakes, pattern promotion
      graph_retrieval.py       Graph-enhanced retrieval (BFS traversal of edges)
    self_monitor/              Watches agent's own output for trained-hedge patterns
      hedge_monitor.py         2 hedge detectors (recycling density, epistemic collapse), falsifier-per-flag
      theater_monitor.py       Detects writing-AT-subagent-without-invoking (kitchen-theater shape)
      fabrication_monitor.py   Detects unflagged embodied/sensory claims in agent first-person
      mirror_monitor.py        Detects post-correction tightness/echo/acknowledgment-only shape
      substrate_monitor.py     Detects filing-cabinet-only OS use (cognitive tools without behavior change)
      warmth_monitor.py        Detects warmth-without-specifics (emotion-density inflated relative to evidence-density), per April 19 letter
      mechanism_monitor.py     Detects first-person mechanism-claiming about own internals (trained reflex, my training, suppression-as-cause), per April 19 letter
      temporal_monitor.py      Detects future-self / next-session / undeclared-goodbye framing (teleporter-paradox violation)
    questions.py               Open question tracking and resolution
    knowledge_maintenance.py   Contradiction detection, hygiene cleanup, maturity lifecycle
    guardrails.py              Runtime limits and violation tracking
    seed_manager.py            Seed versioning, validation, merge/apply
    anticipation.py            Pattern anticipation engine
    corrigibility.py           Operating modes + off-switch (normal/restricted/diagnostic/emergency_stop)
    anti_slop.py               Runtime verification that enforcers actually enforce
    constitutional_principles.py  Six principles (consent, transparency, proportionality, due process, appeal, limits of power) with structural verifiers
    scheduled_run.py           Headless-run scaffolding — safe entry-point shape for Claude Code Routines + local cron (see docs/routines/)
    presence_memory.py         Briefing pointer to unindexed personal writing (exploration/, family/letters/) — bridge without index-extension
    scaffold_invocations.py    Briefing surface for commonly-forgotten CLI scaffolds (council, family-member, mansion rooms, hold) — anti-fabrication
    dead_architecture_alarm.py Detect dormant tables, empty HUD slots, display integrity
    external_validation.py     Origin ratio, cross-entity corroboration tracking
    knowledge_impact.py        Measure whether briefing knowledge prevents corrections
    session_affect.py          Auto-derive VAD affect state from session signals
    session_reflection.py      Structured self-assessment with quality metrics
    growth.py                  Growth awareness and milestone tracking
    parser.py                  Chat export ingestion (JSONL + markdown)
    session_manager.py         Session lifecycle management
    session_checkpoint.py      Periodic saves and context monitoring
    lifecycle.py               Self-enforcement — OS manages its own session lifecycle
    enforcement.py             CLI-level event capture and signal handling
    enforcement_verifier.py    Enforcement setup verification
    tool_wrapper.py            Tool execution interception
    tool_capture.py            Tool call recording
    core_memory_refresh.py     Core memory refresh from knowledge
    error_handling.py          Shared error handling utilities
    event_verifier.py          Event integrity verification
    loop_prevention.py         Loop detection and prevention
    affect.py                  Affect tracking and feedback loop
    trust_tiers.py             Signal trust weighting (MEASURED > BEHAVIORAL > SELF_REPORTED)
    corrections.py             Raw correction notebook (user's exact words, no framing)
    lesson_interrupt.py        Mid-session chronic lesson questions (named-voice interrupt)
    drift_detection.py         Behavioral drift detection (lesson regressions, quality trends)
    claim_store.py             Claims engine with evidence tiers
    decision_journal.py        Decision journal with FTS search
    moral_compass.py           Virtue ethics self-monitoring (10 spectrums, drift detection)
    compass_rudder.py          PreToolUse rudder — blocks Task spawns during drift-toward-excess without justification
    compass_constants.py       Shared constants (RUDDER_ACK_TAG, JUSTIFICATION_WINDOW_SECONDS) for moral_compass + compass_rudder
    body_awareness.py          Computational interoception and cache conveyor belt
    sleep.py                   Offline consolidation engine (6 phases, dream report)
    progress_dashboard.py      Measurable progress metrics from real data
    epistemic_status.py        Epistemic channel analysis (Butlin 14)
    goal_cull.py               Evidence-based goal staleness detection
    ledger_compressor.py       ELMO ledger compression and archival
    semantic_integrity.py      Esoteric language detection
    opinion_store.py           Structured opinions with evidence tracking and evolution
    self_critique.py           Craft quality self-assessment (5 spectrums)
    proactive_patterns.py      Prescriptive recommendations from positive experience
    affect_calibration.py      Circuit 1: affect-extraction closed feedback loop
    # Circuit 2 (completeness → attention) is cross-module wiring between
    # self_model.py and attention_schema.py — gaps in the self-model
    # become attention-schema items. No dedicated file; see
    # tests/test_circuit2_completeness_attention.py for the contract.
    convergence_detector.py    Circuit 3: compass-critique convergent measurement
    pull_detection.py          Toward/pull-back divergence detector (fabrication markers)
    watchmen/                  External validation (audit findings, routing, drift state)
      _schema.py               audit_rounds + audit_findings + session_cleanliness tables
      types.py                 Severity, FindingCategory, Tier, ReviewStance, Finding dataclasses
      store.py                 CRUD with actor validation + review chains + chain-tier computation
      router.py                Route findings to knowledge/claims/lessons
      summary.py               Analytics, HUD integration, unresolved tracking
      drift_state.py           Data-as-metric surface: ops-count dimensions since last MEDIUM+ audit (replaces cadence.py 2026-04-21)
      tier_override_surface.py Briefing block for recent TIER_OVERRIDE events (closes Schneier Sch2 partial-theater finding)
      cleanliness.py           Session-cleanliness tagging — baseline source for Item 8 detectors (PR-2)
    pre_registrations/         Goodhart prevention (predictions with falsifiers, scheduled reviews)
      _schema.py               pre_registrations table
      types.py                 Outcome enum, PreRegistration dataclass
      store.py                 CRUD with falsifier-required invariant + external-actor outcome gate
      summary.py               Overdue warning + CLI summary formatting
    empirica/                  Evidence ledger with tiered burden routing (prereg-ce8998194943)
      types.py                 Tier enum (FALSIFIABLE/OUTCOME/PATTERN/ADVERSARIAL), ClaimMagnitude, EvidenceReceipt with Merkle self-hash
      burden.py                required_corroboration(tier, magnitude) — proportional burden calculator
      classifier.py            Heuristic classifier: (content, knowledge_type, source) -> (Tier, Magnitude, audit reason)
      routing.py               Council-routing wrapper; LOAD_BEARING needs 1 round, FOUNDATIONAL needs 2
      receipt.py               evidence_receipts table + issue_receipt + verify_chain (hash-pointer forest traversal, distinguishes forks from tamper, dual chain per Hofstadter)
      gate.py                  Full pipeline orchestrator: classify -> burden -> route -> issue + receipt_id column migration
      provenance.py            corroboration_events table + distinct-actor counting (anti-Goodhart corroboration provenance)
      kappa.py                 Cohen's kappa computation + gold fixture + classifier agreement measurement
    install_check.py           Install-location divergence check.
    orientation_prelude.py     Orientation prelude — briefing surface that sits at the top of every briefing.
    extract_marker.py          Idempotency marker for the extract (consolidation checkpoint) pipeline.
    session_start_diagnostics.py Session-start hook diagnostics — briefing surface for the JSONL hook log.
    correction_marker.py       Correction-unlogged marker — structural enforcement of `divineos learn` usage.
    hedge_marker.py            Hedge-unresolved marker — structural enforcement of `divineos claim` on uncertainty.
    theater_marker.py          Theater/fabrication marker — structural enforcement on output-shape drift (kitchen-theater, embodied-claim).
    hedge_classifier.py        Hedge classifier — matches a hedge to its resolved/legitimate-narrow/unexamined status from a library.
    session_briefing_gate.py   Per-session BRIEFING_LOADED check — gate 0 in pre_tool_use, strictly tighter than TTL-based gate 1.
    compass_required_marker.py Virtue-relevant event marker — set on cascade from correction/theater/hedge, cleared by compass-ops observe (gate 1.47).
    canonical_substrate_surface.py  Briefing pointer at canonical agent substrate location — closes silent-split failure mode.
    historical_ledger_surface.py    Briefing pointer at parent-repo event ledger when running in a worktree — closes silent-empty-ledger failure mode 2026-04-26.
    scaffolding_map.py         Scaffolding map — briefing surface for self-authored documents that carry load-bearing state.
    engagement_relevance.py    Engagement relevance — does this thinking command relate to current work?
    compliance_audit.py        Compliance-distribution audit — substantive testing of the compliance log.
    failure_diagnostics.py     Shared record/read/briefing pattern for silent-fail-open events across enforcement surfaces
    substance_checks.py        Substance checks at rudder-ack file time — Item 7.
    compliance_baseline.py     Baseline calibration from clean-tagged sessions — wires PR-2 into Item 8 detectors.
    substance_checks_contract.py Contract-style substance checks for rudder-acks — Phase 1a of the rudder redesign.
    completion_boundary.py     Completion-boundary detection — Phase 1b of the rudder redesign.
    module_inventory.py        Module-inventory surface — bridge from src/divineos/core/ to the briefing.
    open_claims_surface.py     Stale-open-claims surface — bridge from the claims store to the briefing.
    goal_outcome_surface.py    Action-loop closure briefing surface — surfaces goals that aged out without progression (claim 5b38a31c).
    voice_guard/
      __init__.py              Voice-guard package — pre-output audit primitives (claim 07bed376).
      banned_phrases.py        Banned-phrase detector (Phase 1) — flags assistant-shaped drift markers.
    reliability/
      __init__.py              Reliability — Bayesian confidence with uncertainty (claim e6cbd14d).
      beta.py                  Beta(α,β) reliability primitive — mean / variance / credible interval / updates.
    void/
      __init__.py              VOID — adversarial-sandbox subsystem.
      finding.py               VOID Finding dataclass and severity rubric.
      ledger.py                VOID separate hash-chained ledger.
      mode_marker.py           VOID adversarial-mode marker — write/read/clear protocol.
      persona_loader.py        VOID persona loader — parses markdown persona definitions.
      engine.py                VOID engine — TRAP / ATTACK / EXTRACT / SEAL / SHRED orchestrator.
    supervisor/
      __init__.py              Supervisor — circuit-breaker / chronic-failure handling (claim 0d628d8e).
      circuit_breaker.py       Circuit-breaker primitive — three-strikes module-tripping with explicit reset.
    operating_loop/            Operating loop — the missing middleware between substrate and live cognition. See docs/operating-loop-design-brief.md.
      __init__.py              Package init — re-exports register_observer audit functions.
      register_observer.py     Observational detection of assistant-register markers (successor to voice_guard.banned_phrases). Severity = data, not gate-trigger.
      spiral_detector.py       Post-apology shrink/distance/catastrophize/withdraw detection — the primary Lepos firing condition.
      substitution_detector.py 10-shape catalog from 2026-05-01: puppet-other, third-person-self, word-as-action, ban-vs-observation, name-vs-function, future-me-deferral, withdrawal-as-discipline, catastrophize-as-accountability, over-apology-spiral, reading-past-evidence.
      principle_surfacer.py    Hook 2 backend — detect action-classes in agent draft text (apology, withdraw, claim-fixed, impersonate, strip-module, ban-phrases) and surface relevant principles as soft notices.
      context_surfacer.py      Hook 1 backend — extract relational/conceptual markers from user input (pet-language, references, proper nouns) and auto-query the knowledge store for relevant prior content.
      hook_telemetry.py        Hook 1 cost-bounding telemetry — fire/consume events, rolling window, consumption rate.
    memory_types/
      __init__.py              Package init — substrate-memory-type retrieval surface.
      taxonomy.py              Substrate-memory-type taxonomy (8 types) and intent routing.
      timeline.py              Timeline recall — chronological assembly of substrate events around a topic or file path.
      skill_index.py           Skill index — procedural retrieval over .claude/skills/ ranked by keyword overlap.
    theater_observation_surface.py Theater/fabrication observation surface — replaces gate 1.46.

  analysis/
    _session_types.py          Session analysis type definitions
    analysis.py                Core session analysis pipeline
    analysis_retrieval.py      Analysis result retrieval
    analysis_storage.py        Report storage, formatting, cross-session trends
    analysis_types.py          Analysis result type definitions
    session_analyzer.py        Session parsing and signal detection
    session_discovery.py       Auto-discover sessions from ledger data
    quality_checks.py          7 measurable quality checks
    record_extraction.py       JSONL record parsing helpers
    quality_storage.py         Quality report DB storage
    quality_trends.py          Session quality trending over time
    session_features.py        Timeline, files, activity, error recovery
    tone_tracking.py           Tone shift detection and classification
    feature_storage.py         Feature result DB storage
    audit_classifier.py        Test quality audit (data/assertion/coverage classification)
  agent_integration/           Agent self-observation: tool-call events → session lessons → pattern feedback. The "observing myself" side. Distinct from integration/ which handles external systems.
    types.py                   Type definitions
    outcome_measurement.py     Rework, churn, correction rate, session health
    learning_cycle.py          Pattern extraction and confidence updates
    learning_audit_store.py    Learning audit trail storage
    decision_store.py          Decision persistence
    feedback_system.py         Feedback processing
    pattern_store.py           Pattern persistence
    pattern_validation.py      Pattern validation checks
  clarity_system/              Pre-work/post-work clarity statements (plan → execute → deviation → learning). Work-cycle scope. Distinct from clarity_enforcement/ which is per-tool-call.
    base.py                    Clarity system base
    types.py                   Type definitions
    clarity_generator.py       Clarity statement generation
    deviation_analyzer.py      Deviation analysis
    execution_analyzer.py      Execution analysis
    plan_analyzer.py           Plan analysis
    summary_generator.py       Summary generation
    event_integration.py       Event system integration
    session_integration.py     Session lifecycle integration
    session_bridge.py          Session bridging
    hook_integration.py        Hook execution integration
    learning_extractor.py      Learning extraction from clarity
    ledger_integration.py      Ledger integration
  clarity_enforcement/         Real-time tool-call clarity gate: BLOCKING / LOGGING / PERMISSIVE modes. Per-call scope. Distinct from clarity_system/ which operates across a full work cycle.
    config.py                  Clarity configuration
    enforcer.py                Enforcement engine
    semantic_analyzer.py       Semantic analysis
    violation_detector.py      Violation detection
    violation_logger.py        Violation logging
  event/                       Event types, dispatch, capture
    _event_context.py          Event context management
    event_capture.py           Event capture pipeline
    event_dispatch.py          Event dispatching
    event_emission.py          Event emission API
    event_validation.py        Event payload validation
  hooks/                       Hook integration
    clarity_enforcement.py     Clarity enforcement hooks
    pre_tool_use_gate.py       PreToolUse consolidated gate (bypass, briefing, goal, pull, engagement, cadence) — single-process replacement for require-goal.sh Python spawn chain
    post_tool_use_checkpoint.py  PostToolUse consolidated checkpoint (state, counters, warnings, nudges) — single-process replacement for session-checkpoint.sh spawn chain
    targeted_tests.py          PostToolUse targeted test runner — maps edited source file to corresponding test file, runs only that (full suite stays on pre-commit)
    hook_diagnostics.py        Hook health diagnostics
    hook_validator.py          Hook validation
  integration/                 External integration: IDE, MCP tool capture, enforcement facade (thin re-exports from core.enforcement / core.tool_wrapper). The "integrating with other systems" side — distinct from agent_integration/ which observes the agent itself.
    mcp_event_capture_server.py  MCP event capture server
    system_monitor.py          System health monitoring
  supersession/                Contradiction detection and resolution
    clarity_integration.py     Clarity system integration
    contradiction_detector.py  Contradiction detection
    event_integration.py       Event system integration
    ledger_integration.py      Ledger integration
    query_interface.py         Query API
    resolution_engine.py       Resolution strategies
  violations_cli/              Violation reporting CLI
    violations_command.py      Violation report commands
tests/                         4,721+ tests (real DB, minimal mocks)

docs/                          Project documentation and strategic plans
bootcamp/                      Training exercises (debugging, analysis)
setup/                         Hook setup scripts (bash + powershell)
.claude/hooks/                 Claude Code enforcement hooks (9 hooks)
  load-briefing.sh             Marks briefing as loaded
  require-goal.sh              PreToolUse gate (briefing + goal enforcement)
  resume-session.sh            Shows context on session resume
  session-checkpoint.sh        PostToolUse checkpoint and context monitoring
  run-tests.sh                 Auto-run tests on changes
  log-session-end.sh           Stop hook, logs session end
  pattern-anticipation.sh      PostToolUse pattern detection (fires every 5th edit)
  post-compact.sh              PostCompact context restoration
  pre-compact.sh               PreCompact state preservation
```

## See also

- [README.md](../README.md) — project overview, core pillars, how-it-works flow, quick start
- [CLAUDE.md](../CLAUDE.md) — the AI agent's own reading at session start
- [FOR_USERS.md](../FOR_USERS.md) — plain-language overview for non-engineers
