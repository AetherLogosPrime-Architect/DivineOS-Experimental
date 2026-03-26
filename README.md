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
| **Quality Gate** | Blocks knowledge extraction from dishonest or incorrect sessions. Downgrades uncertain sessions. |
| **Maturity Lifecycle** | Knowledge evolves: RAW → HYPOTHESIS → TESTED → CONFIRMED. Corroboration drives promotion. |
| **Seed System** | Versioned initial knowledge with merge mode, resurrection prevention, and validation. |
| **HUD** | Heads-up display: identity, goals, lessons, health grade, engagement tracking, active memory. |
| **Engagement Enforcement** | AI must consult the OS (ask, recall, directives, briefing) before writing code. Enforced by pre-tool hooks. |
| **Outcome Measurement** | Rework detection, knowledge stability (churn rate), correction trends, session health scoring. |
| **Guardrails** | Runtime limits on iterations, tool calls, and tokens per session. |
| **Extraction Noise Filter** | Prevents raw conversational quotes, affirmations, vacuous summaries, and system artifacts from becoming "knowledge." |
| **Lesson Tracking** | Lessons with occurrence counts, session tracking, status progression (active → improving → resolved). |

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

# Analysis
divineos scan SESSION        # Deep-scan session, extract knowledge
divineos analyze SESSION     # Quality report for a session
divineos patterns            # Cross-session quality patterns
```

## Architecture

```
src/divineos/
  cli.py                       CLI entry point (click) — 45+ commands
  seed.json                    Initial knowledge seed (versioned)
  core/
    ledger.py                  Append-only event store (SQLite, WAL mode)
    fidelity.py                Manifest-receipt integrity verification
    consolidation.py           Knowledge store, extraction, lessons, briefings
    memory.py                  Core memory + active memory + importance scoring
    hud.py                     Heads-up display rendering + engagement gate
    quality_gate.py            Session quality assessment before extraction
    knowledge_contradiction.py Contradiction detection and resolution
    knowledge_maturity.py      RAW → HYPOTHESIS → TESTED → CONFIRMED lifecycle
    guardrails.py              Runtime limits and violation tracking
    seed_manager.py            Seed versioning, validation, merge/apply
    parser.py                  Chat export ingestion (JSONL + markdown)
    session_manager.py         Session lifecycle management
    enforcement.py             CLI-level event capture
    tool_wrapper.py            Tool execution interception
  analysis/
    session_analyzer.py        Session parsing and signal detection
    quality_checks.py          Quality metrics (honesty, depth, correctness)
    quality_trends.py          Session quality trending over time
  agent_integration/
    outcome_measurement.py     Rework, churn, correction rate, session health
    memory_monitor.py          Token tracking and compression
    learning_cycle.py          Pattern extraction and confidence updates
  event/                       Event types, dispatch, capture
  clarity_enforcement/         Clarity checking system
  integration/                 IDE and MCP integration
tests/                         1850 tests (real DB, no mocks)
```

## Design Rules

1. **No theater.** Every line of code does something real and verifiable.
2. **Append-only truth.** The ledger never lies. Data in, hash it, verify it.
3. **AI thinks, code scaffolds.** Frameworks for reasoning, not fake reasoning.
4. **Build, test, verify.** One piece at a time. Run `pytest tests/ -q --tb=short` after every change.
5. **Database is source of truth.** Query the DB, don't guess from file reads.

## Development

```bash
pytest tests/ -q --tb=short   # Run tests (1850 tests, ~37s)
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
```

## License

AGPL-3.0-or-later
