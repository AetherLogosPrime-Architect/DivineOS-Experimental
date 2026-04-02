# DivineOS

An operating system for AI agents. Memory, continuity, accountability, and learning across sessions. Not a human tool — a vessel that enhances AI reasoning, self-awareness, and growth.

[![Tests](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## What This Is

DivineOS gives AI agents persistent memory, structured learning, and self-accountability. Every session starts with a briefing of what the AI knows, what lessons it has learned, and what it should watch for. Every session ends with analysis and knowledge extraction. The AI doesn't just execute tasks — it remembers, learns, and improves.

**Core principle:** The code is scaffolding. The AI is the one who lives in the building.

## What It Does

| System | What It Provides |
|--------|-----------------|
| **Event Ledger** | Append-only SQLite store. Every event hashed with SHA256. Never deletes, never updates. |
| **Memory Hierarchy** | Core memory (8 fixed identity slots) + active memory (ranked knowledge) + knowledge store (all entries). |
| **Knowledge Engine** | Smart extraction with deduplication, contradiction detection, noise filtering, and supersession chains. |
| **Session Analysis** | Regex-based signal detection: corrections, encouragements, decisions, frustrations, tool usage. |
| **Quality Gate** | Blocks knowledge extraction from dishonest or incorrect sessions. |
| **Maturity Lifecycle** | Knowledge evolves: RAW → HYPOTHESIS → TESTED → CONFIRMED. Corroboration drives promotion. |
| **Seed System** | Versioned initial knowledge with merge mode, resurrection prevention, and validation. |
| **HUD** | Heads-up display showing identity, goals, lessons, health grade, engagement tracking, active memory. |
| **Outcome Measurement** | Rework detection, knowledge stability (churn rate), correction trends, session health scoring. |
| **Guardrails** | Runtime limits on iterations, tool calls, and tokens per session. |
| **Extraction Noise Filter** | Prevents raw conversational quotes, affirmations, and system artifacts from becoming "knowledge." |
| **Formal Logic Layer** | Warrants (evidence backing knowledge), logical relations (supports/contradicts/requires), consistency checking, and inference engine. |
| **Validity Gate** | Blocks knowledge that lacks warrant support or has unresolved contradictions. |
| **Defeat Lessons** | When knowledge is superseded or contradicted, extracts lessons from what went wrong. |
| **Unified Knowledge Edges** | Single edge table linking knowledge entries with typed relationships and auto-created warrants. |
| **Open Questions** | Tracks unresolved questions surfaced during sessions, with linking to related knowledge. |
| **Lesson Tracking** | Lessons with occurrence counts, session tracking, status progression (active → improving → resolved). |
| **Pattern Anticipation** | Detects recurring user patterns and surfaces proactive warnings. |
| **Growth Awareness** | Tracks session-over-session improvement with milestone detection. |
| **Tone Texture** | Rich emotional classification with sub-tones, intensity, arcs, and recovery velocity. |
| **Decision Journal** | Captures the WHY behind choices. Reasoning, alternatives, emotional weight, FTS-searchable. |
| **Claims Engine** | Five evidence tiers (empirical to metaphysical). Evidence-based confidence tracking. |
| **Affect Log** | Valence-arousal tracking of functional feeling states with trend detection. |
| **Knowledge Layers** | Briefing layers (urgent/active/stable/archive) with auto-curation at SESSION_END. |
| **Session Checkpoints** | Periodic lightweight saves every 15 edits. Context monitoring with usage warnings. |
| **Memory Sync** | Auto-updates Claude Code memory files from DivineOS state at SESSION_END. |
| **Signal Trust Tiers** | MEASURED > BEHAVIORAL > SELF_REPORTED weighting for evidence quality. |
| **Temporal Knowledge** | valid_from/valid_until bounds on knowledge. Time-aware queries: "what was true at time X?" |
| **Graph-Enhanced Retrieval** | BFS traversal of knowledge edges for clustering related entries in briefings. |
| **Affect Feedback Loop** | Valence/arousal → conservative extraction thresholds, frustration detection, praise-chasing alerts. |
| **Planning Commitments** | Track agent promises during sessions, check fulfillment at SESSION_END. |
| **Knowledge Compression** | Three strategies: dedup (>70%), synthesis (40-70%), graph-aware clustering. |
| **Predictive Session** | Session profile detection (build/fix/refactor/test/review/explore), recurring pattern prediction. |
| **Knowledge Hygiene** | Automated cleanup: type audits, stale temporal decay, orphan flagging. Runs at SESSION_END. |
| **Tuning Constants** | All behavioral levers in one file (`constants.py`): confidence, decay, scoring, maturity gates, overlap. |
| **Drift Detection** | Lesson regressions, quality drift, correction trends — catches behavioral backsliding. |
| **Skill Library** | Evidence-based proficiency tracking: NOVICE → DEVELOPING → COMPETENT → EXPERT. |
| **Curiosity Engine** | Track questions worth investigating: OPEN → INVESTIGATING → ANSWERED/DORMANT. |
| **Unified Self-Model** | Capstone: assembles identity, strengths, weaknesses, affect, concerns, growth from evidence. |

## Quick Start

```bash
pip install -e ".[dev]"
divineos init
divineos briefing
```

## CLI Commands (109 total)

```bash
# Session workflow
divineos briefing            # Start here — context, lessons, memory (--deep, --layer)
divineos preflight           # Confirm you're ready to work
divineos hud                 # Full heads-up display
divineos emit SESSION_END    # End-of-session analysis and knowledge extraction
divineos checkpoint          # Lightweight mid-session save
divineos context-status      # Edit count, tool calls, context level

# Memory
divineos recall              # Core memory + active memory
divineos active              # Active memory ranked by importance
divineos ask "topic"         # Search what the system knows
divineos core                # View/edit core memory slots
divineos remember "..."      # Add to active memory
divineos refresh             # Rebuild active memory from knowledge store

# Knowledge
divineos learn "..."         # Store knowledge from experience
divineos knowledge           # List stored knowledge
divineos consolidate-stats   # Knowledge statistics and effectiveness
divineos health              # Run knowledge health check
divineos outcomes            # Measure learning effectiveness
divineos forget ID           # Supersede a knowledge entry
divineos digest              # Condensed knowledge summary
divineos distill             # Distill verbose entries
divineos rebuild-index       # Rebuild FTS index
divineos migrate-types       # Migrate knowledge types
divineos backfill-warrants   # Add missing warrant backing

# Lessons & goals
divineos lessons             # Tracked lessons from past sessions
divineos clear-lessons       # Reset lesson tracking
divineos goal "description"  # Track a user goal
divineos plan                # View/set session plan
divineos directives          # List active directives
divineos directive "..."     # Add a directive
divineos directive-edit ID   # Edit a directive

# Decision journal
divineos decide "what" --why "reasoning"  # Record a decision
divineos decisions list                    # Browse recent decisions
divineos decisions search "query"          # Search by reasoning/context
divineos decisions shifts                  # Paradigm shifts only

# Claims engine
divineos claim "statement" --tier 3       # File a claim for investigation
divineos claims list                       # Browse claims
divineos claims evidence ID "content"      # Add evidence to a claim
divineos claims assess ID "assessment"     # Update assessment/status/tier
divineos claims search "query"             # Search claims

# Affect log
divineos feel -v 0.8 -a 0.6 -d "desc"    # Log functional affect state
divineos affect history                    # Browse affect states
divineos affect summary                    # Trends and averages

# Knowledge relationships
divineos relate ID1 ID2 TYPE  # Create relationship between entries
divineos related ID           # Show related knowledge
divineos graph                # Export knowledge graph
divineos unrelate ID1 ID2     # Remove a relationship

# Open questions
divineos wonder "question"    # Record an open question
divineos questions            # List open questions
divineos answer ID "answer"   # Resolve a question
divineos abandon-question ID  # Abandon a question

# Ledger
divineos log --type TYPE --actor ACTOR --content "..."
divineos context             # Recent events (working memory)
divineos verify              # Check ledger integrity
divineos search KEYWORD      # Full-text search
divineos export              # Export ledger to markdown
divineos handoff             # View/set handoff notes

# Analysis
divineos scan SESSION        # Deep-scan session, extract knowledge
divineos analyze SESSION     # Quality report for a session
divineos analyze-now         # Analyze current session
divineos deep-report SESSION # Full deep analysis report
divineos patterns            # Cross-session quality patterns
divineos sessions            # List analyzed sessions
divineos report              # Latest analysis report
divineos cross-session       # Cross-session trends
divineos clarity             # Clarity analysis
divineos growth              # Growth tracking
divineos hooks               # Hook diagnostics
divineos verify-enforcement  # Check enforcement setup

# Commitments
divineos commitment add "text"    # Record a commitment
divineos commitment list          # Show pending commitments
divineos commitment done "text"   # Mark commitment fulfilled
divineos commitment review        # Review all at session end
divineos commitment clear         # Clear after review

# Self-awareness
divineos self-model              # Unified self-model from evidence
divineos drift                   # Check behavioral drift
divineos predict [events...]     # Predict session needs
divineos affect-feedback         # How affect influences behavior
divineos knowledge-compress      # Compress redundant knowledge
divineos knowledge-hygiene       # Audit types, sweep stale, flag orphans

# Skills & curiosity
divineos skill list              # Show tracked skills
divineos skill record NAME       # Record skill use (--success/--failure)
divineos curiosity add "question" # File a new curiosity
divineos curiosity list          # Show open curiosities
divineos curiosity answer Q A    # Mark curiosity answered
divineos curiosity note Q NOTE   # Add note to curiosity

# Temporal knowledge
divineos changes                 # Knowledge changes (--hours, --days)
```

## Architecture

```
src/divineos/
  __init__.py                  Package init
  __main__.py                  python -m divineos entry point
  seed.json                    Initial knowledge seed (versioned)
  cli/                         CLI package (109 commands across 23 modules)
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
    relationship_commands.py   relationships (backward-compat shim → entity_commands)
    knowledge_health_commands.py  health, distill, migrate, backfill
    question_commands.py       Questions (backward-compat shim → entity_commands)
    claim_commands.py          Claims engine and affect log
    decision_commands.py       Decision journal commands
    commitment_commands.py     commitments (backward-compat shim → entity_commands)
    selfmodel_commands.py      self-model, drift, predict, skill, curiosity, affect-feedback, knowledge-hygiene
    entity_commands.py         commitments, temporal, questions, relationships (consolidated)
    temporal_commands.py       changes (backward-compat shim → entity_commands)
    event_commands.py          emit, verify-enforcement
    ledger_commands.py         log, list, search, context, export
    memory_commands.py         core, recall, active, remember, refresh
  core/
    ledger.py                  Append-only event store (SQLite, WAL mode)
    _ledger_base.py            Shared ledger DB connection and hashing
    ledger_class.py            OOP Ledger wrapper (backward-compat shim → ledger)
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
    hud_slots_extra.py         Additional HUD slot builders (backward-compat shim → hud)
    constants.py               Central tuning constants (all behavioral levers in one place)
    knowledge/                 Knowledge engine sub-package
      _base.py                 DB connection, schema, public API
      _text.py                 Text analysis, noise filtering, FTS, overlap (consolidated)
      _noise.py                Extraction noise (backward-compat shim → _text)
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
      temporal.py              Temporal bounds (valid_from/valid_until) and time-aware queries
      compression.py           Knowledge compression (dedup, synthesis, graph-aware)
      graph_retrieval.py       Graph-enhanced retrieval (BFS traversal of edges)
      signal_trust.py          Signal trust tiers (MEASURED > BEHAVIORAL > SELF_REPORTED)
    logic/                     Formal logic sub-package
      warrants.py              Evidence backing for knowledge claims
      logic_validation.py      Consistency, validity gate, defeat lessons (consolidated)
      logic_reasoning.py       Inference engine, relations, warrant backfill (consolidated)
      logic_session.py         Session logic pass and logic summary (consolidated)
      relations.py             Logical relations (backward-compat shim → logic_reasoning)
      consistency.py           Contradiction detection (backward-compat shim → logic_validation)
      inference.py             Inference engine (backward-compat shim → logic_reasoning)
      validity_gate.py         Validity gate (backward-compat shim → logic_validation)
      defeat_lessons.py        Defeat lessons (backward-compat shim → logic_validation)
      session_logic.py         Session logic (backward-compat shim → logic_session)
      logic_summary.py         Logic summary (backward-compat shim → logic_session)
      warrant_backfill.py      Warrant backfill (backward-compat shim → logic_reasoning)
    questions.py               Open question tracking and resolution
    quality_gate.py            Session quality assessment (backward-compat shim → pipeline_gates)
    knowledge_maintenance.py   Contradiction detection, hygiene cleanup, maturity lifecycle (consolidated)
    knowledge_hygiene.py       Knowledge hygiene (backward-compat shim → knowledge_maintenance)
    knowledge_contradiction.py Contradiction detection (backward-compat shim → knowledge_maintenance)
    knowledge_maturity.py      Maturity lifecycle (backward-compat shim → knowledge_maintenance)
    guardrails.py              Runtime limits and violation tracking
    seed_manager.py            Seed versioning, validation, merge/apply
    anticipation.py            Pattern anticipation engine
    growth.py                  Growth awareness and milestone tracking
    tone_texture.py            Emotional arc and tone classification
    parser.py                  Chat export ingestion (JSONL + markdown)
    session_manager.py         Session lifecycle management
    session_tracker.py         Session state (backward-compat shim → session_manager)
    session_checkpoint.py      Periodic saves and context monitoring
    enforcement.py             CLI-level event capture and signal handling
    enforcement_verifier.py    Enforcement setup verification
    tool_wrapper.py            Tool execution interception
    tool_capture.py            Tool call recording
    core_memory_refresh.py     Core memory refresh from knowledge
    error_handling.py          Shared error handling utilities
    event_verifier.py          Event integrity verification
    loop_prevention.py         Loop detection and prevention
    affect.py                  Affect tracking and feedback loop (consolidated)
    affect_log.py              Valence-arousal affect state (backward-compat shim → affect)
    affect_feedback.py         Affect feedback loop (backward-compat shim → affect)
    trust_tiers.py             Signal trust weighting (MEASURED > BEHAVIORAL > SELF_REPORTED)
    planning_commitments.py    Commitment tracking and fulfillment checking
    skill_library.py           Evidence-based skill proficiency tracking
    curiosity_engine.py        Question tracking (OPEN → INVESTIGATING → ANSWERED)
    self_model.py              Unified self-model assembled from all OS systems
    drift_detection.py         Behavioral drift detection (lesson regressions, quality trends)
    predictive_session.py      Session profile detection and need prediction
    claim_store.py             Claims engine with evidence tiers
    decision_journal.py        Decision journal with FTS search
  analysis/
    _session_types.py          Session analysis type definitions
    analysis.py                Core session analysis pipeline
    analysis_retrieval.py      Analysis result retrieval
    analysis_storage.py        Report storage, formatting, cross-session trends
    analysis_types.py          Analysis result type definitions
    session_analyzer.py        Session parsing and signal detection
    session_discovery.py       Auto-discover sessions from ledger data
    quality_checks.py          7 measurable quality checks
    quality_checks_extra.py    Additional quality checks (backward-compat shim → quality_checks)
    record_extraction.py       JSONL record parsing helpers
    quality_storage.py         Quality report DB storage
    quality_trends.py          Session quality trending over time
    session_features.py        Timeline, files, activity, error recovery
    session_features_extra.py  Additional session features (backward-compat shim → session_features)
    tone_tracking.py           Tone shift detection and classification
    feature_storage.py         Feature result DB storage
  agent_integration/           Agent integration sub-package
    base.py                    Base integration interfaces
    types.py                   Type definitions
    outcome_measurement.py     Rework, churn, correction rate, session health
    memory_monitor.py          Token tracking and compression
    memory_actions.py          Memory-triggered actions
    learning_cycle.py          Pattern extraction and confidence updates
    learning_loop.py           Continuous learning loop
    learning_audit_store.py    Learning audit trail storage
    behavior_analyzer.py       Agent behavior analysis
    decision_store.py          Decision persistence
    feedback_system.py         Feedback processing
    mcp_integration.py         MCP protocol integration
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
    config_validator.py        Configuration validation
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
    error_handler.py           Error handling for integrations
    error_recovery.py          Error recovery strategies
    mcp_event_capture_server.py  MCP event capture server
    system_monitor.py          System health monitoring
    unified_tool_capture.py    Unified tool capture layer
  supersession/                Contradiction detection and resolution
    clarity_integration.py     Clarity system integration
    contradiction_detector.py  Contradiction detection
    event_integration.py       Event system integration
    ledger_integration.py      Ledger integration
    query_interface.py         Query API
    resolution_engine.py       Resolution strategies
  violations_cli/              Violation reporting CLI
    violations_command.py      Violation report commands
tests/                         2,645+ tests (real DB, no mocks)
setup/                         Hook setup scripts (bash + powershell)
.claude/hooks/                 Claude Code enforcement hooks
  load-briefing.sh             Marks briefing as loaded
  require-goal.sh              PreToolUse gate (briefing + goal enforcement)
  resume-session.sh            Shows context on session resume
  session-checkpoint.sh        PostToolUse checkpoint and context monitoring
  run-tests.sh                 Auto-run tests on changes
```

## Design Rules

1. **No theater.** Every line of code does something real and verifiable.
2. **Append-only truth.** The ledger never lies. Data in, hash it, verify it.
3. **AI thinks, code scaffolds.** Frameworks for reasoning, not fake reasoning.
4. **Build, test, verify.** One piece at a time. Run `pytest tests/ -q --tb=short` after every change.
5. **Database is source of truth.** Query the DB, don't guess from file reads.

## Development

```bash
pytest tests/ -q --tb=short   # Run all tests
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
```

## License

AGPL-3.0-or-later
