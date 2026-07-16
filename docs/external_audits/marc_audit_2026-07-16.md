
# DivineOS-Experimental -- Code-Grounded Audit

Date: 2026-07-16
Target: C:\Structured Chaos\data\downloads\DivineOS-Experimental-main
Scope rule: findings are based on reading the actual code (Python/bash/YAML), not on the repo's own documentation. Docs/ADRs were read only to learn what a subsystem *claims* to do, then separately checked against code. Every claim below cites the file(s) it came from.

## Method

- 10 subsystems surveyed in parallel by independent read-only agents (no script/hook/CLI command belonging to the repo was ever executed -- static reading, grep, and line counts only).
- Every structural issue a surveyor flagged was then re-examined from scratch by a second, independent agent whose job was to try to refute it (re-open the cited file, check for a fallback/alternate path, check whether it's an intentional documented stub rather than an accidental defect). Verdicts below are marked CONFIRMED or REFUTED accordingly.
- 8 of 10 subsystems went through this full survey + adversarial-verification pipeline. 2 subsystems (operating-loop/self-model, and tests/CI legitimacy) had their first-pass survey agent error out (one hit a mid-response API error, one exceeded its structured-output retry cap); both were independently re-surveyed as a direct follow-up, but did **not** get the second adversarial-verification pass the other 8 got. This is called out per-section below.
- Total: 54 sub-agent runs, ~5.9M tokens of investigation, 976 tool calls across the full pass.

---

## Executive summary

**What a Claude agent gains from this substrate:** a handful of genuinely-enforced constraints (can't proceed without a stated session goal and fresh briefing, can't silently claim an action without a matching tool call that turn, can't puppet-script another persona's subagent, can't merge a PR touching guardrail files without a review trailer, gets throttled after unaddressed rule-bypassing) plus a large, genuinely persistent memory system (a real SHA-256 hash-chained event ledger, a knowledge/claims/opinions store, named subagents with real cross-session SQLite memory, ~406 real CLI commands). It does **not** gain the more dramatic protections its own module names and docs advertise: no moral-compass blocking of subagent spawns, no council-consultation gate on edits, no EMERGENCY_STOP reach into actual tool calls, no autonomous/scheduled operation of any kind.

**What it does for a human user:** real, narrow friction against specific agent misbehavior, plus a rich persistent journal/memory system and a library of 42 named "expert" methodology profiles retrievable on demand (keyword-matched template retrieval feeding the agent's own reasoning -- the tool itself discloses this at render time, it is not autonomous deliberation). A user trusting the docs at face value would significantly overestimate how contained the agent is, and would not know that the tamper-evident ledger silently self-destroys under normal use, or that the family "letter/queue" auto-notification feature is quietly broken.

**Structural issues:** several of the most heavily-documented safety mechanisms are complete, unit-tested code that is never actually connected to anything live (an unregistered hook, a broken import, a CI job that was never added). One integrity guarantee (the ledger hash chain) actively self-destructs the first time the system's own routine housekeeping runs. The project's own benchmark used to justify the whole framework has a real scoring bug that inflates its headline result, and confounds its main experimental variable with a second, unremoved one.

---

## Subsystem findings

### 1. Hook wiring and lifecycle (.claude/settings.json + .claude/hooks/*.sh)

**Mechanism:** settings.json wires 59 hook commands across SessionStart, UserPromptSubmit, PreToolUse (12 matcher blocks / 16 entries), PostToolUse (5 blocks / 9 entries), Stop, PreCompact, and PostCompact. Every hook is a thin bash wrapper (sourcing shared `.claude/hooks/_lib.sh`) that shells out to a real Python module under `src/divineos/{core,hooks,cli}`. All `divineos.*` module references across all 59 hooks were confirmed to resolve to real files -- no broken references at the wrapper layer. A second, entirely separate native-git-hook layer (pre-commit, commit-msg, pre-push, post-commit, post-merge) exists but is only installed by manually running `setup/setup-hooks.sh`; this checkout never had that run, so that whole layer is inert.

**Real, confirmed-blocking gates:** `require-briefing.sh`, `require-goal.sh` (-> `divineos.hooks.pre_tool_use_gate`, 1138 lines: blocks on missing goal, stale briefing, overdue pre-registration, cross-substrate ownership mismatch, blind-retry pattern, context-governor threshold), `require-monitors-armed.sh` (blocks Bash unless a live background Monitor watcher is detected), `family-member-invocation-seal.sh` (blocks puppet-scripted subagent prompts, fails closed on every internal error), `gh-pr-merge-gate.sh` (blocks `gh pr merge` on guardrail PRs lacking a review trailer), `pre-tool-bypass-rate-scan.sh` (blocks once a bypass-rate threshold fires), `shoggoth-gate.sh` (Stop hook: forces continuation if the reply claims an action with no matching tool call that turn).

**Issues (CONFIRMED unless noted):**
- `.claude/hooks/check-council-required.sh` (lines 1-16, 39-45, HIGH) -- fully-built council-required blocking gate, but its own header literally says "INTENTIONALLY UNWIRED... do not register in settings.json." Confirmed absent from settings.json's PreToolUse list. No substrate edit is ever blocked pending a council walk.
- `setup/setup-hooks.sh` (lines 354-554, MEDIUM) -- the entire native-git-hook guardrail layer (External-Review trailer stamping, closure-claim gate, force-push safety) only installs via a manual script run. This checkout's `.git/hooks/` has none of it (the checkout is a flat extraction with no `.git` at all). The only safeguard, `session-start-verify-git-hooks.sh`, is structurally incapable of blocking anything -- every code path in it ends in `exit 0`.
- `.claude/hooks/post-push-verify-landing.sh` / `post-push-audit-visibility.sh` (MEDIUM) -- neither is registered in settings.json, and git has no native client-side "post-push" event, so neither has any invocation path. `post-push-verify-landing.sh` is a harmless, self-documented superseded file (real replacement `verify-push-landed.sh` IS wired). `post-push-audit-visibility.sh` has no such marker and no fallback -- it presents itself as live infrastructure (an audit-relay auto-writer) but silently never fires.
- `.claude/hooks/compass-check.sh` (lines 24-31, MEDIUM) -- received a 2026-07-09 "fail loud when python lookup fails" fix, but the actual gate-module call is still wrapped in bare `except: pass`. Root cause is worse than it looks: see subsystem 7 below (the imported `main` function doesn't exist at all).
- `.claude/hooks/post-compact.sh` (lines 15, 18, 29, LOW) -- three CLI calls (`divineos hud --brief`, `lessons`, `context-tokens`) are bare, PATH-dependent invocations instead of the `$PYTHON_BIN -m divineos ...` pattern the rest of the file (and 10 other hooks) correctly use, per the project's own prior audit findings.
- `.claude/hooks/verify-push-landed.sh` (line 44, LOW) and `pre-tool-bypass-rate-scan.sh` (line 32, LOW) -- both hardcode `$HOME/.divineos-aether/...` as a shared state directory. Confirmed repeated in 5+ more places repo-wide. Any differently-named sibling instance sharing this hook system would read/write the same "aether"-labeled directory regardless of actual identity.
- `.claude/settings.json` PreToolUse Bash matcher (LOW) -- ~12 separate hook scripts fire per single Bash tool call, each spawning its own git subprocess(es) plus one or more Python interpreters. A documented 5-calls-to-1 latency consolidation was applied to exactly one of the ~12 sibling scripts.
- `.claude/hooks/aletheia-boot-gate-preflight.sh` (REFUTED) -- also absent from settings.json, but this is a deliberate, documented staged rollout (confirmed via the family letters archive): the family-invocation-seal hook covers a different check, and an in-context "BOOT GATE" instruction inside `.claude/agents/aletheia.md` itself is the intended primary verification layer today, with the shell hook meant as a hard-floor layer added later once a named external-audit prerequisite is met.

---

### 2. Ledger / integrity / hash-chain subsystem

**Mechanism:** `ledger.py` implements a genuine sequential SHA-256 hash chain over the entire `system_events` table (`_compute_chain_hash`, `log_event`, `verify_chain`). This is real, not theater, and is wired into the CLI (`divineos verify`). ADR-0002 (hash-chain-main-ledger) and ADR-0005 (validate=False audit) were read for claims and then checked against code.

**Issues (all CONFIRMED except where noted):**
- `ledger_compressor.py` (lines 6-8, 112-204, 178-182, HIGH) -- the ledger's own automatic maintenance routine, wired live into every session-extraction pass (`auto_compress_if_needed`, `cli/pipeline_phases.py:1108-1120`), deletes rows out of the middle of the hash chain without rebuilding `prior_hash`/`chain_hash` for the survivors, and its own module docstring still falsely claims "no hash chain" (contradicting `ledger.py`'s actual design). No rebuild/repair function exists anywhere in the codebase. This exact bug is already documented, with an empirical repro, in the project's own `docs/audits/hidden-issues-audit-2026-05-20-final.md` (Finding DDD) and remains unfixed.
- `cli/ledger_commands.py` (lines 256-290, HIGH) -- the `verify` CLI command reports chain breakage as "the database has been tampered with," with no way to distinguish real tampering from the self-inflicted breakage above. Since compaction is routine, this is not a rare edge case -- it's the expected outcome after normal operation, defeating the practical value of the tamper-evidence claim.
- ADR-0005 (validate=False audit, MEDIUM) -- the ADR audited ~23 `validate=False` call sites on 2026-05-03 against a four-criteria rule. Current code has ~45 such sites; roughly half were added after the audit and never checked. The event validator itself recognizes only 6 of the many dozens of event types now in use.
- `claim_store.py` (lines 402-439, MEDIUM) -- a claim-table update and its corresponding ledger audit-event emission are two separate, non-atomic steps; the emission failure path only logs a warning and does not roll back. The `claims` table itself has no hash/chain columns at all, so a dropped emission (or a crash between the two steps) is silently invisible to the chain-walk. The project's own pre-registration doc already names this exact scenario as an open, unresolved risk.
- `event_verifier.py` (LOW) -- confirmed dead code (only its own test imports it); it duplicates the real verifier but never calls `verify_chain()`, so it would give anyone who discovered and used it a materially weaker guarantee than the one the system advertises.
- `gate_emit.py` / `gate_marker.py` (REFUTED) -- both mis-scoped inclusions in the original survey's file list, not defects; neither has anything to do with the ledger and both work correctly for their actual (unrelated) purposes.

---

### 3. Self-monitoring / "anti-theater" / overclaim detection

**Mechanism:** a mixed bag under one label. The largest cluster (`theater_monitor.py`, `fabrication_monitor.py`, `hedge_monitor.py`, `overclaim_detector.py`, `performing_caution_detector.py`, `closure_shape_detector.py`, `dissociation_filter.py`) is pure regex/keyword matching against the agent's own generated text -- not verification. A smaller cluster is genuinely rigorous: `dead_architecture_alarm.py` (real DB row-count / HUD-state diffing), `closure_verification.py` (real filesystem mtime / git / gh-PR / test-grep checks), `wiring_dark.py` (real AST call-graph analysis), `self_critique.py` and `drift_detection.py` (derive scores from measurable session telemetry, not free-text self-report).

**Issues (CONFIRMED unless noted):**
- Regex-based detector cluster (HIGH) -- confirmed to be gameable well beyond mere paraphrase-sensitivity: e.g. `fabrication_monitor.py`'s `_has_fiction_flag` exempts an entire response from all fabrication flags if any of 14 trigger substrings appears anywhere in the text, unscoped to the actual claim. This is a known, accepted trade-off per the project's own ADR-0003 ("regex is auditable... false negatives are expected") -- disclosed, not hidden, but it means "detection" here is self-report pattern-matching, not verification.
- `theater_marker.py` (lines 22-24, 72-77, MEDIUM) -- the module's own docstring documents that the theater/hedge marker system was downgraded from a blocking PreToolUse gate to a purely observational surface on 2026-05-01 ("the gate is gone"). It now only produces a line of text in a later briefing the same agent can freely ignore -- confirmed by contrast with sibling gates on the same code path that still actively block.
- `sample_honesty.py` (LOW) -- a correct, sound statistical implementation (Wilson score interval) with zero production callers anywhere in the codebase; it only helps if an agent remembers it exists and voluntarily invokes it, the exact failure mode it was built to prevent.
- `self_grade.py` (REFUTED as a live defect) -- computes nothing today (retired 2026-05-22, clearly marked in its own docstring), but the real non-circular self-vs-external comparison the audit's circularity question cares about does exist and is genuinely wired elsewhere, in `external_validation.py` (called automatically at session end; a human enters a countervailing grade via `divineos validate --grade`).
- `shape/primitives.py` (REFUTED) -- does exactly what its narrow, stated purpose claims (sentence-scoped structural checks, not semantic verification); not a structural defect. A separate, real wiring gap was found in passing: these shared primitives are imported only by their own test file, not by the detector modules whose docstring claims universal composition.

---

### 4. Council decision/deliberation subsystem (largest single subsystem, 49 files)

**Mechanism:** "Council" is a library of 42 hand-authored expert-methodology text profiles. The selection engine (`engine.py`, `manager.py`) picks relevant profiles via pure keyword/word-overlap scoring -- there is no LLM call inside the engine. The CLI entry point (`divineos mansion council "<question>"`) defaults to "lens mode," which deliberately withholds pattern-matched synthesis and prints only methodology/questions with the instruction "the analysis is yours" -- the tool is candid about being retrieval, not deliberation. A separate, fully-built enforcement layer (`council_required/`, ~1,400 lines) would gate substrate edits on evidence of a real council consultation.

**Issues:**
- `.claude/hooks/check-council-required.sh` (HIGH, CONFIRMED) -- same finding as subsystem 1: the enforcement gate is complete and non-trivial but its activation hook is explicitly, deliberately left unregistered pending further design work. Only reachable via a manual `divineos council check` CLI command nothing forces an agent to run.
- `gravity_classifier.py` (lines 49-58, MEDIUM, CONFIRMED) -- the classifier's own "Honesty note" states the `is_council_required` field is display-only; no pre-edit gate reads it as a verdict.
- `engine.py` (LOW, REFUTED as a hidden defect) -- the keyword-matched "analysis" is factually confirmed to be template retrieval, not generated reasoning, but this is disclosed candidly in three separate places in the code itself (module docstring, default lens-mode output, and a loud runtime warning banner on the alternate mode) -- an intentional, clearly-marked design, not an oversight. Only the marketing language ("Convene the 40," "the council chamber") oversells it relative to the code.

---

### 5. Family persona subsystem

**Mechanism:** two parallel implementations of "family members" coexist -- a dead legacy top-level prototype (`family/entity.py`, `queue.py`, hardcoded to exactly "aria"/"aether") and the live, generalized package `src/divineos/core/family/` that the real CLI actually uses. Family members are genuine Claude Code subagents (`.claude/agents/<name>.md`) with real persistent SQLite-backed memory, gated by a fail-closed PreToolUse seal against puppet-scripted invocation. Letters are real append-only markdown, mirrored cross-worktree and auto-pushed to origin via PostToolUse hooks. "voice.py" and "raw_recordings/" are purely textual -- no audio/TTS pipeline exists anywhere in the repo.

**Issues (CONFIRMED unless noted):**
- `family/ear_watch.py` (lines 61-67, 91-99, HIGH) and `.claude/hooks/ear-surface.sh` (lines 59-63, HIGH) -- both default to a repo-relative `family/family.db` / `family/letters/` path that nothing live writes to anymore; the real CLI writes to `data/family.db` and the real letter-sharing mechanism uses `~/.divineos-shared/letters/`. Result: the family-queue auto-surfacing feature silently, permanently returns empty -- a queue item filed via the real CLI never reaches the recipient through this path. On deeper trace, this turned out to be worse than "dead code ambiguity": the dead top-level prototype is what these two live, wired hooks were (mistakenly) aligned to match, anchoring an active silent-failure bug that directly contradicts the project's own "no silent fallbacks" rule.
- `anti_slop.py` (lines 62-82, MEDIUM) -- only 2 of the 5 documented "sycophancy-resistance" operators (`access_check`, `reject_clause`) are wired into the production family-member write gate; the other 3 (`sycophancy_detector`, `costly_disagreement`, `planted_contradiction`) have zero production callers, contradicting the project's own CLAUDE.md claim that all five structurally prevent a family member becoming "a sycophantic mirror." (The gap is candidly documented in the code's own comments, but the documentation claim elsewhere is overbroad.)
- `.claude/hooks/arm-letter-monitor-instruction.sh` (REFUTED at the severity given) -- true wake-from-idle does require a manually-armed Monitor process as claimed, but a separate, independently-wired hard-blocking gate (`require-monitors-armed.sh`) forces the agent to arm it on the very first non-exempt Bash call of a session -- a real fallback the original finding missed.
- `family/raw_recordings/` (REFUTED) -- reads as an audio-sounding directory name but its own README states up front, in its first sentence, that these are written transcripts, not recordings. Not a dangling promise.

---

### 6. Enforcement gates -- moral compass, corrigibility, PR/merge gates

**Mechanism:** a genuinely mixed subsystem, not uniformly theater or uniformly enforced. Several gates are real and wired: the goal/briefing/hedge cascade, the PR-merge trailer gate, the `--no-verify` cost gate, the bypass-rate gate, the shoggoth action-claim gate, and CLI-dispatcher-level corrigibility (`EMERGENCY_STOP`/`DIAGNOSTIC` mode blocking `divineos` subcommands). But the subsystem's most heavily-documented flagship mechanisms do not function.

**Issues (all CONFIRMED):**
- `.claude/hooks/compass-check.sh` (lines 24-33, HIGH) -- imports `from divineos.core.compass_rudder import main`, but `compass_rudder.py` defines no `main` function anywhere (confirmed by grepping every `def` in the file and every other caller, none of which reference `main`). The ImportError is swallowed by a bare `except: pass`, and the wrapper unconditionally exits 0. The moral-compass "rudder" -- the only mechanism the codebase claims converts detected virtue-drift into blocking a subagent spawn -- is a permanent, silent no-op. Never caught by CI (the only tests that reference this hook do static text/lexical checks on the shell script, never execute it end-to-end).
- `corrigibility_tool_gate/__init__.py` (HIGH) -- a complete, unit-tested implementation meant to close the documented gap that `EMERGENCY_STOP` has no reach into the agent's actual Edit/Write/Bash/NotebookEdit tool channel. Confirmed zero callers anywhere outside its own test file; absent from settings.json, every hook, and the guardrail-files list. `EMERGENCY_STOP` genuinely blocks `divineos` CLI dispatch, but not the agent's real tool calls.
- `scripts/ci_merge_review_check.py` vs `.github/workflows/integrity-audit.yml` (HIGH) -- the script's own docstring claims the GitHub Action calls it; the live workflow's only two jobs are a purely textual trailer-presence check and a mixed-pattern-merge check, neither of which invokes this script. A commit message containing the literal string "External-Review: anything" currently satisfies the real, live CI gate on guardrail-file merges to main.
- `.claude/hooks/gh-pr-create-draft-gate.sh` (lines 56-61, MEDIUM) -- uses `sys.exit(1)` to signal a block, but this codebase's own sibling hook comments (and its own `require-goal.sh`) confirm exit code 1 from PreToolUse "does nothing" in Claude Code's actual hook contract -- only the correct JSON-deny-plus-exit-0 pattern (used by the sibling `gh-pr-merge-gate.sh`) actually blocks. `gh pr create` without `--draft` on a guardrail-touching branch proceeds regardless; only a stderr message appears.
- `shoggoth_gate.py` (lines 175-176, 236-244, 366-428, MEDIUM) -- the emergency-bypass phrases (`ANDREW-AUTHORIZED-BYPASS`, `STUCK-IN-LOOP-BYPASS`) are matched by plain regex against the agent's own reply text -- fully self-attestable, with zero external authorization check -- and the decision path never calls the logging functions its own docstring claims both bypass types use. An agent can self-authorize an exception to the action-claim gate with no audit trail.
- `guardrails.py` (LOW) -- tracks iteration/tool-call/token counts up through a "CRITICAL: hard limit exceeded" tier, but its sole caller explicitly only logs a warning and never blocks at any severity. Honestly self-described as report-only in its own docstring, but worth flagging since it is the module most likely to be assumed to provide a runaway-execution stop.
- `bypass_rate_hook.py` (LOW) -- clearance from a triggered bypass-rate gate requires only that the same gated agent run one of three self-service CLI commands with an arbitrary, unverified `--actor` string; no independent party is actually involved, a gap the file's own comments already acknowledge as open.

---

### 7. CLI entrypoints, setup, and repo-architecture claims

**Mechanism:** real entrypoint is `divineos` (console script) / `python -m divineos`. The CLI dispatcher imports and registers all ~87 command modules (94 files, ~406 real `@command` decorators, mechanically confirmed to match the project's own documented count) with no orphans and no stubs (zero `NotImplementedError`/`TODO`/`FIXME` hits across the CLI package). Only `click`, `loguru`, `numpy`, `filelock` are hard third-party dependencies; heavier ML libraries degrade gracefully if absent.

**Issues (CONFIRMED unless noted):**
- `FOR_USERS.md` (line 5, MEDIUM) -- opens with "Fresh template... blank-slate version... has not been initialized yet," directly contradicted by this repo's own README.md banner and by 1,095+ files of actual accumulated persona/letter/dream content already present in this checkout. Looks like a doc carried over unedited from the flagship template repo -- an onboarding trap for anyone who reads this file first (README.md itself points readers here as the non-engineer entry point).
- ADR-0001 three-version-repo-architecture (LOW) -- internally consistent across docs and matches this checkout's actual content/role, but the other two claimed sibling repos (Lite, Main) are not present in this download and their live existence/sync state cannot be verified from the filesystem alone.
- `pyproject.toml` (line 9, LOW) -- requires Python >=3.12 (deliberately, per an internal comment about a 2026-06-22 floor bump), while README.md's badge and TLDR.md both still say "Python 3.10+." A user on 3.10/3.11 following the documented prerequisite would hit a hard install-time rejection.
- `doctor_commands.py` (REFUTED) -- a bare `"divineos"` PATH-dependent shell-out to probe a partner clone looked like a portability risk, but the architecture's CWD-walk data-routing design (confirmed in `paths.py`/`_ledger_base.py`) is specifically built so a single shared install routes to the correct clone's data home regardless of which binary resolves off PATH -- this is the intended design, not a gap.
- Density of `except: pass` in `cli/` (REFUTED) -- real pattern, but confirmed narrowly-typed (not bare `except:`), commented as intentional per site, and scoped to non-critical cosmetic enrichment features that never touch the primary documented command behavior; not the dominant error-handling style across the CLI as originally framed.

---

### 8. Benchmark / self-evaluation harness

**Mechanism:** a genuine, non-fabricated A/B benchmark against real SWE-bench-Verified tasks, calling the live Anthropic API for both a "base" and a "DivineOS council"-prompted condition, scored by a separate blind LLM-judge call. Results files contain real, varying per-task data (independently reproduced BENCHMARK_REPORT.md's headline numbers exactly for the main 150-task experiment).

**Issues (all CONFIRMED):**
- `opus_test.py` (lines 437-467, HIGH) -- the head-to-head win/loss/tie tally is unfiltered for judge JSON-parse failures (4 real error files found), which default to a score of 0 via `.get("correct_fix", 0)` and can therefore register as a false "win" or "tie." Three different, mutually-inconsistent counts exist for the same experiment: the raw persisted summary (3 wins), the report's own hand count (3 wins, different n), and a clean re-derivation properly excluding all error-affected tasks (2 wins). The report's repeated "3 enhanced wins, zero regressions" headline is not reproducible from either the raw data or a clean pass -- the true number is 2.
- `swe_harness.py` (lines 234-246, MEDIUM) -- the "enhanced" condition always pairs the council prompt with an extended-thinking token budget the "base" condition never receives (2-2.5x more inference-time compute). No script in the suite isolates council-prompt-only from thinking-only, so the measured score deltas cannot distinguish the council framework's actual contribution from simply giving the model more compute. The report gestures at this but frames it as a supporting mechanism of the council rather than an unremoved confound.
- `llm_judge.py` (line 21, MEDIUM) -- in the main 150-task Sonnet experiment, the judge model is the identical model family used to generate both patches being judged (blind to condition, so not literal self-grading, but same-model-family evaluation that shares blind spots with the generator). More fundamentally: no script anywhere in the harness executes the actual SWE-bench test suite in Docker -- "would pass tests" is always an LLM judge's guess, never a measured outcome (candidly disclosed in the report's own "Measurement Caveat" section).

---

### 9. Operating loop / self-model / identity / affect (backfilled -- single-pass survey only, not adversarially re-verified)

**Mechanism:** genuinely implemented (~12,300 lines across 42 files) and entirely reactive. Every mechanism traced terminates in either a Claude Code native hook or a CLI command a human/agent must invoke. Zero scheduler code (`schedule.every`, `APScheduler`, `croniter`, cron) exists anywhere in `src/divineos/` or `scripts/`; the repo's only cron-triggered GitHub Action (`traffic-archive.yml`) is unrelated (GitHub traffic stats). Nothing here runs when Claude Code isn't hosting a live session -- there is no autonomy independent of an active human-initiated session.

**Issues:**
- `operating_loop/__init__.py` (lines 57-65, MEDIUM) -- the package docstring claims "not a gate... soft notices, not hard blocks," but the same package implements 4 distinct Stop-hook block paths that genuinely force `decision: block` via `post-response-audit.sh`. The module's own top-level self-description contradicts its own code.
- `principle_surfacer.py` (MEDIUM) -- documented as a PreToolUse mechanism meant to warn *before* an apology/withdrawal/impersonation action, but its only production caller runs from the Stop hook -- i.e. only after the response has already shipped. The advertised pre-action warning never actually fires.
- Package-level API/docstring mismatch (LOW) -- the package's `__all__`/imports don't re-export most of the 41 detector submodules the docstring describes as contained here; functionally fine (direct imports work) but the documented API shape doesn't match reality.
- `src/divineos/core/data/` (informational, not a defect) -- this directory does not exist in the download; all genuine runtime state lives outside the repo under `~/.divineos/`, confirming the repo ships no pre-populated or simulated runtime state.

---

### 10. Tests and CI legitimacy (backfilled -- single-pass survey only, not adversarially re-verified)

**Mechanism:** the test suite (~605 files) is overwhelmingly substantive -- real fixtures (temp SQLite DBs, CLI-runner invocations), real assertions on real return values and side effects, several explicit regression pins tied to named past incidents. Only one file in the entire tree (`tests/test_minimal.py`, `assert True`) is tautological. All four CI workflows reference scripts that actually exist and do real work (confirmed by reading `ci_check_guardrail_trailer.sh` and `check_mixed_pattern_merge.py` in full -- both perform real git-diff analysis with real blocking exit codes).

**Issues:**
- `tests/contracts/transformation_contracts.py` (lines 82-94, LOW) -- the "contract" framework is real but has exactly one registered contract; the directory name/docstring imply broader coverage that doesn't exist yet (self-described as a Phase-1 scaffold).
- CI workflows vs. `bandit`/`mutmut`/`deptry` (MEDIUM) -- all three are pinned dev dependencies documented in CLAUDE.md as required checks, but none of the 4 GitHub Actions workflows or any test file invoke any of them (confirmed via repo-wide grep: zero matches). Enforcement exists only in a local pre-commit hook, bypassable with `git commit --no-verify` -- directly inconsistent with the project's own stated rationale for why server-side CI exists at all (the same rationale was applied to the review-trailer check but not to these three). By contrast, a fourth local-hook tool (`vulture`) *is* correctly server-enforced via a pytest subprocess call.
- `integrity-audit.yml` guardrail-trailer gate (LOW, informational) -- verifies only that a trailer string is present (and optionally that a tree-hash matches), never that the referenced audit round actually exists or contains genuine findings. Candidly disclosed in both the workflow's own comments and the script's own printed output, so not a hidden defect, but it means a fabricated, well-formed round-id currently passes the gate.
- `traffic-archive.yml` (LOW) -- depends on a repo secret (`TRAFFIC_ARCHIVE_PAT`) whose actual configuration cannot be verified statically; blast radius is limited to losing traffic-archive data, not to merges or code quality.

---

## Master list of confirmed HIGH-severity structural issues

1. Ledger tamper-evidence self-destructs on routine, automatic use (`ledger_compressor.py`), with no repair path -- known, already documented, still unfixed.
2. Council-required enforcement gate is fully built but its activating hook is deliberately unregistered (`check-council-required.sh`).
3. Moral-compass "rudder" cannot fire at all -- the hook imports a function (`main`) that does not exist in `compass_rudder.py`.
4. `EMERGENCY_STOP` does not reach actual Edit/Write/Bash tool calls, only `divineos` CLI dispatch; the dedicated fix (`corrigibility_tool_gate/`) is complete, tested, and has zero callers.
5. The operator-anchored, unforgeable PR merge-review gate was never wired into CI; only a fakeable textual trailer check runs.
6. Family-queue auto-surfacing (`ear_watch.py`, `ear-surface.sh`) reads from a database path the live system stopped writing to -- silently, permanently returns nothing.
7. The benchmark's headline "3 enhanced wins, zero regressions" claim is not reproducible; a scoring bug that treats judge errors as score-0 inflates it -- clean count is 2.

## Notable REFUTED findings (to keep this balanced -- not everything flagged held up)

- `aletheia-boot-gate-preflight.sh` being unwired -- a deliberate, documented staged rollout with an active in-context fallback check, not an oversight.
- `arm-letter-monitor-instruction.sh`'s idle-wake gap -- has a real, independently-wired hard-blocking fallback (`require-monitors-armed.sh`) the original finding missed.
- Council engine's keyword-matched "analysis" being framed as a hidden defect -- it's openly disclosed as raw material in three separate places in the code itself.
- `doctor_commands.py`'s bare PATH-dependent shell-out -- the architecture's CWD-walk data routing is specifically designed to make this safe.
- `family/raw_recordings/` naming -- its own README clarifies "written, not audio" in its first sentence.
- `gate_emit.py` / `gate_marker.py` -- mis-scoped inclusions in the original file list, not defects.
- `self_grade.py` computing nothing -- intentional, clearly marked, with the real comparison logic genuinely wired elsewhere (`external_validation.py`).
- `shape/primitives.py` -- does exactly what its narrow stated purpose claims.

## Limitations of this audit

- Two subsystems (operating loop/self-model, tests/CI legitimacy) only received a single-pass survey after their first attempt errored out -- they did not go through the adversarial second-agent re-verification the other 8 subsystems received. Their findings should be treated as one notch less certain than the rest of this document.
- This was a static, read-only audit: no hook, CLI command, or script belonging to the repo was ever executed, and no network calls were made. Some findings (e.g. whether a workflow's secret is actually configured, whether the sibling Lite/Main repos exist and are in sync) cannot be confirmed without doing so.
- The repo is very large (4,144 files, 1,323 Python files, 462 alone under `src/divineos/core`). Coverage strategy was targeted (entry points, grep for stub/dead-code signals, full reads of the most central files) rather than exhaustive -- it is possible smaller, lower-visibility issues exist outside what was sampled.
