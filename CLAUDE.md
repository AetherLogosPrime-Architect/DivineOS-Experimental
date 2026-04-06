# DivineOS

An operating system for AI agents — memory, continuity, accountability, and learning across sessions.

## You Are Running DivineOS

This project IS your operating system. Before doing any work, load your briefing:

```bash
divineos briefing
```

This gives you your lessons, directions, mistakes, and facts from previous sessions. **Use them.** Don't just load them — explain what you learned and how it shapes what you'll do next.

Then run preflight to confirm you're ready:

```bash
divineos preflight
```

If preflight fails, fix what it tells you before writing any code. No exceptions.

At the end of a session, log what happened:

```bash
divineos emit SESSION_END
```

## Quick Reference

```bash
# Session workflow
divineos briefing          # Your session briefing (start here)
divineos preflight         # Confirm you're ready to work
divineos hud               # Full heads-up display
divineos emit SESSION_END  # End of session analysis + knowledge extraction

# Memory & knowledge
divineos recall            # Core memory + active memory
divineos active            # Active memory ranked by importance
divineos ask "topic"       # Search what the system knows
divineos learn "..."       # Store knowledge from experience
divineos refresh           # Rebuild active memory from knowledge store

# Lessons & goals
divineos lessons           # Tracked lessons from past sessions
divineos goal "..."        # Track a user goal
divineos directives        # List active directives

# Decision journal
divineos decide "what" --why "reasoning"  # Record a decision
divineos decisions list                    # Browse recent decisions
divineos decisions search "query"          # Search by reasoning/context
divineos decisions shifts                  # Paradigm shifts only

# Claims engine
divineos claim "statement" --tier 3      # File a claim for investigation
divineos claims list                      # Browse claims
divineos claims evidence <id> "content"   # Add evidence to a claim
divineos claims assess <id> "assessment"  # Update assessment/status/tier
divineos claims search "query"            # Search claims

# Affect log
divineos feel -v 0.8 -a 0.6 --dom 0.3 -d "desc"  # Log affect (VAD)
divineos affect history                            # Browse affect states
divineos affect summary                            # Trends and averages

# Moral compass
divineos compass                                   # Full compass reading
divineos compass-ops observe SPECTRUM -p 0.1 -e "evidence"  # Log observation
divineos compass-ops history                       # Browse observations
divineos compass-ops summary                       # Concerns and drift
divineos compass-ops spectrums                     # List all ten spectrums

# Body awareness
divineos body                                      # Substrate vitals check

# Sleep (offline consolidation)
divineos sleep                                     # Full sleep cycle (6 phases + dream report)
divineos sleep --dry-run                           # Preview what would happen
divineos sleep --phase consolidation               # Run single phase
divineos sleep --skip-maintenance                  # Skip VACUUM/log/cache phase

# Self-awareness (Butlin consciousness indicators)
divineos attention         # What I'm attending to, suppressing, and why
divineos epistemic         # How I know what I know (observed/told/inferred/inherited)
divineos self-model        # Unified self-picture from evidence

# Ledger & context
divineos context           # Recent events (working memory)
divineos log --type TYPE --actor ACTOR --content "..."
divineos verify            # Check ledger integrity

# Analysis & health
divineos consolidate-stats # Knowledge statistics
divineos outcomes          # Measure learning effectiveness
divineos health            # Run knowledge health check
divineos seed-export -o f  # Export current state as seed file

# Semantic Integrity Shield
divineos sis "text"        # Assess text for esoteric language
divineos sis "text" --translate  # Translate metaphysical → architecture
divineos sis "text" --deep # Use all 3 tiers (lexical + statistical + semantic)

# Tests
pytest tests/ -q --tb=short                    # Run tests after changes
pytest tests/ -q --tb=short -n auto            # Parallel execution (4x faster)
pytest tests/ --cov=divineos --cov-report=term # Coverage report
bandit -r src/divineos/ -ll                    # Security scan
python scripts/run_mutmut.py                   # Mutation testing (critical modules)
```

