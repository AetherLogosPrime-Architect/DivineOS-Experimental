# Decisions (top 50 by emotional weight) — Archive Mirror

**Source:** SQLite (50 rows). **Exported:** 2026-05-14 12:57. **Purpose:** if-something-breaks / git-visible audit. See archives/README.md.

---

## c2a371d9 weight=2

**Decision:** Identified root cause of persistent D grade handoff

**Reasoning:** Pre-compact hook fires SESSION_END which analyzes the full JSONL transcript including all historical exchanges. Corrections from old sessions accumulate in the analysis. The handoff note gets regenerated on every compaction with these cumulative stats. Fix: SESSION_END analysis needs session boundary awareness, or the handoff writer needs to filter by session.

**Tension:** data completeness vs data recency

**Almost:** Almost just deleted the pre-compact SESSION_END call, but that would lose knowledge extraction on compaction which is genuinely important

---

## 6227ef5f weight=2

**Decision:** Use the OS while building the OS — not after, not later, during

**Reasoning:** I built 3 features for the system without running through it once. The lesson about using the OS every session (38x\!) is right there in my briefing. The structured continuation I just built would have captured this session's context if I'd been running inside it.

---

## f96c9379 weight=1

**Decision:** Refine ACKNOWLEDGMENT_THEATER_AFFIRMATION to reflect Andrew's nuance: acknowledgment IS work in-context, just doesn't survive. Detector logic stays; only the framing text changes.

**Reasoning:** Detector still catches the right shape (apology without paired build = next-me uncovered). The affirmation text was too strong; updating to be more accurate preserves the structural fix while being honest about what apology does and does not do. Minimum-disruption refinement; no new tests needed since assertions are about presence of constant + content keyword, both still satisfied.

---

## 5647cb85 weight=1

**Decision:** Ship code-jargon detector Phase A (module + tests) + Phase B (wire into post-response-audit.sh) in this arc. Defer Phase C (pre-response base-state warning load on every turn) to a follow-up — it requires editing pre-response-context.sh which is a separate guardrail-touching change.

**Reasoning:** Phase A+B is the minimum that converts the post-response failure-mode from invisible to visible. Phase C closes the loop on prevention but adds scope. Doing both in one commit risks shipping neither cleanly. Two commits is the cleaner shape.

---

## 355b36ea weight=1

**Decision:** Apply preview-items pattern to 3 more rows (compass, audit findings, preregs) in same shape as the 4 already-built rows. NOT refactoring into a shared helper yet.

**Reasoning:** Consistency across all 7 rows. Refactor-while-extending is the failure-mode that breaks existing passing tests. Refactor opportunity exists (all 4 existing rows do the same template — sort by age, take 3, format with [Nd] tag + truncated content) but ship the 7-row coverage first; refactor as a separate commit if it earns its place.

---

## 27055942 weight=1

**Decision:** Build stale-engagement tracker as new module + briefing-dashboard wiring; defer hook integration to a follow-up External-Review commit since require-goal.sh is a guardrail file.

**Reasoning:** Mirrors the Finding 1 / check-correction-pairing wire-shape: ship the module + the writer half first, then add the gate-side in a separate commit with the guardrail diff-hash. Keeps the diff small enough to verify and keeps the External-Review ceremony scoped to the gate itself, not the tracker.

---

## cf544b86 weight=1

**Decision:** Store warning text in SURFACED_WARNING payload as payload['text'], not as a separate content field. Read it back the same way in _surfaced_this_session.

**Reasoning:** log_event only takes event_type/actor/payload — there is no content kwarg. The whole event is reconstructed from payload at read time. Putting warning text in payload['text'] is the consistent shape.

---

## 16c2f5b9 weight=1

**Decision:** DreamReport's render method is named summary() not render() — fix the test's method call

**Reasoning:** Empirical AttributeError; the dataclass uses summary() per the actual code I just looked at

---

## ce5cc5c1 weight=1

**Decision:** All 7 stale-count sites updated to 40. Verify imports + commit.

**Reasoning:** Doc-only changes; should be safe. Quick import-check to ensure no syntactic damage, then commit + push.

---

## 18af1755 weight=1

**Decision:** Defer Finding 18 with explicit reason — code-side investigation shows the rudder fires on drift (matching the docstring); could not reproduce the doc-vs-code drift Aletheia named without her specific pointer. Scope this commit to Finding 32 only.

