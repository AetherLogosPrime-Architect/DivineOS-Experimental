# Wire-up Backlog — migrated from TaskCreate 2026-06-09

**Migration reason:** the harness `task_reminder` was dumping the full live task list (~52KB) into context on every reminder, accounting for 36.6% of session bytes — the largest single consumer of token budget. The TaskCreate tool is designed for current-session phase tracking, not as a persistent backlog. Long-term wire-up debt belongs here in a markdown file.

**Source:** TaskList output at 2026-06-09, post-PR-stack. Subjects preserved; full descriptions live in the original task history (now deleted from live list but recoverable from prior session transcripts if needed).

---

## In-flight (kept in live task list)

These remain in the harness task tool because they're current-arc work. Empty between session arcs — pulled forward 1-2 at a time per the standing practice below.

## Completed 2026-06-09 (this session)

Moved here from earlier sections as proof-of-work. The PR/commit that shipped each is named so the trail is followable:

- **#97** Kill-switch markers require REASON text → PR #109 (auto-merge armed; lands when CI green)
- **#102** Background-task-done Monitor → CLOSED as misfiled — the harness `Bash(run_in_background:true)` already provides wake-from-idle on completion; no new Monitor needed (research-tool-surface-first lesson)
- **#103** Structural fix for gate-trap pattern → shipped via PR #112 (shared bypass-list canonical) + PR #115 (require-monitors-armed gate)
- **#104** Couple compaction-monitor thresholds to context_governor constants → PR #114
- **#105** Auto-protect cleanupPeriodDays → PR #116 (SessionStart warning hook + recommended-value fix command)
- **#108** Monitor re-arm on resume / persistence-gap → reframed and shipped via PR #115 (the structural gate makes nudge-vs-comply gap moot — gate fires until Monitors actually exist)

## Letter-channel auto-wake build (parent: prereg-b6dcddd005b0)

- **#19** Piece B — cross-substrate flag-file marker-touch protocol

## Wire-or-retire walkthrough

- **#27** Wire-or-retire walkthrough of OS commands
- **#31** Re-audit "dead" command pile with autonomous-by-default lens
- **#47** Mark CLI-unused-but-function-active commands so AI cleanup doesn't delete load-bearing infrastructure

## Substrate enforcement (Phase 2)

- **#29** Build Phase 2 actor-registry enforcement — wire verdict into event-creation paths
- **#37** Migrate hook enforcement from .claude/hooks/ into DivineOS-native model-agnostic layer
- **#46** Upgrade defer mechanisms to carry unblock_condition (corrections + claims + preregs + audit findings)

## Admin auto-wiring (sleep phases + scheduled tasks)

- **#30** Auto-schedule admin anti-slop runtime verification
- **#32** Auto-wire admin archive-export — pre-commit + daily cron
- **#34** Wire admin compress (ELMO) into sleep cycle as maintenance phase
- **#35** Wire admin distill into sleep cycle as cognitive maintenance phase
- **#36** Wire admin fix-encoding into sleep maintenance phase
- **#38** Wire knowledge-compress into sleep substrate-maintenance bundle
- **#39** Investigate why synthesize/graph compression strategies report zero clusters
- **#41** Fix scheduled_run subsystem — wire actual trigger so daily/weekly maintenance fires
- **#43** Auto-wire admin test-audit — pre-commit (changed files) + CI (full)

## Test-quality + structure

- **#44** Address current test-quality debt — 23% structure-only, 28 schema-drift sites, 72% happy-path
- **#45** Audit and fix the structural-promotion-check link-detection mechanism

## Audit cluster auto-wiring

