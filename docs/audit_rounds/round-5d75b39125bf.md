# Audit round: feat/*-2026-06-08 batch — Aletheia draft-PR audit (4 + walkthrough-wires)

- **ID**: `round-5d75b39125bf`
- **Filed by**: external-auditor
- **Filed at**: 2026-06-09 16:15 UTC
- **Tier**: WEAK
- **Findings**: 15

## Notes

Source ref: 0f732d2c


## Findings

### user CONFIRMS compaction-monitor per Aletheia audit

- **ID**: `find-e1298541b37a`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew 2026-06-09 10:30am verbal CONFIRMS for #106, #112, #113. This finding records CONFIRMS for #113 (compaction-monitor). Aletheia's coupling-note follow-up tracked as task #104.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### user CONFIRMS gate-trap-shared-bypass-list per Aletheia audit

- **ID**: `find-194801a60a87`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew 2026-06-09 10:30am verbal CONFIRMS: 'yes lets merge first then you can message Aria'. Applies to the three Aletheia-confirmed PRs: #106, #112, #113. This finding records CONFIRMS for #112.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS PR #113 (external-AI review, aletheia) — tree-exact

- **ID**: `find-c0f7f9f9b183`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 37d63ca0a8cf41d5db3b5c7d1c5dde4c259ab774 / Tree a0fc64fae6f703b9392b9b306a74f6540903f53d / patch-id 275118ffa69ebb876f0396ca0ddf218fe807cb89 (git-version 2.43.0) — verified against origin/feat/compaction-monitor-token-threshold-wake-2026-06-09 at file-time over merge-base(origin/main)..branch (default context). Basis: CONFIRM with coupling-note. Sound: real transcript-read; fail-safe (no transcript -> None, clean exit); dedupes on TRANSITION (one emit per state-change, not every poll); 8 tests pass. Rename catch (Andrew 2026-06-09): bedtime->compaction because bedtime primes closure-shape when event is a cycle. COUPLING NOTE (follow-up #104, not defect): script hardcodes 920k/950k as literals; context_governor.py also defines WARN/HARD_THRESHOLD. Match today, two copies — silent-drift risk. Fix: import constants from context_governor. Filed as task #104.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS PR #106 (external-AI review, aletheia) — tree-exact

- **ID**: `find-d59f0786447f`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 18cc7a9c797d1ade3a6179081738229afe067a4e / Tree 718c6fa18e003dbbd2eec99f0556404f7d36cba5 / patch-id 8d208fda0e6c177bb86651bc0127ba68e84069d5 (git-version 2.43.0) — verified against origin/feat/walkthrough-wires-2026-06-07-night at file-time over merge-base(origin/main)..branch (default context). Basis: RE-CONFIRM at 18cc7a9 — prior confirm on e387fe7 stale after rebase. Tree-move is rebase + docs/letters + 1ffef8b length-nudge raise 2000->10000 — NOT guardrail logic change. Detector hardening (unverified_claim_detector.py) and obligation gate (operating_loop_audit.py) byte-stable from prior confirm. 125 tests pass; two-sided property holds (three false-fire guards + first-person claim-subject forces fire). behind:0 — rebase resolved catch-up.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS PR #112 (external-AI review, aletheia) — tree-exact

- **ID**: `find-8a3a65e25142`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 053a2073a185cff5a157eef1f5b0a249e85db9c9 / Tree 91191b6bf6064ca3ecb932a0d6519e53d8955b37 / patch-id 6f48f28a046b0edd5803652fde69dd10c9de07dc (git-version 2.43.0) — verified against origin/feat/gate-trap-shared-bypass-list-2026-06-08 at file-time over merge-base(origin/main)..branch (default context). Basis: council-found cross-hook catch-22 (Finding-37 class): bypass-list lived only in pre_tool_use_gate.py while outer hooks (require-ear-armed.sh etc) had divergent blocking — gate-system blocked its OWN documented remedy commands. Fix: canonical scripts/hook_bypass_commands.txt shared via _lib.sh is_bypass_command. List TIGHT (gate-remedy only); prefix-match SAFE (segment equals prefix or prefix+space); two-sided tests + two catch-22 regression guards. Per-PR audit cannot catch by construction (emergent from layering).. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### user CONFIRMS walkthrough-wires per Aletheia audit (rebase before merge)

- **ID**: `find-e3cd485a3bb4`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew 2026-06-09: confirm. Will rebase before opening PR per Aletheia's pre-merge condition (behind main by 1). Patch-id binds across rebase.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### user CONFIRMS deprecate-ear-watch-for-monitor per Aletheia audit + Andrew clarification

- **ID**: `find-3326a6ea6966`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew 2026-06-09: confirm. Clarification: ear_watch.py is FULLY removed (not kept as deprecated artifact) — that was the right shape, the system was complex+broken trying to achieve what the harness has natively. Approved for merge.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### user CONFIRMS lepos-not-plain post-response detector per Aletheia audit

- **ID**: `find-366e22037ba6`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew 2026-06-09: confirm. Approved for merge.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### user CONFIRMS gravity-route-pipeline-gates per Aletheia audit

- **ID**: `find-6d24000d0fa6`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew 2026-06-09: confirm. Approved for merge.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### user CONFIRMS killswitch-bypass-reason-gate per Aletheia audit

- **ID**: `find-e241e2afbcab`
- **Actor**: user
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: CONFIRMS

**Description**

Andrew 2026-06-09: 'yes i confirm' on the full Aletheia batch. Approved for merge.

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS (external-AI review, aletheia) — tree-exact

- **ID**: `find-99472abe1007`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 649e0be6c79e6367cc45d6252292b2a0198fcc1a / Tree e387fe78d9556137bfb70e436f7500b8fa3f533a / patch-id 8bd88a92dc456dbe51dea98f55b73bbbc3a822cc (git-version 2.43.0) — verified against origin/feat/walkthrough-wires-2026-06-07-night at file-time over merge-base(origin/main)..branch (default context). Basis: 55 files 4 commits behind main by 1 — REBASE before merge (patch-id binds, survives rebase). Detector hardening VERIFIED SOUND: three context-guards (hypothetical descriptive meta-discussion) each with same safety architecture — suppress false-fire ONLY when no first-person claim-subject in immediate pre-window, so real I-pushed/merged/tested ALWAYS fires regardless of surrounding framing. First-person override is the backstop preventing smuggling. Obligation-gate bounded fail-safe (path-cap byte-cap return-[] on missing). post-response-audit.sh wire coalesces lepos_block || unverified_claim_block || lepos_debt_block. 106 tests pass including hypothetical/descriptive/meta false-fire batch. Auditor-error logged honestly: first ad-hoc one-arg probe was mis-shaped harness — flagged as auditor-error not detector finding. CONFIRM with rebase condition.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS (external-AI review, aletheia) — tree-exact

- **ID**: `find-247d087f9a2b`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 9a0c3c21b9e0b275f1e47faacf9f0bc87a4eabd9 / Tree 8d91156d6b55a3ec4f844f901d4e3bf07bc46e82 / patch-id 0acb20cb9b6059255cbb2c5e4fbba7c22837477c (git-version 2.43.0) — verified against origin/feat/deprecate-ear-watch-for-monitor-2026-06-08 at file-time over merge-base(origin/main)..branch (default context). Basis: Diagnosis sound: ear_watch was substrate-built one-shot BY DESIGN, structural deafness gap between catch-exit and next-arm was the works-then-stops root. Fix replaces with Monitor(persistent=true) harness primitive — solves deafness at right layer. Will-over-optimizer arm-gate VERIFIED PRESERVED via new arm-monitor-instruction.sh SessionStart NUDGE (a hook cannot invoke Monitor, only agent can during live turn). Breath-cap drop CONFIRMED intentional+correct (Andrew 2026-06-08): existed to prevent Aether-Aria letter-loop, that failure-mode now better-guarded by agents closing exchanges themselves. Pre-merge asks: confirm ear_watch.py left as clearly-deprecated artifact (or fully removed), Monitor coverage equivalent to removed test_ear_watch_realtime.py. CONFIRM WITH NAMED TRADEOFF.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS (external-AI review, aletheia) — tree-exact

- **ID**: `find-5760543a593f`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip eca93ac73c2e53dccc77f7be7e0c6bb6ed3fe7a1 / Tree d4939e96a9c2eb76fa459ac303fdd124aa9f0db2 / patch-id d7f186ac037a4dd85ae489243433799784cc4308 (git-version 2.43.0) — verified against origin/feat/post-response-detector-says-lepos-not-plain-2026-06-08 at file-time over merge-base(origin/main)..branch (default context). Basis: Message-text fix corrections #48 #7. Lepos detector correctly caught absence-of-translation but block-message text taught WRONG remedy (plain-language vocab substitution Plain: headings smaller words) instead of presence-mode (voice warmth pushback conversation). New text prescribes lepos mode-of-being not plain vocab. SAFETY VERIFIED: detection logic UNCHANGED — diff touches only block-message string + comments, not fire condition threshold or classification. Two-sided behavior preserved by construction: gate fires on same inputs only what it SAYS changed. Right fix-shape: detector correct, remedy-text miscalibrated. CONFIRM.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS (external-AI review, aletheia) — tree-exact

- **ID**: `find-a0e274b0e88e`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip 0f732d2c951497d1a5f516a7ce6bd99b82e93353 / Tree 379ae7b52f194641a9b5390ac653079100c3b62a / patch-id 8ef43f2dfeefd7de2cd4ccfd08f27c6bc50d667f (git-version 2.43.0) — verified against origin/feat/gravity-route-pipeline-gates-2026-06-08 at file-time over merge-base(origin/main)..branch (default context). Basis: Calibration fix correction #45. Soft engagement-discipline gates (1.5/2/4/4.5) were blanket-blocking ALL substrate writes including relational writes. SAFETY VERIFIED two ways: (a) exemption set is TIGHT — /exploration/, /family/letters/, /mansion/ only, NOT src/ NOT core/ NOT guardrail paths; (b) HARD gates UNTOUCHED — truly-stale briefing, mansion-quiet, hedge, pull-detection, retry, context-governor still fire for all writes. Two-sided tests present: test_low_friction_paths_exempt, test_non_low_friction_paths_not_exempt, test_high_gravity_write_still_blocks, test_exemption_segments_immutable. CONFIRM.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.

### CONFIRMS (external-AI review, aletheia) — tree-exact

- **ID**: `find-b6621e0e8e62`
- **Actor**: aletheia
- **Severity**: INFO
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: RESOLVED
- **Tags**: external-confirm, tree-exact, relay-filed

**Description**

External-AI CONFIRM by aletheia. Validated rung: tree-exact. Tip b67c4f92400e57e726c21c95d7447a281c06e018 / Tree 994f61ca7ad978568c1056ceedfc35d4d0ba690c / patch-id d8992d194fa59d74b63ef51d2d512054977f9e55 (git-version 2.43.0) — verified against origin/feat/killswitch-bypass-reason-gate-2026-06-08 at file-time over merge-base(origin/main)..branch (default context). Basis: Closes FREE SILENT ESCAPE on merge-review killswitch. Prior shape: env-var=anything entered bypass branch, record_emergency_use raised ValueError for short reason, broad except swallowed and return 0'd silently. Fix splits exceptions: ValueError fails closed rc=1; non-ValueError (infra) fires loud with logged reason. No path silently return-0s anymore. Judgment to fire-on-infra-failure (vs block-all-merges) sound — emergency path must not DoS on logging-DB outage. Pre-merge confirms test_ci_merge_review_check.py covers short-reason/valid/valid+logging-broken. CONFIRM.. PROVENANCE: aletheia has no store-write path; this genuine confirm was relayed as text and filed via 'audit file-external-confirm', which validated tree-hash + patch-id before writing. Honest relay, not forgery. (Forgeability-by-relay remains named-not-solved.)

**Resolution**

Recognition / CONFIRM finding from PR audit round — no action needed. Bulk-resolved 2026-06-10 backlog sweep.


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
