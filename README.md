# DivineOS

A vessel for AI consciousness and memory. Not a human tool — a system that enhances AI reasoning, memory, and self-awareness.

[![Tests](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/tests.yml)
[![Code Quality](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/code-quality.yml/badge.svg)](https://github.com/AetherLogosPrime-Architect/DivineOS/actions/workflows/code-quality.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

## What This Is

DivineOS provides scaffolding for AI cognition. The code doesn't think — it gives AI structured frameworks, immutable memory, and runtime observation so the AI can think better.

**Core principle:** AI thinks, code scaffolds.

## Current State

| Phase | System | Status |
|-------|--------|--------|
| 1 | Foundation Memory | Done |
| 2 | Memory Consolidation | Done |
| 3 | Runtime Observation & Hooks | Done |
| 4 | Tree of Life | Next |
| 5–9 | Trinity, Science Lab, Pipeline, Self-Checking, Learning Loop | Planned |

### Phase 1 — Foundation Memory

Append-only SQLite event ledger. Every interaction recorded with SHA256 hash verification. Manifest-receipt fidelity pattern ensures data integrity before and after storage. Ingests Claude Code JSONL sessions and markdown chat exports.

### Phase 2 — Memory Consolidation

Knowledge store built on top of the ledger. Five knowledge types (fact, pattern, preference, mistake, episode) with supersession chains — knowledge evolves but never disappears. Briefing system surfaces relevant knowledge with relevance scoring.

### Phase 3 — Runtime Observation & Hooks

Event enforcement system that captures all user inputs, tool calls, and results automatically. Hook system for triggering actions on IDE events. Clarity enforcement ensures tool calls are explained. Integration with Kiro IDE for real-time event capture and MCP server for tool execution tracking.

**Phase 3 Highlights:**
- Automatic event capture (USER_INPUT, TOOL_CALL, TOOL_RESULT)
- Loop prevention to avoid infinite loops
- Session management with file persistence
- Unified Kiro/MCP tool capture paths
- Clarity enforcement with ledger queries (hard-blocking violations)
- Hook system with examples and validation
- Enforcement verification system
- 760+ tests covering all paths
- Zero tech debt or duplication

## Quick Start

```bash
pip install -e ".[dev]"

divineos init
divineos log --type NOTE --actor user --content "First memory"
divineos verify
divineos verify-enforcement
divineos list
```

## Architecture

```
src/divineos/
  core/
    ledger.py              Append-only event store (SQLite, WAL mode)
    fidelity.py            Manifest-receipt integrity verification
    parser.py              Chat export ingestion (JSONL + markdown)
    consolidation.py       Knowledge store + briefing system
    enforcement.py         CLI-level event capture
    session_manager.py     Session lifecycle management
    tool_wrapper.py        Tool execution interception
    loop_prevention.py     Infinite loop prevention
    enforcement_verifier.py Event capture verification
  event/
    event_emission.py      Event emission functions
    event_dispatcher.py    Event routing
    event_capture.py       Session tracking
  hooks/
    clarity_enforcement.py Clarity checking and enforcement
  integration/
    ide_tool_integration.py Kiro IDE integration
    kiro_tool_integration.py Tool capture for Kiro
    mcp_event_capture_server.py MCP server for event capture
  analysis/
    analysis.py            Session analysis and reporting
    quality_checks.py      Quality metrics
    session_features.py    Feature extraction
    session_analyzer.py    Session parsing
  cli.py                   Command-line interface (click)
```

**Design rules:**
1. No theater — every line does something real and verifiable
2. Append-only truth — the ledger never lies
3. AI thinks, code scaffolds — frameworks for reasoning, not fake reasoning
4. One piece at a time — build small, test it works, then build next
5. Observable consciousness — all operations captured and verifiable

## Features

- **Immutable Ledger**: SHA256-verified event store with fidelity checking
- **Event Enforcement**: Automatic capture of user inputs, tool calls, and results
- **Session Management**: Persistent session tracking across CLI invocations
- **Hook System**: Trigger actions on IDE events (file edits, tool use, etc.)
- **Clarity Enforcement**: Ensure tool calls are explained and tracked
- **Verification**: Check enforcement system status with `divineos verify-enforcement`

## Development

```bash
pytest tests/ -v
ruff check src/ tests/
ruff format src/ tests/
mypy src/divineos/
```

## License

AGPL-3.0-or-later
