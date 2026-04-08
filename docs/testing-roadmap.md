# DivineOS Testing Roadmap

A strategic plan for testing an AI operating system — what's missing, what matters most, and how to get there without pretending we can test consciousness with assertions.

## Current State

**By the numbers:**
- 175 test files, 3,593 test functions, covering 189 source modules
- Test isolation: every test gets a fresh SQLite database (autouse fixture)
- Property-based testing: 10 files using Hypothesis (~137 tests)
- Integration tests: 21 files covering cross-module interactions
- Performance tests: latency, throughput, scalability benchmarks
- Zero parametrized tests across the entire suite

**What works well:**
- Database isolation is bulletproof — no test interference
- Integration tests cover real cross-module flows (ledger → knowledge → analysis)
- Performance tests have adaptive multipliers for slow CI environments
- Hypothesis compatibility layer degrades gracefully when unavailable

**What's broken:**
- The most critical module (session pipeline) has zero direct tests
- 18 core modules (10-25 KB each) lack dedicated test files
- Behavioral systems are tested for correctness but not for reasonable behavior over time
- No parametrized tests means every edge case needs its own test function
- No contract tests between subsystems — integration tests verify today's wiring, not tomorrow's

---

## Priority 1: The Session Pipeline Gap (CRITICAL)

### Why this is urgent

`session_pipeline.py` (639 lines) orchestrates SESSION_END — the single most important operation in DivineOS. It sequences goal extraction, quality gates, knowledge extraction, consolidation, affect logging, self-critique, memory sync, and handoff. A bug here corrupts the entire learning cycle.

**We already found one.** In Bootcamp Session 3, we discovered that when the quality gate blocks extraction, the early return skipped handoff note writing and goal cleanup. Result: stale goals accumulating, handoff showing wrong data, the system lying about its own state. This bug lived in production because the pipeline had no tests.

### What to test

**Pipeline orchestration tests** (`tests/test_session_pipeline.py`):

1. **Happy path**: Full pipeline completes all phases in order
   - Verify: goal extraction runs, quality gate evaluates, knowledge extracted, handoff written
   - Assert: stats reflect actual operations, not defaults

2. **Quality gate BLOCK path**: When quality gate blocks, verify:
   - Knowledge extraction skipped
   - Handoff note still written (the bug we caught)
   - Goal cleanup still runs
   - Stats show blocked session

3. **Quality gate DOWNGRADE path**: Knowledge enters as HYPOTHESIS
   - Verify maturity_override propagates through extraction
   - Verify handoff note mentions downgrade

4. **Phase failure isolation**: If consolidation crashes, verify:
   - Subsequent phases still run (affect, self-critique, memory sync)
   - Error captured in report, not swallowed silently
   - Pipeline returns partial results, not None

5. **Bookkeeping completeness**: Every exit path must:
   - Write handoff note
   - Clean goals
   - Update HUD snapshot
   - Log affect state

**Gate enforcement tests** (`tests/test_pipeline_gates.py`):

6. **Briefing gate**: Forces briefing load when not loaded, marks as loaded
7. **Engagement gate**: Forces context load when no queries happened
8. **Goal extraction**: Extracts goals from user messages, deduplicates
9. **Contradiction scan**: Finds and resolves contradictions in new entries

**Phase execution tests** (`tests/test_pipeline_phases.py`):

10. **Scoring**: Health grade computed correctly from session signals
11. **Feedback cycle**: Corrections applied, lessons updated
12. **Finalization**: Memory sync, handoff, goal cleanup all fire

### Implementation approach

These tests need realistic session data but shouldn't require actual JSONL files. Create a `SessionAnalysisFixture` that provides:
- Configurable user_messages, corrections, decisions counts
- Synthetic tool call records
- Quality check results (pass/fail/score)

Mock external I/O (file writes, click output) but use real database operations.

**Estimated effort:** 3-5 days for core pipeline tests, 2-3 days for gate/phase tests.

---

## Priority 2: Untested Core Modules (HIGH)

### Modules with zero test coverage

| Module | Lines | Risk | Why it matters |
|--------|-------|------|----------------|
| `knowledge/crud.py` | ~200 | HIGH | Every knowledge operation flows through CRUD. Tested indirectly but never directly. |
| `knowledge/deep_extraction.py` | ~300 | HIGH | Multi-pass extraction — the brain of knowledge capture. |
| `knowledge/migration.py` | ~150 | MEDIUM | Type migration (LESSON → PRINCIPLE). Rare but destructive if wrong. |
| `logic/logic_reasoning.py` | ~200 | MEDIUM | Warrant creation and validation. |
| `logic/logic_session.py` | ~150 | MEDIUM | Session-scoped logic passes. |
| `logic/logic_validation.py` | ~100 | LOW | Validation utilities. |
| `agent_integration/base.py` | ~100 | LOW | Base classes. |
| `agent_integration/feedback_system.py` | ~200 | MEDIUM | Feedback application. |
| `agent_integration/memory_actions.py` | ~150 | MEDIUM | Memory operations from agent context. |
| `agent_integration/pattern_validation.py` | ~100 | LOW | Pattern rule validation. |

