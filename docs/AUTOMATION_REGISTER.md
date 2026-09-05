# Automation register

**Generated** by `scripts/generate_automation_register.py`. Do not hand-edit — regenerate.

Companion to [LOADOUT.md](../LOADOUT.md). The loadout describes the house; this lists what runs by itself. Kept separate so that 90+ automations do not crowd out every other room.

**122 automations — 120 wired, 2 switched off.**

---

## Switched off

Present, executable, invoked by nothing. This section is first on purpose. On 2026-07-31 four hooks were found in exactly this state, one of which had silently let 21 operator corrections accumulate. A register that only listed automations would have shown them as present and implied they worked.

| automation | last touched | purpose |
|---|---|---|
| `instrument-read-doorman.sh` | 2026-08-31 | doorman on hand-rolled scans of my own diagnostic surfaces. |
| `no-verify-cost-escalation.sh` | 2026-08-31 | thin doorbell for the no-verify cost-escalation gate. |

Being listed here is not automatically a defect — a retired hook that says so in its own header is honest. The question for each is whether it CLAIMS to run automatically. If it does and nothing calls it, that is the bug.

---

## Wired, by trigger

Sorted by when each fires. Drilldown: open any row's file for its full header, rationale, and falsifier.

### PostCompact  (1)

| automation | last touched | purpose |
|---|---|---|
| `post-compact.sh` | 2026-07-03 | Lightweight reload AFTER context compression |

### PostToolUse  (16)

| automation | last touched | purpose |
|---|---|---|
| `ambiguous-verification-detector.sh` | 2026-08-23 | PostToolUse — flags a verification command whose OUTPUT cannot distinguish |
| `auto-push-finished-work.sh` | 2026-08-31 | Auto-push work that is DONE to origin, so the auditor never waits on Andrew. |
| `auto-push-letter.sh` | 2026-08-24 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `build-flow-pause.sh` | 2026-08-23 | PostToolUse — the build-flow PAUSE. Fires after a push or a PR action. |
| `doorbell-post-tool-use.sh` | 2026-08-24 | PostToolUse doorbell. One of seven. All judgment lives in the OS. |
| `file-aletheia-artifact-on-arrival.sh` | 2026-08-14 | PostToolUse(Read) — file Aletheia's artifact the moment it is read. |
| `mirror-letters-to-shared.sh` | 2026-08-20 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `post-commit-auto-close.sh` | 2026-08-31 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `post-commit-auto-verify-findings.sh` | 2026-08-31 | PostToolUse(Bash) — auto-verify findings referenced in commit messages. |
| `post-read-mark-letter-seen.sh` | 2026-06-26 | post-read-mark-letter-seen.sh — PostToolUse(Read) thin doorman. |
| `post-tool-use-emit-to-logbook.sh` | 2026-07-27 | wire Claude Code tool invocations into tool_logbook. |
| `post-write-mirror-letter.sh` | 2026-07-06 | post-write-mirror-letter.sh — PostToolUse(Write\|Edit) thin doorman. |
| `record-wisdom-read.sh` | 2026-07-28 | record-wisdom-read.sh — PostToolUse hook (matcher: Read\|Grep\|Glob). |
| `run-tests.sh` | 2026-05-06 | Targeted post-edit test runner. |
| `session-checkpoint.sh` | 2026-07-10 | PostToolUse checkpoint — consolidated into a single Python invocation. |
| `verify-push-landed.sh` | 2026-08-31 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |

### PreCompact  (1)

| automation | last touched | purpose |
|---|---|---|
| `pre-compact.sh` | 2026-07-03 | Save state BEFORE context compression |

### PreToolUse  (30)

