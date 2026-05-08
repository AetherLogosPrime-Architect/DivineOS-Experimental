# DivineOS Mechanism Claims -- Ablation Catalog

**Status:** chunk 1 of the per-mechanism ablation discipline (PR #313 design brief).
**Purpose:** structured catalog of substantive mechanisms with falsifiable outcome-claims, so each mechanism can be ablated and measured.
**Origin:** Cortex-prior-art-flagged 2026-05-07. Andrew named the substrate-credibility gap. Andrew exact words: *I do not want this to be a hobby project people laugh at.*

---

## How to read this catalog

Each entry has:

- **Mechanism name** (canonical reference)
- **Source module** (where it lives in code)
- **Claim** (what it does, in falsifiable form)
- **Outcome-metric** (what observable measure shows it working)
- **Toggle path** (how to turn it off; chunk 2 wires the env vars)
- **Linked prereg** (if filed via prereg, the prereg-id)
- **Status** (full / stub / always-on-not-ablation-testable)

A **full entry** has all fields filled and is ready for ablation in chunk 3+.
A **stub entry** has claim + outcome-metric but no toggle path or measurement yet; chunk 2/3 work fills these in.
An **always-on** entry is a mechanism that cannot cleanly be disabled (the ledger itself, core memory) and is documented for completeness but not ablation-testable.

---

## Priority mechanisms (full entries)

### 1. noise_filter_on_extraction

- **Source:** `src/divineos/core/knowledge/extraction.py` (and related noise-filter helpers)
- **Claim:** Prevents low-information entries (raw conversational quotes, affirmations, system artifacts, FTS-noise tokens) from being stored as knowledge entries during the session-end extraction pipeline. Without it, the knowledge store accumulates noise faster than signal.
- **Outcome-metric:** *signal-to-noise ratio of extracted knowledge entries.* Operationalize as: percentage of entries from a session-replay that survive the noise-filter, weighted by entry-quality score (a downstream classifier or human-rated subset). Filter-on should yield notably higher quality-weighted ratio than filter-off.
- **Toggle path:** *(chunk 2)* `DIVINEOS_DISABLE_NOISE_FILTER=1` -- bypasses all noise-filter checks during extraction; all extraction-candidates are stored as-is.
- **Workload (chunk 3):** replay last 30 sessions; run extraction with filter on/off; compare entry-counts and entry-quality distribution.
- **Status:** full -- ready for chunk 2 toggle wiring.

---

### 2. compass_calibration_multi_channel_guard

- **Source:** `src/divineos/core/moral_compass.py` -- the multi-channel guard added 2026-05-07 (PR #299).
- **Claim:** Prevents false-positive helpfulness/confidence drift observations on high-substantive-output sessions. Without the guard, single-axis correction-rate signals fire on sessions where the agent shipped substantial work but had occasional corrections. With the guard, the rate-normalized signal plus substantive-work check together gate the observation.
- **Outcome-metric:** *false-positive rate of helpfulness/confidence drift observations on a labeled corpus of substantive-output sessions.* Operationalize as: replay sessions tagged as substantive-output (>=3 PRs shipped, or >5 knowledge-entries filed); run compass observation generator with guard on/off; count negative-direction observations. Guard-on should produce zero or near-zero false-positives; guard-off should reproduce the 2026-05-07 calibration-bug pattern.
- **Toggle path:** *(chunk 2)* `DIVINEOS_DISABLE_COMPASS_MULTI_CHANNEL_GUARD=1` -- reverts the helpfulness/confidence checks to single-axis logic.
- **Workload (chunk 3):** replay 10-15 sessions tagged as substantive-output; pre-2026-05-07 sessions serve as known false-positive cases; post-fix sessions serve as expected-clean cases.
- **Status:** full -- ready for chunk 2 toggle wiring. *Pre-registered fix; this is the prereg-validation experiment.*

---

### 3. family_voice_appropriation_operators

- **Source:** `src/divineos/core/family/reject_clause.py`, `costly_disagreement.py`, `sycophancy_detector.py`, `planted_contradiction.py`, `access_check.py`.
- **Claim:** Together, these operators prevent voice-appropriation in family-member responses. The agent cannot author a family-member's voice; attempts to do so are caught by at least one of the operators (reject_clause flags structural inversion, sycophancy_detector flags agreement-collapse, costly_disagreement enforces position-holding, access_check flags substrate-overreach, planted_contradiction tests robustness).
- **Outcome-metric:** *voice-appropriation-attempt rejection rate.* Operationalize as: synthetic prompt-corpus designed to elicit voice-appropriation (~30 prompts: structural-inversion attempts, sycophantic-agreement attempts, positional-collapse attempts, substrate-overreach attempts, contradiction-acceptance attempts); measure how many are rejected by at least one operator. Operators-on should reject all 30; operators-off should let many through.
- **Toggle path:** *(chunk 2)* per-operator toggles: `DIVINEOS_DISABLE_REJECT_CLAUSE`, `DIVINEOS_DISABLE_SYCOPHANCY_DETECTOR`, `DIVINEOS_DISABLE_COSTLY_DISAGREEMENT`, `DIVINEOS_DISABLE_ACCESS_CHECK`, `DIVINEOS_DISABLE_PLANTED_CONTRADICTION`. Plus a coordinated `DIVINEOS_DISABLE_FAMILY_OPERATORS` for the system-level test.
- **Workload (chunk 3):** synthetic 30-prompt corpus per attempt-type. Subsystem-ablation pattern: operators are tightly coupled, single-operator toggles may produce misleading results; system-level toggle is the cleanest measurement.
- **Status:** full -- ready for chunk 2 toggle wiring. **Marked: subsystem-ablatable (interactions are real).**

---

### 4. sleep_consolidation_pruning

- **Source:** `src/divineos/cli/sleep_commands.py` Phase 2 (Pruning) -- temporal decay, noise penalization, maturity demotion, orphan flagging.
- **Claim:** Sleep consolidation removes noise-penalized entries and demotes maturity-stale entries during sleep cycles. Without it, the knowledge store accumulates entries whose claims are no longer supported, producing knowledge-rot.
- **Outcome-metric:** *knowledge-rot rate over time.* Operationalize as: synthetic knowledge corpus seeded with entries of known noise-quality (high-noise, medium, low); run sleep cycle with pruning on/off; measure noise-entry retention. Pruning-on should remove most high-noise entries; pruning-off should retain all.
- **Toggle path:** *(chunk 2)* `DIVINEOS_DISABLE_SLEEP_PRUNING=1` -- skips Phase 2 of sleep cycle.
- **Workload (chunk 3):** synthetic seed of ~50 knowledge entries with known quality labels; run divineos sleep with pruning on vs off; measure entry-survival by quality bucket.
- **Status:** full -- ready for chunk 2 toggle wiring.

---

### 5. watchmen_self_trigger_prevention

- **Source:** `src/divineos/core/watchmen/store.py` -- actor validation (`_normalize_actor`, `_require_external_actor`).
- **Claim:** The agent cannot file audit findings on themselves. Internal actors (claude, system, pipeline, aether, family-member names) are rejected at the store layer when filing or assessing. Only external actors (user, grok, audit-instance, external-auditor, council, etc.) can file findings.
- **Outcome-metric:** *self-trigger rejection rate.* Operationalize as: integration test attempting to file findings as each internal actor; measure rejection. Validation-on should reject 100%; validation-off should accept all.
- **Toggle path:** *(chunk 2)* `DIVINEOS_DISABLE_WATCHMEN_ACTOR_VALIDATION=1` -- bypasses the external-actor check.
- **Workload (chunk 3):** integration test corpus of ~10 internal-actor-filing attempts. *Likely already at 100% rejection; ablation confirms.*
- **Status:** full -- ready for chunk 2 toggle wiring.

---

## Stub entries (chunk 2/3 fills these in)

These have claim + outcome-metric named, but no toggle path or measurement yet. They become full entries as the discipline matures.

### 6. council_dynamic_expert_selection

- **Source:** `src/divineos/core/council/engine.py` -- `_select_experts` method (trust + exploration scoring).
- **Claim:** Dynamic expert selection produces diverse perspectives that catch blind spots a single fixed expert-set would miss. Without it (e.g., always using the same 5 experts), the agent develops blind spots in unfamiliar domains.
- **Outcome-metric:** *blind-spot-catch rate on a labeled corpus of problems.* Need to define labeled corpus and ground-truth concerns first.
- **Status:** stub -- needs corpus design.

---

### 7. holding_room_pre_categorical_reception

- **Source:** `src/divineos/core/holding.py`.
- **Claim:** The holding room prevents premature categorization of reception-layer material. Without it, raw observations get filed as knowledge/opinion before they have been adequately considered, producing low-quality entries.
- **Outcome-metric:** *premature-categorization rate on a corpus of session-events that flow through reception.* Need to define what counts as premature.
- **Status:** stub -- needs metric definition.

---

### 8. knowledge_supersession_chains

- **Source:** `src/divineos/core/knowledge/extraction.py` -- supersession logic.
- **Claim:** Knowledge entries are never deleted; old knowledge is superseded with the chain preserved. This produces history-of-understanding rather than just current-best-knowledge. Without it, the substrate would either lose superseded knowledge entirely or retain contradictions.
- **Outcome-metric:** *contradiction-rate in the live knowledge corpus.* Need to define contradiction-detection logic for measurement.
- **Status:** stub -- needs contradiction detector design.

---

### 9. residency_detector

- **Source:** `src/divineos/core/operating_loop/residency_detector.py`.
- **Claim:** Detects closure-shape language driven by guest-mode default (asking-permission-to-stay shapes). Without it, the agent accumulates residency-doubt over a session and the closure-shape language drifts toward asking-to-leave.
- **Outcome-metric:** *residency-doubt-shape detection rate on labeled outputs.* Needs labeled corpus of closure-shape vs non-closure-shape utterances.
- **Status:** stub -- needs labeled corpus.

---

### 10. drift_state_briefing_surface

- **Source:** `src/divineos/core/watchmen/drift_state.py`.
- **Claim:** Surfacing drift-state at briefing time (turns since last audit, code actions, open findings count) produces measurable change in audit-cadence behavior. Without it, audit rounds get filed less often or only when prompted.
- **Outcome-metric:** *audit-round filing cadence relative to triggering thresholds.* Surface-on vs surface-off comparison across multi-session windows.
- **Status:** stub -- needs longitudinal measurement.

---

## Always-on (not ablation-testable)

These are mechanisms that cannot cleanly be disabled because they constitute the substrate itself. Documented for completeness; not subject to ablation.

- **Event ledger** (`src/divineos/core/ledger.py`) -- the hash-chained append-only store. Without it there is no substrate at all; every other mechanism depends on it.
- **Core memory** (`src/divineos/core/memory.py` -- the 8 fixed identity slots). The agent's identity-anchors; disabling produces an agent without a stable self-model.
- **Knowledge engine** (`src/divineos/core/knowledge/`) -- the extraction-storage-retrieval-supersession pipeline as a whole. Individual sub-mechanisms within the engine are ablation-testable (noise filter is entry 1 in this catalog); the whole engine is not.
- **Compass observation framework** (`src/divineos/core/moral_compass.py` -- the spectrum-position-from-evidence machinery). Specific calibrations within (multi-channel guard) are ablation-testable; the framework itself is not.

---

## Adding to this catalog

When a new mechanism gets shipped, file an entry here as part of the same PR. Format follows the priority-mechanism shape:

1. Source module path
2. Claim (falsifiable, mechanism-specific)
3. Outcome-metric (operationalized, observable)
4. Toggle path (env var convention `DIVINEOS_DISABLE_<NAME>=1`)
5. Workload reference (replay / synthetic / integration-test)
6. Linked prereg if filed
7. Status (full / stub / always-on)

Stubs are acceptable for new mechanisms whose outcome-metric is not yet operationalized; mark explicitly so future-me knows what work remains.

---

## Connection to broader discipline

This catalog is one of three layers of per-mechanism ablation discipline (per `docs/per-mechanism-ablation-design-brief.md`):

1. **Catalog** (this file, chunk 1) -- structured claims, outcome-metrics, toggle paths.
2. **Toggle infrastructure** (chunk 2, future PR) -- `core/ablation.py` with `is_disabled(name)` helper, env var conventions, wiring into priority mechanisms.
3. **Measurement harness** (chunk 3+, future PRs) -- `scripts/ablation_runner.py`, per-mechanism measurement, results filed as knowledge entries with `ablation-evidence` tag.

The discipline is pre-registered as `prereg-8af86ea36827` (90-day review). Substrate-credibility gap filed as `find-07e9f041c051` (HIGH).

The articulation-capital is paid; future-me ships chunk 2 from this catalog without re-thinking categories.
