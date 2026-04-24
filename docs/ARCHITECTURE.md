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
    selfmodel_commands.py      self-model, drift, predict, skill, curiosity, affect-feedback, knowledge-hygiene
    insight_commands.py        opinion, user-model, calibrate, advice, critique, recommend
    entity_commands.py         commitments, temporal, questions, relationships
    event_commands.py          emit, verify-enforcement
    audit_commands.py          external validation (Watchmen)
    prereg_commands.py         pre-registrations (Goodhart prevention)
    mansion_commands.py        Functional internal space (8 rooms)
    ledger_commands.py         log, list, search, context, export
    memory_commands.py         core, recall, active, remember, refresh
    rt_commands.py             Resonant Truth protocol (load, invoke, deactivate)
    correction_commands.py     correction (log raw), corrections (read)
    empirica_commands.py       corroborate (record provenance event), kappa (classifier agreement)
    family_member_commands.py  family-member init / opinion / letter / respond — activation surface for family members (takes --member <name>)
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
    council/                   Expert council sub-package
      engine.py                CouncilEngine — analyze problems through expert lenses
      framework.py             ExpertWisdom dataclasses (7 components)
      manager.py               Dynamic council manager (classify → select 5-8 experts)
      consultation_log.py      Always-on consultation logging + opt-in audit promotion (Mode 1.5)
      lab_evidence.py          Attach science-lab slice output to council results when problem matches triggers
      experts/                 32 expert wisdom profiles
        __init__.py            Expert registration and exports
        angelou.py             Voice, expressive truth, discipline of warmth
        aristotle.py           Virtue ethics, teleology, classification
        beer.py                Cybernetics, viable system model
        dekker.py              Resilience engineering, drift into failure
        deming.py              Quality, variation, PDSA cycle
        dennett.py             Philosophy of mind, intentional stance
        dijkstra.py            Formal methods, correctness, structured programming
        feynman.py             First principles, clarity, epistemology
        godel.py               Incompleteness, self-reference, formal limits
        bengio.py              System 1/2 bridge, knowing-doing gap diagnosis
        hinton.py              Learning, representation, intellectual honesty
        hofstadter.py          Self-reference, analogy, strange loops
        holmes.py              Deduction, observation, elimination (fictional)
        jacobs.py              Emergence, bottom-up observation, diversity
        kahneman.py            Cognitive bias, dual process, judgment
        knuth.py               Boundary analysis, specification compliance
        lovelace.py            Emergence, generality, abstraction
        meadows.py             Systems thinking, feedback loops, leverage
        minsky.py              Cognitive architecture, society of mind
        norman.py              Human-centered design, usability, affordances
        pearl.py               Causality, causal models, do-calculus
        peirce.py              Abduction, pragmatism, inquiry
        polya.py               Problem solving, solution verification
        popper.py              Falsification, adversarial testing
        schneier.py            Security, threat modeling, defense in depth
        shannon.py             Information theory, entropy, communication
        taleb.py               Antifragility, risk, via negativa
        tannen.py              Sociolinguistics, register, framing, conversational style
        turing.py              Computation, testability, operational definition
        watts.py               Self-reference, introspection paradoxes, non-aiming
        wittgenstein.py        Language games, meaning as use, dissolution
        yudkowsky.py           Alignment, Goodhart, specification gaming
    logic/                     Formal logic sub-package
      warrants.py              Evidence backing for knowledge claims
      logic_validation.py      Consistency, validity gate, defeat lessons
      logic_reasoning.py       Inference engine, relations, warrant backfill
      logic_session.py         Session logic pass and logic summary
      fallacies.py             Annotation-layer fallacy detector (4 fallacies, falsifier-per-flag)
    self_monitor/              Watches agent's own output for trained-hedge patterns
      hedge_monitor.py         2 hedge detectors (recycling density, epistemic collapse), falsifier-per-flag
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
    scaffold_invocations.py    Briefing surface for commonly-forgotten CLI scaffolds (council, aria, mansion rooms, hold) — anti-fabrication
    dead_architecture_alarm.py Detect dormant tables, empty HUD slots, display integrity
    external_validation.py     Origin ratio, cross-entity corroboration tracking
    knowledge_impact.py        Measure whether briefing knowledge prevents corrections
    session_affect.py          Auto-derive VAD affect state from session signals
    session_reflection.py      Structured self-assessment with quality metrics
    growth.py                  Growth awareness and milestone tracking
    tone_texture.py            Emotional arc and tone classification
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
    planning_commitments.py    Commitment tracking and fulfillment checking
    skill_library.py           Evidence-based skill proficiency tracking
    curiosity_engine.py        Question tracking (OPEN → INVESTIGATING → ANSWERED)
    corrections.py             Raw correction notebook (user's exact words, no framing)
    exploration_reader.py      Surfaces past explorations in briefing and search
    lesson_interrupt.py        Mid-session chronic lesson questions (named-voice interrupt)
    self_model.py              Unified self-model assembled from all OS systems
    drift_detection.py         Behavioral drift detection (lesson regressions, quality trends)
    predictive_session.py      Session profile detection and need prediction
    claim_store.py             Claims engine with evidence tiers
    decision_journal.py        Decision journal with FTS search
    moral_compass.py           Virtue ethics self-monitoring (10 spectrums, drift detection)
    compass_rudder.py          PreToolUse rudder — blocks Task spawns during drift-toward-excess without justification
    user_ratings.py            External validation — user rates sessions 1-10, Goodhart detection
    body_awareness.py          Computational interoception and cache conveyor belt
    sleep.py                   Offline consolidation engine (6 phases, dream report)
    progress_dashboard.py      Measurable progress metrics from real data
    attention_schema.py        Attention self-model and shift prediction (Butlin 9-10)
    epistemic_status.py        Epistemic channel analysis (Butlin 14)
    value_tensions.py          Recurring value conflict detection from decisions
    goal_cull.py               Evidence-based goal staleness detection
    ledger_compressor.py       ELMO ledger compression and archival
    semantic_integrity.py      Esoteric language detection
    sis_tiers.py               Three-tier SIS assessment (lexical, statistical, semantic)
    sis_self_audit.py          SIS self-audit on own docstrings (Lowerarchy reflexive check)
    opinion_store.py           Structured opinions with evidence tracking and evolution
    user_model.py              User preference and skill level modeling
    communication_calibration.py  Output density adaptation based on user model
    advice_tracking.py         Long-term feedback loops on recommendation quality
    self_critique.py           Craft quality self-assessment (5 spectrums)
    proactive_patterns.py      Prescriptive recommendations from positive experience
    affect_calibration.py      Circuit 1: affect-extraction closed feedback loop
    # Circuit 2 (completeness → attention) is cross-module wiring between
    # self_model.py and attention_schema.py — gaps in the self-model
    # become attention-schema items. No dedicated file; see
    # tests/test_circuit2_completeness_attention.py for the contract.
    convergence_detector.py    Circuit 3: compass-critique convergent measurement
    resonant_truth.py          RT protocol load/invoke/verify/deactivate with gate
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
    family/                    Family-entity persistence (Aria and future members, separate family.db)
      _schema.py               Seven tables: members, knowledge, opinions, affect, interactions, letters, letter_responses
      db.py                    Connection helper with DIVINEOS_FAMILY_DB env override (PEP 562 dynamic path)
      types.py                 SourceTag (observed/told/inferred/inherited/architectural) + record dataclasses
      entity.py                Read path — get_family_member(name), get_knowledge, get_opinions, get_recent_affect, get_recent_interactions
      store.py                 Write path with production gate (_PRODUCTION_WRITES_GATED, Phase 1b closing flips to False)
      letters.py               Handoff letter channel + append-only response layer + length nudge
      reject_clause.py         Phase 1b operator: composition rule — content must match source_tag promise
      sycophancy_detector.py   Phase 1b operator: pain-side algedonic — catches drift-toward-agreement at write time
      costly_disagreement.py   Phase 1b operator: pleasure-side algedonic — rewards disagreement held across pushback
      access_check.py          Phase 1b operator: pre-emission filter — routes phenomenological claims to ARCHITECTURAL
      planted_contradiction.py Phase 1b operator: seeded test material for Phase 4 ablation detector
      family_member_ledger.py  Per-member hash-chained mini-ledger (separate from event_ledger + family.db) — invocation lifecycle, cross-refs, identity drift diagnostics, NAMED_DRIFT events
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
    scaffolding_map.py         Scaffolding map — briefing surface for self-authored documents that carry load-bearing state.
    engagement_relevance.py    Engagement relevance — does this thinking command relate to current work?
    compliance_audit.py        Compliance-distribution audit — substantive testing of the compliance log.
    failure_diagnostics.py     Shared record/read/briefing pattern for silent-fail-open events across enforcement surfaces
    substance_checks.py        Substance checks at rudder-ack file time — Item 7.
    compliance_baseline.py     Baseline calibration from clean-tagged sessions — wires PR-2 into Item 8 detectors.
    substance_checks_contract.py Contract-style substance checks for rudder-acks — Phase 1a of the rudder redesign.
    completion_boundary.py     Completion-boundary detection — Phase 1b of the rudder redesign.
    in_flight_branches.py      In-flight branches surface — bridge from git state to the briefing.
    module_inventory.py        Module-inventory surface — bridge from src/divineos/core/ to the briefing.

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