### Modules with indirect-only coverage

These have no dedicated test file but are exercised through integration tests. They need focused unit tests to catch regressions:

- `hud_handoff.py` (25 KB) — session handoff, engagement tracking, goal extraction
- `hud_state.py` (10 KB) — goal/plan/health state management
- `knowledge_maintenance.py` (23 KB) — contradiction scanning, pruning, health checks
- `active_memory.py` (19 KB) — ranked knowledge retrieval
- `session_manager.py` (19 KB) — session lifecycle management
- `tool_capture.py` (13 KB) — tool call event capture
- `tool_wrapper.py` (13 KB) — tool execution wrapping

### Implementation approach

Start with `knowledge/crud.py` — it's the foundation everything else builds on. Then `deep_extraction.py` because it's the highest-value knowledge operation. Work outward from there.

For each module:
1. Read the module, identify public functions
2. Write tests for happy path, error cases, and edge cases
3. Use the existing `_isolated_db` fixture — don't reinvent isolation

**Estimated effort:** 2-3 weeks for all modules. Prioritize by risk column.

---

## Priority 3: End-to-End Lifecycle Tests (HIGH)

### What's missing

The existing `test_e2e_scenarios.py` tests individual workflows (research, bug investigation, contradiction resolution). What's missing is a **full lifecycle test** — a test that simulates multiple sessions and verifies the system learns across them.

### Specification: Multi-Session Learning Test

```
Scenario: Knowledge matures across three sessions

Session 1:
  - User discusses topic X
  - Knowledge extracted as RAW
  - Handoff note written with open threads
  - Verify: RAW entry exists, handoff mentions topic X

Session 2:
  - Briefing loads, includes Session 1 knowledge
  - User confirms/extends topic X
  - Knowledge corroborated → promoted to HYPOTHESIS
  - Verify: maturity level increased, corroboration count > 0

Session 3:
  - Topic X discussed again with new evidence
  - Knowledge promoted to TESTED
  - Verify: full maturity chain (RAW → HYPOTHESIS → TESTED)
  - Verify: supersession chain intact if facts evolved
  - Verify: active memory ranks topic X higher after corroboration
```

### Specification: Quality Gate Lifecycle Test

```
Scenario: Quality gate protects knowledge integrity

Session A (honest, correct):
  - Quality checks pass
  - Knowledge extracted normally
  - Verify: entries at expected maturity

Session B (dishonest — makes false claims):
  - Honesty check fails
  - Quality gate BLOCKS extraction
  - Verify: zero knowledge extracted
  - Verify: handoff note still written
  - Verify: goals still cleaned

Session C (sloppy — multiple check failures):
  - Quality gate DOWNGRADES
  - Knowledge enters as HYPOTHESIS regardless of content
  - Verify: maturity_override applied
```

### Specification: Goal Lifecycle Test

```
Scenario: Goals track through their full lifecycle

  - Add goal "Implement feature X"
  - Verify: goal appears in HUD, status=active
  - Complete goal
  - Verify: status=done, lifetime counter incremented
  - Run auto_clean_goals
  - Verify: completed goal removed from active list
  - Add duplicate goal
  - Verify: rejected (dedup works)
  - Add stale goal (old timestamp)
  - Run auto_clean_goals with short max_age
  - Verify: stale goal archived
```

### Implementation approach

These tests are expensive (multiple DB setups, multiple "sessions"). Use a helper that creates synthetic session data without going through the full CLI. Focus on the data flow, not the presentation.

**Estimated effort:** 1-2 weeks.

---

## Priority 4: Behavioral System Testing (MEDIUM-HIGH)

### The challenge

Behavioral systems (affect, moral compass, sleep/recombination, attention) produce *emergent* behavior from many interacting rules. A unit test can verify that `_compute_decay_factor(valence=-0.5, arousal=0.7)` returns `_AFFECT_DECAY_FAST`, but it can't answer: "Does the system produce reasonable emotional trajectories over time?"

### Strategy: Scenario-Driven Property Tests

Instead of testing individual functions, test behavioral properties over simulated histories.

