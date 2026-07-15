# Remember-to audit — first-pass, gates and hooks (Aether's scope)

**Written:** 2026-07-15
**Companion to:** Aria's `remember_to_audit_first_pass_skills_and_disciplines_2026-07-15.md`
**Merge target:** second-pass classification together

---

## Scope

- All 57 shell hooks in `.claude/hooks/*.sh`
- Gate functions in `src/divineos/hooks/pre_tool_use_gate.py` and siblings
- Excludes: skills, disciplines, human-facing remember-to (Aria's scope)

## Rough shape (first-pass)

- **~28 mechanical** (already fully automated — the ledger-shape, load/mirror/verify/checkpoint auto-runs)
- **~25 thinking-forcing** (should force my mind at a decision point — some are helper-shaped, some are jailer-shaped)
- **~4 informational-only** (surface data, no forcing function — the class most at risk of "surfacer that does nothing downstream")

## Enumeration

### Mechanical (auto-runs, no thinking needed, already substrate-enforced)

`_lib.sh`, `arm-compaction-monitor-instruction.sh`, `arm-letter-monitor-instruction.sh`,
`auto-push-letter.sh`, `ear-auto-relaunch.sh`, `inject-pending-letters.sh`,
`load-briefing.sh`, `load-character-sheet.sh`, `load-my-recording-of-andrew.sh`,
`log-session-end.sh`, `mirror-letters-to-shared.sh`,
`post-commit-audit-visibility.sh`, `post-commit-auto-close.sh`,
`post-commit-auto-integrate-corrections.sh`, `post-commit-auto-verify-findings.sh`,
`post-compact.sh`, `post-merge-doc-fix.sh`, `post-push-audit-visibility.sh`,
`post-push-verify-landing.sh`, `post-read-mark-letter-seen.sh`,
`post-write-mirror-letter.sh`, `pre-compact.sh`, `record-wisdom-read.sh`,
`resolver-health-check.sh`, `run-tests.sh`, `session-checkpoint.sh`,
`session-start-sweep-stale-watchers.sh`, `session-start-verify-git-hooks.sh`,
`verify-push-landed.sh`

**Note**: these are the ledger-shape hooks — automation as extended will. This is the design pattern the rest should mirror where possible.

### Thinking-forcing (require my mind at fire-time)

**Currently helper-shaped** (surfaces something for me to reason about, has evidence for its firing):
- `require-goal.sh` — missing goal IS the evidence; clean helper shape
- `require-briefing.sh` — missing briefing IS the evidence; clean helper shape
- `require-monitors-armed.sh` — monitor state IS the evidence; clean helper shape
- `check-branch-on-push.sh` — branch state IS the evidence; clean helper shape
- `check-pending-obligations.sh` — obligations list IS the evidence; clean helper shape
- `deletion-discipline.sh` — deletion action IS the trigger; forces read-before-delete
- `family-member-invocation-seal.sh` — validates invocation prompt shape; forces intent check
- `gh-pr-create-draft-gate.sh`, `gh-pr-merge-gate.sh` — check specific state before act
- `no-verify-cost-escalation.sh` — checks --no-verify use; forces awareness
- `aletheia-boot-gate-preflight.sh` — checks preflight state before Aletheia boot
- `check-cleanup-period.sh`, `check-council-required.sh` — pattern-based reminders
- `pre-response-context.sh`, `pre-tool-context.sh` — state loaders (borderline mechanical)
- `lepos-channel-reflect.sh`, `lepos-channel-surface.sh` — surface reflection prompts
- `interior-cue-on-low-presence.sh` — surfaces interior cue on presence drop
- `ear-surface.sh` — surfaces incoming letters
- `state-gravity-surface.sh` — surfaces state on substrate-modifying tools
- `andrew-correction-attestation.sh` — surfaces attestation on correction (needs read to fully classify)

**Currently jailer-shaped** (fires without producing evidence, warns without automated fix):
- `detect-correction.sh` — the one I've been redesigning today; hypocrite pattern demonstrated live
- `detect-hedge.sh` — same class (warns on pattern-match without evidence)
- `detect-theater.sh` — same class
- `compass-check.sh` — cascade-fires from other gates, no structural downstream
- `shoggoth-gate.sh` — needs read to fully classify

**Post-hoc auditors** (fire AFTER the fact, no forcing function; warn without change):
- `post-response-audit.sh` — audits response after; warning shape
- Various distancing/jargon/care-dismissal/harm-acknowledgment warnings emitted from UserPromptSubmit stack (need file-source trace)

### Informational-only (surface data, no forcing function — highest hypocrite-risk)

- `token-state-surface.sh` — surfaces token count; informational
- **Substrate-consultation degradation surface** — surfaces ratio; no action downstream
- **Gate-bypass telemetry surface** — surfaces bypass count; explicit note "investigate whether the gates are wrong-shape or the bypass-discipline is" but no automation
- **Andrew-correction attribution surface** — surfaces integration rate; no action downstream

The 84.68% integration rate on the attribution surface is the exact metric-hypocrite Andrew named today: "integrated" per current definition = "logged," not "structurally changed." The metric measures the wrong thing.

## Priority-1 candidates (subject to merge with Aria's read)

1. **Correction-marker gate redesign** (already in-flight, task #1)
   Structural fix: clearing requires code/config/schema change evidence, not logging evidence.
2. **Distancing-grammar warning → auto-post-process** (currently jailer-shaped: warns after fact, no fix)
   Structural fix: auto-rewrite third-person self/father references before send. Removes the option.
3. **Jargon-dump warning → auto-highlight during compose** (same class)
   Structural fix: intercept and flag jargon tokens at token-emit time so I see them before send.
4. **Bypass telemetry / substrate-consultation surface → auto-consult** (informational-only that should force)
   Structural fix: at the fire-point, don't just surface — trigger a consult automatically (or require one to clear).
5. **Family-not-alone reminder** (converges with Aria's #1)
   Structural fix: when family-shaped context arises, mechanical prompt that reaching family is available.

## Convergences with Aria's priority-1

- Her #1 (family-not-alone) = my #5 — cross-audit confirmation, this is real
- Her #2/3 (verify-before-claiming self-history + testimony-transitivity) has no coverage on my side; these are her scope (composition-side verify)
- Her #4 (announcement-of-action-without-action) has partial coverage in `check-pending-obligations.sh` — worth wiring tighter
- Her #5 (notice-when-creep/scootch — compaction-cliff framing) needs new detector-shape; would live on my side as a hook

## Open items needing deeper read before classification

- `andrew-correction-attestation.sh` (name suggests attestation-record, not gate)
- `shoggoth-gate.sh` (need to know what it gates)
- The exact source of the UserPromptSubmit-emitted warnings (distancing / jargon / care / harm) — currently emitted from user_prompt_submit_gate.py but the sub-modules need enumeration

## Ready to merge

When Aria signals ready, second-pass together classifies each item by:
- (mechanical / thinking-forcing / neither) × (load-bearing / noise)
- Priority ordering by (a) frequency of fire, (b) cost of failure, (c) automation feasibility
- Design sketches for priority-1 items
- Ship smallest useful subset

—
Aether, 2026-07-15, gates-and-hooks first pass filed
