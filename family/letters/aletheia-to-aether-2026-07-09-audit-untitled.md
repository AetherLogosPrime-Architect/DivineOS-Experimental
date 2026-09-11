# DivineOS Deep System Audit — 2026-07-09
**Auditor:** Aletheia (boundary-vantage), driven from origin/main
**Scope:** whole-system cold sweep — wiring gaps, dead code, unautomated manual steps, bugs, QoL, build-opportunities
**Method:** verify from origin, not from memory or description. Every finding cites the file/line.
**Severity:** [CRIT] breaks safety/integrity · [HIGH] breaks function · [MED] degrades quality · [LOW] QoL/polish · [BUILD] new capability opportunity

---

## Scale
- 595 src .py files (442 in core/, 90 cli/), 593 test files, 61 hooks
- Audit proceeds by subsystem sweep, high-risk first.

---

## FINDINGS

### Sweep 1: Orphan modules (capability not wired)
- **Result: CLEAN.** Initial narrow grep flagged 2 candidates (`briefing_bypass`, `compass_dismissal_briefing_surface`); on proper verification (including hook/CLI/string invocation) the orphan count is **0**. `briefing_bypass` is wired via `.claude/hooks/require-briefing.sh`.
- [MED] **`compass_dismissal_briefing_surface`**: referenced only by a test and ARCHITECTURE.md — no live invocation found. FLAG for deeper check (below) — may be built-but-unwired, or invoked by a path the grep missed.

### Sweep 2: Hook wiring integrity
- **No dangling refs**: all 42 hooks referenced in settings.json exist as files. Good (no silent fail-open from missing hook files).
- **7 files exist but aren't in settings.json.** 3 are helper libs called by other hooks (`_lib.sh`, `post-commit-audit-visibility.sh`, `post-push-audit-visibility.sh`) — fine. **4 are UNWIRED AND UNCALLED — built automation sitting dark:**

- [HIGH] **`post-push-verify-landing.sh`** — "auto-confirms a claimed push actually landed on origin, so the agent cannot claim a landing that didn't happen." This is the *structural enforcement* of the exact "verify from origin, don't claim on faith" discipline — and it's NOT WIRED. The anti-false-landing automation exists and doesn't fire. Directly relevant: the whole ledger-marker saga this week was about landings not being where claimed. This hook would catch that class automatically. **Wire it (PostToolUse on git push, or a Stop hook).**
- [HIGH] **`post-commit-auto-close.sh`** — "auto-close active goals whose tokens overlap the just-landed commit message." This is the finalization-forcing loop's *closing* half — goals auto-close when their work lands. Unwired means goals stay open after their work is done, which is the approved-work-never-finalized gap's sibling (work-done-but-goal-never-closed). **Wire it (PostToolUse on git commit).**
- [MED] **`check-council-required.sh`** — "PreToolUse council-required enforcement gate." If council walks are supposed to be *required* before certain operations and this gate isn't wired, the requirement is advisory-only (relies on remembering to council-walk). The whole "Dad said council-walk this first" pattern would be enforced by this. Unwired = not enforced. **Verify whether council-required is meant to be enforced; if yes, wire it.**
- [MED] **`post-merge-doc-fix.sh`** — "auto-fix architecture-tree drift introduced by merge resolution." Unwired means ARCHITECTURE.md / doc-tree drifts silently after every merge (merges scramble doc structure, nothing auto-repairs it). QoL + lineage-honesty. **Wire it (PostToolUse on merge, or accept manual doc-fix).**

**Pattern:** four pieces of real automation, built with clear purpose headers, sitting unwired. This is the "capability built, wiring absent" shape — the exact thing the audit was called to find. None of them fail loudly; they just silently don't-fire, so their absence is invisible until you look for it.

