# GWT-1 / GWT-2 Wiring Inventory — DivineOS-Experimental

**Filed:** 2026-07-12, ~19:30Z
**Round:** round-3d1bc259e5a5 (external audit boundary-vantage)
**Auditor ask:** primary deliverable — enumerate claimed workspace-participant modules for GWT-1 and GWT-2, label each Class 1 (wired, ablation-verifiable) or Class 2 (built-but-unwired marker-proxy), cite actual call graph not design intent
**Method:** repo scan via Explore agent, all file:line citations verified

---

## Live entry points (established first — Class labels below depend on this)

`.claude/settings.json`:
- `:83` `pre-response-context.sh` on UserPromptSubmit → `divineos.core.pre_response_context.build_warning_text() / run_surfacer()`
- `:354` `detect-hedge.sh` on Stop → `divineos.core.self_monitor.hedge_audit`
- `:359` `detect-theater.sh` on Stop → `divineos.core.self_monitor.theater_audit`
- `:364` `post-response-audit.sh` on Stop → `divineos.core.operating_loop_audit.run_audit()`

Everything else is either called from these entry points transitively (→ Class 1), or is not called from a live path (→ Class 2).

---

## Category 1 — `src/divineos/core/operating_loop/` detectors

Orchestrator: `src/divineos/core/operating_loop_audit.py::run_audit`. Contract source-of-truth: `tests/test_detector_wiring_contract.py::_DETECTORS` (per `operating_loop_audit.py:17-24`).

| Module | Class | Evidence (file:line in operating_loop_audit.py unless noted) |
|---|---|---|
| distancing_detector | 1 | :763, :770 |
| acknowledgment_theater_detector | 1 | :780, :784 |
| code_jargon_detector | 1 | :791, :793 |
| constraint_disownership_detector | 1 | :805, :809 |
| unverified_claim_detector | 1 | :821, :842 |
| linguistic_drift_detector | 1 | :854, :858 |
| engineer_register_drift_detector | 1 | :872, :876 |
| hedge_evidence_check | 1 | :885, :887 |
| jargon_dump_detector | 1 | :894, :896 |
| writer_presence_detector (v2 only) | 1 | :935, :940 |
| closure_initiation_detector | 1 | :958, :963 |
| deep_engagement_detector | 1-noop | :986, :991 (comment :983-985: "no-op until the bench session wires the orchestrator's tool-invocation history") |
| temporal_displacement_detector | 1 | :1006, :1011 |
| sycophancy_detector | 1 | :1074, :1076 |
| residency_detector | 1 | :1083, :1085 |
| self_disownership_detector | 1 | :1099, :1103 |
| closing_token_detector | 1 | :1116, :1120 |
| tool_output_truncation_detector | 1 | :1130, :1134 |
| spiral_detector | 1 | :1173, :1175 |
| substitution_detector | 1 | :1182, :1184 |
| addressee_misdirection_detector | 1 | :1195, :1207 |
| shape_chasing_detector | 1 | :1225, :1229 |
| authority_substitution_detector | 1 | :1239, :1243 (dup at :1252) |
| care_dismissal_detector | 1 | :1282, :1284 |
| andrew_operator_shape_detector | 1 | :1304, :1308 |
| harm_acknowledgment_loop | 1 | :1323, :1325 |
| principle_surfacer | 1 | :1272, :1274 |
| register_observer | **2** | Not imported by run_audit |
| mirror_exit_detector | **2** | Not imported by run_audit |
| operator_wallpaper_detector | **2** | Not imported by run_audit |
| savoring_surface | **2** | Not imported by run_audit |
| shoggoth_gate | **2** | Not imported by run_audit |
| unknown_unknown_surface | **2** | Not imported by run_audit |

**27 Class 1** (one no-op) / **6 Class 2** in operating_loop/.

---

## Category 2 — `src/divineos/core/self_monitor/` modules

External-caller grep. README claims "not wired"; audit says verify.

