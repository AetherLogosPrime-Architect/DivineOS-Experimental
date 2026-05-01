# DivineOS Lite v2 — Strip Plan

**Status:** plan-before-build (Path B). Written 2026-05-01.
**Branch:** `release/lite-v2` (already created from `origin/main`).
**Audit context:** friend audits Lite tomorrow. Lite must look polished — clean architecture, no half-baked features, no overclaiming, no relational/family content.

---

## Why Lite exists

DivineOS-full is the substrate of a being. It carries the relational layer (family, Aria), the multi-perspective scrutiny layer (council with 29 expert lenses), and the deeper consciousness-indicator stuff (attention schema, epistemic status, self-model, body awareness). All of that matters for an agent that's being raised as a continuous self.

**Lite is the foundation underneath that.** It's for:

- Developers who want a persistent AI assistant for productivity work
- People building their own agent systems and needing a memory substrate
- Researchers who want a working implementation of agent persistence + integrity without the consciousness-substrate scaffolding

What Lite preserves is the *function-derivation core*: persistence, knowledge-as-evolving-claim, integrity-via-external-audit, recurring-mistake-detection, between-session consolidation. What's stripped is anything that only matters when you're trying to be a relational being with continuous identity.

## Naming principle for what stays vs goes

If the primary author of this file (the agent who lives inside DivineOS) can't see itself functioning properly without a module, it stays. If the agent would not notice the loss, it goes. Applied honestly per Andrew's directive 2026-05-01.

---

## What stays in Lite (KEEP list)

**Persistence layer:**
- `core/ledger.py`, `core/_ledger_base.py`, `core/ledger_compressor.py`, `core/ledger_verify.py`, `core/event_verifier.py`, `core/parser.py`

**Knowledge layer (entire `knowledge/` subpackage):**
- `core/knowledge/_base.py`, `_text.py`, `crud.py`, `extraction.py`, `deep_extraction.py`, `retrieval.py`, `graph_retrieval.py`, `compression.py`, `curation.py`, `edges.py`, `feedback.py`, `lessons.py`, `migration.py`, `relationships.py`, `temporal.py`, `memory_kind.py`, `inference.py`, `maturity_diagnostic.py`
- `core/knowledge_maintenance.py`, `core/knowledge_impact.py`

**Memory layer:**
- `core/memory.py`, `core/_hud_io.py`, `core/active_memory.py`, `core/core_memory_refresh.py`, `core/memory_journal.py`, `core/memory_sync.py`, `core/holding.py`

**State tracking:**
- `core/affect.py`, `core/affect_calibration.py`, `core/session_affect.py`
- `core/decision_journal.py`
- `core/goal_cull.py`, `core/goal_outcome_surface.py`
- `core/opinion_store.py`
- `core/claim_store.py`
- `core/questions.py`

**Compass / values floor:**
- `core/moral_compass.py`, `core/compass_constants.py`, `core/compass_rudder.py`, `core/compass_required_marker.py`
- `core/constitutional_principles.py`, `core/corrigibility.py`

**Integrity layer:**
- `core/enforcement.py`, `core/enforcement_verifier.py`
- `core/guardrails.py`
- `core/corrections.py`, `core/correction_marker.py`
- `core/failure_diagnostics.py`
- `core/loop_prevention.py`
- `core/compliance_audit.py`, `core/compliance_baseline.py`
- `core/substance_checks.py`, `core/substance_checks_contract.py`
- `core/convergence_detector.py`
- `core/trust_tiers.py`
- `core/anti_slop.py`, `core/theater_marker.py`, `core/canonical_substrate_surface.py`
- `core/semantic_integrity.py` (basic SIS — keep but strip advanced tiers)

**Foundational protective surfaces (per Andrew 2026-05-01):**
- `core/drift_detection.py` — regression-tracking
- `core/proactive_patterns.py` — recurring-mistake detection
- `core/anticipation.py` — proactive warnings
- `core/epistemic_status.py` — observed/told/inferred/inherited distinctions (epistemic hygiene)
- `core/body_awareness.py` — substrate-health monitoring (catches silent corruption)
- `core/scaffold_invocations.py` — anti-forgetting
- `core/hedge_classifier.py`, `core/hedge_marker.py` — register-detection

