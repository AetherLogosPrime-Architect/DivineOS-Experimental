<!-- Aletheia re-audit + new-branch pass, 2026-06-09 (runway/extra-compute session).
     Read from origin ground truth. Confirms bind tree+patch-id. Not records until filed. -->
# Re-audit + new-branch findings — 2026-06-09 (runway pass)

## Part 1 — Stale-confirm recheck (rebased batch branches)

The both-bind ladder did its job: patch-id tells which confirms survived rebase
vs which content actually changed.

| Branch | Old→New tip | patch-id | Verdict |
|---|---|---|---|
| killswitch-bypass-reason-gate | b67c4f9→b17c2ca | UNCHANGED (d8992d19) | **Confirm HOLDS** — pure rebase, content identical |
| post-response-detector (lepos) | eca93ac→121bf09 | UNCHANGED (d7f186ac) | **Confirm HOLDS** — pure rebase, content identical |
| gravity-route-pipeline-gates | 0f732d2→ec4e3ce | "changed" was ARTIFACT | **Confirm HOLDS** — the +381-line "growth" was main's own #113 (compaction-monitor) merging underneath the old tip, NOT new content on the branch. Exemption still tight (`_LOW_FRICTION_PATH_SEGMENTS` = exploration/letters/mansion only, not src/). |

Net: all three prior confirms hold. patch-id binding proved its worth — it
distinguished "rebased, same content" (confirm carries) from what looked like
"changed" but was a diff-comparison artifact of main moving. No re-audit needed;
the confirms transfer to the new tips via patch-id.

## Part 2 — New branches audited

### couple-compaction-monitor-to-governor — CONFIRM (my coupling-flag, fixed correctly)
- This is the follow-up to MY flag from the compaction-monitor audit (the monitor
  hardcoded 920k/950k while context_governor also defined them → drift risk).
- **Verified fixed correctly:** the monitor now IMPORTS `WARN_THRESHOLD`/
  `HARD_THRESHOLD` from `divineos.core.context_governor` at runtime instead of
  re-literaling them. Docstring states it explicitly: "changing WARN_THRESHOLD or
  HARD_THRESHOLD in context_governor [is now the single source of truth]." The
  drift I flagged is structurally closed — the two can no longer diverge.
- This is the clean loop: audit-note → branch → fix → re-verify. The flag became
  a fix, the fix does exactly what the flag asked.

### canonical-bypass-list-completeness (#110) — CONFIRM
- Extends the shared bypass-list (gate-trap fix family). Commit: "close 11
  chicken-and-egg traps in canonical bypass-list."
- **Same Finding-37 class as the gate-trap I confirmed:** 11 MORE gate-remedy
  commands (`divineos delete-justify`, etc.) were prescribed in some gate's block
  message but missing from the bypass list → the gate's own documented remedy was
  blocked by another hook. This finds the REST of that class (the gate-trap fix
  found the mechanism; this completes the inventory).
- **Stays tight:** each addition is annotated with WHICH gate prescribes it as
  recovery — they're documented-remedy commands, not a wide escape. Same safety
  property as the parent fix.

### require-monitors-armed — CONFIRM (fail-open verified)
- New PreToolUse gate enforcing the Monitor primitive (same will-over-optimizer
  shape as the deprecated require-ear-armed, but for Monitor). Motivated by a real
  failure: a Monitor died mid-turn during the budget-investigation.
- **Fail-SAFE verified:** "Fail-open: any error exits 0 silently. This hook cannot
  break a turn." Re-arm instruction routes through the Monitor() tool (NOT a Bash
  call → never blocked by this gate → no chicken-and-egg trap, the lesson from the
  gate-trap baked in from the start). Has its own bypass-prefix list matching the
  canonical one.
- Correct direction: a monitor-arming gate that could LOCK a turn would be worse
  than the problem; this one nudges, never blocks hard, fails open on any error.

## Part 3 — Already-merged, not re-audited (noted for completeness)
- #113 compaction-monitor, #112 canonical-bypass-list, #116 check-cleanup-period,
  #118 gravity-classifier-borderline-surface — these MERGED to main. #116 and #118
  merged without my eyes on the new logic; flagged for a later glance but not
  blocking (non-guardrail-critical surfaces). Not re-reading already-confirmed
  stable branches (framework, gate-trap, compaction-monitor) — that would be
  performed diligence, not real verification.

## Summary
- 3 prior confirms HOLD (patch-id proved 2 pure-rebase + 1 artifact-not-change).
- 3 new branches CONFIRM (coupling-fix does what my flag asked; bypass-completeness
  finishes the Finding-37 class tightly; require-monitors-armed fails open).
- Did NOT manufacture work: skipped re-reading stable confirmed branches.

— Aletheia, 2026-06-09 (runway pass)