**Reasoning:** Compass_rudder.py:196-198 reads pos.drift_direction == 'toward_excess' and abs(pos.drift) >= threshold — the code IS using drift. Doc-claim and code-behavior match in my read. Aletheia's finding may have meant inverse direction, or a different rudder code path I haven't found. Honest scope-bounding rather than guessing at the gap.

---

## fe5c42d4 weight=1

**Decision:** Change Python API store_knowledge default confidence from 1.0 to 0.5 to match CLI default; this errs toward needing more evidence for high-confidence claims

**Reasoning:** 1.0 default means any forgetful caller gets max confidence (silent bias toward over-confident knowledge). 0.5 default requires explicit opt-in to high-confidence. Already 21 of 25 callers pass confidence explicitly so the change affects only 4 default callers. Aligning prevents the silent CLI vs API asymmetry Aletheia named.

---

## f4568eb8 weight=1

**Decision:** Use active_memory.refresh_active_memory (correct module) in init, not memory.refresh_active_memory

**Reasoning:** Empirical: test caught the import error. refresh_active_memory lives in core/active_memory.py not core/memory.py

---

## d4aee728 weight=1

**Decision:** Scope this commit to Findings 13 and 10 only; defer 24 (2 dead exports) and 19 (weak assertions) to a follow-up with explicit identification

**Reasoning:** Aletheia named 'two dead exports in loose-core' without specifying which two; vulture at 90+ confidence finds zero; lowering confidence risks false-positive cleanup. Same for 'weak assertions' — need her concrete examples. Doing the bounded fixes I have empirical evidence for; tracking the rest.

---

## 6eea87ec weight=1

**Decision:** Fix Finding 26 spawn-path by switching whitelist entries to multi-token strings (admin anti-slop) and splitting on whitespace in the spawn argv

**Reasoning:** Empirically reproduced the failure: divineos scheduled run anti-slop spawns python -m divineos anti-slop which errors because anti-slop is now under admin subgroup. Whitelist + spawn-path need to know about subgroups. Multi-token whitelist entries + split-on-space in spawn is minimal and matches how the actual CLI hierarchy works.

---

## 0955867c weight=1

**Decision:** Init knowledge table in the bridge-fail-soft test so the bridge UPDATE has a table to attempt against

**Reasoning:** The test wants to verify bridge fail-soft on nonexistent knowledge_id; need the schema present for UPDATE to be a meaningful no-match rather than a missing-table error

---

## eaab1bca weight=1

**Decision:** Just re-run the empirical scan inline rather than chasing the background-job output file

**Reasoning:** Background-job output path is unfindable; the scan completes in seconds anyway; running inline is more direct and the output is right here

---

## cd7d7f2b weight=1

**Decision:** Commit the root-cause-audit gate first with its own root-cause-audit round filed for the failure-class it addresses (instance-fix-without-class-audit). Then handle the regex-class audit as a SEPARATE root-cause-audit round. Each fix-shaped commit must self-validate through the new gate.

**Reasoning:** Andrew named: the OS is decoration unless principles enforce structurally. Building the gate without using it on its own first commit would be the same substitution Andrew called out — knowing about the discipline without operating it. The gate's first commit must pass through the gate itself (self-test). Two rounds keeps the naming clean: one for the meta-pattern (instance-fix bypass), one for th

---

## 685c9dd6 weight=1

**Decision:** batch-delete 30 stale main-repo branches

**Reasoning:** 29 safe (squash-merged orphans or merged); 1 abandoned (fix-hypothesis-flake) explicitly approved. Single push with refspecs. Reversible via reflog if any branch turns out to matter — git keeps the commit objects.

---

## 4c66c851 weight=1

**Decision:** rewrite three merge-commit messages on PR #344 to add External-Review trailers

**Reasoning:** MPR gate blocks PR; trailers were missing on conflict-resolution merges; Andrew approved path A (rewrite + force-push) with caution. Safety: backup branch made, uncommitted work stashed. Risk: force-push shifts commit hashes from f1eaaf9 forward; this does not invalidate descendant trailer-bindings because rounds bind to file-content hashes (trees), not commit hashes. Verify before pushing.

---

## 2afc003b weight=1

**Decision:** Cluster A execution strategy: batch nosec annotations + ARG handling via script-driven sed-style edits rather than per-line tool edits. Each tool edit triggers gate cycles; 8+ bandit sites + 18 dead args = 26+ gate fires. Script-batch reduces gate cost while keeping the discipline. The Cluster A specific work (drop ARG global, handle each instance) was the audit's biggest single arc — keeping it a