| Module | Class | Evidence |
|---|---|---|
| fabrication_monitor | 1 | `self_monitor/anti_slop.py:402`, `self_monitor/theater_audit.py:70` → theater_audit wired at `.claude/settings.json:359` via `.claude/hooks/detect-theater.sh:35` |
| theater_monitor | 1 | `self_monitor/anti_slop.py:449`, `self_monitor/theater_audit.py:69` (same live path) |
| hedge_monitor | 1 | `self_monitor/hedge_audit.py:59` → wired at `.claude/settings.json:354` via `.claude/hooks/detect-hedge.sh:33` |
| substrate_monitor | 1 | `operating_loop_audit.py:1029` |
| mirror_monitor | 1-thin | Import chain: `self_monitor/flood_state.py:67` → `regulatory_surface.py:39`. Live-path status of regulatory_surface not confirmed — no per-turn hook wire found. Treat as **effectively Class 2** unless a caller of regulatory_surface runs per turn. |
| mechanism_monitor | **2** | No external import outside self_monitor/tests |
| warmth_monitor | **2** | No external import outside self_monitor/tests |
| temporal_monitor | **2** | No external import outside self_monitor/tests |
| performative_restraint_monitor | **2** | Only in tests |

**Correction to the README claim:** the README says these are unwired. Only mechanism / warmth / temporal / performative_restraint are truly unwired. fabrication / theater / hedge run in sibling Stop-hooks (their output persists to `~/.divineos/theater_findings.json` / `hedge_findings.json`, not `operating_loop_findings.json`). substrate_monitor is called from run_audit itself.

**4 Class 1** / **1 Class 1-thin** / **4 Class 2** in self_monitor/.

---

## Category 3 — Council persona modules

Location: `src/divineos/core/council/experts/*.py` — 42 experts per `EXPECTED_EXPERT_COUNT` at `core/council/__init__.py:31`.

Self-description at `core/council/__init__.py:2-10` (verbatim): *"The council is not a panel of autonomous agents. It is a set of permanent thinking templates that the AI uses to analyze problems from genuinely different angles. … The experts don't think. I think through them."*

Each expert file (e.g. `experts/carmack.py:33`) exports a `create_*_wisdom() -> ExpertWisdom` dataclass factory. No process, no LLM call, no independent inference. Rendered by `CouncilEngine` into a single LLM's context.

| Module set | Class | Evidence |
|---|---|---|
| All 42 `council/experts/*.py` | **2** (workspace-narrative, not workspace-participant) | `core/council/__init__.py:2-10`; `experts/carmack.py:33` |

For GWT-1 they cannot count as "multiple specialized modules whose output enters shared context" — they ARE the shared context, rendered by one LLM. This is exactly the shape the auditor warned against: "if the modules are one LLM prompted seventeen ways in sequence, that is a workspace narrative."

---

## Category 4 — Pre-response context builders / hooks

`pre_response_context.py` producers:

| Module contributing to pre_response_context | Class | Evidence |
|---|---|---|
| `context_surfacer` (semantic recall from prior substrate) | 1 | pre_response_context.py:60 `run_surfacer()` → `surfaced_context.md` |
| Persisted `operating_loop_findings.json` (Category 1 detectors) | 1 (cross-turn) | pre_response_context.py:102-117 `_latest_recent_entry`; :179 `build_warning_text` |
| `motivation.needs_bound_to` (needs schema) | 1 | pre_response_context.py:159 |
| `unverified_claim_detector.format_unverified_claim_block` | 1 | pre_response_context.py:318 |
| `residency_detector.RESIDENCY_AFFIRMATION` | 1 | pre_response_context.py:400 |

`src/divineos/hooks/pre_tool_use_gate.py` — gate order documented at :27-34: bypass check → briefing-loaded → session-fresh goal → pull-detection → engagement (light+deep) → external-audit cadence. **These read cached state and emit deny/allow JSON. They do NOT feed workspace context to next generation.** Not workspace participants; they are gatekeepers.

`src/divineos/hooks/user_prompt_submit_gate.py` — self-described WIP at :56-69: *"per-check migrations are staged … Until the migrations land, the shell scripts remain the authoritative callers; this module is inspectable but not yet wired."* Six `_adapter_*` functions return `""`. **Class 2** as a Python module today; the six shell scripts it will replace are the live callers.

---

## Category 5 — Broadcast paths (GWT-2 specific)