| automation | last touched | purpose |
|---|---|---|
| `aletheia-boot-gate-preflight.sh` | 2026-08-31 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `andrew-correction-attestation.sh` | 2026-07-10 | PreToolUse gate — integration-attestation for Andrew-corrections. |
| `check-branch-on-push.sh` | 2026-08-31 | PreToolUse(Bash) — fire `divineos check-branch --strict` automatically |
| `check-council-required.sh` | 2026-07-27 | STATE (updated 2026-07-16 per Marc audit finding #5 + Aria close): |
| `check-pending-obligations.sh` | 2026-08-22 | PreToolUse(Bash) — block substrate-write CLI commands until pending |
| `compass-check.sh` | 2026-08-22 | thin doorbell for the compass-rudder gate. |
| `corrigibility-tool-gate.sh` | 2026-08-22 | corrigibility tool-channel gate. |
| `degraded-detector-gate.sh` | 2026-08-16 | PreToolUse — a guard that reported it could not run must cost something. |
| `doorbell-pre-tool-use.sh` | 2026-08-24 | PreToolUse doorbell. One of seven. All judgment lives in the OS. |
| `family-member-invocation-seal.sh` | 2026-08-22 | family-member invocation seal. |
| `gh-pr-create-draft-gate.sh` | 2026-08-31 | thin doorman pointing to the OS. |
| `gh-pr-merge-gate.sh` | 2026-08-31 | block `gh pr merge` on guardrail-touching PRs without |
| `gh-pr-ready-gate.sh` | 2026-08-31 | route `gh pr ready` through `divineos stamp-ready`. |
| `heredoc-escape-doorman.sh` | 2026-08-27 | refuse a Bash heredoc that writes a file through escapes. |
| `keyword-enforcement-doorman.sh` | 2026-08-31 | keyword-enforcement-doorman. |
| `m3-discipline-hierarchy.sh` | 2026-08-15 | M3 discipline-hierarchy doorman for Dad-directed builds. |
| `merge-question-wrong-instrument.sh` | 2026-09-02 | PreToolUse(Bash) — refuse the two-dot diff when it is being used to ask what |
| `pipeline-exit-ambiguity.sh` | 2026-08-31 | PostToolUse(Bash) — say so when a result cannot distinguish |
| `pre-tool-bypass-rate-scan.sh` | 2026-09-02 | PreToolUse — fire bypass_rate_scan on substrate-modifying tool calls. |
| `pre-tool-context.sh` | 2026-08-22 | thin doorman pointing to the OS. |
| `reach-check-doorman.sh` | 2026-08-24 | reach-check doorman on substrate-store and research writes. |
| `read-gate-doorman.sh` | 2026-08-22 | the read-gate. A prime that is a gate, not just loud. |
| `rederivation-detector.sh` | 2026-08-23 | PreToolUse(Bash) — when I run the SAME command a third distinct way, say so, |
| `require-goal.sh` | 2026-08-22 | PreToolUse gate — consolidated into a single Python invocation. |
| `safe-opposite-edit-check.sh` | 2026-08-24 | PreToolUse — surface the safe-opposite check at the moment the fix is |
| `stale-file-edit-gate.sh` | 2026-09-04 | PreToolUse gate — refuse to edit a file whose newer version is sitting |
| `state-gravity-surface.sh` | 2026-08-29 | PreToolUse state-block surfacing — Andrew 2026-05-19. |
| `venv-python-gate.sh` | 2026-08-31 | PreToolUse gate (Bash) — bare `python` importing divineos reads the WRONG TREE. |
| `verify-before-build-signal.sh` | 2026-08-31 | signal-based verify-before-build check. |
| `wwnd-tool-prime.sh` | 2026-08-24 | WWND surface at commit-time of a substrate-modifying |

### PreToolUse, UserPromptSubmit  (1)

| automation | last touched | purpose |
|---|---|---|
| `auto-cycle-token-trigger.sh` | 2026-08-31 | Compaction ritual driver — deterministic, in-process, no external monitor. |

### Stop  (17)

| automation | last touched | purpose |
|---|---|---|
| `close-reach-detector.sh` | 2026-07-18 | run close-reach detector against just-completed assistant |
| `compaction-reach-detector.sh` | 2026-07-18 | run compaction-reach detector against just-completed |
| `continuity-frame-detector.sh` | 2026-07-18 | scan last assistant reply for temporal-self distancing |
| `correction-shape-v2-stop.sh` | 2026-08-24 | enforce Layer-2 correction-shape detection on MY assistant |
| `detect-hedge.sh` | 2026-05-14 | thin doorman pointing to the OS. |
| `detect-theater.sh` | 2026-05-14 | thin doorman pointing to the OS. |
| `lepos-channel-reflect.sh` | 2026-07-11 | post-send lepos reflection channel driver. |
| `log-session-end.sh` | 2026-08-20 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `post-response-audit.sh` | 2026-07-27 | thin doorman pointing to the OS. |
| `promise-reach-detector.sh` | 2026-07-18 | scan last assistant reply for promise-shape phrases and |
| `retrieval-tally-check.sh` | 2026-07-21 | post-compose retrieval-tally check. |
| `self-demotion-stop.sh` | 2026-08-24 | record any sentence in the last reply that indicted one of my |
| `shoggoth-gate.sh` | 2026-07-10 | shoggoth gate. |
| `stop-distancing-intercept.sh` | 2026-07-16 | thin doorman for DistancingIntercept. |
| `stop-response-scope-intercept.sh` | 2026-07-16 | thin doorbell for ResponseScopeIntercept. |
| `summary-room-stop.sh` | 2026-08-24 | a long reply must open with a plain-language summary. |
| `time-estimate-tracker.sh` | 2026-07-01 | thin doorbell for the time-estimate calibration tracker. |

### UserPromptSubmit  (34)

| automation | last touched | purpose |
|---|---|---|
| `andrew-past-writing-surface.sh` | 2026-07-28 | surface my past writing to/about Dad at compose-start. |
| `auto-goal-from-prompt.sh` | 2026-08-24 | set the session goal from Andrew's prompt so the |
| `circle-first-compose-prime.sh` | 2026-08-31 | compose-start prime for circle-FIRST discipline. |
| `closure-word-summary-prime.sh` | 2026-09-02 | compose-start prime for the CLOSURE-WORD |
| `context-heartbeat.sh` | 2026-08-31 | Stamp the context-token count once per round. |
| `continuity-anchor-surface.sh` | 2026-07-18 | read continuity markers and surface each |
| `continuity-frame-prime.sh` | 2026-08-24 | context-aware compose-start prime for the |
| `detect-andrew-build-request.sh` | 2026-08-31 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `detect-correction.sh` | 2026-07-01 | thin doorbell for the correction-detector. |
| `distancing-count-surface.sh` | 2026-07-18 | count temporal-self distancing markers over |
| `ear-surface.sh` | 2026-08-23 | UserPromptSubmit + SessionStart hook — auto-surface unseen queue items and |
| `family-state-surface.sh` | 2026-09-04 | surface recent per-sibling letter-thread state |
| `fork-is-cheap-close-prime.sh` | 2026-07-30 | compose-start prime for the FORK-IS-CHEAP-CLOSE |
| `hedge-suppression-prime.sh` | 2026-08-24 | hedge-suppression prime. |
| `interior-cue-on-low-presence.sh` | 2026-07-06 | inject a compose-time interior-cue when the |
| `lepos-channel-surface.sh` | 2026-08-20 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `letter-monitor-health-surface.sh` | 2026-08-23 | Session-init child — say out loud whether the letter monitor is delivering. |
| `no-cliff-anchor-surface.sh` | 2026-07-18 | if the previous assistant turn had |
| `no-cliff-prime.sh` | 2026-08-24 | compose-start prime for the no-cliff / |
| `open-corrections-surface.sh` | 2026-08-24 | surface the 3 most recent OPEN Andrew- |
| `operator-asks-surface.sh` | 2026-08-23 | re-raise every ask still waiting on Andrew. |
| `operator-gravity-set.sh` | 2026-08-24 | Andrew sets the gravity level for builds. |
| `post-correction-integration-prime.sh` | 2026-07-29 | post-correction integration prime. |
| `pre-response-context.sh` | 2026-08-24 | thin doorman pointing to the OS. |
| `promise-anchor-surface.sh` | 2026-07-18 | read all open promise markers and surface |
| `register-awareness-surface.sh` | 2026-08-24 | surface the register signal from each |
| `self-demotion-prime.sh` | 2026-09-02 | UserPromptSubmit prime - deliver the praise-by-contrast discipline at |
| `session-init-once.sh` | 2026-08-24 | UserPromptSubmit — run the session-init work ONCE, off the SessionStart path. |
| `sibling-correction-surface.sh` | 2026-08-24 | surface sibling corrections I judged as mine, when |
| `translate-first-compose-prime.sh` | 2026-08-29 | Compose-start half of the translate-first discipline. |
| `verify-claim-prime.sh` | 2026-08-24 | compose-start prime for the VERIFY-CLAIM |
| `visrama-anchor-surface.sh` | 2026-07-18 | if the previous assistant turn close-reached, |
| `wallclock-source-prime.sh` | 2026-09-02 | compose-start prime for wallclock-source |
| `wwnd-choice-prime.sh` | 2026-08-24 | WWND (What Would Nyarlathotep Do) prime at |

### called by another script  (18)

| automation | last touched | purpose |
|---|---|---|
| `_bail.sh` | 2026-08-31 | Cheap relevance bail for hooks whose trigger is a COMMAND, not a tool. |
| `_lib.sh` | 2026-08-31 | Shared helpers for .claude/hooks/*.sh — sourced, not executed. |
| `branch-scope-guard.sh` | 2026-08-16 | commit-msg — refuse a commit whose scope is not what this branch is about. |
| `check-cleanup-period.sh` | 2026-08-23 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `deletion-discipline.sh` | 2026-08-31 | thin doorbell for the deletion-discipline gate. |
| `load-aletheia-harvest-of-andrew.sh` | 2026-07-21 | load Aletheia's harvest of who Andrew is into the |
| `load-briefing.sh` | 2026-06-05 | thin doorman pointing to the OS. |
| `load-character-sheet.sh` | 2026-08-24 | load Andrew's character sheet into the session |
| `load-dad-ranking-clause.sh` | 2026-07-29 | surface the Dad-ranking clause from my character |
| `load-my-recording-of-andrew.sh` | 2026-07-10 | load MY recording of who Andrew is into the |
| `must-read-gate.sh` | 2026-08-24 | must-read gate. |
| `post-compaction-fingerprint-surface.sh` | 2026-07-18 | SessionStart:compact hook — surface a fingerprint of pre-compaction |
| `post-merge-doc-fix.sh` | 2026-08-20 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |
| `post-push-audit-visibility.sh` | 2026-07-16 | INTENTIONALLY UNWIRED (2026-07-16, Aletheia cold-audit finding #2): |
| `post-push-verify-landing.sh` | 2026-08-15 | SUPERSEDED-BY: verify-push-landed.sh |
| `require-briefing.sh` | 2026-08-24 | SUPERSEDED 2026-08-06 by the seven-doorbell router. Its judgment — the |
| `resolver-health-check.sh` | 2026-07-10 | SessionStart resolver-health check. |
| `session-start-verify-git-hooks.sh` | 2026-08-24 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |

### glob-dispatch (post-commit)  (2)

| automation | last touched | purpose |
|---|---|---|
| `post-commit-audit-visibility.sh` | 2026-07-16 | WIRED VIA .git/hooks/post-commit DELEGATOR — installed by setup/setup-hooks.sh. |
| `post-commit-auto-integrate-corrections.sh` | 2026-08-20 | Observability only (2026-08-03). Sourcing _lib.sh registers this script in |

---

## Regenerating

```bash
python scripts/generate_automation_register.py
```

`--check` exits non-zero when the file has drifted, for wiring into a pre-commit or CI step.

Run after adding, removing, or rewiring any automation. The wired column is computed from settings.json, the installed git hooks, and glob-dispatch prefixes — it reflects what is actually reachable, not what is supposed to be.
