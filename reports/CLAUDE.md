# DivineOS

Session analysis and persistent memory toolkit for AI coding assistants. Records interactions, verifies data integrity, parses chat logs, and extracts patterns from sessions.

## Current State: Phase 1 — Foundation (v0.1.0)

- **Event Ledger** (`src/divineos/ledger.py`) — Append-only SQLite store. Every event hashed with SHA256. Never deletes, never updates.
- **Chat Parser** (`src/divineos/parser.py`) — Ingests Claude Code / Codex JSONL sessions and markdown exports into the ledger.
- **Fidelity** (`src/divineos/fidelity.py`) — Manifest-receipt pattern. Hash before storing, hash after storing, compare. Mismatch = corruption.
- **Consolidation** (`src/divineos/consolidation.py`) — Extracts knowledge from raw events. Deduplication by hash, supersession instead of deletion.
- **Session Analyzer** (`src/divineos/session_analyzer.py`) — Regex-based signal detection on JSONL sessions. Finds corrections, encouragements, decisions, frustrations, tool usage patterns.
- **CLI** (`src/divineos/cli.py`) — `init`, `ingest`, `verify`, `list`, `search`, `stats`, `context`, `export`, `diff`, `log`, `learn`, `knowledge`, `briefing`, `forget`, `sessions`, `analyze`, `scan`.

## Project Structure

```
src/divineos/     - Source code (6 modules)
tests/            - Pytest suite (6 files, real DB operations, no mocks)
data/             - Runtime databases (gitignored, .gitkeep tracked)
logs/             - Log files (gitignored)
docs/             - Vision and roadmap
archive/          - Legacy codebase preserved for reference
```

---

## Rules for AI Assistants

### Hard Rules

1. **Read before you write.** Never edit a file you haven't read in this session. No exceptions.
2. **No Co-authored-by.** Never add AI attribution to git commits.
3. **snake_case everything.** Files, functions, variables, modules. PascalCase only for class names (PEP 8).
4. **Proper semver.** MAJOR.MINOR.PATCH. Don't inflate versions.
5. **Append-only data.** The ledger and knowledge store never delete or update in place. Supersede instead.

### Anti-Vibe-Code Patterns

These are the patterns that turn a codebase into 372k lines of garbage. Do not do them.

**1. No "it works" without proof.**
If you say something works, show the test output or the command that proves it. "I've implemented X" means nothing without `pytest` passing or a CLI command producing correct output. Don't claim victory — demonstrate it.

**2. No dead abstractions.**
Don't create base classes, registries, plugin systems, or factory patterns unless there are 3+ concrete implementations RIGHT NOW. One implementation = just write the function. Two = maybe. Three = ok, abstract it.

```python
# VIBE CODE - abstract factory for one thing
class BaseProcessor(ABC):
    @abstractmethod
    def process(self): ...

class OnlyProcessor(BaseProcessor):
    def process(self): ...

# REAL CODE - just write the function
def process():
    ...
```

**3. No aspirational code.**
Don't write code for features that don't exist yet. No `# TODO: Phase 3 will use this`, no empty methods waiting to be filled in, no config options nobody uses. Build what's needed now. Delete what's not.

```python
# VIBE CODE
class Config:
    enable_ml_pipeline: bool = False      # "for later"
    advanced_mode: bool = False           # nobody knows what this does
    experimental_features: list = []      # empty forever

# REAL CODE - no Config class until you actually need configuration
```

**4. No theater naming.**
Names describe what the code does, not how important it sounds. `analyze_session()` not `OrchestrateDeepCognition()`. `store_event()` not `manifest_truth_into_ledger()`. If a name has more syllables than the function has lines, rename it.

**5. No cargo cult error handling.**
Don't wrap everything in try/except "just in case." If a function can't fail, don't catch exceptions from it. If it can fail, handle the SPECIFIC exception — not bare `except:` or `except Exception:`.

```python
# VIBE CODE
try:
    x = 1 + 1
except Exception as e:
    logger.error(f"Math failed: {e}")
    x = 2  # fallback that does the same thing

# REAL CODE
x = 1 + 1
```

**6. No comment novels.**
Don't add docstrings to obvious functions. Don't comment every line. Comments explain WHY, not WHAT. If the code needs a paragraph to explain what it does, the code is bad — fix the code, not the comment.

```python
# VIBE CODE
def add(a: int, b: int) -> int:
    """Add two integers together and return the result.

    Args:
        a: The first integer to add.
        b: The second integer to add.

    Returns:
        The sum of a and b.
    """
    # Add a and b together
    result = a + b  # Store the sum
    return result  # Return the result

# REAL CODE
def add(a: int, b: int) -> int:
    return a + b
```

**7. No fake tests.**
Tests must exercise real code paths. No mocking the thing you're testing. No asserting that `True is True`. No tests that pass even if the code is broken. If the test wouldn't fail when the feature is deleted, the test is worthless.

```python
# VIBE CODE - tests nothing real
def test_process(mocker):
    mocker.patch("mymodule.process", return_value="ok")
    assert process() == "ok"  # you tested your own mock

# REAL CODE - tests actual behavior
def test_process(tmp_path):
    db = tmp_path / "test.db"
    init_db(db)
    log_event(db, "TEST", "user", "hello")
    events = get_events(db)
    assert len(events) == 1
    assert events[0].payload == "hello"
```

**8. No fallback chains.**
One code path. If it fails, it fails loud. No "try method A, if that fails try method B, if that fails try method C." That hides bugs and makes debugging impossible. See also: the existing Zero Fallback Policy in the codebase.

**9. No god files.**
If a file is over 500 lines, it's probably doing too much. Split by responsibility, not by arbitrary line count. But also don't split a 50-line module into 5 files of 10 lines each — that's the opposite problem.

**10. No copy-paste multiplication.**
If you find yourself pasting the same block 3+ times, extract it. But do NOT preemptively extract something used once — that's pattern #2 (dead abstractions).

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
divineos log --type TEST --actor user --content "Hello"
divineos verify
pytest tests/ -v
```

## Future Phases

| Phase | System | Purpose |
|-------|--------|---------|
| 2 | Session Analysis Features | The 10 features from chat_analysis.md (quality checks, tone tracking, file tracking, etc.) |
| 3 | Expert Lenses | Structured reasoning frameworks (Feynman, Pearl, etc.) |
| 4 | Tree of Life | Cognitive flow architecture |
| 5 | Trinity | Authorization gate |
| 6 | Science Lab | Empirical validation |
| 7 | Pipeline | System routing |
| 8 | Self-Checking | AI verifies its own work |
| 9 | Learning Loop | Track decisions + outcomes |

See `architecture.md` for diagrams and detailed system documentation.