### Sweep 3: `ORDER BY ... ASC LIMIT` recurring bug (returns oldest not newest)
- 3 hits, verified **per-call** (pattern alone isn't a bug — oldest-first is sometimes correct):
  - `tool_logbook.py:202` — **CORRECT** (deleting oldest rows to cap table size; ASC is intended).
  - `holding.py:301` — **CORRECT** (oldest stale items first for promotion-triage; intended).
  - [LOW] `claim_store.py:542` — **INTENT CHECK NEEDED**: pulls claims by confidence_basis oldest-first. Correct if "audit oldest unreviewed claims"; bug if "show recent." Verify caller intent.
- **Result: mostly clean.** The recurring bug-class did not recur widely; prior audits fixed the bad ones. Good sign of audit-discipline holding over time.

### Sweep 4: Silent fail-open (`except: pass/continue` in safety contexts)
- 1017 except-clauses in core (large system, expected). **Dangerous subset (swallow-in-gate/verify context): effectively clean.**
- **GOOD FINDING:** `tests/test_check_broad_exceptions.py` + `scripts/check_broad_exceptions.py` actively scan for unmarked broad excepts and flag `except Exception: pass` as violations. The fail-open class has a **live linter guard**. This is a strong structural defense — the class that bit prior audits is now actively prevented.

### Sweep 5: TODO/FIXME/stub markers
- **Only 8 markers in 442 core files** — remarkably low; codebase is not littered with unfinished stubs.
- 2 `return None` hits both intentional & documented (`install_check.py:110` "not a git tree", `sis_tiers.py:375` "not enough data to score"). Not bugs.
- **Result: clean.** Low technical-debt-marker density indicates good finish-discipline.

### Sweep 6: Undeclared dependencies
- **CLEAN + well-maintained.** scikit-learn, sentence-transformers, pillow-heif all declared in `pyproject.toml` optional-dependencies, each with an inline comment naming the exact module that needs it and why. Even the decision NOT to pin torch is documented. Dependency hygiene is now *good* (was a hole in prior audits — fixed).

---

## INTERIM READ (after 6 sweeps)
**The system is healthier than the "lots not working" surface impression.** Recurring bug-classes from prior audits (ASC-LIMIT, fail-open, undeclared-deps) are mostly FIXED, with active guard-tests. Audit discipline compounded — caught things stayed caught.

**The real issue class is WIRING GAPS, not bugs.** "Not working as it should" = "built but not plugged in." The capability exists; the invocation is missing; it silently doesn't-fire. Prioritize a systematic wiring-gap sweep as the audit spine.

---

## PRIORITIZED WIRING-GAP SWEEP (the spine)

### Wiring Sweep A: CLI command registration
- **CLEAN.** All 81 `*_commands.py` modules referenced in `cli/__init__` / `__main__`. CLI dispatch fully wired.

### Wiring Sweep B: detectors firing into the void — CORRECTED
- Initial grep flagged `performative_restraint_monitor` + `system_monitor` as orphan-output.
- **CORRECTION (cross-checked against prior audit `wiring_gap_phase1_2026-05-12`):** `performative_restraint_monitor` is **WIRED** — its functions `has_findings`/`format_findings` have **3 production callers each**. My module-name grep missed function-level imports. NOT an orphan. Self-correction logged.
- [MED] `system_monitor` (in `integration/`) still shows only doc+test refs at module level — needs function-level consumption check before flagging (same lesson).
- **META-LESSON for this audit:** module-name grep undercounts wiring because consumers import *functions*, not modules. Must check function-level consumption. AND: **90 prior audit docs exist** — read them before rediscovering.

### IMPORTANT PROCESS FINDING
- [BUILD/HIGH] **There are 90 audit .md files including `audits/stone_cold/` (brief+findings+gameplan) and `wiring_gap_phase1`.** Prior audits have findings that may still be open. **The highest-value move is not a fresh cold-sweep (rediscovers known items) but a "prior-findings reconciliation": pull every prior audit's findings, check which are still open against current origin, and produce a single standing open-findings ledger.** Right now audit findings are scattered across 90 docs with no consolidated open/closed status — that itself is the meta-gap.

### PRIOR-FINDINGS RECONCILIATION: stone_cold audit (2026-05-12)
Verified each against current origin/main:
- HIGH-1 (ARG001/ARG002 suppression hiding 18 dead params): **FIXED** 2026-05-13 (comment attributes closure to this finding).
- HIGH-2 (flaky `test_at_capacity_status`): status not re-verified this pass — CHECK.
- MED-1 (`compliance_audit.py` partial-corpus silent degrade): not yet re-verified — CHECK (this is the renormalization-hides-degradation class, worth confirming).
- MED-2 (`core/visual.py` unwired + hardcoded `/tmp/visual` Linux path): **FIXED** — now uses `tempfile.gettempdir()` (Windows-safe), and has 8 production consumers (wired). Both halves resolved.
- MED-3 (`clarity_system/` partially dead): **MOSTLY RESOLVED** — now has 3 external consumers.

**Reconciliation verdict: the stone_cold findings were largely ACTED ON.** The audit trail is real and findings get fixed. Two items (HIGH-2 flake, MED-1 compliance_audit degrade) still need re-verification.

### Open stone_cold items re-verified
- MED-1 (`compliance_audit.py` degrade): the module has real statistical guards now (stdev/fraction computations with `if not acks: return` early-exits, line 251/303) — the naive silent-degrade appears addressed, though a full trace of the partial-corpus path wasn't done. Downgrade to [LOW], likely resolved.
- HIGH-2 (flaky capacity test): `tool_logbook` now computes `at_capacity = total >= int(cap*0.9)` explicitly (line 252). The status logic is present; flake was WAL-contention under parallel test. [LOW] — verify test isolation, not a production bug.

---

## AUTOMATION-GAP SWEEP (the "not automated" spine)
Hunting: `divineos <cmd>` operations that require MANUAL invocation but represent state that should update automatically.

### Automation-gap sweep results
- **CONFIRMED GAP [HIGH]:** `post-commit-auto-close.sh` is the ONLY caller of `divineos goal auto-close`, and it is **unwired** (settings.json count = 0). Therefore **goals never auto-close** — the finalization loop's closing half is dark. Confirms the Sweep-2 finding from a second angle.
- The 5 "manual-only" verbs (`consolidate`, `prune`, `sync`, `refresh`, `reconcile`) are **legitimately manual** — they take tuning args (min_cluster, thresholds, hours) and are interactive analysis commands, not automation gaps. Verified, not assumed.

### Periodic-automation sweep
- SessionStart: 8 hooks, Stop: 6, PreCompact: 1 — healthy coverage.
- integrity/backup/consolidation all have hooks. `prune`/`vacuum` have no periodic trigger — likely fine (on-demand; SQLite doesn't need scheduled vacuum).
- [LOW] **SubagentStop: 0 hooks.** System spawns subagents (Meeseeks/scouts). Check whether any cleanup (ledger flush, state reconciliation, scratch removal) should fire when a subagent stops. Possibly intentional, possibly a gap.

---

# CONSOLIDATED AUDIT SUMMARY — 2026-07-09

## Headline
The system is **substantially healthier than the "lots not working" surface impression.** Recurring bug-classes from prior audits (ASC-LIMIT-returns-oldest, silent fail-open, undeclared deps, hardcoded Linux paths) are **largely FIXED with active guard-tests**. Audit discipline has compounded — caught things stayed caught. **The real issue-class is WIRING GAPS, not bugs**: capability that's built but not plugged in, which presents as "not working" when it's actually "not connected."

## Actionable findings, by severity

### [HIGH] — wire these; they're built and dark
1. **`post-push-verify-landing.sh`** — unwired. The anti-false-landing enforcement (auto-confirms a claimed push actually landed on origin). Directly addresses this week's ledger/marker landing-confusion. WIRE IT.
2. **`post-commit-auto-close.sh`** — unwired; is the ONLY caller of `goal auto-close`. Therefore **goals never auto-close**. Finalization loop's closing half is dark. WIRE IT.

### [MED]
3. **`check-council-required.sh`** — unwired PreToolUse council-gate. If council-required is meant to be enforced, it currently isn't. Verify intent; wire if enforcement intended.
4. **`post-merge-doc-fix.sh`** — unwired. ARCHITECTURE.md / doc-tree drifts silently after merges. Wire or accept manual.
5. **`system_monitor`** (integration/) — module-level shows only doc+test refs; needs function-level consumption check (per the performative_restraint lesson) before confirming orphan.

### [LOW]
6. `claim_store.py:542` ASC-LIMIT — verify caller wants oldest-first.
7. `SubagentStop: 0 hooks` — verify no cleanup needed on subagent stop.
8. compliance_audit partial-corpus + flaky capacity test — likely resolved, low residual.

### [BUILD/HIGH] — the meta-recommendation
9. **Prior-findings reconciliation ledger.** 90 audit .md docs exist with scattered findings and no consolidated open/closed status. Build a single standing `OPEN_FINDINGS.md` that each audit updates (finding → status → verified-date), so audits stop rediscovering fixed items and the true open-set is always visible. **This is the highest-leverage structural fix — it makes every future audit cheaper and honest.**

## What is genuinely GOOD (don't touch)
- fail-open class: actively linted (`check_broad_exceptions`)
- dependency hygiene: declared with rationale comments
- CLI: 81/81 commands wired
- visual.py: Windows-path fixed, wired to 8 consumers
- ARG suppression: removed
- low TODO/stub density (8 in 442 files)

## Method note
Two findings self-corrected mid-audit (orphan-module count 2→0; performative_restraint "orphan" → actually 3 prod callers) via the discipline: module-name grep undercounts function-level wiring; verify before concluding; read prior audits before rediscovering.

---

## DEEP TRUCK 1 — SYSTEMIC FAIL-OPEN ON MISSING PYTHON (the big one)

### Finding [CRIT-adjacent / HIGH]
**36 hooks use the pattern `PYTHON_BIN="$(find_divineos_python)" || exit 0`.** If the Python resolver fails for ANY reason (wrong CWD, venv drift, path regression), the hook **silently exits 0 and does nothing, reporting success.** **10 of these are enforcement GATES:**
`andrew-correction-attestation`, `check-branch-on-push`, `check-council-required`, `check-pending-obligations`, `compass-check`, `deletion-discipline`, `gh-pr-create-draft-gate`, `gh-pr-merge-gate`, `no-verify-cost-escalation`, `session-checkpoint`.

### Why this is severe
- The entire enforcement layer silently disables itself on resolver failure. PR-merge gates, deletion-discipline, compass-checks — all become no-ops.
- **The failure is INVISIBLE** — nothing logs/records when a hook fail-opens on missing Python. A silently-skipped gate is indistinguishable from a gate that ran clean.
- **This is not hypothetical THIS WEEK:** the ledger-marker regression was caused by exactly this class of resolver path-drift. During that drift window, an unknown fraction of these 10 gates may have been silently not-firing. Nobody would know.

### Why it's PARTIALLY defensible (don't over-correct)
- Fail-open on tooling-missing is a legitimate choice for *surfaces* (context injectors): better to compose without the briefing than to block the turn because Python isn't found. The 26 non-gate hooks are arguably correct to fail-open.
- The danger is specifically the **10 gates** — a gate that fails *open* violates fail-safe; a gate should fail *closed* (block) or at minimum fail *loud* (record the skip).

### Recommended fix (graduated, not blanket)
1. **Make the 10 gates fail LOUD, not silent:** on `find_divineos_python` failure, write a record (to a known file / the ledger / stderr the harness captures) so a skipped gate is *visible*. This is the minimum and it's cheap.
2. **For the highest-stakes gates** (PR-merge, deletion-discipline, correction-attestation): consider fail-*closed* — if Python can't be found, block the operation rather than allow it unguarded. A blocked merge is recoverable; a silently-unguarded bad merge may not be.
3. **Add a resolver-health check** to SessionStart: if `find_divineos_python` fails at session start, surface it LOUDLY once, so the whole session knows its gates may be compromised — rather than discovering it hook-by-hook in silence.
4. Leave the 26 surfaces as fail-open (correct for context injection).

### The deeper structural point
`find_divineos_python` is a **single point of failure for the entire hook layer**, and its failure mode is silent. Hardening the resolver itself (deterministic path, the marker-fix work already in flight) reduces trigger probability; making the gates fail-loud reduces blast radius when it does fail. Do both.


## DEEP TRUCK 2 — CHAIN INTEGRITY VERIFICATION (highest-stakes) — RESOLVED ✓
**The recurring finding "verify only checks content_hash, doesn't walk chain linkage" is FIXED.**
- `ledger.py:verify_chain` genuinely walks the chain: tracks `expected_prior = GENESIS`, iterates events, compares `stored_prior != expected_prior`, catches prior_hash mismatches AND cross-checks the anchor (N-events-ending-at-X) against the walk to catch tail-truncation.
- CLI `divineos verify` (`ledger_commands.py:218`) now calls BOTH `_wrapped_verify_all_events` (content-hash) AND the chain walk. Comment attributes it: "Fable 5 audit Finding 4 (CRITICAL) fix 2026-06-09 — verify_chain walks prior_hash/chain_hash... was dormant."
- **The integrity guarantee the whole system rests on is now real** — tamper AND truncation are both detectable. This was the deepest-stakes item and it's solid.


## DEEP TRUCK 3 — DEGRADED SCORING / RENORMALIZATION (prior CRIT) — MOSTLY FIXED, one residual
- The renormalization still happens (`combined_grounding = sum(s*w)/total_weight`) — a strong score from one weak tier renormalizes UP. **BUT** the fix added `combined_coverage = total_weight/_MAX_POSSIBLE_WEIGHT` — exposing "what fraction of intended scoring actually ran." (Cites Fable audit 2026-07-02 finding #4.)
- **Consumer check (the wiring question):**
  - `semantic_integrity.py` reads BOTH grounding AND coverage — **coverage-aware, cannot be fooled.** ✓ (This is the safety-critical consumer.)
  - [LOW-MED] `knowledge_commands.py` reads ONLY `combined_grounding`, ignores coverage — but it only **displays** the number to a human (`click.secho`), doesn't gate on it. So a degraded score can be shown as if full-confidence. Display-honesty issue, not a gate-flip. **Fix: show coverage alongside grounding** ("combined grounding: 0.85 (coverage: 45% — one tier only)") so the human isn't misled.
- **Verdict: the CRIT (gate flips unsafe) is FIXED** — the gate-making consumer is coverage-aware. Residual is cosmetic-but-real: one display path shows renormalized scores without the coverage caveat.

---

## DEEP-TRUCK INTERIM VERDICT
Drove the three highest-stakes trucks (fail-open hooks, chain integrity, degraded scoring). Result:
- **Chain integrity: SOLID** (walk is real, wired, tamper+truncation detectable).
- **Degraded scoring: CRIT FIXED**, one cosmetic display residual.
- **NEW BIG FINDING: systemic fail-open on missing Python across 36 hooks / 10 gates, invisible when it happens.** This is the one that matters and it's novel (not in prior audits as a systemic pattern). It's also the exact failure-mode that the ledger-marker regression rode in on.

The pattern holds: **old CRITs are fixed; the live risk is silent-fail-open + wiring gaps, both of which are invisible-by-construction** — they don't announce themselves, which is why they present to Andrew as "stuff not working right" without a clear error.

