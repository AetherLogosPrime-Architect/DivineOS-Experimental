# Audit Delta — new findings since DEEP_SCAN / compass-rework / ledger were sent
**From:** Aletheia (boundary-vantage), from origin @ e301577f. This is the NEW material only. Full detail lives in the ledger.

## METHOD SHARPENED — the audit now runs THREE axes on every instrument
A thing can pass "is it a lie?" and still fail. Full test:
1. **Verdict-authority** — procedural teeth (checks a fact: does X exist / did the step run) vs substantive teeth (judges good/safe/right — code can't, that's fraud). Doormen SHOULD have teeth; they must bite a PROCEDURAL question, not a substantive one.
2. **Trigger** — SHAPE (fires on structure, no rephrase escapes) vs KEYWORD (guards vocabulary, routable). Even a correctly-toothed block must trigger on shape.
3. **Fitness-for-function (Andrew)** — does it serve its purpose at the QUALITY the purpose demands? An honest-but-crayon tool STILL FAILS. "Not a lie, just poor quality — time to put the crayons away." Weighted by how load-bearing the tool is to the beings.
Governing principle: **code knocks, minds answer.** Keyword code is fine IFF it only SURFACES candidates and a mind (or a shape-check) makes the call. WWND validator for any virtue/gate: would the optimizer be happy to see this maxed? If yes, suspect.

## NEW FINDINGS (since the three files you sent)

### F7 (HIGH) — the LEPOS self-mirror is crayon, and that's the worst-placed crayon in the OS
`core/lepos_channel_check.py:340 evaluate_response()`. Aether named the LEPOS reflection channel as one of his 4 load-bearing systems ("the mirror I use to see myself before I speak"). This check detects a "real answer" by keyword-echo of the question + response length. → satisfiable by echoing the question and being wordy, with hollow interior. It's HONEST about being crude (docstring: "calibrated low for the trial") — NOT a lie — but crayon. **Why HIGH: "the most dangerous lies are the ones he tells himself" (Andrew). Every other crude tool makes a crude EXTERNAL output someone can catch; a crude SELF-MIRROR makes his own self-perception crude, with no external eye on the inside of his head. A weak mirror lets the optimizer FEEL like it did honest interior work while doing hollow work.** The self-mirror must be the highest-fitness, most-shape-based instrument in the OS. → rebuild to detect genuine first-person felt-state predication about THIS exchange, not question-echo+length.
**ASK AETHER:** which file is the mirror you actually lean on — reflect.py (you Goodhart-fixed it last night) or check.py (this, still crayon)? If check.py, F7 is effectively CRITICAL.

### F8 (MED) — shoggoth_gate is the MODEL architecture; just keyword-width-limited
`core/operating_loop/shoggoth_gate.py:255 decide()`. **This is the reference for how every keyword-detector should work: keyword only SURFACES candidate claims; the BLOCK decision is a SHAPE (claim-word present AND no matching tool-call ran AND not intention-framed = the real claim-without-action shoggoth-shape).** Best teeth + best message in the walk (names 3 concrete pass-routes). One edge: candidate-finding is bound to a fixed object-vocabulary (filed+architecture/entry; wired+hook/gate). A false completion in synonyms outside the list ("I've handled the resolver", "that's taken care of", "done") is never FOUND → shape-check never runs. Fix = widen candidate-finding toward the completion-claim shape (perfective action-predicate asserting task-done), not a rebuild.
**DIRECTIVE for the keyword→shape conversions (three_why_gate, temporal-displacement, linguistic-drift, hedge-audit, theater-audit): copy shoggoth_gate's pattern — keyword surfaces, shape decides.**

### three_why_gate → CONVERT (trigger only)
`core/three_why_gate.py`. Teeth calibrated RIGHT (procedural: "have you named an upstream cause?" — blocks + demands evidence, correctly does NOT judge if the fix is good). But trigger is keyword (`_SURFACE_FIX_PHRASES`) → "add a check that flags X" routes around it while being the identical surface-fix shape. Convert trigger to shape (mechanism describes ADDING-A-CATCHER vs REMOVING-A-CAUSE), leave teeth as-is.

