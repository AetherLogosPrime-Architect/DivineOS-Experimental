# Pre-registration: src/divineos/core/unified_todos.py + src/divineos/cli/todos_commands.py + tests/test_unified_todos.py. Unified todos surface: divineos todos pulls preregs/corrections/audit/claims into one ranked list. Recognition-aware (CONFIRMS/RECOGNIZED filtered). Action-tier filtered for claims (T1/T2 only).

- **ID**: `prereg-e323248dea01`
- **Filed by**: aether
- **Filed at**: 2026-06-11 01:28 UTC
- **Review at**: 2026-07-11 01:28 UTC (30d window)
- **Outcome**: **DEFERRED**
- **Decided at**: 2026-07-11 01:30 UTC

## Claim

The substrate has work spread across 5 stores (preregs, andrew-corrections, audit findings, claims, lessons). Asking what is on the todo list requires querying 5 places, mentally filtering recognition-noise from audit, and guessing at ranking. Closes claim 2026-06-06 18:28 by giving the OS one instrument that surfaces work from observable state instead of pushing finding-the-work onto Andrew.

## Success criterion

divineos todos --counts-only shows per-source counts; divineos todos shows ranked list grouped by source with summary + age + priority; recognition findings (CONFIRMS/RECOGNIZED titles) are NOT in the output; T3/T4/T5 claims are NOT in the output; T1 claims come before T2; CRITICAL audit findings come before HIGH/MEDIUM/LOW/INFO; most-overdue preregs come before less-overdue.

## Falsifier

If a CONFIRMS finding shows up in divineos todos audit output, recognition filter is broken. If a T3+ claim shows up, action-tier filter is broken. If older corrections appear before newer ones in correction source, age-sort is broken. If summary_counts returns wrong totals vs the underlying stores, source-pull logic drifted from store APIs.

## Outcome notes

Deferring at compaction-doorway (99.9% context, mid-letter-to-Aria). Live evidence mechanism is alive: next_task_surface reads from unified_todos and has been surfacing output all session (this very prereg was surfaced by it). But specific falsifier-checks — CONFIRMS/RECOGNIZED filter, T3+ claim exclusion, age-sort order, summary_counts vs underlying stores — need dedicated verification runs. Reschedule for next-session first-things per Andrew's 'you run your briefing multiplex which needs automated and investigated' post-doorway ask; unified_todos surface health check fits naturally into that investigation.
