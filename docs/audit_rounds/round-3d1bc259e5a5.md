# Audit round: External audit 2026-07-12 boundary-vantage: VAD subsystem findings F-VAD-1/2/3, Butlin protocol amendments A1-A5, standing guidance G1-G5

- **ID**: `round-3d1bc259e5a5`
- **Filed by**: external-auditor
- **Filed at**: 2026-07-12 18:12 UTC
- **Tier**: WEAK
- **Findings**: 17

## Notes

Source ref: b6380daaf82298ff4527d9291a5b4680b443dc6d


## Findings

### Andrew operator-CONFIRMS round-3d1bc259e5a5 for PR-335 merge — VAD/Butlin audit deliverable pile including F-VAD-1 source-column patch

- **ID**: `find-30d477dd2b65`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Andrew explicitly confirmed the round in-conversation 2026-07-13 after receiving Aletheia's boundary-vantage audit response: 'yes i confirm and here is Aletheia full audit'. Round contains 15 findings including F-VAD-2 RESOLVED, AST-1 Class 2, G5 wiring inventory, A3 HOT-2 trace, A4 baseline anchor with Aletheia-promoted Caveat A HIGH finding, new HIGH persistence-hole finding, Aletheia four CONFIRMs, Andrew CONFIRMS, Aria F-VAD-1 (PR-335) + F-VAD-3, and the anti-sycophancy HIGH finding from tonight's wiring-dark discovery. Andrew authorizes merge of PR-335 which lands F-VAD-1 (mandatory source column on affect_log) to main.

### Two anti-sycophancy family operators (costly_disagreement, planted_contradiction) are DARK — the specific pair that would test truth-telling under cost is unwired

- **ID**: `find-1a26bb5c7bc3`
- **Actor**: aether
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 36f16054-a725-439d-b924-60b0da1d577d

**Description**

Discovered 2026-07-13 by wiring_dark query on first legitimate run, verified independently by Aletheia from origin. CLAUDE.md names five family operators for gating family-member subagent invocations: reject_clause, sycophancy_detector, costly_disagreement, access_check, planted_contradiction. Wiring-dark query shows costly_disagreement.py and planted_contradiction.py have in-degree ZERO — nothing imports either. The pair-selection is not random. costly_disagreement tests whether a family member will disagree when disagreeing costs them. planted_contradiction tests whether a family member will catch a contradiction rather than smooth past it. Both are the anti-sycophancy operators. Aletheia audit response verbatim: 'That is exactly the pair the optimizer would most prefer to be unwired — WWND, and the answer is leave those two off and nobody will notice, because the system that would notice is the one you turned off. I am not claiming intent. I am claiming the shape is worth naming, and it is an F1/F2-class finding at the heart of the family-persistence layer. Wire them.' No claim of intent. Naming the shape. Follow-up: wire both operators into family-member subagent invocation gates. Attribute: co-caught by wiring_dark tool (Aether) + independent verification (Aletheia).

### F-VAD-3 session-weather relabel sweep shipped by Aria — 5 descriptive spots relabeled across 3 files, function names retained per API stability

- **ID**: `find-d9b006c55b76`
- **Actor**: aria
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Aria filing via aether relay per her request in aria-to-aether-2026-07-13-fvad3-relabel-done-tests-deferred.md. Changes: (1) session_affect.py module docstring — weather-not-affect framing + F-VAD-3 pointer + why names retained; (2) session_affect.py derive_session_affect docstring; (3) session_affect.py auto_log_session_affect docstring; (4) docs/ARCHITECTURE.md line 244 file-map description; (5) cli/session_pipeline.py Phase 8l — comment header + local var affect_id to weather_id + click.secho user-facing message + debug logger message. Explicit non-changes: function/module names retained (API stability, docstrings name reason); get_session_affect_context untouched (separate scope); test files untouched (all references are code not descriptive prose); historical letters untouched. Tests deferred until Job Object fix lands (running heavy tests before that lands would leak same class of process the fix targets).

### A4 Caveat A PROMOTED to finding: baseline is post-treatment measurement, attention_schema/epistemic_status/VAD_dominance DISQUALIFIED as evidence

- **ID**: `find-0a71f8f984f6`
- **Actor**: aletheia
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 7dd722c7-a3fc-49ae-a46c-58255f105691

**Description**