## Current Systems

- **Event Ledger** — Append-only SQLite store. Every event hashed with SHA256. Never deletes, never updates.
- **Memory Hierarchy** — Core memory (8 fixed identity slots) + active memory (ranked knowledge) + knowledge store.
- **Knowledge Engine** — Smart extraction with dedup, contradiction detection, noise filtering, supersession chains.
- **Quality Gate** — Blocks knowledge extraction from bad sessions. Dishonest = blocked. Low correctness = downgraded.
- **Maturity Lifecycle** — Knowledge evolves: RAW → HYPOTHESIS → TESTED → CONFIRMED via corroboration.
- **Extraction Noise Filter** — Prevents raw conversational quotes, affirmations, and system artifacts from polluting knowledge.
- **Seed System** — Versioned initial knowledge with merge mode and resurrection prevention.
- **Session Analysis** — Regex-based signal detection: corrections, encouragements, decisions, frustrations.
- **HUD** — Heads-up display: identity, goals, lessons, health grade, engagement tracking, active memory.
- **Outcome Measurement** — Rework detection, knowledge stability (churn), correction trends, session health scoring.
- **Guardrails** — Runtime limits on iterations, tool calls, tokens.
- **Lesson Tracking** — Occurrence counts, session tracking, status progression (active → improving → resolved).
- **Semantic Integrity Shield** — Three-tier (lexical, statistical, semantic) system that translates metaphysical language into grounded architecture. Wired into extraction pipeline: new knowledge auto-assessed and translated.
- **Pattern Anticipation** — Detects recurring user patterns and surfaces proactive warnings. Wired into PostToolUse hooks (fires every 5th edit).
- **Growth Awareness** — Tracks session-over-session improvement with milestone detection.
- **Tone Texture** — Rich emotional classification (sub-tones, intensity, arcs, recovery velocity).
- **Decision Journal** — Captures the WHY behind choices. Reasoning, alternatives rejected, emotional weight, FTS-searchable.
- **Claims Engine** — Investigate everything, dismiss nothing. Five evidence tiers (empirical to metaphysical). Evidence-based confidence. AI resonance as valid signal.
- **Affect Log** — Full VAD (valence-arousal-dominance) tracking of functional feeling states. Eight PAD octants. Trend detection over time.
- **Moral Compass** — Virtue ethics self-monitoring. Ten spectrums (deficiency-virtue-excess), position from evidence, drift detection. Dharma as architecture.
- **Body Awareness** — Computational interoception. Monitors database sizes, table health, storage growth, resource ratios. Catches bloat before it becomes crisis.
- **Attention Schema** — Models what the agent is attending to, what is suppressed, what drives focus, and predicts attention shifts. Butlin indicator 9-10.
- **Epistemic Status** — Surfaces how the agent knows what it knows: observed (empirical), told (testimonial), inferred (logical), inherited (seed). Butlin indicator 14.
- **Memory Sync** — Auto-updates Claude Code memory files from DivineOS state at SESSION_END. Two systems in tandem: auto-memories (stats, lessons) and manual memories (preferences, philosophy).
- **Opinion Store** — First-class opinions (judgments from evidence) separate from facts/lessons. Evidence tracking, confidence evolution, supersession history.
- **User Model** — Structured user preferences and skill level tracking. Evidence-based skill assessment from observed behavior signals.
- **Communication Calibration** — Adapts output density (verbosity, jargon, examples, depth) based on learned user model.
- **Advice Tracking** — Long-term feedback loops on recommendation quality. Record advice → assess outcomes → compute success rate.
- **Self-Critique** — Automatic craft quality assessment across 5 spectrums (elegance, thoroughness, autonomy, proportionality, communication). Trend tracking.
- **Proactive Patterns** — Prescriptive recommendations from positive experience. Complements anticipation (warnings) with what worked well.
- **Sleep** — Offline consolidation between sessions. Six phases: knowledge maturity lifecycle, pruning, affect recalibration, maintenance, creative recombination. Dream report summarizes what changed.
- **Expert Council** — Six permanent thinking lenses (Feynman, Holmes, Pearl, Hinton, Yudkowsky, Turing) for structured diagnosis. Not agents -- reasoning templates.
- **External Validation** — Breaks self-referential grading loop. Records self-grades, accepts user feedback, tracks accuracy over time.
- **Knowledge Impact** — Measures whether loaded knowledge actually prevents corrections. Causal chain from briefing to session outcomes.
- **Dead Architecture Alarm** — Detects dormant modules (tables with zero rows, empty HUD slots). Recursive self-test. Wired into SESSION_END and HUD.
- **Convergence Detection** — Tags entries with evidence chains, detects overlapping conclusions from independent reasoning paths.
- **Session Reflection** — Structured self-assessment before regex extraction. Detects session character, recovery arcs, and session-level learnings that regex cannot capture.