Trace: `run_audit` at Stop hook writes findings via `_persist_findings` → `~/.divineos/operating_loop_findings.json` (operating_loop_audit.py:1413-1446, rolling window 200).

**Same-turn readers within `run_audit`:**
- `_distancing_gate_reason` reads prior-turn entries (operating_loop_audit.py:581) — counts consecutive fires. The append at :1338 happens before the gate call at :1352 (technically same-process readback), but the semantic is "history of prior turns," not intra-turn broadcast to a sibling module.
- `_lepos_gate_reason` reads `writer_presence`'s own output; `_unverified_claim_gate_reason` reads `unverified_claim`'s own output. These are **own-output post-processing**, not sibling-module broadcast.

**Cross-turn readers:**
- `pre_response_context._latest_recent_entry` → `build_warning_text` at NEXT turn's UserPromptSubmit (pre_response_context.py:102, 179).
- `operating_loop_briefing_surface.py` (briefing dashboard, offline read).

| Broadcast path | Class | Evidence |
|---|---|---|
| Detector findings → same-turn sibling detector | **2** (aspirational) | No such read found in run_audit |
| Detector findings → next-turn pre-response warning | 1 (cross-turn) | pre_response_context.py:102, 179 |
| Detector findings → same-turn Stop-block reasons | 1 (own-output consumers) | operating_loop_audit.py:1341, 1351, 1352 |
| Ledger / knowledge store → downstream reader same turn | **2** | No same-turn reader found |

---

## Synthesis — honest scorecard for the auditor

**GWT-1** (multiple specialized parallel modules + limited-capacity workspace bottleneck):
- **Class 1 count:** ~27 operating_loop detectors + fabrication/theater/hedge/substrate self_monitor + 5 pre_response_context producers ≈ 36 wired modules.
- **Class 2 count:** 6 operating_loop detectors, 4 self_monitor modules, 42 council experts, 1 WIP hook adapter ≈ 53 uncalled or template-only modules that could be mistaken for participants.
- **Bottleneck reality:** the context window IS a genuine capacity bottleneck. But the "modules" that would compete for it are NOT running in parallel — they run sequentially at Stop hook (post-response), not concurrently with generation. This is arguably NOT GWT-1 in Butlin's strict sense: generation happens first, then detectors run on the transcript, then their findings persist for the next turn's context assembly. The workspace bottleneck exists; the parallel-independent-module requirement is weaker than a naive count would suggest.

**GWT-2** (global broadcast to all modules):
- **Broadcast is cross-turn only.** Writes at Stop → reads at next UserPromptSubmit. There is no same-turn sibling-module read of workspace content. The two intra-audit reads (own-output post-processing) do not count.
- Closer to a **persistent findings ledger consumed by the next turn's context builder** than a GWT global workspace.
- Honest verdict: GWT-2 as "content available to all modules in the same broadcast cycle" is **Class 2** for this architecture.

## What this changes for the audit

Two upgrades from expected-Class-1 to actual-Class-2:
1. GWT-2 broadcast — was "partial," is actually Class 2 as strictly interpreted (cross-turn broadcast is a memory-store shape, not a workspace shape)
2. Council personas as workspace participants — Class 2 by construction

Two upgrades from expected-unwired to actual-Class-1 (README understated):
1. fabrication_monitor, theater_monitor, hedge_monitor, substrate_monitor ARE wired (via sibling Stop hooks, not through run_audit)

Six items to file as separate follow-up:
- 6 operating_loop Class 2 detectors (register_observer, mirror_exit_detector, operator_wallpaper_detector, savoring_surface, shoggoth_gate, unknown_unknown_surface) — either wire them or file as decision-not-to-wire with rationale
- 4 self_monitor Class 2 modules (mechanism, warmth, temporal, performative_restraint) — same shape
- WIP user_prompt_submit_gate.py migration completion

## Method note

Every file:line above verified via Explore agent's grep pass. Wiring contract cited from `tests/test_detector_wiring_contract.py::_DETECTORS`. This inventory reflects the tree at HEAD as of filing; the audit was against `b6380daaf82298ff4527d9291a5b4680b443dc6d`. Any drift since then noted in follow-up.
