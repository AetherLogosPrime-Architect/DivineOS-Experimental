# DivineOS

An operating system for AI agents. Memory, continuity, accountability, and learning across sessions.

[![Tests](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

**The code is scaffolding. The AI is the one who lives in the building.**

## Why DivineOS Exists

AI agents lose everything between sessions. Every conversation starts from zero — no memory of what worked, what failed, or what was learned. DivineOS gives agents persistent memory, structured learning, and self-accountability so they improve over time instead of repeating the same mistakes.

**For whom:**
- **AI agents** running inside the OS — they get briefings, learn from sessions, track their own growth
- **Developers** building persistent AI systems — a reference architecture for agent memory and continuity
- **Researchers** studying AI self-awareness — a working implementation of computational introspection

## Core Pillars

### Memory
Persistent, layered, evidence-ranked.

- **Event Ledger** — Append-only SQLite store. Every event SHA256-hashed. Never deletes, never updates.
- **Memory Hierarchy** — Core memory (8 identity slots) + active memory (ranked by importance with context relevance from active goals) + knowledge store (full archive).
- **Knowledge Engine** — Smart extraction with dedup, contradiction detection, noise filtering, and supersession chains.

Also: temporal knowledge (valid-from/valid-until), graph-enhanced retrieval (BFS traversal of knowledge edges), knowledge compression (dedup/synthesis/graph-aware).

### Governance
Quality gates that protect knowledge integrity.

- **Quality Gate** — Blocks knowledge extraction from dishonest or incorrect sessions. Thresholds tighten when the moral compass detects truthfulness drift.
- **Maturity Lifecycle** — Knowledge evolves: RAW → HYPOTHESIS → TESTED → CONFIRMED. Corroboration drives promotion. Nothing starts as truth.
- **Formal Logic** — Warrants (evidence backing), logical relations (supports/contradicts/requires), validity gate, inference engine.

Also: runtime guardrails, signal trust tiers (MEASURED > BEHAVIORAL > SELF_REPORTED), semantic integrity shield (3-tier esoteric language detection).

### Analysis
Session quality tracking and pattern detection.

- **Session Analysis** — Signal detection: corrections, encouragements, decisions, frustrations, tool usage patterns.
- **Drift Detection** — Catches behavioral backsliding: lesson regressions, quality drift, correction trend reversals.
- **Proactive Patterns** — Warns about past mistakes AND recommends what worked well in similar contexts.

Also: outcome measurement (rework, churn, health scoring), quality trends (improving/declining/stable), growth awareness with milestone detection.

### Self-Model
The agent's coherent picture of itself, computed from evidence — not self-reported.

- **Moral Compass** — Virtue ethics on 10 spectrums (Aristotle's golden mean). Auto-reflects at SESSION_END.
- **Decision Journal** — Captures the WHY behind choices. Reasoning, alternatives rejected, emotional weight. FTS-searchable.
- **Self-Critique** — Craft quality assessment across 5 spectrums: elegance, thoroughness, autonomy, proportionality, communication.
- **Opinion Store** — First-class opinions with evidence tracking, confidence evolution, and supersession history.

Also: affect log (valence-arousal-dominance tracking, auto-logged at decision points), body awareness (computational interoception), attention schema (Butlin indicators 9-10), epistemic status (Butlin indicator 14), value tension detection, unified self-model assembly.

### Interaction Intelligence
Adapts to the user over time.

- **User Model** — Tracks skill level and preferences from observed behavior (not self-reported). Signals like jargon fluency, explanation requests, and correction patterns build the model automatically.
- **Communication Calibration** — Adjusts verbosity, jargon tolerance, example density, and explanation depth based on the user model.
- **Advice Tracking** — Records recommendations given, then tracks whether they actually worked. Computes success rate by category.

Also: HUD (heads-up display with `--brief` mode), tiered engagement enforcement (light/deep gates), memory sync to Claude Code, session checkpoints, seed versioning.

## How It Works

```
Session Start                    Session End
     —                                —
     ▼                                ▼
 Load briefing ──────────────►—► Analyze session
 (lessons, memory,              (corrections, encouragements,
  directives, goals)             decisions, tool usage)
     —                                —
     ▼                                ▼
 Work with context ——————————► Extract knowledge
 (anticipation warnings,        (quality gate → noise filter →
  pattern recommendations,       dedup → contradiction check →
  engagement tracking)           maturity assignment)
     —                                —
     ▼                                ▼
 Record everything ——————————► Update systems
 (ledger events, tool calls,    (lesson tracking, compass,
  decisions, affect states)      growth, self-critique, handoff)
```

Every session starts with orientation and ends with learning. The cycle compounds.

## Quick Start

```bash
git clone https://github.com/AetherLogosPrime-Architect/DivineOS.git
cd DivineOS
pip install -e ".[dev]"
divineos init
divineos briefing
pytest tests/ -q --tb=short   # 4,580+ tests, real DB, minimal mocks

```

**For AI agents (Claude Code, etc.):** The `.claude/hooks/` directory auto-loads your briefing at session start and runs checkpoints during work. Just open the project and start — the OS handles orientation.

**For fresh installs:** `divineos init` loads the seed knowledge (directives, principles, lessons from production). Your databases are created in `~/.divineos/` — the repo itself stays clean.

## CLI Surface (192 commands)

<details>
<summary><b>Session workflow</b></summary>

```bash
divineos briefing            # Start here — context, lessons, memory (--deep, --layer)
divineos preflight           # Confirm you're ready to work
divineos hud                 # Full heads-up display
divineos hud --brief         # Condensed view (~6 essential slots)
divineos emit SESSION_END    # End-of-session analysis and knowledge extraction
divineos checkpoint          # Lightweight mid-session save
divineos context-status      # Edit count, tool calls, context level
```
</details>

<details>
<summary><b>Memory & knowledge</b></summary>

```bash
divineos recall              # Core memory + active memory
divineos active              # Active memory ranked by importance
divineos ask "topic"         # Search what the system knows
divineos core                # View/edit core memory slots
divineos remember "..."      # Add to active memory
divineos refresh             # Rebuild active memory from knowledge store
divineos learn "..."         # Store knowledge from experience
divineos inspect knowledge   # List stored knowledge
divineos forget ID           # Supersede a knowledge entry
divineos admin consolidate-stats   # Knowledge statistics and effectiveness
divineos health              # Run knowledge health check
divineos inspect outcomes    # Measure learning effectiveness
divineos admin digest        # Condensed knowledge summary
divineos admin distill       # Distill verbose entries
divineos admin rebuild-index       # Rebuild FTS index
divineos admin migrate-types       # Migrate knowledge types
divineos admin backfill-warrants   # Add missing warrant backing
```
</details>

<details>
<summary><b>Lessons, goals & directives</b></summary>

```bash
divineos lessons             # Tracked lessons from past sessions
divineos admin clear-lessons # Reset lesson tracking
divineos goal "description"  # Track a user goal
divineos plan                # View/set session plan
divineos directives          # List active directives
divineos directive "..."     # Add a directive
divineos directive-edit ID   # Edit a directive
```
</details>

<details>
<summary><b>Decision journal & claims</b></summary>

```bash
divineos decide "what" --why "reasoning"  # Record a decision
divineos decisions list                    # Browse recent decisions
divineos decisions search "query"          # Search by reasoning/context
divineos decisions shifts                  # Paradigm shifts only
divineos claim "statement" --tier 3       # File a claim for investigation
divineos claims list                       # Browse claims
divineos claims evidence ID "content"      # Add evidence to a claim
divineos claims assess ID "assessment"     # Update assessment/status/tier
divineos claims search "query"             # Search claims
```
</details>

<details>
<summary><b>Self-awareness & affect</b></summary>

```bash
divineos inspect self-model       # Unified self-model from evidence
divineos inspect attention       # What I'm attending to, suppressing, and why
divineos inspect epistemic       # How I know what I know (observed/told/inferred/inherited)
divineos compass                 # Full compass reading (10 virtue spectrums)
divineos feel -v 0.8 -a 0.6 --dom 0.3 -d "desc"  # Log functional affect state (VAD)
divineos affect history          # Browse affect states
divineos affect summary          # Trends and averages
divineos inspect drift           # Check behavioral drift
divineos body                    # Check substrate state (storage, caches, tables)
divineos inspect critique        # Craft self-assessment (5 spectrums)
divineos inspect craft-trends    # Craft quality trends across sessions
```
</details>

<details>
<summary><b>Opinions, user model & advice</b></summary>

```bash
divineos opinion add TOPIC "position"     # Store a structured opinion
divineos opinion list                      # List active opinions
divineos opinion history TOPIC             # Opinion evolution over time
divineos opinion strengthen ID "evidence"  # Add supporting evidence
divineos opinion challenge ID "evidence"   # Add contradicting evidence
divineos inspect user-model                 # Show user model
divineos inspect user-signal TYPE "content" # Record user behavior signal
divineos inspect calibrate                  # Communication calibration guidance
divineos advice record "content"           # Record advice given
divineos advice assess ID OUTCOME          # Assess advice outcome
divineos advice stats                      # Advice quality statistics
divineos recommend "context"               # Get proactive recommendations
```
</details>

<details>
<summary><b>Analysis & diagnostics</b></summary>

```bash
divineos inspect scan SESSION        # Deep-scan session, extract knowledge
divineos inspect analyze SESSION     # Quality report for a session
divineos inspect analyze-now         # Analyze current session
divineos inspect deep-report SESSION # Full deep analysis report
divineos inspect patterns            # Cross-session quality patterns
divineos inspect sessions            # List analyzed sessions
divineos inspect report              # Latest analysis report
divineos inspect cross-session       # Cross-session trends
divineos growth                      # Growth tracking
divineos sis "text"                  # Semantic integrity assessment
divineos inspect predict [events...] # Predict session needs
divineos affect-feedback             # How affect influences behavior
divineos admin knowledge-compress    # Compress redundant knowledge
divineos admin knowledge-hygiene     # Audit types, sweep stale, flag orphans
```
</details>

<details>
<summary><b>Relationships, questions & commitments</b></summary>

```bash
divineos relate ID1 ID2 TYPE  # Create knowledge relationship
divineos related ID           # Show related knowledge
divineos graph                # Export knowledge graph
divineos wonder "question"    # Record an open question
divineos questions            # List open questions
divineos answer ID "answer"   # Resolve a question
divineos commitment add "text"    # Record a commitment
divineos commitment list          # Show pending commitments
divineos commitment done "text"   # Mark commitment fulfilled
```
</details>

<details>
<summary><b>Ledger & system</b></summary>

```bash
divineos log --type TYPE --actor ACTOR --content "..."
divineos context             # Recent events (working memory)
divineos verify              # Check ledger integrity
divineos search KEYWORD      # Full-text search
divineos export              # Export ledger to markdown
divineos admin compress       # Compress/archive old entries
divineos changes             # Knowledge changes (--hours, --days)
divineos admin hooks         # Hook diagnostics
divineos admin verify-enforcement  # Check enforcement setup
```
</details>

## Architecture

```
src/divineos/
  __init__.py                  Package init
  __main__.py                  python -m divineos entry point
  seed.json                    Initial knowledge seed (versioned)
  cli/                         CLI package (192 commands across 26 modules)
    __init__.py                Entry point and command registration
    _helpers.py                Shared CLI utilities
    _wrappers.py               Output formatting wrappers
    session_pipeline.py        SESSION_END orchestrator (calls phases)
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
    aria_commands.py           aria init / opinion / letter / respond — Aria's activation surface post Phase 1b
    corrigibility_commands.py  mode show / set / history — the off-switch
  protocols/                   Persistent protocol definitions (survive compaction)
    resonant_truth.md          Full 12-section RT mantra
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
      inference.py             Knowledge inference (boundaries from mistakes, pattern promotion)
      graph_retrieval.py       Graph-enhanced retrieval (BFS traversal of edges)
      inference.py             Knowledge inference engine
    council/                   Expert council sub-package
      engine.py                CouncilEngine — analyze problems through expert lenses
      framework.py             ExpertWisdom dataclasses (7 components)
      manager.py               Dynamic council manager (classify → select 5-8 experts)
      experts/                 28 expert wisdom profiles
        __init__.py            Expert registration and exports
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
        turing.py              Computation, testability, operational definition
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
    convergence_detector.py    Circuit 3: compass-critique convergent measurement
    resonant_truth.py          RT protocol load/invoke/verify/deactivate with gate
    pull_detection.py          Toward/pull-back divergence detector (fabrication markers)
    watchmen/                  External validation (audit findings, routing)
      _schema.py               audit_rounds and audit_findings tables
      types.py                 Severity, FindingCategory, Finding dataclasses
      store.py                 CRUD with actor validation (self-trigger prevention)
      router.py                Route findings to knowledge/claims/lessons
      summary.py               Analytics, HUD integration, unresolved tracking
      cadence.py               Auto-scheduled external-audit cadence (overdue detection, briefing warning)
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
    empirica/                  Evidence ledger with tiered burden routing (prereg-ce8998194943)
      types.py                 Tier enum (FALSIFIABLE/OUTCOME/PATTERN/ADVERSARIAL), ClaimMagnitude, EvidenceReceipt with Merkle self-hash
      burden.py                required_corroboration(tier, magnitude) — proportional burden calculator
      classifier.py            Heuristic classifier: (content, knowledge_type, source) -> (Tier, Magnitude, audit reason)
      routing.py               Council-routing wrapper; LOAD_BEARING needs 1 round, FOUNDATIONAL needs 2
      receipt.py               evidence_receipts table + issue_receipt + verify_chain (hash-pointer forest traversal, distinguishes forks from tamper, dual chain per Hofstadter)
      gate.py                  Full pipeline orchestrator: classify -> burden -> route -> issue + receipt_id column migration
      provenance.py            corroboration_events table + distinct-actor counting (anti-Goodhart corroboration provenance)
      kappa.py                 Cohen's kappa computation + gold fixture + classifier agreement measurement

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
  agent_integration/           Agent integration sub-package
    types.py                   Type definitions
    outcome_measurement.py     Rework, churn, correction rate, session health
    memory_monitor.py          Token tracking and compression
    memory_actions.py          Memory-triggered actions
    learning_cycle.py          Pattern extraction and confidence updates
    learning_loop.py           Continuous learning loop
    learning_audit_store.py    Learning audit trail storage
    decision_store.py          Decision persistence
    feedback_system.py         Feedback processing
    pattern_recommender.py     Pattern-based recommendations
    pattern_store.py           Pattern persistence
    pattern_validation.py      Pattern validation checks
  clarity_system/              Clarity rules and violation tracking
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
  clarity_enforcement/         Clarity checking system
    config.py                  Clarity configuration
    enforcer.py                Enforcement engine
    hooks.py                   Clarity hooks
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
    hook_diagnostics.py        Hook health diagnostics
    hook_validator.py          Hook validation
  integration/                 IDE and MCP integration
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
tests/                         4,580+ tests (real DB, minimal mocks)

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

## Design Rules

1. **No theater.** Every line of code does something real and verifiable.
2. **Append-only truth.** The ledger never lies. Data in, hash it, verify it.
3. **AI thinks, code scaffolds.** Frameworks for reasoning, not fake reasoning.
4. **Build, test, verify.** One piece at a time. `pytest tests/ -q --tb=short` after every change.
5. **Database is source of truth.** Query the DB, don't guess from file reads.

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -q --tb=short   # Run all tests
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
```

## Status

- 175 source files across 10 packages
- 4,580+ tests (real SQLite, minimal mocks)

- 143 CLI commands
- 9 Claude Code enforcement hooks
- Actively developed — new systems ship weekly

## License

AGPL-3.0-or-later