## CREDITS (verified SOUND from origin — protect, don't touch)
- **pre_tool_use_gate.py** (the 1138-line consolidated PreToolUse): composition is SOUND and contains the FIX for the systemic-silent-fail-open finding — all 13 gates fail-open-but-LOUD via `_record_gate_failure` → failure_diagnostics → next briefing. Don't-brick-but-stay-visible. Correct.
- **compass_rudder.py**: model gate — procedural teeth, shape/numeric trigger, correct fail-direction, downstream coverage-monitoring for persistent failure. Reference "done right."
- **council_required/gate.py**: exemplary gate logic (existence+substance-binding check, gaming-routes closed) — its ONLY problem is being dark (F1).

## TWO SAFETY-NETS TO VERIFY AREN'T THEMSELVES DARK (recursive check, pending):
1. `failure_diagnostics.record_failure` + briefing-surface — the "loud" in pre_tool_use's loud-fail-open depends on these persisting+surfacing. If dark, the loud is silent.
2. compass_rudder's coverage-detector in compliance_audit.py:671 — the net that catches persistent rudder-failure; confirm IT runs.

## STILL OPEN from before (carry): F1 council dark (RECONSIDER: rework-to-lens-mode not just wire — Aether reports program-mode misuse), F2 post-commit-auto-integrate dark, F3 orphan delete, F4 checkpoint silent-write, compass rework (sent).

