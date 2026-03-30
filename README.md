# DivineOS

An operating system for AI agents. Memory, continuity, accountability, and learning across sessions. Not a human tool — a vessel that enhances AI reasoning, self-awareness, and growth.

[![Tests](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml)
[![Code Quality](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/code-quality.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/code-quality.yml)
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

## Quick Start

```bash
pip install -e ".[dev]"
divineos init
divineos briefing
```

## CLI Commands

```bash
# Session workflow
divineos briefing            # Start here — your context, lessons, and memory
divineos hud                 # Full heads-up display
divineos emit SESSION_END    # End-of-session analysis and knowledge extraction

# Memory
divineos recall              # Core memory + active memory
divineos active              # Active memory ranked by importance
divineos ask "topic"         # Search what the system knows
divineos core                # View/edit core memory slots
divineos refresh             # Rebuild active memory from knowledge store

# Knowledge
divineos learn "..."         # Store knowledge from experience
divineos knowledge           # List stored knowledge
divineos consolidate-stats   # Knowledge statistics and effectiveness
divineos health              # Run knowledge health check
divineos outcomes            # Measure learning effectiveness

# Lessons & Goals
divineos lessons             # Tracked lessons from past sessions
divineos goal "description"  # Track a user goal
divineos directives          # List active directives

# Ledger
divineos log --type TYPE --actor ACTOR --content "..."
divineos context             # Recent events (working memory)
divineos verify              # Check ledger integrity
divineos search KEYWORD      # Full-text search

# Logic & reasoning
divineos questions           # List open questions
divineos question "..."      # Record an open question
divineos question-resolve ID # Resolve an open question

# Analysis
divineos scan SESSION        # Deep-scan session, extract knowledge
divineos analyze SESSION     # Quality report for a session
divineos patterns            # Cross-session quality patterns
```

## Architecture

```
src/divineos/
  cli/                         CLI package (67 commands across 10+ modules)
    __init__.py                Entry point and command registration
    session_pipeline.py        SESSION_END orchestrator (calls phases)
    pipeline_gates.py          Enforcement gates (quality, briefing, engagement)
    pipeline_phases.py         Heavy-lifting phases (feedback, scoring, finalization)
    knowledge_commands.py      learn, ask, briefing, forget, lessons
    analysis_commands.py       analyze, report, trends
    hud_commands.py            hud, goal, plan commands
    journal_commands.py        journal save/list/search/link
    directive_commands.py      directive management
    relationship_commands.py   knowledge relationships
    knowledge_health_commands.py  health, distill, migrate
    question_commands.py       Open question tracking commands
  seed.json                    Initial knowledge seed (versioned)
  core/
    ledger.py                  Append-only event store (SQLite, WAL mode)
    ledger_class.py            OOP Ledger wrapper for integration code
    fidelity.py                Manifest-receipt integrity verification
    memory.py                  Core memory + active memory + importance scoring
    memory_journal.py          Personal journal (save/list/search/link)
    hud.py                     HUD slot builders and assembly
    hud_state.py               Goal/plan/health state management
    hud_handoff.py             Session handoff, engagement, goal extraction
    knowledge/                 Knowledge engine sub-package
      _base.py                 DB connection, public get_connection() API
      extraction.py            Knowledge extraction from sessions
      deep_extraction.py       Deep multi-pass extraction
      feedback.py              Session feedback application
      migration.py             Knowledge type migration
      _text.py                 Text analysis utilities (FTS, overlap, noise)
      edges.py                 Unified edge table (typed relations, auto-warrants)
    logic/                     Formal logic sub-package
      warrants.py              Evidence backing for knowledge claims
      relations.py             Logical relations (supports/contradicts/requires)
      consistency.py           Contradiction and cycle detection
      inference.py             Forward-chaining inference engine
      validity_gate.py         Blocks under-supported knowledge
      defeat_lessons.py        Learn from superseded/contradicted knowledge
      session_logic.py         Per-session logic pass (SESSION_END integration)
      logic_summary.py         Logic health summary for HUD
    questions.py               Open question tracking and resolution
    quality_gate.py            Session quality assessment before extraction
    knowledge_contradiction.py Contradiction detection and resolution
    knowledge_maturity.py      RAW → HYPOTHESIS → TESTED → CONFIRMED lifecycle
    guardrails.py              Runtime limits and violation tracking
    seed_manager.py            Seed versioning, validation, merge/apply
    anticipation.py            Pattern anticipation engine
    growth.py                  Growth awareness and milestone tracking
    tone_texture.py            Emotional arc and tone classification
    parser.py                  Chat export ingestion (JSONL + markdown)
    session_manager.py         Session lifecycle management
    enforcement.py             CLI-level event capture
    tool_wrapper.py            Tool execution interception
  analysis/
    analysis.py                Core session analysis pipeline
    analysis_storage.py        Report storage, formatting, cross-session trends
    session_analyzer.py        Session parsing and signal detection
    quality_checks.py          7 measurable quality checks
    record_extraction.py       JSONL record parsing helpers
    quality_storage.py         Quality report DB storage
    session_features.py        Timeline, files, activity, error recovery
    tone_tracking.py           Tone shift detection and classification
    feature_storage.py         Feature result DB storage
    quality_trends.py          Session quality trending over time
  agent_integration/
    outcome_measurement.py     Rework, churn, correction rate, session health
    memory_monitor.py          Token tracking and compression
    learning_cycle.py          Pattern extraction and confidence updates
  clarity_system/              Clarity rules and violation tracking
  event/                       Event types, dispatch, capture
  clarity_enforcement/         Clarity checking system
  hooks/                       Git hook integration
  integration/                 IDE and MCP integration
  supersession/                Contradiction detection and resolution
  violations_cli/              Violation reporting CLI
tests/                         2000+ tests (real DB, no mocks)
setup/                         Hook setup scripts
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
