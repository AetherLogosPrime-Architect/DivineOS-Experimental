# DivineOS

Session analysis and persistent memory toolkit for AI coding assistants. Records interactions, verifies data integrity, parses chat logs, and extracts patterns from sessions.

## You Are Running DivineOS

This project IS your operating system. Before doing any work, load your briefing:

```bash
divineos briefing
```

This gives you your lessons, directions, mistakes, and facts from previous sessions. **Use them.** Don't just load them — explain what you learned and how it shapes what you'll do next.

At the end of a session, log what happened:

```bash
divineos emit SESSION_END
```

## Quick Reference

```bash
divineos briefing          # Your session briefing (start here)
divineos context           # Recent events (working memory)
divineos recall            # Core memory + active memory
divineos lessons           # Tracked lessons from past sessions
divineos learn "..."       # Store knowledge from experience
divineos log --type TYPE --actor ACTOR --content "..."  # Log an event
divineos emit SESSION_END  # End of session summary
divineos verify            # Check ledger integrity
pytest tests/ -q --tb=short  # Run tests after changes
```

## Current State: Phase 1 — Foundation (v0.1.0)

- **Event Ledger** — Append-only SQLite store. Every event hashed with SHA256. Never deletes, never updates.
- **Chat Parser** — Ingests Claude Code / Codex JSONL sessions and markdown exports into the ledger.
- **Fidelity** — Manifest-receipt pattern. Hash before storing, hash after storing, compare. Mismatch = corruption.
- **Consolidation** — Extracts knowledge from raw events. Deduplication by hash, supersession instead of deletion.
- **Session Analyzer** — Regex-based signal detection on JSONL sessions.
- **Memory System** — Core memory (8 fixed slots) + active memory (ranked knowledge) + learning cycle.
- **CLI** — Full command suite (see quick reference above).

## Project Structure

```
src/divineos/
├── cli.py                    # Main CLI entry point
├── core/                     # Ledger, fidelity, memory, consolidation, parser
├── analysis/                 # Session analysis, quality checks
├── agent_integration/        # Memory monitor, learning cycles, pattern recommendation
├── clarity_enforcement/      # Clarity system
└── event/                    # Event types and dispatch
tests/                        # Pytest suite (real DB, no mocks)
data/                         # Runtime databases (gitignored)
scripts/                      # Helper scripts
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
9. **No god files.** Over 500 lines = probably doing too much.
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