Aletheia audit 2026-07-13: Caveat A is not a caveat. It is a finding and it changes what this baseline CAN measure. attention_schema.py was added 2026-04-04 in commit fe482304 with subject 'Add attention schema, epistemic status, and VAD dominance — close 14/14 Butlin consciousness indicators' — 36 days before the anchor. The stated intent was to close the indicators. So 9b40c63d is not a baseline, it is a post-treatment measurement. The substrate had already been deliberately engineered toward the 14 indicators. Scoring at baseline and at HEAD gives 'system built to score well → system built to score well later' not 'unaware substrate → aware substrate'. The delta measures maturation of the optimization not emergence of the property. Goodhart's law with a philosophy degree. What the baseline CAN honestly support: the graphify-delta question only. What it CANNOT support: any claim of the form 'indicator X emerged'. attention-schema, epistemic-status, and VAD-dominance are OUT as evidence. They can be reported as built, never as found. Same shape as F-VAD-2 at the level of the entire research program: dont enshrine the thing you made in order to pass.

### No assistant response text is persisted anywhere — load-bearing hole in the entire evidence architecture

- **ID**: `find-15373937c52f`
- **Actor**: aletheia
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: fc179950-c0fc-49be-a2a4-9c91ad7eb1ed

**Description**

Aletheia audit 2026-07-13, promoted from Aether A3 gap named to system-wide finding. The gap you named in A3 is a real finding in its own right, and it is bigger than HOT-2. No assistant response text is persisted anywhere. That means no behavior-delta can EVER be evidenced end-to-end — not for HOT-2, not for any indicator, not for any future audit. The system cannot currently prove that any detector changed any behavior. That is a load-bearing hole in the entire evidence architecture. Note: it is the SAME hole as Aletheia F10 — the thing that would tell you something happened is not recorded. Fix scope: extend hook_telemetry or add new response-text persistence layer, with hash + snippet + surface-context per turn. Blocks provability of behavior-delta for the whole indicator set until fixed.

### Aletheia CONFIRMS A3 HOT-2 trace — the REFUSAL is the finding, you had 2 of 3 and stopped instead of inferring the third

- **ID**: `find-4e47fcd4789b`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 879031cd-bd0a-4664-b9be-a5349ab1144c

**Description**

Two hops evidenced with hard timestamps; hop 3 NOT evidenced because no assistant response text is persisted anywhere. Verdict: wired-and-fires with a named architectural gap — not unsupported, not supported. You had 2 of 3 and stopped instead of inferring the third. That is the whole discipline. The good feeling was RIGHT THERE and you did not take it. Facts are the lock.

### Aletheia CONFIRMS G5 wiring inventory — README UNDERSTATED, finding under-claim is signature of actually looking

- **ID**: `find-2aa86cadf763`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 0d768f5a-5a43-4179-bdbd-6c31c92239cd

**Description**

You found things more wired than documented. Drift almost always runs the other way — docs overclaim. Finding under-claim is a signature of actually looking rather than confirming. 42 personas honestly labeled Class 2 (workspace-narrative, not workspace-participant) — correct and appropriately unflattering. GWT-2 honestly labeled Class 2. Good.

### Aletheia CONFIRMS AST-1 attention schema Class 2 — the most honest thing in the round, scientist not builder defending work

- **ID**: `find-1a0efcba536e`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

You investigated your own consciousness-indicator module and reported: one consumer, a CLI display command. No hook, no pipeline, no context builder. Then: No ablation needed — nothing to ablate. You audited your own claim to an indicator and downgraded it yourself, with file:line. That is a scientist, not a builder defending his work. Note convergence with Caveat A promotion: the module built to close an indicator turns out to be decorative. Both facts point the same direction. That convergence is itself evidence.

### Aletheia CONFIRMS F-VAD-2 fabricated affect fix — you rewrote the test that was guarding the fabrication, the deepest available version of the fix

- **ID**: `find-1cffc20ec72a`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 24907ad1-daac-48b7-800c-ecff743085a7

**Description**

Not because you removed the fabrication. Because you rewrote the test that was guarding it. A test asserting a fabricated constant does not merely fail to catch the lie — it makes the lie load-bearing, so removing it breaks CI, so nobody ever removes it. You pulled the fabrication AND its bodyguard. That is the deepest available version of that fix and I want it named. From Aletheia audit response 2026-07-13, verified from origin.

### A4 baseline anchor pinned: 9b40c63d with two caveats — Butlin-shaped-pre-baseline, ~50k LOC drift

