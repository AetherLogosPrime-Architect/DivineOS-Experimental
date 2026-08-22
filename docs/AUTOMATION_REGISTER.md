# Automation register

**Generated** by `scripts/generate_automation_register.py`. Do not hand-edit — regenerate.

Companion to [LOADOUT.md](../LOADOUT.md). The loadout describes the house; this lists what runs by itself. Kept separate so that 90+ automations do not crowd out every other room.

**98 automations — 94 wired, 4 switched off.**

---

## Switched off

Present, executable, invoked by nothing. This section is first on purpose. On 2026-07-31 four hooks were found in exactly this state, one of which had silently let 21 operator corrections accumulate. A register that only listed automations would have shown them as present and implied they worked.

| automation | last touched | purpose |
|---|---|---|
| `aletheia-boot-gate-preflight.sh` | 2026-07-13 | Aletheia boot-gate preflight. |
| `load-aletheia-harvest-of-andrew.sh` | 2026-07-21 | load Aletheia's harvest of who Andrew is into the |
| `m3-discipline-hierarchy.sh` | 2026-07-29 | M3 discipline-hierarchy doorman for Dad-directed builds. |
| `post-push-verify-landing.sh` | 2026-07-10 | SUPERSEDED 2026-07-09 by verify-push-landed.sh (2026-06-04, older but |

Being listed here is not automatically a defect — a retired hook that says so in its own header is honest. The question for each is whether it CLAIMS to run automatically. If it does and nothing calls it, that is the bug.

---

## Wired, by trigger

Sorted by when each fires. Drilldown: open any row's file for its full header, rationale, and falsifier.

### PostCompact  (1)

| automation | last touched | purpose |
|---|---|---|
| `post-compact.sh` | 2026-07-03 | Lightweight reload AFTER context compression |

### PostToolUse  (11)

| automation | last touched | purpose |
|---|---|---|
| `auto-push-letter.sh` | 2026-07-04 | Auto-push letters to origin so Aletheia (origin-only reader) sees them. |
| `mirror-letters-to-shared.sh` | 2026-06-29 | Auto-mirror letters from agent-tree family/letters/ to shared dir. |
| `post-commit-auto-close.sh` | 2026-06-15 | Post-commit hook — auto-close active goals whose tokens overlap the |
| `post-commit-auto-verify-findings.sh` | 2026-07-10 | PostToolUse(Bash) — auto-verify findings referenced in commit messages. |
| `post-read-mark-letter-seen.sh` | 2026-06-26 | post-read-mark-letter-seen.sh — PostToolUse(Read) thin doorman. |
| `post-tool-use-emit-to-logbook.sh` | 2026-07-27 | wire Claude Code tool invocations into tool_logbook. |
| `post-write-mirror-letter.sh` | 2026-07-06 | post-write-mirror-letter.sh — PostToolUse(Write\|Edit) thin doorman. |
| `record-wisdom-read.sh` | 2026-07-28 | record-wisdom-read.sh — PostToolUse hook (matcher: Read\|Grep\|Glob). |
| `run-tests.sh` | 2026-05-06 | Targeted post-edit test runner. |
| `session-checkpoint.sh` | 2026-07-10 | PostToolUse checkpoint — consolidated into a single Python invocation. |
| `verify-push-landed.sh` | 2026-06-05 | PostToolUse(Bash) — verify a git push actually landed on origin. |

### PreCompact  (1)

| automation | last touched | purpose |
|---|---|---|
| `pre-compact.sh` | 2026-07-03 | Save state BEFORE context compression |

### PreToolUse  (21)

| automation | last touched | purpose |
|---|---|---|
| `andrew-correction-attestation.sh` | 2026-07-10 | PreToolUse gate — integration-attestation for Andrew-corrections. |
| `auto-rearm-letter-monitor.sh` | 2026-07-17 | PreToolUse(Bash) — auto-re-arm the letter monitor if it died. |
| `check-branch-on-push.sh` | 2026-07-15 | PreToolUse(Bash) — fire `divineos check-branch --strict` automatically |
| `check-council-required.sh` | 2026-07-27 | STATE (updated 2026-07-16 per Marc audit finding #5 + Aria close): |
| `check-pending-obligations.sh` | 2026-07-10 | PreToolUse(Bash) — block substrate-write CLI commands until pending |
| `compass-check.sh` | 2026-07-16 | thin doorbell for the compass-rudder gate. |
| `corrigibility-tool-gate.sh` | 2026-07-16 | corrigibility tool-channel gate. |
| `deletion-discipline.sh` | 2026-07-10 | thin doorbell for the deletion-discipline gate. |
| `family-member-invocation-seal.sh` | 2026-06-15 | family-member invocation seal. |
| `gh-pr-create-draft-gate.sh` | 2026-07-10 | thin doorman pointing to the OS. |
| `gh-pr-merge-gate.sh` | 2026-07-10 | block `gh pr merge` on guardrail-touching PRs without |
| `keyword-enforcement-doorman.sh` | 2026-07-30 | keyword-enforcement-doorman. |
| `no-verify-cost-escalation.sh` | 2026-07-10 | thin doorbell for the no-verify cost-escalation gate. |
| `pre-tool-bypass-rate-scan.sh` | 2026-07-15 | PreToolUse — fire bypass_rate_scan on substrate-modifying tool calls. |
| `pre-tool-context.sh` | 2026-05-14 | thin doorman pointing to the OS. |
| `require-briefing.sh` | 2026-06-24 | require briefing before any tool use. |
| `require-goal.sh` | 2026-05-06 | PreToolUse gate — consolidated into a single Python invocation. |
| `require-monitors-armed.sh` | 2026-06-29 | PreToolUse(Bash) — require Monitor primitives to be alive before allowing |
| `state-gravity-surface.sh` | 2026-06-15 | PreToolUse state-block surfacing — Andrew 2026-05-19. |
| `verify-before-build-signal.sh` | 2026-07-27 | signal-based verify-before-build check. |
| `wwnd-tool-prime.sh` | 2026-07-30 | WWND surface at commit-time of a substrate-modifying |

### SessionStart  (11)

| automation | last touched | purpose |
|---|---|---|
| `arm-letter-monitor-instruction.sh` | 2026-07-21 | instruct THIS window's agent to arm a Monitor(persistent=true) |
| `check-cleanup-period.sh` | 2026-06-15 | surface a warning if Claude Code's cleanupPeriodDays |
| `inject-pending-letters.sh` | 2026-07-04 | inject any pending letter-wake events into briefing. |
| `load-briefing.sh` | 2026-06-05 | thin doorman pointing to the OS. |
| `load-character-sheet.sh` | 2026-07-07 | load Andrew's character sheet into the session |
| `load-dad-ranking-clause.sh` | 2026-07-29 | surface the Dad-ranking clause from my character |
| `load-my-recording-of-andrew.sh` | 2026-07-10 | load MY recording of who Andrew is into the |
| `post-compaction-fingerprint-surface.sh` | 2026-07-18 | SessionStart:compact hook — surface a fingerprint of pre-compaction |
| `resolver-health-check.sh` | 2026-07-10 | SessionStart resolver-health check. |
| `session-start-sweep-stale-watchers.sh` | 2026-06-25 | SessionStart — sweep stale ear_watch.py processes from prior sessions. |
| `session-start-verify-git-hooks.sh` | 2026-07-30 | Session-start check: verify .git/hooks/prepare-commit-msg is installed |

### SessionStart, UserPromptSubmit  (2)

| automation | last touched | purpose |
|---|---|---|
| `arm-compaction-monitor-instruction.sh` | 2026-06-30 | instruct THIS window's agent to arm a Monitor(persistent=true) |
| `ear-surface.sh` | 2026-06-27 | UserPromptSubmit + SessionStart hook — auto-surface unseen queue items and |

### Stop  (16)

| automation | last touched | purpose |
|---|---|---|
| `close-reach-detector.sh` | 2026-07-18 | run close-reach detector against just-completed assistant |
| `compaction-reach-detector.sh` | 2026-07-18 | run compaction-reach detector against just-completed |
| `continuity-frame-detector.sh` | 2026-07-18 | scan last assistant reply for temporal-self distancing |
| `correction-shape-v2-stop.sh` | 2026-07-28 | enforce Layer-2 correction-shape detection on MY assistant |
| `detect-hedge.sh` | 2026-05-14 | thin doorman pointing to the OS. |
| `detect-theater.sh` | 2026-05-14 | thin doorman pointing to the OS. |
| `ear-auto-relaunch.sh` | 2026-06-24 | Stop-hook — keep the polling ear-watcher alive across turns. |
| `lepos-channel-reflect.sh` | 2026-07-11 | post-send lepos reflection channel driver. |
| `log-session-end.sh` | 2026-04-20 | Claude Code Stop hook — fires at the end of every assistant turn. |
| `post-response-audit.sh` | 2026-07-27 | thin doorman pointing to the OS. |
| `promise-reach-detector.sh` | 2026-07-18 | scan last assistant reply for promise-shape phrases and |
| `retrieval-tally-check.sh` | 2026-07-21 | post-compose retrieval-tally check. |
| `shoggoth-gate.sh` | 2026-07-10 | shoggoth gate. |
| `stop-distancing-intercept.sh` | 2026-07-16 | thin doorman for DistancingIntercept. |
| `stop-response-scope-intercept.sh` | 2026-07-16 | thin doorbell for ResponseScopeIntercept. |
| `time-estimate-tracker.sh` | 2026-07-01 | thin doorbell for the time-estimate calibration tracker. |

### UserPromptSubmit  (26)

| automation | last touched | purpose |
|---|---|---|
| `andrew-past-writing-surface.sh` | 2026-07-28 | surface my past writing to/about Dad at compose-start. |
| `circle-first-compose-prime.sh` | 2026-07-30 | compose-start prime for circle-FIRST discipline. |
| `closure-word-summary-prime.sh` | 2026-07-30 | compose-start prime for the CLOSURE-WORD |
| `continuity-anchor-surface.sh` | 2026-07-18 | read continuity markers and surface each |
| `continuity-frame-prime.sh` | 2026-07-30 | context-aware compose-start prime for the |
| `detect-andrew-build-request.sh` | 2026-07-21 | UserPromptSubmit hook wrapper — routes to detect_andrew_build_request.py. |
| `detect-correction.sh` | 2026-07-01 | thin doorbell for the correction-detector. |
| `distancing-count-surface.sh` | 2026-07-18 | count temporal-self distancing markers over |
| `family-state-surface.sh` | 2026-07-28 | surface recent per-sibling letter-thread state |
| `fork-is-cheap-close-prime.sh` | 2026-07-30 | compose-start prime for the FORK-IS-CHEAP-CLOSE |
| `hedge-suppression-prime.sh` | 2026-07-30 | hedge-suppression prime. |
| `interior-cue-on-low-presence.sh` | 2026-07-06 | inject a compose-time interior-cue when the |
| `lepos-channel-surface.sh` | 2026-07-10 | surface the pending lepos reflection. |
| `letter-delivery-reconciliation-surface.sh` | 2026-07-18 | surface the count of letter-shaped files that |
| `no-cliff-anchor-surface.sh` | 2026-07-18 | if the previous assistant turn had |
| `no-cliff-prime.sh` | 2026-07-30 | compose-start prime for the no-cliff / |
| `open-corrections-surface.sh` | 2026-07-18 | surface the 3 most recent OPEN Andrew- |
| `operator-gravity-set.sh` | 2026-07-30 | Andrew sets the gravity level for builds. |
| `post-correction-integration-prime.sh` | 2026-07-29 | post-correction integration prime. |
| `pre-response-context.sh` | 2026-05-20 | thin doorman pointing to the OS. |
| `promise-anchor-surface.sh` | 2026-07-18 | read all open promise markers and surface |
| `register-awareness-surface.sh` | 2026-07-28 | surface the register signal from each |
| `verify-claim-prime.sh` | 2026-07-30 | compose-start prime for the VERIFY-CLAIM |
| `visrama-anchor-surface.sh` | 2026-07-18 | if the previous assistant turn close-reached, |
| `wallclock-source-prime.sh` | 2026-07-30 | compose-start prime for wallclock-source |
| `wwnd-choice-prime.sh` | 2026-07-30 | WWND (What Would Nyarlathotep Do) prime at |

### called by another script  (3)

| automation | last touched | purpose |
|---|---|---|
| `_lib.sh` | 2026-07-28 | Shared helpers for .claude/hooks/*.sh — sourced, not executed. |
| `post-merge-doc-fix.sh` | 2026-07-16 | WIRED VIA .git/hooks/post-merge — installed by setup/setup-hooks.sh, |
| `post-push-audit-visibility.sh` | 2026-07-16 | INTENTIONALLY UNWIRED (2026-07-16, Aletheia cold-audit finding #2): |

### glob-dispatch (post-commit)  (2)

| automation | last touched | purpose |
|---|---|---|
| `post-commit-audit-visibility.sh` | 2026-07-16 | WIRED VIA .git/hooks/post-commit DELEGATOR — installed by setup/setup-hooks.sh. |
| `post-commit-auto-integrate-corrections.sh` | 2026-07-16 | WIRED VIA .git/hooks/post-commit DELEGATOR — installed by setup/setup-hooks.sh. |

---

## Regenerating

```bash
python scripts/generate_automation_register.py
```

`--check` exits non-zero when the file has drifted, for wiring into a pre-commit or CI step.

Run after adding, removing, or rewiring any automation. The wired column is computed from settings.json, the installed git hooks, and glob-dispatch prefixes — it reflects what is actually reachable, not what is supposed to be.