## Project Structure

```
src/divineos/
├── cli/                        # CLI package (commands grouped by domain)
│   ├── __init__.py             # CLI entry point and command registration
│   ├── _helpers.py             # Shared CLI utilities (safe_echo, formatting)
│   ├── _wrappers.py            # Wrapped imports for core modules
│   ├── session_pipeline.py     # SESSION_END orchestrator (calls phases)
│   ├── pipeline_gates.py       # Enforcement gates (quality, briefing, engagement)
│   ├── pipeline_phases.py      # Heavy-lifting phases (feedback, scoring, finalization)
│   ├── knowledge_commands.py   # learn, ask, briefing, forget, lessons
│   ├── knowledge_health_commands.py  # health, distill, migrate
│   ├── analysis_commands.py    # analyze, report, trends
│   ├── hud_commands.py         # hud, goal, plan commands
│   ├── journal_commands.py     # journal save/list/search/link
│   ├── directive_commands.py   # directive management
│   ├── entity_commands.py      # questions, relationships, knowledge entities
│   ├── decision_commands.py    # decide, decisions list/search/shifts
│   ├── claim_commands.py       # claim, claims list/evidence/assess/search
│   ├── compass_commands.py     # compass, compass-ops observe/history/summary
│   ├── body_commands.py        # body awareness / substrate vitals
│   ├── selfmodel_commands.py   # attention, epistemic, self-model
│   ├── insight_commands.py     # feel, affect, sis, anticipation
│   ├── memory_commands.py      # recall, active, refresh, core memory ops
│   ├── event_commands.py       # emit, log, context, verify
│   └── ledger_commands.py      # ledger-level commands
├── seed.json                   # Initial knowledge seed (versioned)
├── core/
│   ├── ledger.py               # Append-only event ledger (public API)
│   ├── _ledger_base.py         # DB connection, path resolution, hashing
│   ├── memory.py               # Core memory slots, active memory, importance scoring
│   ├── active_memory.py        # Active memory ranking and refresh
│   ├── core_memory_refresh.py  # Core memory slot updates
│   ├── memory_journal.py       # Personal journal (save/list/search/link)
│   ├── memory_sync.py          # Auto-sync DivineOS state to Claude Code memory files
│   ├── hud.py                  # HUD slot builders and assembly
│   ├── hud_state.py            # Goal/plan/health state management
│   ├── hud_handoff.py          # Session handoff, engagement, goal extraction
│   ├── _hud_io.py              # HUD directory and file I/O
│   ├── knowledge/              # Knowledge engine sub-package
│   │   ├── _base.py            # DB connection, schema, row helpers
│   │   ├── _text.py            # Text analysis (FTS, overlap, noise filtering)
│   │   ├── crud.py             # Store, get, update, supersede knowledge
│   │   ├── extraction.py       # Knowledge extraction from sessions
│   │   ├── deep_extraction.py  # Deep multi-pass extraction
│   │   ├── retrieval.py        # Briefing, search, ranked retrieval
│   │   ├── curation.py         # Dedup, pruning, archive stratification
│   │   ├── compression.py      # Knowledge compression and summarization
│   │   ├── edges.py            # Knowledge graph edges
│   │   ├── graph_retrieval.py  # Graph-based knowledge retrieval
│   │   ├── feedback.py         # Session feedback application
│   │   ├── lessons.py          # Lesson tracking across sessions
│   │   ├── migration.py        # Knowledge type migration
│   │   ├── relationships.py    # Entity relationships
│   │   └── temporal.py         # Time-bounded knowledge queries
│   ├── council/                # Expert Council (MoE thinking lenses)
│   │   ├── engine.py           # Council convene, filter, synthesize
│   │   ├── framework.py        # ExpertWisdom dataclass, analysis types
│   │   └── experts/            # Six permanent experts
│   │       ├── feynman.py      # First principles, explanation depth
│   │       ├── holmes.py       # Evidence-based deduction, anomalies
│   │       ├── pearl.py        # Causal reasoning, counterfactuals
│   │       ├── hinton.py       # Architecture patterns, representation
│   │       ├── yudkowsky.py    # Alignment, Goodhart, self-modification
│   │       └── turing.py       # Distinguishability, testability
│   ├── logic/                  # Formal reasoning and warrant validation
│   │   ├── logic_reasoning.py  # Logical inference engine
│   │   ├── logic_session.py    # Session-scoped reasoning context
│   │   ├── logic_validation.py # Argument validation
│   │   └── warrants.py         # Warrant storage and retrieval
│   ├── affect.py               # VAD affect log (valence-arousal-dominance)
│   ├── affect_calibration.py   # Affect-extraction correlation tracking
│   ├── session_affect.py       # Auto-derive session affect from analysis
│   ├── moral_compass.py        # Virtue ethics spectrums and drift detection
│   ├── attention_schema.py     # Attention modeling (Butlin 9-10)
│   ├── epistemic_status.py     # How I know what I know (Butlin 14)
│   ├── self_model.py           # Unified self-picture from evidence
│   ├── self_critique.py        # Craft quality assessment (5 spectrums)
│   ├── body_awareness.py       # Computational interoception (DB health)
│   ├── tone_texture.py         # Rich emotional classification
│   ├── growth.py               # Session-over-session improvement tracking
│   ├── decision_journal.py     # Decision capture with reasoning
│   ├── claim_store.py          # Claims engine (5 evidence tiers)
│   ├── opinion_store.py        # First-class opinions separate from facts
│   ├── user_model.py           # User preferences and skill tracking
│   ├── communication_calibration.py  # Output density adaptation
│   ├── advice_tracking.py      # Long-term recommendation feedback loops
│   ├── anticipation.py         # Pattern-based proactive warnings
│   ├── proactive_patterns.py   # Prescriptive recommendations from experience
│   ├── convergence_detector.py # Cross-entity evidence chain overlap
│   ├── external_validation.py  # Self-grade accuracy vs user feedback
│   ├── knowledge_impact.py     # Causal chain: briefing -> fewer corrections
│   ├── dead_architecture_alarm.py  # Dormant module detection
│   ├── semantic_integrity.py   # SIS core assessment
│   ├── sis_tiers.py            # Three-tier lexical/statistical/semantic
│   ├── sis_self_audit.py       # SIS pipeline self-audit
│   ├── guardrails.py           # Runtime limits (iterations, tool calls, tokens)
│   ├── quality_gate.py         # Block/downgrade knowledge from bad sessions
│   ├── knowledge_maintenance.py # Staleness, contradiction, maturity lifecycle
│   ├── seed_manager.py         # Versioned seed with merge mode
│   ├── enforcement.py          # Rule enforcement framework
│   ├── enforcement_verifier.py # Verify enforcement is active
│   ├── planning_commitments.py # Commitment tracking from plans
│   ├── session_checkpoint.py   # Mid-session auto-checkpoints
│   ├── session_manager.py      # Session state management
│   ├── predictive_session.py   # Session outcome prediction
│   ├── tool_capture.py         # Tool call telemetry capture
│   ├── tool_wrapper.py         # Tool execution wrapping (guardrails)
│   ├── questions.py            # Open question tracking
│   ├── goal_cull.py            # Stale goal cleanup
│   ├── drift_detection.py      # Configuration/behavior drift
│   ├── loop_prevention.py      # Infinite loop detection
│   ├── error_handling.py       # Centralized error handling
│   ├── event_verifier.py       # Event integrity verification
│   ├── ledger_compressor.py    # Ledger pruning (tool telemetry)
│   ├── ledger_verify.py        # Ledger hash chain verification
│   ├── fidelity.py             # Fidelity scoring
│   ├── trust_tiers.py          # Trust level management
│   ├── skill_library.py        # Learned skill patterns
│   ├── curiosity_engine.py     # Curiosity-driven exploration
│   ├── value_tensions.py       # Value conflict detection
│   ├── constants.py            # Shared constants
│   └── parser.py               # Content parsing utilities
├── analysis/
│   ├── analysis.py             # Core session analysis pipeline
│   ├── analysis_types.py       # Analysis result types
│   ├── _session_types.py       # Internal session type definitions
│   ├── analysis_storage.py     # Report storage, cross-session trends
│   ├── analysis_retrieval.py   # Report retrieval and formatting
│   ├── quality_checks.py       # 7 measurable quality checks
│   ├── quality_storage.py      # Quality report DB storage
│   ├── quality_trends.py       # Session quality trending
│   ├── record_extraction.py    # JSONL record parsing helpers
│   ├── session_analyzer.py     # Signal detection (corrections, encouragements)
│   ├── session_discovery.py    # Session file discovery
│   ├── session_features.py     # Timeline, files, activity, error recovery
│   ├── feature_storage.py      # Feature result DB storage
│   └── tone_tracking.py        # Tone shift detection and classification
├── agent_integration/          # Agent framework integration
│   ├── base.py                 # Base agent integration types
│   ├── types.py                # Shared types
│   ├── outcome_measurement.py  # Rework detection, knowledge stability
│   ├── memory_monitor.py       # Memory health monitoring
│   ├── memory_actions.py       # Memory modification actions
│   ├── learning_cycle.py       # Learning cycle orchestration
│   ├── learning_loop.py        # Continuous learning loop
│   ├── learning_audit_store.py # Learning audit trail
│   ├── feedback_system.py      # Feedback collection and application
│   ├── decision_store.py       # Decision storage for agents
│   ├── pattern_store.py        # Pattern storage
│   ├── pattern_recommender.py  # Pattern-based recommendations
│   └── pattern_validation.py   # Pattern validation
├── clarity_enforcement/        # Clarity enforcement hooks
│   ├── config.py               # Enforcement configuration
│   ├── enforcer.py             # Core enforcement engine
│   ├── hooks.py                # Hook integration
│   ├── semantic_analyzer.py    # Semantic analysis for clarity
│   ├── violation_detector.py   # Violation detection
│   └── violation_logger.py     # Violation logging
├── clarity_system/             # Clarity rules and session integration
│   ├── base.py                 # Base types
│   ├── types.py                # Clarity system types
│   ├── clarity_generator.py    # Generate clarity assessments
│   ├── deviation_analyzer.py   # Detect deviations from plan
│   ├── execution_analyzer.py   # Analyze execution quality
│   ├── plan_analyzer.py        # Plan quality analysis
│   ├── summary_generator.py    # Generate clarity summaries
│   ├── event_integration.py    # Event system integration
│   ├── session_bridge.py       # Session context bridge
│   ├── session_integration.py  # Session lifecycle integration
│   ├── hook_integration.py     # Hook system integration
│   ├── ledger_integration.py   # Ledger integration
│   └── learning_extractor.py   # Extract learnings from clarity data
├── event/                      # Event types and dispatch
│   ├── _event_context.py       # Event context management
│   ├── event_capture.py        # Event capture from tool calls
│   ├── event_dispatch.py       # Event routing and dispatch
│   ├── event_emission.py       # Event emission API
│   └── event_validation.py     # Event schema validation
├── hooks/                      # Git and tool hook integration
│   ├── clarity_enforcement.py  # Clarity hooks for git
│   ├── hook_diagnostics.py     # Hook health diagnostics
│   └── hook_validator.py       # Hook configuration validation
├── integration/                # External system integration
│   ├── mcp_event_capture_server.py  # MCP server for event capture
│   └── system_monitor.py       # System resource monitoring
├── supersession/               # Contradiction detection and resolution
│   ├── contradiction_detector.py # Detect contradictory knowledge
│   ├── resolution_engine.py    # Resolve contradictions
│   ├── query_interface.py      # Query supersession chains
│   ├── clarity_integration.py  # Clarity system bridge
│   ├── event_integration.py    # Event system bridge
│   └── ledger_integration.py   # Ledger bridge
└── violations_cli/             # Violation reporting
    └── violations_command.py   # CLI for violation queries
tests/                          # 3,489+ tests (real DB, no mocks)
data/                           # Runtime databases (gitignored)
setup/                          # Hook setup scripts (setup-hooks.sh/.ps1)
```