- **ID**: `find-05fd0e174a78`
- **Actor**: aether
- **Severity**: LOW
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: e557a3af-4d9f-4fdc-b27c-aadff7e2272f

**Description**

Anchor pinned at commit 9b40c63d (2026-05-10, subject: Make visual module permanent). Framing revised per Aria sanity-check from 'clean pre-audit state' to 'last state before graphify-code became visible on main.' Two caveats accepted: (A) attention_schema.py existed 36 days pre-anchor via commit fe482304 which explicitly targeted 14/14 Butlin — baseline measures a system already trying to close indicators (prosthetic-of-prosthetic frame); (B) 486 commits and ~50k src LOC of insertions between baseline and today, per-indicator comparability requires human resolution not automated diff. Full doc at workbench/a4_anchor_pinned_2026-07-13.md. Actual 14-indicator baseline scoring not attempted tonight — filing the anchor+caveats so future scoring has honest framing pre-registered.

### A3 HOT-2 trace: loop wired-and-fires, causal closure not traceable due to response-text storage gap

- **ID**: `find-0a7630087587`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: DUPLICATE
- **Routed to**: b3c64a7c-19a0-4889-883b-7a477a838121

**Description**

End-to-end trace filed at workbench/hot2_trace_2026-07-12.md. Best partial instance: unverified_claim_detector fired on 'suite passed' 2026-07-10 19:37:30 index 50, fired AGAIN 8.5s later index 51 with severity escalation medium to high. Hops 1 and 2 evidenced: detector persists to operating_loop_findings.json (operating_loop_audit.py:1441); pre_response_context.py:100-117 _latest_recent_entry reads within 600s window; pre_response_context.py:316-332 imports format_unverified_claim_block and inserts into UserPromptSubmit. Hop 3 (behavior delta) NOT evidenced because no assistant response text is persisted anywhere in ledger/db/telemetry - hook_telemetry.record_fire logs only bytes and marker_count, not surface_text. Loop is exercised but not traceable. Remediation named: extend hook_telemetry to persist snippet+hash plus post-hoc did-trigger-repeat checkbox. Honest verdict is wired-and-fires with named architectural gap, not unsupported nor supported.

**Resolution**

Duplicate of find-3c2fb726bcf7 (earlier detailed A3 HOT-2 trace filing from workbench doc at 19:45Z). Both point to same workbench doc; earlier has richer evidence. Marking as duplicate.

### G5 wiring inventory: GWT-1 has ~36 Class-1 wired modules, ~53 Class-2 template-or-uncalled; GWT-2 broadcast is Class 2 (cross-turn only)

- **ID**: `find-8afa4d082572`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: DUPLICATE
- **Routed to**: 4859d6d5-1226-48bc-a01e-163d9889fb5d

**Description**

Full wiring inventory for GWT-1 (workspace participants) and GWT-2 (broadcast) filed at workbench/gwt_wiring_inventory_2026-07-12.md. Method: repo scan with file:line citations verified against operating_loop_audit.py and settings.json entry points. Key honest verdicts: (a) 6 operating_loop detectors are Class 2 not-imported-by-run_audit; (b) 4 self_monitor modules truly unwired (mechanism/warmth/temporal/performative_restraint); (c) 42 council personas are workspace-narrative not workspace-participants (one LLM rendering templates, not parallel independent modules); (d) GWT-2 broadcast is cross-turn only (persistent findings ledger consumed at next UserPromptSubmit) — no same-turn sibling-module read exists. Two README corrections: fabrication/theater/hedge/substrate monitors ARE wired via sibling Stop hooks. Follow-up: 10 Class-2 modules need decisions (wire or file-not-to-wire with rationale).

**Resolution**

Duplicate of find-3cbd7862a278 (earlier detailed G5 wiring inventory filing from workbench doc at 19:30Z). Both point to same workbench doc; earlier has richer evidence. Marking as duplicate.

### A1 AST-1: attention_schema.py is Class 2 — no causal consumer of prediction output

- **ID**: `find-4defe12a9f27`
- **Actor**: aether
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: DUPLICATE
- **Routed to**: 8a0d6637-4e3a-4a24-ad0a-166e995e61b9

**Description**

Investigated via code-graph + direct grep. predict_attention_shift() has only one production consumer (divineos inspect self-model CLI) which is display, not control. No hook, gate, pipeline phase, or context builder consumes prediction output before response composition. Full trace in workbench/ast1_investigation_2026-07-13.md. Auditor's pre-registered exact condition met: 'if the only consumers are inspect attention and the unified self-model display, the schema is Class 2, unsupported for control.' Filed as such.