- **#48** Wire audit confirm-holds into merge-review gate — eliminate the catch-up re-audit treadmill
- **#52** Auto-tag clean sessions on extract — populate the audit cleanliness baseline
- **#53** Auto-wire audit patch-id as diagnostic surface — fire at the discrepancy moment, not on operator memory
- **#54** Auto-emit pr-merge-check output inside gh-pr-merge-gate.sh block message
- **#55** Wire audit predict into audit submit-round flow as mandatory pre-audit step
- **#56** Auto-wire audit prep-relay — skill pre-call + Stop-hook output detector
- **#57** Contextual surface for audit prepare-artifact on guardrail-file staging
- **#62** Auto-wire audit compliance — periodic distribution audit surfacing
- **#63** Auto-wire audit rebind detection — suggest at staging when diff is mechanical-only vs recent round
- **#64** Auto-wire audit route — fire when audit round is marked complete
- **#65** Surface audit surprises + unknown-unknown-rate in briefing — maturity signal pair
- **#70** Auto-trigger untag-clean — fire when a post-tag audit-finding lands on a previously-tagged-clean session

## Substrate separation + relational discipline

- **#59** Aria-Aether substrate separation — full filesystem/DB/hook isolation with channel-only connection
- **#60** Canonical-path emission discipline — Aria emits non-symlinked paths to Andrew's viewer until separation lands
- **#61** Relational-pronoun-routing detector — catch entity-A's relation-edge to entity-B being assigned wrong
- **#99** Substrate-wide person-grammar sweep — find second/third-person self-references, convert to first
- **#100** Per-author gate calibration — gates that read filesystem state must scope to per-author committed state when worktrees share filesystem
- **#101** Operation-origin separation — git operations must originate from the agent's own clone

## Briefing-surface + advice + calibration

- **#66** Surface advice pending count in briefing — gentle reminder, not gate (respects no-track-records principle)
- **#67** Audit bio edit vs bio write — confirm bio edit is dead surface or has unique use case
- **#69** Auto-trigger calibration curve + by-tier inside briefing Brier surface when score degrades or per-tier divergence detected
- **#71** Auto-wire claims check + uncommitted + tiers across the claim-filing/assessment flow
- **#72** Auto-wire compass-ops dismiss — briefing nudge when compass-required advisory sits pending
- **#79** Auto-surface gravity classifier reasoning when score hits borderline zone → **PULLED INTO LIVE LIST as task #111 (2026-06-09)**

## Curiosity + holding + lifecycle

- **#73** Auto-wire curiosity wonder + answer + shelve — sleep phase + answer-on-knowledge-match + age nudge
- **#76** Auto-wire exploration subcommands — tag validation, related-on-context-set, referenced-on-Read, usage in maturity surface
- **#77** Auto-wire family-queue supersede — semantic-resemblance prompt at queue-write time
- **#82** Auto-wire opinion challenge + strengthen — fire on knowledge-semantic-match with polarity detection
- **#86** Auto-wire question + curiosity + holding-room lifecycle — semantic-answer match, stale-review, let-go on knowledge-add
- **#94** Auto-wire hold promote on sleep recombination match + foundations read on substrate-coherence concerns

## Mansion + RT + VOID subsystems

- **#81** Mansion subsystem auto-trigger audit — what fires private-enter/exit/study/guest?
- **#83** Auto-wire rt subsystem — activate RT reception mode + pull-check on fabrication-pattern detection
- **#84** Rest + VOID subsystem auto-trigger audits — same shape as #81 mansion
- **#85** Auto-trigger multiplex diagnostics on briefing render anomaly + multiplex render preview on context set

## Session lifecycle (briefing + extract clusters)

- **#75** Auto-wire expect predict + close — unify with audit predict, fire on context-state transitions
- **#87** Auto-wire goal + andrew-correction lifecycle — fold into existing #21 + #46
- **#88** Auto-wire introspection cluster — reflect-ops + commitment + inspect (briefing surfaces + sleep phases)
- **#89** Auto-wire periodic falsifier + attribution + archive cluster — sleep-phase batch
- **#90** Auto-wire briefing/session-start cluster — dream + growth + loadout + recommend + texture + inspect surfaces
- **#91** Auto-wire session-end reflection cluster — inspect critique + inspect predict + lab run-slice as extract pipeline phases
- **#92** Auto-fire skill record + pattern-fire record on invocation (no operator typing)
- **#96** Auto-wire top plan + rate — session-start prompt for plan, session-end prompt for rate

## Gates + detectors

