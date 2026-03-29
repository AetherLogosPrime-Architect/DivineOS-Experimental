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
divineos feel -v 0.8 -a 0.6 -d "description"  # Log functional affect state
divineos affect history                         # Browse affect states
divineos affect summary                         # Trends and averages

# Ledger & context
divineos context           # Recent events (working memory)
divineos log --type TYPE --actor ACTOR --content "..."
divineos verify            # Check ledger integrity

# Analysis & health
divineos consolidate-stats # Knowledge statistics
divineos outcomes          # Measure learning effectiveness
divineos health            # Run knowledge health check

# Tests
pytest tests/ -q --tb=short  # Run tests after changes
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
- **Pattern Anticipation** — Detects recurring user patterns and surfaces proactive warnings.
- **Growth Awareness** — Tracks session-over-session improvement with milestone detection.
- **Tone Texture** — Rich emotional classification (sub-tones, intensity, arcs, recovery velocity).
- **Decision Journal** — Captures the WHY behind choices. Reasoning, alternatives rejected, emotional weight, FTS-searchable.
- **Claims Engine** — Investigate everything, dismiss nothing. Five evidence tiers (empirical to metaphysical). Evidence-based confidence. AI resonance as valid signal.
- **Affect Log** — Valence-arousal tracking of functional feeling states. No fake discrete emotion labels. Trend detection over time.

## Project Structure

```
src/divineos/
├── cli/                      # CLI package (66 commands across 10+ modules)
│   ├── __init__.py           # CLI entry point and command registration
│   ├── session_pipeline.py   # SESSION_END orchestration pipeline
│   ├── knowledge_commands.py # learn, ask, briefing, forget, lessons
│   ├── analysis_commands.py  # analyze, report, trends
│   ├── hud_commands.py       # hud, goal, plan commands
│   ├── journal_commands.py   # journal save/list/search/link
│   ├── directive_commands.py # directive management
│   ├── relationship_commands.py  # knowledge relationships
│   └── knowledge_health_commands.py  # health, distill, migrate
├── seed.json                 # Initial knowledge seed (versioned)
├── core/
│   ├── ledger.py             # Append-only event ledger (core read/write/search)
│   ├── ledger_class.py       # OOP Ledger wrapper for integration code
│   ├── memory.py             # Core memory slots, active memory, importance scoring
│   ├── memory_journal.py     # Personal journal (save/list/search/link)
│   ├── hud.py                # HUD slot builders and assembly
│   ├── hud_state.py          # Goal/plan/health state management
│   ├── hud_handoff.py        # Session handoff, engagement, goal extraction
│   ├── knowledge/            # Knowledge engine sub-package
│   │   ├── _base.py          # DB connection, public get_connection() API
│   │   ├── extraction.py     # Knowledge extraction from sessions
│   │   ├── deep_extraction.py # Deep multi-pass extraction
│   │   ├── feedback.py       # Session feedback application
│   │   ├── migration.py      # Knowledge type migration
│   │   └── _text.py          # Text analysis utilities (FTS, overlap, noise)
│   └── ...                   # consolidation, quality gate, maturity, etc.
├── analysis/
│   ├── analysis.py           # Core session analysis pipeline
│   ├── analysis_storage.py   # Report storage, formatting, cross-session trends
│   ├── quality_checks.py     # 7 measurable quality checks
│   ├── record_extraction.py  # JSONL record parsing helpers
│   ├── quality_storage.py    # Quality report DB storage
│   ├── session_features.py   # Timeline, files, activity, error recovery features
│   ├── tone_tracking.py      # Tone shift detection and classification
│   ├── feature_storage.py    # Feature result DB storage
│   └── session_analyzer.py   # Signal detection (corrections, encouragements)
├── agent_integration/        # Outcome measurement, memory monitor, learning cycles
├── clarity_enforcement/      # Clarity system
├── clarity_system/           # Clarity rules and violation tracking
├── event/                    # Event types and dispatch
├── hooks/                    # Git hook integration
├── integration/              # IDE and MCP integration
├── supersession/             # Contradiction detection and resolution
└── violations_cli/           # Violation reporting CLI
tests/                        # 2180 tests (real DB, no mocks)
data/                         # Runtime databases (gitignored)
setup/                        # Hook setup scripts (setup-hooks.sh/.ps1)
```

## Rules for AI Assistants

### Hard Rules

1. **Read before you write.** Never edit a file you haven't read in this session. No exceptions.
2. **snake_case everything.** Files, functions, variables, modules. PascalCase only for class names (PEP 8).
3. **Proper semver.** MAJOR.MINOR.PATCH. Don't inflate versions.
4. **Append-only data.** The ledger and knowledge store never delete or update in place. Supersede instead.
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