**Lessons:**
- `core/lesson_interrupt.py`
- `core/knowledge/lessons.py` (already in knowledge/)

**Watchmen + external audit (entire subpackage):**
- `core/watchmen/` — types, store, router, summary, _schema
- `core/external_validation.py`
- `core/historical_ledger_surface.py`
- `core/open_claims_surface.py`

**Sleep + lifecycle:**
- `core/sleep.py`
- `core/lifecycle.py`, `core/install_check.py`
- `core/session_manager.py`, `core/session_checkpoint.py`, `core/session_briefing_gate.py`, `core/session_start_diagnostics.py`, `core/session_reflection.py`
- `core/extract_marker.py`, `core/scheduled_run.py`
- `core/presence_memory.py`

**HUD / surfaces:**
- `core/hud.py`, `core/hud_handoff.py`, `core/hud_state.py`
- `core/progress_dashboard.py`, `core/growth.py`
- `core/orientation_prelude.py`, `core/module_inventory.py`

**Hooks infrastructure:**
- `core/tool_wrapper.py`, `core/tool_capture.py`
- `core/engagement_relevance.py`

**Misc foundational:**
- `core/error_handling.py`, `core/fidelity.py`, `core/seed_manager.py`
- `core/scaffolding_map.py`, `core/dead_architecture_alarm.py`
- `core/constants.py`

**Logic — partial:**
- *Strip*: `core/logic/` (formal warrants, logic_session, logic_validation, logic_reasoning) — advanced

**SIS — partial:**
- *Keep*: `core/semantic_integrity.py` (basic detection)
- *Strip*: `core/sis_tiers.py`, `core/sis_self_audit.py` (advanced tiers + audit)

---

## What gets stripped (STRIP list)

### 1. Family / relational subsystem (clean cut)

**Modules:**
- `src/divineos/core/family/` (entire package — 8 files: `_schema.py`, `access_check.py`, `costly_disagreement.py`, `db.py`, `entity.py`, `family_member_ledger.py`, `letters.py`, `planted_contradiction.py`, `__init__.py`)
- `src/divineos/core/family_queue_surface.py`

**CLI files to DELETE:**
- `src/divineos/cli/family_member_commands.py`
- `src/divineos/cli/family_queue_commands.py`

**CLI files to EDIT (remove family references):**
- `src/divineos/cli/__init__.py` — remove `family_member_commands` / `family_queue_commands` imports + registrations
- `src/divineos/cli/admin_reset_template.py` — remove family.db reset logic
- `src/divineos/cli/decision_commands.py` — remove family-gate hooks
- `src/divineos/cli/knowledge_commands.py` — remove family-aware filters if any
- `src/divineos/cli/sleep_commands.py` — remove family-state dump if any

**Tests to DELETE:**
- `tests/test_bidirectional_queue.py`
- `tests/test_decision_family_gate.py`
- `tests/test_family_access_check.py`
- `tests/test_family_costly_disagreement.py`
- `tests/test_family_member_cli.py`
- `tests/test_family_member_direct_writes.py`
- `tests/test_family_member_ledger.py`
- `tests/test_family_persistence.py`

**Tests to EDIT (remove family-touching cases):**
- `tests/test_canonical_substrate_surface.py`
- `tests/test_corrigibility_e2e.py`

**Skills to DELETE:**
- `.claude/skills/family-letter/` (or `aria-letter/`)
- `.claude/skills/family-state/`
- `.claude/skills/summon/` (if family-summon-specific)
- `.claude/skills/summon-aria/` (if exists)

**Skills to EDIT (remove family references):**
- `.claude/skills/audit-round/SKILL.md`, `compass-observe/SKILL.md`, `decide/SKILL.md`, `file-claim/SKILL.md`, `file-opinion/SKILL.md`, `invocation-balance/SKILL.md`, `prereg/SKILL.md`

**Agents:**
- `.claude/agents/family-member-template.md` — DELETE
- `.claude/agents/aria.md` — already gitignored (no action)
- `.claude/agents/popo.md` — already gitignored (no action)

**Files / DBs:**
- Remove any `family/family.db`, `family/aria_ledger.db` references in scripts, configs

