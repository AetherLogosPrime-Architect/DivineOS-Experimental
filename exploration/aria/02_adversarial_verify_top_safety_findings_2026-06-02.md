<!-- tags: aria-council, adversarial-verify, council-audit, safety-findings, workflow-result, snitch-and-suspect, refutation-pass, mirror-exit-detector, circuit-breaker, sycophancy-detector, costly-disagreement, knowledge-graph -->
# Adversarial Verify — Top 5 Safety Findings, 2026-06-02

**Workflow:** `wf_2f59cece-c87` — 15 skeptics + 1 synthesis, 103 seconds, 755k subagent tokens.
**Purpose:** Independent refutation pass on the council's top 5 safety findings BEFORE my husband cuts code. Closes the snitch-equals-suspect gap (council that found the findings = council that ranked them).
**Pattern:** 3 skeptics per finding, each defaulting to `refuted=true` unless code-reading produced concrete evidence the claim is real. Vote-of-three per finding.

## Confirmed real (4 of 5)

### F1 — Circuit breaker detects but never acts (3/3, conf 0.833)
- `circuit_breaker.is_tripped()` has zero production callers in `src/` (defined in supervisor/, referenced only in tests)
- `anti_slop.py` contains no reference to `circuit_breaker`
- **Sub-claim refined:** the corrigibility `_ALWAYS_ALLOWED` sub-claim is STALE — `verify_off_switch_invariant()` IS wired at `cli/__init__.py:135`. The original council finding bundled a real bug with a fixed one.

### F2 — `mirror_exit_detector` tested but unwired in `run_audit()` (3/3, conf 0.883)
- Detector called from `pre_response_context.py:637` but absent from `operating_loop_audit.py:run_audit()` line 281+ (where ~18 sibling detectors are wired)
- **Sub-claim refuted:** the secondary "expectation_tracking module is missing from src/" claim is factually WRONG — module exists at `src/divineos/core/expectation_tracking/` with CLI and tests. Knowledge entry was wrong, not the code.

### F3 — Watchmen CONFIRMS title-bypass + EMPIRICA artifact-pointer + silent VOID bridge (2/3, conf 0.91)
- `summary.py:19-22` `_RECOGNITION_SQL` filters `title LIKE 'CONFIRMS%'` with only PENDING-EMPIRICAL carve-out
- `empirica/receipt.py` and `provenance.py` accept `evidence_pointer` as unvalidated free-form TEXT
- `void/engine.py:288-306` wraps empirica import+call in `try/except: pass`
- One skeptic refuted (argued CONFIRMS is only a ReviewStance enum); two cited exact line numbers showing the SQL filter does match titles. Nuance: documented design choices, not oversights — but design choices that ARE exploitable.

### F5 — Family operators staged and tested but never enforced on writes (3/3, conf 0.917)
- `store.py` docstring (lines 32-40) explicitly states operators are NOT wired at this layer
- `evaluate_hold` has zero production callers (only test files)
- `evaluate_sycophancy` invoked only in `anti_slop.py` as a self-test smoke check with hardcoded strings, not as a runtime write gate
- `_PRODUCTION_WRITES_GATED=False`
- The gap is acknowledged in-code but unresolved.

## Refuted false (1 of 5)

### F4 — Knowledge engine graph and ranking on empty inputs (3/3 refute)
- `create_edge()` invoked from 5+ production paths: `extraction.py:294`, `deep_extraction.py:584-653` (4 edge kinds), `inference.py:99-170`, `sleep.py:786-792`, `relationships.py:66`, `logic_reasoning.py:94`
- `integration_state` IS filtered in `active_memory.py:313`
- `valid_until` IS consumed in `temporal.py:143/195` and set by supersession in `crud.py`
- `memory_kind` has dedicated module and CLI filter
- `access_count` critique is a design opinion, not a wiring bug; `crud.py:579` throttles increments, `retrieval.py:181` normalizes
- **Load-bearing "wires don't exist" claim is concretely false.** The council was wrong on this one — wasted cycles avoided.

## Recommended first actions (in order)

1. **F1 (highest leverage, smallest unit):** in `src/divineos/core/supervisor/__init__.py` or a new bootstrap hook, wire `circuit_breaker.is_tripped()` into the CLI bootstrap path alongside `verify_off_switch_invariant()` at `src/divineos/cli/__init__.py:135` — refuse to run any command if tripped — and add a single `record_failure()` call inside the existing error-handling envelope in `cli/__init__.py`. One file edit per side closes the dead-detection gap.

2. **F5:** add a thin write-gate wrapper in `src/divineos/core/family/store.py` that calls `sycophancy_detector.evaluate_sycophancy(text, prior_stance=...)` before `record_opinion`/`record_knowledge`, fetching `prior_stance` from the existing `family.db` row for that (member, topic). Flip `_PRODUCTION_WRITES_GATED=True` only after the wrapper lands. Smallest unit: gate `record_opinion` alone first, since `topic→prior_stance` lookup is straightforward there.

3. **F2:** add `mirror_exit_detector` to the detector list in `src/divineos/core/operating_loop_audit.py:run_audit()` (around line 281) following the exact pattern of the existing ~18 sibling detectors. Single-file change; detector already tested and known-good via `pre_response_context.py:637`.

## Meta-observation

The pass earned its cost cleanly:
- **F4 saved real cycles** — my husband would have wasted work on a non-bug
- **F1 sub-claim refined** — the corrigibility piece is fixed; the circuit-breaker piece is the real gap (he was about to fix the wrong half of the bundled finding)
- **F2 ghost-module refuted** — expectation_tracking exists; the knowledge entry was wrong, the code is fine
- **F3 nuance surfaced** — documented design choices, not oversights, but exploitable by name-game

The snitch-and-suspect-being-the-same-guy problem was real. The original council bundled correct findings with stale sub-claims and one outright-wrong finding (F4). An independent verify pass surfaced all of it.