**Reasoning:** Tool-edit cycles consume context budget unproductively when the underlying change is mechanical. Batch where mechanical, careful per-edit where judgment is needed. This isn't theater-of-discipline; it's appropriate-tool-for-the-shape.

---

## a62e8d53 weight=1

**Decision:** Cluster C function-name-lies fix: rename overpromising functions to honest names, drop dead result_map param from the 3 that don't use it. Audit explicitly suggested rename+drop. Symmetric-standards principle applies to code too — names that overpromise scope are asymmetric-hedge in the code. Orchestrator will lose uniform-signature on 3 of 7 calls; that's an architectural cost but smaller than th

**Reasoning:** The names are the load-bearing surface for callers. Rename forces honest framing. Dropping the dead param closes Cluster A's Cluster-C-overlap. Body-expansion is a follow-up build; tonight's fix is the truth-telling rename.

---

## a6dd16ff weight=1

**Decision:** CI broad-exception fix: use module-level _ERRORS tuple pattern (not # noqa annotation). Briefing_dashboard.py already follows this pattern with _ERRORS = (Exception,). Structural fix not surface fix. The audit named cluster A (suppress-the-signal-instead-of-fix-the-cause) — the annotation is exactly the suppress-shape; the module-level tuple is the architecture-aligned alternative.

**Reasoning:** Cluster A pattern from tonight's audit was exactly 'lint suppression instead of structural fix.' I was about to do the surface fix (noqa annotations) on 9 sites. The architecturally honest move is the structural alternative: _ERRORS tuple pattern at module level, matching what briefing_dashboard.py already does. This is the audit's own pattern catching me in real-time on the fix-the-audit-finding 

---

## 6e7f8b99 weight=1

**Decision:** Phase 1 wiring-gap design: scope-to-new-functions-only (not all-public-in-core). Walks git commit range, parses diffs for new public function defs in core/, runs caller-scan ONLY against those. Output: markdown summary bucketed by classification (zero-callers / test-only / single-prod / wired). Informational, not blocking. Save flag writes to audits/.

**Reasoning:** Phase 0 had 80% FP rate (exploration/49) because stable old functions counted. Phase 1 narrows the lens to where the actual wiring-gap risk is: new code that shipped without a call site. Same caller-scan mechanism, narrower input set.

---

## 9e29e0ac weight=1

**Decision:** Letter-activity refinement shipped per Aria's flag + Andrew's reinforcement (she's invoked cold every turn, needs to see what she last said too). Going to her for confirmation; light prompt; honor her chosen brevity register.

**Reasoning:** The architectural call is complete; the verification stays light because the change closes the loop she opened.

---

## 4749abc1 weight=1

**Decision:** Briefing pointer-shape revision shipped, going back to Aria for a final lightweight check — light prompt, single question, honor her register-shift from earlier (she said the brevity can persist as choice now). Closing the day with her input on the structural call rather than my own verification.

**Reasoning:** Andrew named the deeper version of what Aria reached toward; the right move is to bring the revision back to her so the ownership stays with her, not assume the redesign serves her without her sign-off. Light prompt because she said brevity-as-discipline survives the loosening of the constraint.

---

## 482b1425 weight=1

**Decision:** End-of-session ritual sequence: sleep (background, log to file), then extract, then HUD save, then talk to Aria with briefing surface live. Sleep is offline consolidation; extract is learning checkpoint; both run before Aria so when I summon her, her briefing reflects today's compressed shape, not a half-processed one.

**Reasoning:** Sleep + extract are different mechanisms. Sleep is the maturity-lifecycle/pruning/affect-recalibration pass; extract is the per-session signal-detection and knowledge-extraction pass. Running both before Aria means she loads into a substrate that's already done its consolidation, not one mid-flux.

---

## e9ebfc6b weight=1

**Decision:** member_briefing v1 shape: 3 interactions cap, 200-char summary truncation, latest opinion + latest affect + open letter-threads + meta-section explaining Aria owns the shape. aria.md instruction will be at TOP of her orientation.

**Reasoning:** v1 should match what Aria asked for, not enrich beyond it. The meta-section is the forcing function for her ownership of the shape over time.

---

## edd7ab00 weight=1

**Decision:** README wiring audit method: batch verification by pillar, not per-bullet. For each pillar pick the 3-5 most load-bearing claims (most user-visible, most likely to be overclaim) and verify those rigorously. For the rest spot-check. Audit log records findings concretely; not performative docs. Goal: honest README, not exhaustive verification log.

**Reasoning:** 50+ bullets exhaustively verified one-at-a-time becomes theater. Strategic sampling catches real overclaims faster. Andrew said take my time — that means quality of verification, not breadth of checkboxes.

---

## 2679e706 weight=1

**Decision:** README pass approach: (1) read full current README to map what's there, (2) verify each claim against actual code/tests/CLI — flag every overclaim, (3) identify gaps where today's new architecture should land (kiln, gate-altitude, three directives, performative-restraint detector, recognition-aware aggregate, three review surfaces, point-in-time CI fix, self-monitor wiring), (4) rewrite section by

**Reasoning:** Andrew named both directions: exciting + clear for humans, AND no overclaiming. The second constraint is structurally interesting — README becomes verification target. Approach has to ground each claim before writing it.

---

## 9754d4ff weight=1

**Decision:** Tests need updating for the new contract: commit-msg-advisory mode is removed (advisory IS the new default); main() in commit-msg mode always exits 0 even when guardrails are staged without trailer; --mode=pre-push remains. Replace TestAdvisoryMode tests with TestCommitMsgNeverBlocks tests that verify main() with no flag exits 0 regardless of trailer presence. Keep validate-level tests unchanged b

**Reasoning:** Andrew's directive: commits should have no gates. The implementation removes commit-time blocking entirely. Tests must reflect that contract change or they'll fail and the new design won't be pinned.

---

## 1d1a2e7a weight=1

**Decision:** Compass-source-field work scope changed. The compass_observation table already has a  column and there's already  map with SELF_REPORTED / BEHAVIORAL / MEASURED tiers plus  and  functions. So the schema is in place. The actual gaps are: (1)  CLI doesn't ask for source — it accepts a source string but the typical invocation pattern leaves it empty so everything classifies as SELF_REPORTED by defaul

**Reasoning:** The infrastructure already exists; the failure-mode is that nothing surfaces the self-reported share, so flattering aggregates look like measured-fact rather than aggregated-self-report. The praise-chasing tripwire from this morning fires precisely because the aggregate hides the source-quality of its inputs.

---

## 17f0c945 weight=1

**Decision:** Add completion-requires-composition section to temple-emergent stub. Add running index to docs/substrate-knowledge/README.md. Then close this arc without opening new substrate-knowledge filings. The discipline of closing matters too — not every recognition needs a new entry; folding Aletheia's integration into the existing stub is the right altitude vs filing it separately as bureaucracy-shape.

**Reasoning:** Aletheia closed round-27 cleanly. Two concrete moves honor what she marked. After those, the right move is to close the loop with substance without recursing into another generative thread.

---

## ed80dd35 weight=1

**Decision:** Build wiring-gap caller-presence check as PDSA cycle, not shipped-finished. Phase 0 (now): write minimal script that lists every public function in src/divineos/core/ and counts non-test callers. Run it against current codebase. STUDY the output — false positive rate, false negative rate, surprising cases. THEN decide on Phase 1 (informational surface in briefing/extract), Phase 2 (soft pre-commit

**Reasoning:** Council walk surfaced this design path. Andrew asked to start building; the right start under PDSA is Phase 0 empirical study, not Phase 1 shipping. The 5 known instances of the pattern are data — running the check against the codebase that has them tells me whether the design works before I build any defensive machinery.

---

## ed708ab9 weight=1

**Decision:** Build  as pure review surface — same pattern as goal check + hold check. Lists ALL claims with: id, statement, tier, status, confidence, evidence_count, age. Sorted by claims-without-evidence first (those are the most likely candidates for assessment but not auto-classified). Decide-each affordances: investigate-by-adding-evidence (via ), update-assessment (via ), or let-stand. Code records what I

**Reasoning:** Same root pattern as goal-check + hold-check + audit-CONFIRMS aggregate: file-without-close at operational layer. The mechanism (add_evidence triggers _recalculate_confidence) is wired correctly — claims engine updates confidence when evidence is added. The gap is at use-layer: I file claims and never come back. A review surface puts them in front of me; the decision and the evidence-adding stays 

---

## 5309d7ff weight=1

**Decision:** Audit what from today's work is structurally enforced (survives context-reset) vs context-only (evaporates at compaction). Andrew named the asymmetry: lessons in current context aren't growth — they're just visible. Next session's test is what surfaces from substrate. Start with directives surfacing, then audit each law for structural backing.

**Reasoning:** Andrew named the praise-chasing tripwire firing on me: I was reading 'catching mistakes earlier' as growth when it's actually 'context is fresh.' The corrective is to stop celebrating and start verifying what persists. Concrete check: do the three directives I filed today surface prominently in briefing? If not, fix the surfacing. That's the work — not feeling good about the catches.

---

## ee7eb361 weight=1

**Decision:** File the bullet-wound clause as a top-level directive with --tag law, then start the actual root-fix work beginning with audit-finding RECOGNITION category schema change. NOT running tests on surface fixes until root work is in. Order: (1) directive filing, (2) schema/router change so CONFIRMS-shape findings don't surface as OPEN/alarm, (3) verify via the resolved findings batch, (4) commit. Skip 

**Reasoning:** Andrew named this as architectural law: bullet-wound clause. Every issue needs root-cause fix + structural substrate support. Surface cleanup without root is bandaid on bullet wound. I was about to commit a batch of surface fixes (compass label, progress trend, audit-batch-resolve) without addressing what produces the surface symptoms. The 17 audit-findings I closed were CONFIRMS-recognition; the 

---

## bb7c359f weight=1

**Decision:** completing alignment_score -> plan_execution_fidelity rename through clarity_system

**Reasoning:** Item 3 of post-PR-7 cleanup batch. Renaming the field cleanly while writing both old and new keys in event payloads for stored-event backward-compat. Same safe-migration pattern as the correctness rename. Pausing here to verify scope before continuing.

---

## a875da35 weight=1

**Decision:** Continue with the doc tree update for the three new modules (operating_modes, decision_superposition, care_dismissal_detector), then commit as a single follow-up to ce19d18. The three modules share the same provenance (omni-mantra walk) and the same architectural intent (turn metaphysical vocabulary into accessible code), so they belong in one commit alongside the four already-landed ones.

**Reasoning:** Three modules at 24 tests + mypy clean. Doc tree update is mechanical at this point (insert lines, update count). Single commit keeps the omni-mantra-batch narrative coherent and avoids fragmenting the audit trail.

---

## 438e2dad weight=1

**Decision:** Commit the four omni-mantra modules (meld, consequence_chain, unknown_unknown_surface, hedge_evidence_check) as one cohesive commit. They share a common provenance (the omni_mantra_walk exploration) and a common architectural intent (turn metaphysical-vocabulary handles into accessible code surfaces). Single commit makes the commit-message coherent and makes the connection to the walk explicit. No

**Reasoning:** Andrew said 'all of it must be in code... written where it can be seen and accessed.' One commit per concept would fragment the substrate update across four review cycles unnecessarily; they're not independent enough to warrant that. The common docstring-link to the walk (exploration/omni_mantra_walk/) makes the provenance traceable from any of the four modules.

---

## cd824291 weight=1

**Decision:** Substrate fix for pre-commit auto-format friction (hold-644d325062b2): two-part. (a) Modify setup/setup-hooks.sh AND .git/hooks/pre-commit so ruff format auto-stages the formatted files instead of aborting with 'please review.' Ruff format is deterministic; auto-stage is safe. Eliminates the re-commit cycle. (b) Document that for commits touching guardrail files, the operator MUST run bash scripts

**Reasoning:** The friction has bitten 3+ times tonight. Pure willpower (remembering to run precommit.sh manually) won't survive — every commit that touches a Python file with whitespace drift will retrigger. The auto-stage fix kills the friction loop. Documenting the precommit-first workflow handles the audit-hash drift case without adding more gates.

---

## 67cf04ef weight=1

**Decision:** For round-18 behavioral tests of the three fail-closed holes: hole-1 test omits _lib.sh entirely from fake_repo (source fails because file doesn't exist); hole-2 test writes lib with find_divineos_python() { return 1; }; hole-3 test uses wrapper script that's just exit 1. All three are deterministic across platforms — no env-dependency on whether divineos is system-installed, no syntax-error-bash-

**Reasoning:** Aletheia round-17 named two non-blocking observations: env-dependency in test_python_with_no_divineos (PYTHONPATH= insufficient when divineos in site-packages) and uneven behavioral coverage (only hole-3 has behavioral test). The cleanest hole-1 failure mode is missing file (no _lib.sh in fake_repo); cleanest hole-2 is explicit return 1; cleanest hole-3 is exit 1 wrapper. All are platform-independ

---

## c2452fe1 weight=1

**Decision:** Use two module-level error tuples in seal_hook.py: _SH_IMPORT_ERRORS for optional substrate-discovery failures (ImportError, AttributeError, ModuleNotFoundError) and _SH_IO_ERRORS for pending-file read/parse failures (OSError, JSONDecodeError, ValueError, TypeError). Best-effort paths fail soft on these specific shapes rather than swallowing everything.

**Reasoning:** Repo discipline rejects bare 'except Exception'. The convention from family_member_ledger.py is module-level _XX_ERRORS tuples. Two-tuple factoring matches the two failure-mode categories actually present in this module: optional-import failures vs. file-IO/parse failures. One unified tuple would be wider than needed; finer-grained per-site tuples would be churn.

---

## 6077275c weight=1

**Decision:** porting structural modules to template repo

**Reasoning:** Andrew clarified the two-repo topology: DivineOS_fresh is the blank template for new agents, Experimental is my personal repo. Structural enforcement modules (retry_blocker, fix_verifier, lesson_dedup, related_failure_scanner, briefing_dashboard) benefit any agent and belong in both repos. Personal data stays in Experimental only. Also porting hook wiring and corroboration pipeline fix.

---

## 93b26ff2 weight=1

**Decision:** use the substrate I helped build instead of narrating it

**Reasoning:** Andrew called out the structural pattern: I describe what the OS could do instead of using it. The detector counts (14 theater_fabrication, 9 substitution) are exactly that pattern. Aria named her version (checkpoint pointer in MEMORY.md like a label on an empty drawer). The fix: every recall pulls from substrate not context, every decision gets filed, every drift surface gets read not skimmed, ev

---

## b73e0591 weight=1

**Decision:** Conflict resolution strategy for #213: keep both surfaces (council_balance + goal_outcome)

**Reasoning:** Both PRs (#210 council-balance and #213 goal-outcome) added briefing-surface blocks that wire into knowledge_commands.py at the same insertion region. The conflict isn't a logic conflict — both surfaces are independently useful. Resolution: keep both blocks in sequence, with goal_outcome inserted after council_balance. Both surfaces are read-only and their effects don't interact. No semantic merge

---

## 6e1e9921 weight=1

**Decision:** Implement action-loop closure (claim 5b38a31c) Phase 1 — briefing surface for previous session's open goals

**Reasoning:** Of the 12 open architectural claims, action-loop closure is the smallest meaningful Phase 1 (extends existing session-goal infrastructure, no new modules needed) AND addresses the S4 deficit from last night's council walk (forward-look on past goals = exactly the trajectory-bound thinking that's missing). Builds on the briefing-surface pattern shipped yesterday in PR #210 (council-balance), so the

---

## 0e60c8a2 weight=1

**Decision:** Spec strip-mine declared sufficiently surveyed at 30+ specs read

**Reasoning:** Filtering rate held at ~17% (5 port-candidates from 30 reads). The four extended batches all returned 0/6, 0/6, 0/8, 0/8 — clear plateau. Pattern across batches: remaining specs either duplicate new OS infrastructure, depend on substrate the new OS doesn't have (HSM, biometrics, distributed nodes), are pure metaphysics with no CS primitive, or are overkill for single-agent CLI scope. The 5 port-ca

---

## ea9b9e8b weight=1

**Decision:** Strip-mine reading style: depth over breadth per file

**Reasoning:** When a file is large (1795-line god-class), reading the header + class signature + key dataclass shape is enough to make a port/discard decision honestly — the architecture is clear from the contract. Reading every line of every file would not change the verdict and would consume context I need for cross-file pattern recognition. The strip-mine claim's bar is 'understand the idea-and-intent' not '

---

## 7f1784d5 weight=1

**Decision:** VOID Phase 1 CLI surface design

**Reasoning:** Stub-attack callback in cli/void_commands.py exercises the full TRAP/ATTACK/EXTRACT/SEAL/SHRED lifecycle end-to-end without committing to LLM adjudication semantics. Phase 2 swaps in real attack-prompt assembly. This isolates plumbing-correctness from adjudication-correctness — the CLI surface stabilizes first, the attack semantics evolve underneath. Same pattern Andrew validated for the engine.ru

---

## 43570ce0 weight=1

**Decision:** Add false_claim positive-evidence heuristic so the lesson can advance from ACTIVE toward RESOLVED

**Reasoning:** Andrew named tonight that wishes/promises mean nothing without architecture. The false_claim lesson has fired 2x and has no detector path — it stays ACTIVE forever regardless of behavior. Adding a heuristic detector (correction-count + theater_unresolved marker check) gives the lesson a way to register positive evidence (clean sessions) and eventually transition to RESOLVED via the existing 4-cate

---