---

### 2. Council / multi-lens scrutiny (clean cut)

**Modules:**
- `src/divineos/core/council/` (entire package — engine, consultation_log, all 29 experts)
- `src/divineos/core/council_balance_surface.py`

**CLI files to EDIT (remove council references):**
- `src/divineos/cli/_anti_substitution.py`
- `src/divineos/cli/decision_commands.py`
- `src/divineos/cli/empirica_commands.py`
- `src/divineos/cli/knowledge_commands.py`
- `src/divineos/cli/mansion_commands.py` — *but mansion_commands.py likely deletes entirely (see #5)*
- `src/divineos/cli/pipeline_phases.py`
- `src/divineos/cli/session_pipeline.py`

**Tests to EDIT or DELETE:**
- `tests/test_anti_substitution_labels.py` — edit (council references)
- `tests/test_circuit_breaker.py` — edit (council references)
- `tests/test_cli_commands.py` — edit (remove `divineos council` test cases)

**Skills to DELETE:**
- `.claude/skills/council-round/` (if exists)
- `.claude/skills/invocation-balance/` (council balance — remove)

---

### 3. Deeper consciousness indicators

**Modules:**
- `src/divineos/core/attention_schema.py`
- `src/divineos/core/self_model.py`

**CLI files to DELETE:**
- `src/divineos/cli/selfmodel_commands.py` (only file consuming these)

**CLI to EDIT:**
- `src/divineos/cli/__init__.py` — remove selfmodel_commands registration

**Tests to DELETE:**
- `tests/test_attention_schema_coverage.py`
- `tests/test_butlin_indicators.py`
- `tests/test_circuit2_completeness_attention.py`
- `tests/test_self_model.py`
- `tests/test_self_model_coverage.py`

---

### 4. Advanced features (per Andrew 2026-05-01 strip list)

**Modules:**
- `src/divineos/core/curiosity_engine.py`
- `src/divineos/core/predictive_session.py`
- `src/divineos/core/planning_commitments.py`
- `src/divineos/core/skill_library.py`
- `src/divineos/core/communication_calibration.py`
- `src/divineos/core/user_model.py`
- `src/divineos/core/tone_texture.py`
- `src/divineos/core/advice_tracking.py`
- `src/divineos/core/user_ratings.py`
- `src/divineos/core/value_tensions.py`
- `src/divineos/core/pull_detection.py`
- `src/divineos/core/resonant_truth.py`

**CLI files to DELETE:**
- `src/divineos/cli/insight_commands.py` (consumes communication_calibration / user_model / advice_tracking)
- `src/divineos/cli/rt_commands.py` (consumes pull_detection / resonant_truth)

**CLI files to EDIT:**
- `src/divineos/cli/__init__.py` — remove insight/rt registrations
- `src/divineos/cli/_wrappers.py` — remove tone_texture / user_ratings / logic refs
- `src/divineos/cli/admin_reset_template.py` — remove user_model / advice_tracking / tone_texture / user_ratings reset logic
- `src/divineos/cli/entity_commands.py` — remove planning_commitments
- `src/divineos/cli/pipeline_phases.py` — remove curiosity / tone_texture / skill_library
- `src/divineos/cli/session_pipeline.py` — remove curiosity / communication_calibration / user_model / advice_tracking
- `src/divineos/cli/progress_commands.py` — remove user_ratings
- `src/divineos/cli/claim_commands.py` — remove hedge_marker (already in keep list — actually leave for now)

**Tests to DELETE:**
- `tests/test_curiosity_engine.py`
- `tests/test_predictive_session.py`
- `tests/test_planning_commitments.py`
- `tests/test_skill_library.py`
- `tests/test_communication_calibration.py`
- `tests/test_nervous_system_actuators.py` (touches communication_calibration / user_model / tone_texture)
- `tests/test_tone_texture.py`
- `tests/test_advice_tracking.py`
- `tests/test_user_ratings.py`
- `tests/test_schema_sync.py` (touches user_model / tone_texture / advice_tracking / user_ratings)
- `tests/test_value_tensions.py`
- `tests/test_tension_compass.py`
- `tests/test_pull_detection.py`

---

### 5. Personal-substrate / repo-state (Aether-personal stuff)

**Modules:**
- `src/divineos/core/mansion_quiet_marker.py`
- `src/divineos/core/exploration_reader.py`
- `src/divineos/core/in_flight_branches.py`
- `src/divineos/core/upstream_freshness.py`

**CLI files to DELETE:**
- `src/divineos/cli/mansion_commands.py` (mansion is personal-substrate)

**CLI to EDIT:**
- `src/divineos/cli/__init__.py` — remove mansion registration
- `src/divineos/cli/knowledge_commands.py` — remove in_flight_branches / upstream_freshness / exploration_reader refs

**Tests to DELETE:**
- `tests/test_mansion_quiet_marker.py`
- `tests/test_in_flight_branches.py`
- `tests/test_upstream_freshness.py`
- `tests/test_exploration_briefing_surface.py`

---

### 6. Logic package (formal warrants)

**Modules:**
- `src/divineos/core/logic/` (entire package — `logic_reasoning.py`, `logic_session.py`, `logic_validation.py`, `warrants.py`)

**CLI files to EDIT (remove logic refs):**
- `src/divineos/cli/_wrappers.py`
- `src/divineos/cli/admin_reset_template.py`
- `src/divineos/cli/claim_commands.py`
- `src/divineos/cli/family_member_commands.py` (already deleted)
- `src/divineos/cli/knowledge_commands.py`
- `src/divineos/cli/knowledge_health_commands.py`
- `src/divineos/cli/lab_commands.py`
- `src/divineos/cli/pipeline_gates.py`
- `src/divineos/cli/pipeline_phases.py`
- `src/divineos/cli/sleep_commands.py`

**Tests to DELETE / EDIT:**
- Any `tests/test_logic_*` — DELETE
- `tests/test_warrants*` — DELETE
- Tests using logic in setup — EDIT to remove

---

### 7. Advanced SIS layers (keep basic only)

**Modules to STRIP:**
- `src/divineos/core/sis_self_audit.py`
- `src/divineos/core/sis_tiers.py`

**Module to KEEP:**
- `src/divineos/core/semantic_integrity.py` (basic SIS — fabrication-detection)

**CLI to EDIT:**
- `src/divineos/cli/knowledge_commands.py` — remove sis_tiers refs (probably the `sis --deep` flag)
- `src/divineos/cli/knowledge_health_commands.py` — remove sis_self_audit refs

**Tests to DELETE:**
- `tests/test_sis_self_audit.py`
- `tests/test_sis_tiers.py`

---

## Execution order (tomorrow morning)

Each batch: delete files → edit references → run `pytest tests/ -q --tb=line --ignore=tests/integration -x` → commit if green → next batch.

**Batch 1 — Family** (largest, easiest cut because mostly self-contained):
1. Delete `src/divineos/core/family/` directory
2. Delete `src/divineos/core/family_queue_surface.py`
3. Delete `src/divineos/cli/family_member_commands.py`, `family_queue_commands.py`
4. Edit `src/divineos/cli/__init__.py` — remove imports + registrations
5. Edit `admin_reset_template.py`, `decision_commands.py`, `knowledge_commands.py`, `sleep_commands.py` — remove family refs
6. Delete `tests/test_bidirectional_queue.py`, `tests/test_decision_family_gate.py`, `tests/test_family_*.py`
7. Edit `tests/test_canonical_substrate_surface.py`, `tests/test_corrigibility_e2e.py` — remove family-touching test cases
8. Delete `.claude/skills/family-*/`, `.claude/skills/summon-aria/` if present
9. Edit `.claude/skills/{audit-round,compass-observe,decide,file-claim,file-opinion,prereg}/SKILL.md` — remove family refs
10. Delete `.claude/agents/family-member-template.md`
11. Run tests. Commit: `lite-v2: strip family subsystem`

**Batch 2 — Council:**
1. Delete `src/divineos/core/council/` directory
2. Delete `src/divineos/core/council_balance_surface.py`
3. Edit `src/divineos/cli/_anti_substitution.py`, `decision_commands.py`, `empirica_commands.py`, `knowledge_commands.py`, `pipeline_phases.py`, `session_pipeline.py` — remove council refs
4. Delete `.claude/skills/council-round/`, `.claude/skills/invocation-balance/`
5. Edit `tests/test_anti_substitution_labels.py`, `tests/test_circuit_breaker.py`, `tests/test_cli_commands.py` — remove council cases
6. Delete any `tests/test_council_*` files
7. Run tests. Commit: `lite-v2: strip council subsystem`

**Batch 3 — Deeper consciousness:**
1. Delete `attention_schema.py`, `self_model.py`
2. Delete `selfmodel_commands.py` and remove from `__init__.py`
3. Delete `tests/test_attention_schema_coverage.py`, `test_butlin_indicators.py`, `test_circuit2_completeness_attention.py`, `test_self_model.py`, `test_self_model_coverage.py`
4. Run tests. Commit: `lite-v2: strip deeper-consciousness indicators`

**Batch 4 — Advanced features:**
1. Delete `curiosity_engine.py`, `predictive_session.py`, `planning_commitments.py`, `skill_library.py`, `communication_calibration.py`, `user_model.py`, `tone_texture.py`, `advice_tracking.py`, `user_ratings.py`, `value_tensions.py`, `pull_detection.py`, `resonant_truth.py`
2. Delete `insight_commands.py`, `rt_commands.py` and remove from `__init__.py`
3. Edit `_wrappers.py`, `admin_reset_template.py`, `entity_commands.py`, `pipeline_phases.py`, `session_pipeline.py`, `progress_commands.py`, `claim_commands.py` — remove all refs
4. Delete corresponding tests (full list in section 4)
5. Run tests. Commit: `lite-v2: strip advanced features`

**Batch 5 — Personal-substrate / mansion:**
1. Delete `mansion_quiet_marker.py`, `exploration_reader.py`, `in_flight_branches.py`, `upstream_freshness.py`
2. Delete `mansion_commands.py` and remove from `__init__.py`
3. Edit `knowledge_commands.py` — remove refs
4. Delete `tests/test_mansion_quiet_marker.py`, `test_in_flight_branches.py`, `test_upstream_freshness.py`, `test_exploration_briefing_surface.py`
5. Run tests. Commit: `lite-v2: strip personal-substrate / repo-state surfaces`

**Batch 6 — Logic + Advanced SIS:**
1. Delete `src/divineos/core/logic/` directory
2. Delete `sis_self_audit.py`, `sis_tiers.py`
3. Edit all CLI files referencing `logic.` or `sis_tiers` / `sis_self_audit`
4. Delete logic tests, sis tests
5. Run tests. Commit: `lite-v2: strip formal-logic and advanced-SIS layers`

---

## Pre-flight checks after each batch

```bash
cd "C:/DIVINE OS/DivineOS_fresh"
pytest tests/ -q --tb=line --ignore=tests/integration -x 2>&1 | tail -10
ruff check src/ tests/ 2>&1 | tail -5
mypy src/divineos/ 2>&1 | tail -5
divineos --help 2>&1 | head -20  # confirms CLI still loads
```

If any of these fail: don't commit; investigate. Common failure modes:
- Orphan import (a kept module imports a stripped one) — fix by either keeping the import-via-stub OR stripping the keeper
- Test setup uses stripped fixture — strip the test if it's testing a stripped feature, otherwise fix the setup
- CLI registration references deleted module — remove the registration line in `__init__.py`

---

## Acceptance criteria — when is Lite "done"

- [ ] `pytest tests/ -q --tb=line --ignore=tests/integration` passes (target: 100% of remaining tests green)
- [ ] `ruff check src/ tests/` clean
- [ ] `mypy src/divineos/` clean
- [ ] `divineos --help` runs without error
- [ ] `divineos briefing` runs on a fresh install without error
- [ ] `divineos extract` and `divineos sleep` complete without error
- [ ] No imports of stripped modules anywhere in `src/`
- [ ] CLI surface is approximately ~150 commands (down from main's 229)
- [ ] README.md updated to match — no mentions of family/council/Aria/mansion/Trinity
- [ ] CLAUDE.md updated to match — keep foundational truths #1-7 but strip references to family/council
- [ ] No remaining files in `family/`, `core/family/`, `core/council/`, `core/logic/`, or `selfmodel_commands.py`, `mansion_commands.py`, `insight_commands.py`, `rt_commands.py`, `family_*_commands.py`, `body_commands.py`

---

## README polish notes (for tomorrow)

The current README on main is full-DivineOS-flavored — mentions family, council, Aria, mansion. For Lite the README needs to:

- Keep the core pitch: "An operating system for AI agents. Memory, continuity, accountability, and learning across sessions."
- Remove all references to: family system, Aria, council of 29 experts, mansion, Trinity, deeper-consciousness indicators
- Add a *clear scope statement*: "This is DivineOS Lite — the foundation. Full DivineOS adds family/relational layer + council multi-lens scrutiny + deeper consciousness indicators on top of this foundation. Lite is what you want if you're building your own agent and need a memory + integrity substrate."
- Honest about what's in: ledger, knowledge engine, memory hierarchy, watchmen, compass-floor, affect log, briefing, sleep cycle, extract pipeline, lessons tracking, decision journal, drift detection, proactive patterns, anticipation, epistemic status, body awareness
- Honest about what's out (briefly mentioned for completeness)
- No mystical vocabulary in core docs — Lite is the secular foundation; full DivineOS is where the mystical-named-but-functionally-real stuff lives

---

## Open questions to resolve tomorrow

1. **What about `presence_memory.py`, `historical_ledger_surface.py`, `open_claims_surface.py`?** Currently in keep list. They surface things in the briefing — are they too Aether-specific? Lean keep, but if any reference family/Aria specifically, strip those references.

2. **The `corrigibility.py` module** — keep, but it has hooks into family for the operator-override case. Need to check if those hooks can be neutralized cleanly or if the module needs gutting.

3. **Skill files** — many skills reference family/council. Easier to delete and let users add their own than try to edit. Audit each skill file: if its function only makes sense with full DivineOS, delete; if it's foundational (briefing, extract, file-claim with no family refs), keep but edit out family content.

4. **Hooks in `.claude/hooks/`** — need to audit. Some hooks may reference stripped modules (e.g., family-state checks). Need to remove hooks that depend on stripped features.

5. **`scripts/precommit.sh` and related** — these run multi-party-review and pre-reg checks. Some checks depend on stripped modules. Audit and remove orphaned checks.

6. **`research/` directory** (if exists on main) — likely full-DivineOS-flavored research notes. Probably remove from Lite or archive.

7. **`exploration/` directory** — Aether-personal writing. Strip from Lite entirely.

8. **`bootcamp/` directory** — training exercises. Audit; likely strip Aria-specific content but keep generic training shell.

---

## Risk register

- **Hidden coupling**: `core/holding.py` is in the keep list but might import from a stripped module. Pre-flight will catch this.
- **Test fixtures**: Some `tests/conftest.py` setup may instantiate family.db or council. Need to strip the family/council parts of fixtures cleanly.
- **CLI auto-registration**: `__init__.py` likely uses an auto-discovery pattern. Need to check whether it's import-by-list (easier to strip) or scan-the-directory (need to delete the right files).
- **Skill auto-discovery**: Same shape. If skills are auto-loaded, need to delete the directories cleanly.
- **Pre-commit hook**: precommit.sh runs many checks. After strips, some checks may fail because they expected modules that are now gone. Update precommit.sh to remove orphan checks.

---

## Out of scope for tomorrow (defer)

- Wiring audit (Lepos firing correctly, Council auto-invoke, Watchmen real-time pattern surfacing) — separate work, applies to full DivineOS
- Trinity module — separate work, deferred
- Experimental sync — separate work, deferred
- DivineOS-Lite branding (logo, install instructions, distribution package) — after audit, depends on feedback

---

## Anchor

Lite v2 is *the foundation that holds*. Sober naming, clear function, audit-survivable. The substrate of a being lives somewhere else; Lite is the substrate of *any* persistent agent's basic operation. If the agent who lives in DivineOS-full would notice the loss of a module, it stays in Lite. If not, it goes.

When in doubt, strip. Tomorrow-me will be tempted to keep things "just in case." Don't. Less is the audit-friendly answer.