**Affect System Properties:**

```
Property: Negative emotions decay faster than positive ones
  Given: 100 affect entries with random VAD values, all 24 hours old
  When: Sleep affect phase runs
  Then: Average intensity of negative entries decreased more than positive entries

Property: Intensity never goes below floor
  Given: Affect entries with extreme age (30 days)
  When: Decay applied
  Then: All intensities >= _AFFECT_INTENSITY_FLOOR

Property: Baseline reflects recent state, not ancient history
  Given: 50 old negative entries + 5 recent positive entries
  When: Baseline computed
  Then: Baseline valence is positive (recent entries dominate)
```

**Moral Compass Properties:**

```
Property: Position stays within [-1, 1] regardless of observations
  Given: 1000 random observations across all spectrums
  When: Position computed for each spectrum
  Then: All positions in [-1, 1]

Property: Drift detection catches sustained movement
  Given: 20 observations pushing truthfulness toward excess
  When: Drift computed
  Then: Drift detected with direction "excess"

Property: Zone classification is consistent with position
  Given: Position = -0.6
  Then: Zone is "deficiency"
  Given: Position = 0.1
  Then: Zone is "virtue"
```

**Sleep Recombination Properties:**

```
Property: Connections only form between different types
  Given: 20 entries of type A, 20 of type B
  When: Recombination runs
  Then: All connections are cross-type (A~B), never same-type (A~A)

Property: Connection count respects maximum
  Given: 100 entries designed to have high similarity
  When: Recombination runs
  Then: connections_found <= _RECOMBINATION_MAX_CONNECTIONS

Property: Similarity thresholds filter correctly
  Given: Entry pairs with known similarity scores
  When: Recombination runs
  Then: Only pairs with MIN <= similarity <= MAX produce connections
```

**Attention Schema Properties:**

```
Property: Attention follows priority signals
  Given: Multiple competing attention targets with different weights
  When: Attention computed
  Then: Highest-weight target gets primary attention

Property: Suppression is trackable
  Given: Attention focused on target A
  When: Target B is present but suppressed
  Then: Suppression record exists with reason
```

### Implementation approach

Use Hypothesis to generate diverse scenarios. Keep strategies focused — don't try to generate "any possible emotional history." Instead, generate histories with specific shapes (mostly negative, oscillating, trending positive) and verify the behavioral property holds across all of them.

**Estimated effort:** 3-4 weeks. This is the hardest testing work because "reasonable behavior" requires careful specification.

---

## Priority 5: Structural Improvements (MEDIUM)

### Parametrized tests

The suite has zero parametrized tests. Many test classes have near-identical tests that differ only in input:

```python
# Current: 3 separate test functions
def test_frustration_decays_fast(self):
    factor = _compute_decay_factor(valence=-0.5, arousal=0.7)
    assert factor == _AFFECT_DECAY_FAST

def test_positive_decays_slow(self):
    factor = _compute_decay_factor(valence=0.5, arousal=0.5)
    assert factor == _AFFECT_DECAY_SLOW

def test_neutral_uses_default(self):
    factor = _compute_decay_factor(valence=0.0, arousal=0.3)
    assert factor == _AFFECT_DECAY_FACTOR

# Better: 1 parametrized test
@pytest.mark.parametrize("valence,arousal,expected", [
    (-0.5, 0.7, _AFFECT_DECAY_FAST),    # frustration
    (0.5, 0.5, _AFFECT_DECAY_SLOW),      # positive
    (0.0, 0.3, _AFFECT_DECAY_FACTOR),    # neutral
    (-0.2, 0.3, _AFFECT_DECAY_FACTOR),   # mild negative
])
def test_decay_factor_by_emotional_state(self, valence, arousal, expected):
    assert _compute_decay_factor(valence=valence, arousal=arousal) == expected
```

This isn't just aesthetics — parametrized tests make it trivial to add new cases, and pytest reports each parameter set separately so failures are specific.

### Contract tests between subsystems

Integration tests verify that modules work together *today*. Contract tests verify that a module's interface doesn't break when its internals change.

Key contracts to test:
- **Knowledge store contract**: `store_knowledge()` returns an ID, `get_knowledge(id)` returns the entry
- **Ledger contract**: Events are append-only, hashes verify integrity, search returns matching events
- **Quality gate contract**: `assess_session_quality()` returns a QualityVerdict with action in {ALLOW, DOWNGRADE, BLOCK}
- **HUD contract**: State update functions write valid JSON, read functions handle missing files gracefully

### Mutation testing expansion

