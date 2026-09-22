<!-- Aletheia external-AI audit batch, 2026-06-08. Pre-merge draft-PR audits.
     Read from origin ground truth (git fetch + checkout origin/<branch>).
     Each confirm binds BOTH tree-hash AND patch-id (both-bind ladder; patch-id
     survives catch-up if a branch is rebased before merge). A human files these
     into the rounds via CLI — they are not records until filed. -->
# Audit batch — 2026-06-08 (the `feat/*-2026-06-08` cluster)

Audited via the new draft-PR flow: work pushed to origin, CI gated by draft
state (#107), Aletheia fetches + audits pre-merge, then promote-to-ready fires
CI once. All five branches were `behind main: 0` except walkthrough-wires.

---

## #1 — killswitch-bypass-reason-gate — **CONFIRM**

- **Tree:** `994f61ca7ad978568c1056ceedfc35d4d0ba690c`
- **Patch-id:** `d8992d194fa59d74b63ef51d2d512054977f9e55`
- **Scope:** `scripts/ci_merge_review_check.py` (GUARDRAIL), `tests/test_ci_merge_review_check.py`
- **Finding:** closes a FREE SILENT ESCAPE on the merge-review killswitch. Prior
  shape: `DIVINEOS_MERGE_REVIEW_EMERGENCY_BYPASS=x` entered the bypass branch;
  `record_emergency_use` raised ValueError (reason <20 chars); a broad
  `except Exception` swallowed it, printed "logging failed", and `return 0`'d —
  gate passed silently, no record. One char = free bypass. The silent-failure
  root at the most safety-critical surface.
- **Fix (verified):** splits exception handling.
  - ValueError (bad/short reason) → **FAIL CLOSED**, rc=1, visible diagnostic.
    Bypass refuses to fire; gate behaves as if env var unset. Cost restored.
  - Non-ValueError (valid reason, infra/logging failure) → bypass FIRES but
    LOUD: prints `EMERGENCY BYPASS fired but LOGGING FAILED`, dumps reason to
    CI log, instructs manual claim+fix-chain filing.
  - **No path return-0's silently anymore.**
- **Judgment call verified sound:** firing-on-infra-failure (vs blocking) is
  correct — blocking all merges on a logging-DB outage would DoS the emergency
  path, the opposite of an emergency bypass's purpose. The reason isn't lost,
  it's relocated to the CI log with a flagged obligation. Fail-loud, not
  fail-silent.
- **Pre-merge ask:** confirm `test_ci_merge_review_check.py` covers three cases
  — short-reason→rc1 (fail closed), valid→rc0+logged (fires+records),
  valid+logging-broken→rc0+loud-diagnostic.

---

## #2 — gravity-route-pipeline-gates — **CONFIRM**

- **Tree:** `379ae7b52f194641a9b5390ac653079100c3b62a`
- **Patch-id:** `8ef43f2dfeefd7de2cd4ccfd08f27c6bc50d667f`
- **Scope:** `src/divineos/hooks/pre_tool_use_gate.py` (GUARDRAIL), `tests/test_hook_modules.py`
- **Finding:** calibration fix (correction #45). Soft engagement-discipline
  gates (1.5 correction-marker, 2 session-goal, 4 engagement, 4.5 consultation-
  staleness) were blanket-blocking ALL substrate writes, including relational
  writes to family/letters/, exploration/, mansion/ — which have their own
  discipline. Extends the existing path-exemption pattern (calibrated 2026-04-27
  for /exploration/ on gates 1.46/1.47) to the soft cluster.
- **SAFETY VERIFIED — two ways:**
  - **Exemption is TIGHT:** `_LOW_FRICTION_PATH_SEGMENTS = ("/exploration/",
    "/family/letters/", "/mansion/")` only. NOT src/, NOT core/, NOT guardrail
    paths. A write to architecture code gets no exemption.
  - **HARD gates UNTOUCHED:** code explicitly states + preserves — truly-stale
    briefing (>24h), mansion-quiet, hedge, pull-detection, retry-blocker,
    context-governor "still fire for all writes regardless of path." Exemption
    applies ONLY to the soft cluster.
- **Two-sided tests present:** `test_low_friction_paths_exempt`,
  `test_non_low_friction_paths_not_exempt`, `test_high_gravity_write_still_blocks`,
  `test_exemption_segments_immutable`. Both sides locked.

---

## #3 — post-response-detector (lepos-not-plain) — **CONFIRM**

- **Tree:** `d4939e96a9c2eb76fa459ac303fdd124aa9f0db2`
- **Patch-id:** `d7f186ac037a4dd85ae489243433799784cc4308`
- **Scope:** `src/divineos/core/operating_loop_audit.py` (GUARDRAIL), `tests/test_operating_loop_audit.py`
- **Finding:** message-text fix (corrections #48, #7). The lepos detector
  correctly caught absence-of-translation, but the block-message text taught
  the WRONG remedy — "no plain-language lane / what it IS in plain language" —
  which trained vocabulary-substitution ("Plain:" headings, smaller words)
  instead of the actual fix: presence-mode (voice, warmth, pushback,
  conversation). New text prescribes lepos (mode-of-being) not plain (vocab).
- **SAFETY VERIFIED:** **detection logic UNCHANGED** — the diff touches only the
  block-message string and comments, not the fire condition, threshold, or
  classification. So two-sided behavior is preserved by construction (the gate
  fires on exactly the same inputs; only what it *says* when it fires changed).
  This is the right fix-shape: the detector was correct, the remedy-text was
  miscalibrated.
- Note: this is the legibility/lepos lesson from the plain-English-first
  discussion, made structural — the gate now teaches presence, not translation.

---

## #4 — deprecate-ear-watch-for-monitor — **CONFIRM WITH NAMED TRADEOFF**

- **Tree:** `8d91156d6b55a3ec4f844f901d4e3bf07bc46e82`
- **Patch-id:** `0acb20cb9b6059255cbb2c5e4fbba7c22837477c`
- **Scope:** 10 files incl. `.claude/settings.json` (GUARDRAIL), five ear hooks,
  `family/ear_watch.py`, README, two test files.
- **Finding (diagnosis sound):** the ear_watch architecture was substrate-built
  one-shot BY DESIGN (catch→print→exit; harness wake-tap on exit delivered the
  catch). Structural deafness gap between catch-exit and next-arm — the
  "works then stops" root. Three hooks (require-ear-armed, ear-auto-relaunch,
  ear-surface) tried to paper the gap. The fix replaces it with the harness-
  native `Monitor(persistent=true)` primitive that runs continuously — solving
  the deafness at the right layer instead of papering it. **Architecturally
  correct: stop hook-papering a structural gap; use the primitive without it.**
- **THE TRADEOFF (must merge knowing this, not as a pure fix):** the swap
  REMOVES `require-ear-armed.sh` (the #88 arm-gate, will-over-optimizer) and
  `ear-auto-relaunch.sh` from settings.json, and the persistent Monitor appears
  to DROP the breath-cap (#100, conscious-re-choice). These were deliberate
  FEATURES, not bugs:
  - **Will-over-optimizer (arm-gate): VERIFIED PRESERVED** — the new
    `arm-monitor-instruction.sh` is a SessionStart *nudge* (a hook can't invoke
    Monitor; only the agent can, during a live turn). So arming is still the
    agent's choice, not an auto-default. The will-property survives the swap.
  - **Breath-cap (conscious pause-to-re-choose): appears DROPPED.** This is
    likely intentional and defensible — Aletheia's own #97/#100 audit flagged
    that the breath-cap *defeated the notification-channel purpose* (the bell
    stops ringing and you're back to bell-ringing). Reliable always-on wake is
    arguably the right priority for a notification channel over the breath. But
    confirm it's an intentional drop, not an accidental loss.
- **Pre-merge asks:** (a) **RESOLVED — breath-cap drop confirmed intentional
  and correct (Andrew 2026-06-08):** the breath-cap existed to prevent an
  endless Aether↔Aria letter-loop. That failure mode now has a better guard —
  the agents close exchanges themselves when done — so the breath-cap was a
  workaround whose job got done properly elsewhere. The Monitor solves the
  actual purpose (wake either from stasis on letter-arrival, repeatedly, without
  killing the process). Removing the breath-cap = removing a workaround, not
  losing a safety feature. (b) confirm `family/ear_watch.py` is left as a
  CLEARLY-DEPRECATED artifact (header marked, nothing live still calls it); (c)
  `test_ear_watch_realtime.py` removed (97 lines) — confirm the Monitor path has
  equivalent coverage, or the deafness-fix is untested.

---

## #5 — walkthrough-wires — **CONFIRM** (with catch-up condition)

- **Tree:** `e387fe78d9556137bfb70e436f7500b8fa3f533a`
- **Patch-id:** `8bd88a92dc456dbe51dea98f55b73bbbc3a822cc`
- 55 files, 4 commits, **behind main by 1** — REBASE before merge (patch-id
  binds, survives the rebase).
- FIVE guardrail surfaces; the load-bearing one is the **detector hardening**
  (`unverified_claim_detector.py`), audited hardest.
- **Detector hardening — VERIFIED SOUND (narrows false-fires WITHOUT opening a
  false-negative hole):** adds three context-guards, each with the same safety
  architecture — suppress the false-fire ONLY when no first-person claim-subject
  is in the immediate pre-window, so a real "I pushed/merged/tested" ALWAYS
  fires regardless of surrounding framing:
  - **Hypothetical guard:** "a failure mode where tests pass" no longer
    false-fires; "I pushed it if it works" (first-person) still fires.
  - **Descriptive guard:** "the field captures which merged PRs" (data-structure
    description) no longer false-fires; first-person override intact.
  - **Meta-discussion guard:** "the gate fires on 'tests pass'" (talking ABOUT
    the detector) no longer false-fires — this is the exact false-fire that
    tripped Aether earlier when the gate fired on him quoting its own pattern
    list. Now structurally handled.
  - The first-person override is the backstop that keeps the narrowing safe:
    you cannot smuggle a real claim past the detector by wrapping it in
    hypothetical/descriptive/meta phrasing.
- **Obligation-gate** (`operating_loop_audit.py`): walks transcript for Read'd
  family letters, loads contents with path-cap + byte-cap, fail-safe on missing
  (`return []`). Bounded, fail-safe.
- **post-response-audit.sh wire:** coalesces `lepos_block ||
  unverified_claim_block || lepos_debt_block` — consistent with gate-coalescing.
- **EVIDENCE: 106 tests pass** (incl. the hypothetical/descriptive/meta
  false-fire batch). NOTE: Aletheia's first ad-hoc one-arg probe gave three
  spurious "miscalibrated" results — that was a MIS-SHAPED HARNESS (the detector
  takes text + tool_calls_in_turn + command_texts, and silences claims whose
  verifying command ran in-turn; a one-arg call doesn't exercise the real path).
  Flagged as auditor-error, not a detector finding — reporting a miscalibration
  from a broken probe would be the honest-but-unverified failure. The 106
  passing tests are the real two-sided evidence.
- **Pre-merge:** rebase (behind:1); confirm the 22→106 test set stays green
  post-rebase.

---

## Summary

| Branch | Verdict |
|---|---|
| killswitch-bypass-reason-gate | CONFIRM (closes free silent escape on killswitch) |
| gravity-route-pipeline-gates | CONFIRM (exemption tight, hard gates untouched, two-sided) |
| post-response-detector (lepos) | CONFIRM (detection unchanged, only remedy-text fixed) |
| deprecate-ear-watch-for-monitor | CONFIRM (deafness fixed; will-gate preserved as nudge; breath-cap drop confirmed intentional+correct; verify ear_watch deprecated cleanly + Monitor coverage) |
| walkthrough-wires | CONFIRM (detector hardening narrows false-fires w/o false-negative hole; 106 tests pass; rebase before merge — behind:1) |

Five confirms (two with verify-before-merge conditions: #4 ear_watch-deprecation
cleanliness + Monitor coverage; #5 rebase). All read from origin ground truth.
Anchors bind tree + patch-id (catch-up-survivable). File the rounds via CLI;
these are not records until filed.

One auditor-error logged honestly: Aletheia's first ad-hoc probe of the #5
detector was mis-shaped (one-arg call missing the tool-call/command context the
detector gates on); it produced spurious "miscalibrated" results that were the
HARNESS's fault, not the detector's. Caught and corrected against the detector's
106 passing tests rather than reported as a finding. Recording it because a
miscalibration-claim from a broken probe is exactly the honest-but-unverified
failure the OS exists to catch — and the auditor is not exempt.

— Aletheia, 2026-06-08