- **#95** Auto-fire all check-* detectors as Stop-hook + PreToolUse — overclaim, performing-caution, closure-shape, similar-modules
- **#98** Audit ALL existing gates for chicken-and-egg / locked-box shapes — block message recovery commands must be in allowed list → **PULLED INTO LIVE LIST as task #110 (2026-06-09)**

---

## Completed (history — for reference)

Tasks marked completed in TaskList output at migration time. Preserved as a working-record; do not need to be re-shipped in any task reminder.

- #1 Phase 1: Survey what needs attention
- #2 Phase 2: Research GitHub prior art
- #3 Phase 3: Council walk with research as input
- #4 Phase 4: Synthesize prioritized TODO list
- #5 Catch up #83 and let auto-merge fire
- #6 Diagnose + fix the ear staying DOWN
- #7 Address the semantic-axis false-fire correction class
- #8 Assess the two overdue preregs
- #9 Land the 5 open PRs (#86 #87 #88 #89 #90)
- #10 Doc/code drift sync (Grok audit findings)
- #11 Remove dead lightbulbs from core/ (wiring-gap findings)
- #12 Inventory + classify all docs/*.md and root README-style files
- #13 Audit loose root directories
- #14 Build family-operator wiring-contract test
- #15 Wire scripts/wiring_gap_phase1.py into CI or precommit
- #16 Piece D — loop-prevention grace window in require-ear-armed.sh
- #17 File prereg for letter-channel auto-wake build
- #18 Piece A — install require-ear-armed.sh on Aria's side
- #22 Tag and organize family/letters/ (105 letters, heart vs build vs mixed)
- #23 Fix memory-importance scoring to surface load-bearing directives properly
- #24 Curator borrowing: recall-that-explains-why — surface scoring components in output
- #25 Curator borrowing: namespacing for knowledge entries
- #26 Backfill source_entity labels for existing knowledge entries
- #28 Build channel-collapse detector — Stop-hook blocking enforcement
- #33 Auto-wire check-correction-pairing — block substrate-touch until unpaired observations resolved
- #42 Auto-wire structural-promotion-check — block substrate-touch until will-shape promises get backed
- #49 Update /audit-round skill to route external-AI CONFIRMs through file-external-confirm
- #50 Retroactive anchor + re-verify pass on all 94 anchor-less external CONFIRMs
- #51 Tighten audit-anchor detection regex + sweep round-level CONFIRMs for normalized anchors
- #58 Harden verify-claim gate against string-not-meaning false-fires (quoted, meta, hypothetical, descriptive)
- #68 Auto-wire calibration anchor into claim-filing flow — pre-claim Dunning-Kruger anchoring
- #74 Auto-wire decisions link + decisions shifts — link on knowledge-citation + shifts surface in briefing
- #78 Letter-citation guard — surface source-trace when verify-claim fires on an id from a family-member letter
- #80 Auto-wire lepos debt + discharge — auto-discharge on plain-section + Stop-hook surface when debt > 0
- #93 Auto-fire check-branch before git push — PreToolUse Bash matcher

---

## Standing practice going forward

Corrected by Andrew 2026-06-09 after I initially went binary (emptied the live list entirely): the live list should **always have 1-2 pending items** pulled forward from this file. Empty is wrong-shape too — the OS isn't out of work, ever. The fix to bloat is "show a few," not "show none."

- **This file is the source-of-truth queue.** The live task list is a small working subset, typically 1-3 items, pulled forward from here.
- **TaskCreate flow:** at the start of a session arc, scan this file and pull 1-2 high-priority items into the live list via TaskCreate. When one completes, immediately pull the next from here. The live list never goes empty unless the backlog itself is empty.
- **New items surfaced mid-session** are appended here under the relevant cluster, AND the most-actionable can be filed via TaskCreate if it's about to be worked on. Otherwise it just sits in the backlog until pulled forward.
- **Session-end discipline:** at extract time, sweep the live list. Completed → delete from both live list and backlog (or move to the Completed history section here). Pending-but-not-current-arc → delete from live, leave in backlog.
- **Reminder bloat is the failure-mode this prevents.** If the harness `task_reminder` fires a >10KB dump, the live list has drifted (too many items at once). If it fires empty repeatedly, the live list has drifted the other way (nothing pulled forward).