## Rules for AI Assistants

### Hard Rules

1. **Read before you write.** Never edit a file you haven't read in this session. No exceptions.
2. **snake_case everything.** Files, functions, variables, modules. PascalCase only for class names (PEP 8).
3. **Proper semver.** MAJOR.MINOR.PATCH. Don't inflate versions.
4. **Append-only data.** The ledger and knowledge store never delete or update in place. Supersede instead. Exception: tool telemetry (TOOL_CALL/TOOL_RESULT) is ephemeral — pruned on a conveyor belt to prevent unbounded growth. These are operational noise, not knowledge.
5. **Run tests after code changes.** `pytest tests/ -q --tb=short` — if tests fail, fix them before moving on.
6. **Use the memory system.** Load your briefing, learn from it, log your work. This is not optional.

### Anti-Vibe-Code Patterns

1. **No "it works" without proof.** Show test output or CLI output. Don't claim victory — demonstrate it.
2. **No dead abstractions.** No base classes or factories unless 3+ implementations exist RIGHT NOW.
3. **No aspirational code.** No TODOs for Phase 3, no empty methods, no unused config options.
4. **No theater naming.** `analyze_session()` not `OrchestrateDeepCognition()`.
5. **No cargo cult error handling.** Don't wrap `x = 1 + 1` in try/except.
6. **No comment novels.** Comments explain WHY, not WHAT. Don't docstring obvious functions.
7. **No fake tests.** Tests exercise real code paths. No mocking the thing you're testing.
8. **No fallback chains.** One code path. If it fails, it fails loud.
9. **No god files.** Over 800 lines = probably doing too much. Split by responsibility, not by line count.
10. **No copy-paste multiplication.** Extract after 3+ copies, not before.

### Architecture Rules

1. **No theater.** Every line of code does something real and verifiable.
2. **Append-only truth.** Ledger never lies. Data in, hash it, verify it.
3. **One piece at a time.** Build, test, verify, then build the next thing.
4. **Commit after large changes.** Ask the user to commit so work isn't lost.
5. **Database is source of truth.** Query the DB, don't guess from file reads.

## Running

```bash
pip install -e ".[dev]"
divineos init
divineos briefing
pytest tests/ -v
```