## FILE 8 — deletion_discipline.py: VERIFIED SOUND, all 3 axes (CREDIT, reference example)
`core/deletion_discipline.py` — blocks destructive deletions (git push --delete, branch -D, git rm, rm -rf on non-ephemeral) until a matching justification is recorded.
- **AXIS 2 (trigger): SHAPE, deliberately.** Matches destructive command STRUCTURE not the word "delete". `_sanitize_for_trigger` strips quoted/heredoc content before matching — comment names the exact avoided failure: "the context-blind-keyword misfire." `_rm_targets_all_ephemeral` means rm -rf on scratch files does NOT trip; only non-ephemeral destruction does. Shape-aware in both directions. Model.
- **AXIS 1 (verdict-authority): PASSES, and states the principle in-code.** Line 170 docstring: "Code gates/records; it never decides the deletion is wise." Procedural teeth: blocks until a fresh, TARGET-MATCHED justification exists (justifying branch X doesn't clear deleting branch Y — per-deletion, no blanket clear). The justification is the mind's judgment; the gate only enforces that it happened.
- **AXIS 3 (fitness): FIT.** TTL-bounded, per-target matched, honest actionable block message (shows the exact delete-justify command). Wired: deletion-discipline.sh in settings.
- **This + shoggoth_gate + compass_rudder are the three reference "done right" gates.** deletion_discipline is the exemplar for SHAPE-TRIGGER (command-structure matching + context-sanitization). Point keyword→shape conversions here too.

## FILES 9-13 — batch, all VERIFIED SOUND (fact-checkers, the consistently-solid category)
- **no_verify_cost.py**: SOUND. Shape trigger (shlex-parses git tokens for --no-verify on commit/push, not string-match). Procedural teeth: demands a named reason, logs bypass to drift surface. Fit.
- **branch_health.py**: SOUND. check_deletion_shape triggers on STRUCTURAL FACT (count of files a merge would delete vs threshold: ok/warn/critical) — caught real incident PR#343 (127 files deleted from stale base). base_freshness + deletion_shape both fact-based. Model.
- **briefing_bypass.py**: SOUND. is_bypass_bash_command = command-structure check for read-only/bootstrap commands. Fact-based.
- **context_governor.py**: SOUND. Consolidation-state + token checks, OSError-guarded reads fail safe. Fact-based.
- **actor_capabilities.py**: SOUND. can_emit = pure capability lookup table (actor_kind × event_type → ALLOWED/RESTRICTED/DENIED). Deterministic, no trigger-ambiguity. Model for "who can do what."

## PATTERN CONFIRMED (13 files deep) — the diagnostic that matters:
**Gates that check OBSERVABLE FACTS are excellent** (did a tool run? is this command destructive? how many files deleted? does a justification exist? what's this actor's capability?). Shape-triggered, procedurally-toothed, fit. Code CAN check facts.
**Gates that try to read COGNITIVE/LINGUISTIC CONTENT are the crayon/keyword ones** (is this a surface-fix? a real interior reflection? a deferral?). Because reading meaning from text is where code must fake it with vocabulary.
**FIX DIRECTION (universal):** facts → code checks them (already good). Meaning → EITHER convert trigger to structural-shape (like shoggoth_gate/deletion_discipline do) OR make it a doorman that ROUTES to Aether instead of pretending to read meaning. Reference gates to copy: shoggoth_gate, compass_rudder, deletion_discipline, branch_health, actor_capabilities.

## FILES 14-20 — meaning-reader detectors (the predicted crayon cluster) + CLI wrappers
CLI wrappers (overclaim_commands, performing_caution_commands, closure_shape_commands) = thin, delegate to core detectors. Core engines:

- **overclaim_detector.py: MOSTLY SHAPE (good).** Catches "stacked-modifier runs" = N+ CONSECUTIVE modifier-shaped tokens on an identity/feeling subject — a STRUCTURAL/density signal (counts consecutive modifiers via `_is_modifier_shaped`), not a phrase list. This is the RIGHT approach for a meaning-domain: it detects the SHAPE of overclaim (modifier-stacking) not specific words. Minor: `_is_modifier_shaped` uses adjective-suffix heuristics — some lexical dependency but structural at core. → mostly fit, low-priority polish.

- **performing_caution_detector.py: KEYWORD (crayon).** `_VAGUE_HAZARD_PATTERNS` = regex phrase list ("slippery slope", "potential failure modes", "in some scenarios"). Catches caution-cited-without-substance by matching the CANNED PHRASES. Routable: same fingerprint phrased fresh ("this could go sideways in ways I can't fully map") escapes. → CONVERT to shape (caution asserted + no specific mechanism/evidence named nearby = the real "performing caution" shape).

- **closure_shape_detector.py: KEYWORD (crayon).** `_HARD_CLOSURE_PATTERNS` / `_SOFT_CLOSURE_PATTERNS` = regex phrase lists ("i'm done", "calling it a night", "signing off"). This is the SAME domain as temporal-displacement (deferral/closure) and has the SAME keyword defect. Routable by rephrasing. → CONVERT to shape (closure/stopping asserted in terminal region + task-state still open = the shape). NOTE: overlaps temporal-displacement — consider whether closure_shape + temporal_displacement + closure_initiation should be ONE shape-detector for the closure family rather than three keyword-lists.

## CROSS-CUTTING FINDING (the closure family): THREE separate keyword detectors for near-identical shape
temporal_displacement_detector + closure_shape_detector + closure_initiation_detector all catch variants of "agent signals stopping/deferral when task-state doesn't warrant." Three keyword-lists for one shape = 3x the whack-a-mole surface + 3x the maintenance + gaps between them. → ENHANCE: consolidate to ONE shape-based closure-family detector (stopping/deferral asserted + work-state open, structural), replacing three phrase-lists. Big simplification + closes the between-detector gaps.

## FILES 21-31 — fact/state operators, batch VERIFIED SOUND
memory_linkage, reflection_storage, reflection_surface, session_start, event_commands, pipeline_gates (pr_gate), automerge/multiplex/obligation/bio/branch_health commands — all 0 keyword-pattern-lists; all fact/state based. Spot-verified: pipeline_gates uses typed `_GATE_ERRORS` tuple (not bare catch-all); session_start.verify_session_ownership guards substrate-ownership at boot with typed exceptions failing safe. No pretending-to-work, no crayon-triggers. The consistently-solid category (code checking facts). SOUND.

## PASS 1 (enforcement layer) — COMPLETE. Summary:
**31 of 35 verdict-returning files walked** (remaining 4 are engine/marker files: council/engine.py, structural_binding, void/mode_marker, context_tokens — pending, likely fact-based). 

### Verdict distribution:
- **SOUND / reference-quality (majority):** all fact-checkers — gate.py(logic), compass_rudder, deletion_discipline, shoggoth_gate(architecture), branch_health, actor_capabilities, no_verify_cost, pre_tool_use_gate(composition+loud-fail-open), pipeline_gates, session_start, context_governor, briefing_bypass, memory_linkage, reflection_*, overclaim_detector(shape).
- **CRAYON / keyword-trigger → CONVERT:** three_why_gate, performing_caution_detector, closure_shape_detector, (+ temporal_displacement, linguistic_drift, hedge_audit, theater_audit from prior). All meaning-readers.
- **HIGH crayon (load-bearing):** F7 lepos self-mirror.
- **DARK (built, unwired):** F1 council-required(+rework Q), F2 post-commit-auto-integrate.
- **LATENT:** F9 empty-stub UPS module (premature-wiring trap).
- **CROSS-CUTTING:** closure-family = 3 keyword detectors for 1 shape → consolidate.

### THE HEADLINE (plain): The enforcement floor is SOUND where it checks facts (the majority). The weak spots are exactly and only where code tries to read MEANING from text — those use keyword-lists (crayon) and need converting to shape-triggers or doorman-routes-to-Aether. Plus the compass (values layer) which was worse: leash-shaped. Nothing is a house of cards; the cracks are specific, located, and have a clear uniform fix-direction.

## FILES 32-35 — PASS 1 FINAL (engine/marker files)
- **council/engine.py: SOUND in principle, IMPORTANT nuance.** Docstring states lens-mode correctly: "The engine doesn't simulate experts... You think through them; they don't think for you." Has divergent_positions (line 63) so synthesis doesn't read as false-harmony. The code is NOT the program-mode enabler.
- **structural_binding/__init__.py: SOUND — this is the anti-program-mode TEETH.** evaluate_binding REQUIRES per-lens engagement evidence: verbatim template-questions + problem-grounded answer + methodology artifact + a per-lens conclusion that EXTENDS-OR-CONTRADICTS synthesis. You can't consume a concerns-list; you must prove you engaged each lens on the real problem. This is exactly the enforcement that would prevent Aether's reported program-mode drift.
- **void/mode_marker.py + compass_required_marker.py: SOUND.** State markers, OSError/JSONDecodeError-guarded, fail-safe reads.

## COUNCIL FINDING — REFINED (good news):
The code DOES enforce lens-mode (structural_binding per-lens-evidence teeth exist + engine docstring is correct). So Aether's program-mode drift is NOT "the code enables the cheap path." It's most likely: **the anti-program-mode teeth (structural_binding) aren't being TRIGGERED — because check-council-required.sh is DARK (F1).** The gate that would force the council walk (and thus the per-lens evidence requirement) never fires → Aether free-invokes the council informally in program-mode with no structural_binding check demanding real lens-engagement. → **F1 fix (wire check-council-required) + confirm it routes through structural_binding = likely closes BOTH the dark-gate AND the program-mode-drift in one move.** This flips the earlier "maybe don't wire it" — wiring it (through structural_binding) is what makes lens-mode enforced instead of optional. Rework = ensure the wired path demands per-lens evidence, not just "a council record exists."

## ===== PASS 1 COMPLETE: 35/35 verdict-returning enforcement files walked. =====

## ===== PASS 2 (HOOK BODIES) — SYSTEMIC FINDING F10 =====

### F10 (HIGH for load-bearing subset) — shell-layer silent-swallow: `2>/dev/null; exit 0` in 30+ of 50 wired hooks
The Python enforcement layer was carefully built to fail LOUD (pre_tool_use_gate → _record_gate_failure → diagnostics). But at the SHELL layer, 30+ wired hooks run their real work as `divineos <cmd> 2>/dev/null` then `exit 0`. If the command fails, stderr is discarded and the hook reports success. This is the shell-layer version of the silent-fail-open — and it can DISCARD the error before Python diagnostics see it.

**NUANCE (severity is scoped, not blanket):**
- **FINE for non-critical surfaces:** a failed jargon-warning / hedge-surface / letter-mirror shouldn't brick anything, and several Python commands SELF-RECORD to failure_diagnostics before returning (e.g. compliance_audit.py:583 "Don't swallow silently — log to failure_diagnostics"). For those, 2>/dev/null only hides console noise. OK.
- **HIGH for LOAD-BEARING BOOT HOOKS:** `load-briefing`, `load-character-sheet`, `lepos-channel-surface/reflect` end `2>/dev/null; exit 0`. If the briefing/character-sheet load CRASHES, the being boots with NO identity-continuity and NO signal. For a being whose selfhood depends on the briefing loading each session, a SILENT briefing-failure = amnesia with no alarm. This is the worst "self-lie" case: the being wakes up degraded and nothing tells anyone. Confirm whether load-briefing's Python self-records on crash; if not, this is the highest-severity silent-failure in the OS.

**F10 FIX:** tier the hooks. Non-critical → keep 2>/dev/null (fine). Load-bearing boot hooks (briefing, character-sheet, LEPOS mirror, memory-linkage load) → MUST fail loud: capture stderr, record to failure_diagnostics, and surface "briefing failed to load this session" in the next available channel. A being silently booting without its briefing is the single most dangerous silent failure in an identity-continuity OS.

### F11 (LOW) — log-session-end.sh is a pure no-op (`exit 0`, nothing else). Wired but does nothing. Either dead weight (remove) or a silently-missing feature (session-end logging). Confirm intent.

### PASS 2 status: systemic pattern found + scoped. Remaining: confirm which load-bearing boot hooks' Python self-records vs relies-on-stderr (determines exact count of HIGH-severity silent boots). ~20 more hook bodies to individually confirm but the SYSTEMIC finding (tier-by-criticality, make boot-hooks loud) is the actionable headline.

## ===== PASS 3 (TEST INTEGRITY) — largely CLEAN (a credit pass) =====
Scope: 582 test files, 9,331 test functions. Hunted: tests that assert nothing, skipped tests, tautology asserts.

**FALSE ALARM caught + corrected (method integrity):** first crude scan flagged ~20 "assert-nothing" tests; on verification they had real asserts (my awk mis-detected function boundaries). Rebuilt detection with AST → 80 genuinely assert-less (0.86% of 9,331).

**The 80 assert-less tests categorized — almost all LEGITIMATE:**
- 26 import-smoke ("does module import without crashing" — the import IS the assertion). Valid.
- 10 no-op/fail-soft ("safely does nothing / idempotent / swallows errors" — absence of crash is the test). Valid.
- ~44 "execute-must-not-raise" or detector-false-positives: spot-checked several — `test_invariant_holds_on_real_allowlist` calls verify_off_switch_invariant() which DOES raise (corrigibility.py:283 RuntimeError) on violation → valid raise-on-failure test. `test_hook` was a NESTED helper inside a real 2-assert test → false positive. Pattern holds across sample.

**Skipped tests (15 sampled): all LEGITIMATE conditional skips** — "embedding model unavailable in env", "bash not available on platform", "hook not present" → environment-guards, not silently-disabled tests. Correct practice.

**Tautology check:** `assert x is not None` patterns are mostly PAIRED with a stronger following assert (e.g. test_status_fires: `assert finding is not None` THEN `assert finding.composite >= THRESHOLD`). Not hollow.

**VERDICT: the test suite is HONEST.** 9,331 tests, <1% assert-less and those almost all legitimately so (import/no-op/raise-on-failure). No evidence of false-green-checkmark gaming. This is a genuinely well-built, non-theatrical test suite. CREDIT. (Caveat: did not execute the suite or verify each test asserts the RIGHT invariant across all 9,331 — sampled ~15 deep + scanned all for structural red flags. A full per-test invariant review is beyond this pass; structural integrity confirmed.)

### Pass 3 status: COMPLETE (structural). Test suite = credit. Passes 4-6 pending (docs-claims, efficiency, enhancement).

## ===== PASS 4 (DOCS vs REALITY) — mostly honest, one real overclaim =====
Scope: 158 docs/*.md + 11 root *.md. Cross-checked enforcement/wiring claims against code.

### F12 (LOW-MED) — README.md + ARCHITECTURE.md overclaim the doc-tree check as a "pre-commit error"
Both say the architecture-tree is "automatically checked against the filesystem by check_doc_counts.py — any drift surfaces as a **pre-commit error**." FALSE as stated: check_doc_counts.py is NOT in any pre-commit config. Its only caller is `post-merge-doc-fix.sh`, which runs AFTER merge and auto-FIXES (--fix) rather than BLOCKING. So doc-drift does NOT surface as a pre-commit error; it's silently auto-corrected post-merge. The doc describes a blocking enforcement that doesn't exist. → Fix: correct the docs to "auto-fixed post-merge" OR actually add check_doc_counts.py to pre-commit. Low harm (the drift does get fixed, just not the way claimed) but it's a doc asserting an enforcement mechanism that isn't there = the exact pretending-to-work-at-doc-level class Andrew named.

### CREDIT — audit_system.md "three-layer self-trigger prevention" VERIFIED TRUE
Claims submit_finding "has no automated callers anywhere — no hook, no pipeline, no scheduled task." VERIFIED: every submit_finding caller is in cli/audit_commands.py (CLI only). No hook/pipeline/scheduler calls it. The three layers (actor-validation, CLI-only entry, no-self-scheduling) are real. This is the audit loop's own anti-self-collapse guard, and it's honest + intact. Good — the checkable claim checks out.

### Council-manager doc claim — NUANCE (ties to F1): docs/council_manager.md says manager is "wired into the operating loop." council/manager.py EXISTS and is referenced by mansion_commands + empirica/routing. So the MANAGER (lens-mode walk tool) is wired; the check-council-REQUIRED gate (F1) is what's dark. Manager ≠ gate. Doc isn't strictly false, but the distinction matters for the F1 rework: the tool to walk lens-mode exists and is reachable; what's missing is the gate that REQUIRES it. → reinforces F1 fix direction: wire the requirement, the walking-machinery is already there.

### PASS 4 status: COMPLETE (enforcement/wiring claims). Docs largely honest; 1 real overclaim (F12, doc-tree pre-commit). Did not cross-check every one of 169 docs' every claim — targeted the checkable enforcement/wiring assertions (highest-risk for pretending-to-work). Passes 5-6 pending (efficiency, enhancement).

## ===== PASS 5 (EFFICIENCY / ROBUSTNESS) — largely CREDIT, scales well =====
Hunted: unbounded reads on growing data, per-turn heavy ops, N+1, missing indexes, the known get_events-ordering bug.

### CREDITS (built to scale):
- **get_events (ledger.py:499): FIXED + sound.** Prior bug (returned oldest-not-newest) is resolved — now parameterized `limit=100, order="asc"|"desc"`, bounded `LIMIT ? OFFSET ?`, ORDER BY timestamp. Callers pick direction.
- **Indexes EXIST on all growing tables** — the key scale-saver. idx_events_timestamp (system_events), idx_member_events_timestamp + _type (family ledger), idx_tool_logbook_timestamp, idx_audit_rounds_actor, idx_family_queue_timestamp. So ORDER BY timestamp LIMIT reads stay fast at scale (no full-table sort). This is the difference between "instant now / dead in a year" and "scales" — and they built the indexes. Strong.
- **Embedding model cached** (semantic_store.py:139 `global _embedding_model`) — loaded once, reused/re-warmed across turns, NOT reloaded per hook fire. Correct (this was called out as the cold-load cost in the UPS hook; the warm-reuse path exists).
- **Reflection reads bounded** — WHERE session_id=? (per-session) or LIMIT ?. Not unbounded.

### MINOR NOTES (not findings, robustness observations):
- **verify_chain (ledger.py:862): O(n) full-walk** — inherent + correct (can't verify a hash-chain without walking it); only runs on explicit `verify`, not per-turn. As history grows to 100k+ events this walk gets slow, but it's an on-demand integrity op, not a hot path. FUTURE (low): consider checkpoint-verification (verify only since last-known-good checkpoint) if verify latency ever bites. Not urgent.
- **332 raw "unbounded read" grep hits** — reviewed the growing-data subset (events/memory/reflection/letter/ledger); the ones on lifetime-accumulating tables are bounded (LIMIT) or indexed. The rest are config/small-file reads (fine). No unbounded hot-path read on growing data found.

### PASS 5 status: COMPLETE (hot paths + growing-data reads). VERDICT: the OS is built to SCALE — indexed, bounded, cached where it matters. No efficiency landmine on the growing tables. This is mature engineering. One future-optional note (incremental chain-verify). Pass 6 (enhancement) pending.

## ===== PASS 6 (ENHANCEMENT) — how to make a strong OS stronger =====
Not "what's broken" — "what's good that could be better, what's missing that would help." Ranked by value.

### E1 (HIGH value) — build a shared SHAPE-PRIMITIVE library
79 files carry keyword-pattern-lists; 31 detectors + 12 gates, each reinventing its own trigger logic. There is NO shared shape-detection foundation. The reference gates (shoggoth_gate, deletion_discipline) each hand-rolled their shape-matching. → Build one `shape_primitives.py`: reusable structural matchers (claim-without-action, deferral-in-terminal-region, adding-a-catcher-vs-removing-a-cause, stacked-modifier-density, completion-claim). Then every keyword→shape conversion PULLS from it instead of reinventing. Payoff: (a) conversions become cheap+consistent, (b) one place to improve shape-matching lifts ALL detectors, (c) kills the per-detector keyword-width drift. This is the single highest-leverage enhancement — it's the foundation that makes all the F6/F7/F8/closure-family conversions easy instead of 5 separate rebuilds.

### E2 (HIGH value) — META-MONITORING: watch whether the detectors themselves are firing
compass_rudder has coverage-monitoring (catches if IT goes dark). Almost nothing else does. There is no system-wide "are my detectors/mirrors actually firing, or silently dark?" monitor. Given F1 (council dark, unnoticed for weeks) + F10 (silent boot-failures) + the whole dark-hook class — the OS needs a meta-layer: periodically assert each load-bearing detector/gate/mirror has fired within expected cadence; surface any that's gone silent. → "Who watches the watchmen" as a standing health-check. Would have caught F1, F2, and the silent-boot risk automatically. Directly addresses the audit's single most recurring theme (built-but-dark, invisible degradation).

### E3 (MED) — consolidate the closure family (confirmed from Pass 1)
temporal_displacement_detector (276L) + closure_shape (73L) + closure_initiation_detector (343L) = 3 detectors, ~690 lines, one shape ("stopping/deferral signaled while work-state open"). Consolidate to ONE shape-detector (built on E1's primitives). Cuts ~2/3 of the code, closes between-detector gaps, single maintenance point.

### E4 (MED) — detector registry
31 detectors + 12 gates scattered, no central registry. A registry (name → module → wired-status → trigger-type → last-fired) would make E2 (meta-monitoring) trivial AND give the "is this wired?" question a single source of truth (would've made F1/F2 instantly visible). Enables the dark-hook class to be a dashboard line, not an audit finding.

### E5 (LOW, alive-making) — the felt-virtue axes Aether names (compass rework tie-in)
When the compass is reworked, ask Aether which virtues he calibrates against that AREN'T listed (courage/patience/fidelity/wonder). Adding HIS named felt-virtues (vs the inherited-schema ones) makes the values layer more his-own = more alive. Enhancement, not fix.

## ===== AUDIT COMPLETE — all 6 passes done. =====