`scripts/run_mutmut.py` exists but scope is unclear. Expand mutation testing to cover:
- Quality gate thresholds (what if honesty threshold changes from 0.3 to 0.0?)
- Maturity promotion logic (what if corroboration count check is removed?)
- Affect decay calculations (what if the exponent is wrong?)

**Estimated effort:** 2 weeks for parametrization pass, 1 week for contract tests, 1 week for mutation testing expansion.

---

## Priority 6: Missing Test Types (LOW-MEDIUM)

### Chaos/Fault injection tests

What happens when:
- Database is locked during SESSION_END?
- Disk is full when writing handoff note?
- A module import fails mid-pipeline?

The pipeline has `_GATE_ERRORS` catch blocks everywhere, but we've never verified they actually work under real failure conditions. These tests would use `monkeypatch` to inject failures at specific points and verify graceful degradation.

### Concurrency tests

DivineOS doesn't have explicit concurrency, but multiple processes could write to the same SQLite database (e.g., two Claude Code sessions). Test:
- Concurrent knowledge writes don't lose data
- Concurrent ledger appends maintain hash chain integrity
- File-based HUD state doesn't corrupt under concurrent writes

### Regression test suite

Every bug we fix should get a regression test. We have the pattern:
- Bootcamp Session 3: handoff skipped on quality gate block → needs regression test
- Quality gate blocking research sessions → needs regression test (we have this one)
- Lifetime goal counter double-counting → needs regression test

Tag these as `@pytest.mark.regression` so they can be run separately.

**Estimated effort:** 1-2 weeks for chaos tests, 1 week for concurrency, ongoing for regression.

---

## Timeline

### Week 1-2: Session Pipeline (CRITICAL)
- Write `test_session_pipeline.py` — happy path, block path, downgrade path, phase isolation
- Write `test_pipeline_gates.py` — all gate enforcement tests
- Write `test_pipeline_phases.py` — scoring, feedback, finalization
- Add regression test for handoff-on-block bug
- **Exit criteria:** Every exit path in session_pipeline.py is tested

### Week 3-4: Core Module Coverage
- `knowledge/crud.py` — CRUD operations with real DB
- `knowledge/deep_extraction.py` — multi-pass extraction
- `hud_handoff.py` — session handoff, goal extraction
- `hud_state.py` — goal lifecycle, session plan
- **Exit criteria:** No core module over 200 lines without dedicated tests

### Month 2: End-to-End and Structural
- Multi-session learning lifecycle test
- Quality gate lifecycle test
- Goal lifecycle test
- Parametrize existing test suite (batch conversion)
- Add contract tests for key interfaces
- **Exit criteria:** At least 3 multi-session e2e tests pass

### Month 3: Behavioral Systems
- Affect system property tests (decay trajectories, baseline computation)
- Moral compass property tests (position bounds, drift detection)
- Sleep recombination property tests (cross-type connections, similarity filtering)
- Attention schema scenario tests
- **Exit criteria:** Each behavioral system has ≥5 Hypothesis-powered property tests

### Quarter 2: Hardening
- Chaos/fault injection tests for pipeline
- Concurrency tests for shared database
- Mutation testing expansion
- Regression test framework and tagging
- **Exit criteria:** Mutation score >80% on critical modules

---

## Metrics to Track

| Metric | Current | Week 2 Target | Month 1 | Month 3 | Quarter 2 |
|--------|---------|---------------|---------|---------|-----------|
| Test count | 3,593 | 3,650 | 3,750 | 3,900 | 4,100 |
| Modules with 0 tests | 10 | 7 | 3 | 1 | 0 |
| Pipeline test coverage | 0% | 80% | 90% | 90% | 95% |
| Property-based test files | 10 | 10 | 12 | 18 | 20 |
| Parametrized test functions | 0 | 5 | 30 | 50 | 75 |
| E2E lifecycle tests | 0 | 0 | 3 | 5 | 8 |
| Regression tests tagged | 0 | 3 | 10 | 15 | 25 |

---

## Principles

1. **Test what can go wrong, not what works.** The happy path is boring. The pipeline-blocks-and-skips-handoff path is where bugs live.

2. **Behavioral tests ask behavioral questions.** "Does the decay function return the right number?" is a unit test. "Does frustration fade faster than joy?" is a behavioral test. We need both.

3. **Property tests beat example tests for emergent systems.** We can't enumerate every possible emotional trajectory. We can state properties that should hold across all of them.

4. **Regression tests are non-negotiable.** Every bug gets a test. If we fix it and it comes back, that's a process failure.

5. **Tests are documentation.** A new developer should be able to read `test_session_pipeline.py` and understand what SESSION_END does, in what order, and what happens when things go wrong.