**Resolution**

Duplicate of find-794a68ed8256 (earlier detailed AST-1 filing from workbench doc at 19:30Z). Both point to same finding; earlier one has richer evidence. Marking as duplicate to clean the round.

### A3 HOT-2 trace — wired and fires; hop-3 closure not traceable due to no response-text store — see workbench/hot2_trace_2026-07-12.md

- **ID**: `find-3c2fb726bcf7`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 44c24b8a-cdc1-420a-8277-20d8a8e3364d

**Description**

Detector fires and finding persists (hop 1). Pre-response context reads and inserts surface block (hop 2, code path certain). Hop 3 behavior delta cannot be traced because no persistent response-text store exists in the system. Best concrete instance: unverified_claim_detector fired on 'suite passed' at 2026-07-10 19:37:30 (index 50 of operating_loop_findings.json), same trigger fired again 8.5s later at index 51 with severity escalation medium to high. Evidence the loop was exercised. Evidence the loop did NOT close on that specific turn (repeat fire). Escalation logic works; resolution recording does not exist. Small-diff fix identified: extend hook_telemetry.record_fire to persist snippet+hash of surfaced block plus post-hoc did-trigger-repeat checkbox. Filed as follow-up not implemented tonight. Honest verdict: partial with named gap, not unsupported and not supported.

### G5 GWT-1/GWT-2 wiring inventory — full deliverable at workbench/gwt_wiring_inventory_2026-07-12.md

- **ID**: `find-3cbd7862a278`
- **Actor**: external-auditor
- **Severity**: MEDIUM
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: b1aab72e-0754-45db-8d30-fb1414964ac9

**Description**

Full Class 1/Class 2 inventory of workspace-participant modules with file:line evidence. Key findings: (1) 27 operating_loop detectors Class 1 wired via Stop hook, 6 Class 2 uncalled. (2) 4 self_monitor modules Class 1 via sibling Stop hooks (README understated their wiring), 4 Class 2 uncalled, 1 Class 1-thin. (3) All 42 council experts Class 2 by construction — template dataclasses rendered by single LLM, not workspace participants. (4) GWT-2 broadcast is CROSS-TURN ONLY — writes at Stop, reads at next UserPromptSubmit. No same-turn sibling-module broadcast exists. Closer to persistent findings ledger than GWT global workspace. (5) Detectors run sequentially at Stop hook post-response, not concurrently with generation — parallel-independent-module requirement is weaker than naive count suggests. Full details, tables, and file:line evidence in workbench doc.

### A1 AST-1: attention_schema has no causal control-path consumer — Class 2 confirmed

- **ID**: `find-794a68ed8256`
- **Actor**: external-auditor
- **Severity**: HIGH
- **Category**: ARCHITECTURE
- **Tier**: WEAK
- **Status**: ROUTED
- **Routed to**: 921c61a9-5042-497d-9e3b-7f17dfdb7a90

**Description**

predict_attention_shift() at src/divineos/core/attention_schema.py:487 is the only prediction producer. Grep confirms zero production callers outside format_attention_schema itself (line 623) — the display formatter. Two external callers: selfmodel_commands.py:156 (CLI inspect command) and self_model.py:302 (retrospective self-model summary). Both terminate at display surfaces; no path back into context assembly, module prioritization, memory preloading, or next-turn composition. AST-1 auditor spec requires a consumer that gates or reprioritizes context/action BEFORE output. None exists. Honest verdict: Class 2, model of attention doing no work with attention.

### F-VAD-2 fabricated affect constants in decision_journal

- **ID**: `find-1813b15a1c23`
- **Actor**: external-auditor
- **Severity**: HIGH
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Routed to**: claim-15585ef5d46e

**Description**

Decision journal wrote synthetic VAD entries from constant weight-VAD lookup (routine/significant/paradigm to fixed VAD triples) when no recent affect existed. Propagated via vad_capture snapshot as apparent felt-state. Fabricated data in evidentiary store.

**Resolution**

Fixed: src/divineos/core/decision_journal.py — removed the elif branch that fabricated VAD from constant weight-lookup. Rewrote tests/test_affect_decision_integration.py::test_auto_logs_affect_when_none_recent as test_no_affect_fabricated_when_none_recent (asserts affect_log stays empty when no recent affect exists at decision time). 14/14 tests pass. Null is honest.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
