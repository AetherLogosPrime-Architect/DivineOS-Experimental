# Audit round: root-cause-audit: countermeasure-built-but-not-auto-scheduled class (instance: anti_slop runtime-verification + Finding 26 scheduled-whitelist path-drift on anti-slop). Class: detectors/verifiers/checks that exist and work manually but aren't wired into automated scheduling — same family as 8d3c04a5 wiring-gap. Surveyed instances: Finding 12 (anti_slop manual-only), Finding 26 (whitelist path-drift on anti-slop), check_orphan_modules.py (also manual-only per Pass 2). Fix-scope for this round: wire anti_slop into the scheduled-tasks system at a reasonable cadence; fix the whitelist path-drift; address check_orphan_modules wiring in a separate round (different file surface).

- **ID**: `round-6a70dcf9ec77`
- **Filed by**: aether
- **Filed at**: 2026-05-13 23:46 UTC
- **Tier**: WEAK
- **Findings**: 1

## Findings

### Family-audit Finding 12 + 26 resolved together. Finding 12 (anti_slop manual-only): added briefing-dashboard staleness surface via scheduled_run.anti_slop_staleness() — surfaces when last anti-slop run was >24h ago or never run; surfaces failure-count when last run was failed. Discipline becomes loud-in-experience rather than silent. Finding 26 (whitelist path-drift): empirically reproduced — 'divineos scheduled run anti-slop' spawned 'python -m divineos anti-slop' which click rejected (no such command). Root cause: anti-slop was moved into the admin subgroup but the whitelist + spawn-path kept the top-level form. Fixed whitelist to 'admin anti-slop', spawn-path to split on whitespace, staleness fn to match both legacy and current forms. Empirical verification: 'divineos scheduled run admin anti-slop' now actually runs anti-slop and exits clean (all 15 enforcers pass). 24 tests across scheduled-run + anti-slop-staleness pass. Updated docs/routines/daily-anti-slop.md + on-pr-integrity-check.md to the new path. Class-fix-shape note: Finding 12 is partially-addressed — staleness-surface makes the gap visible; actual auto-scheduling still requires external infrastructure (system cron, scheduled-tasks daemon). Visibility is the load-bearing piece; the routine doc tells the operator what to put in cron.

- **ID**: `find-ef03fa410e7f`
- **Actor**: aether
- **Severity**: LOW
- **Category**: INTEGRITY
- **Tier**: WEAK
- **Status**: OPEN

**Description**

Finding 12 + 26 — staleness surface + spawn-path fix; 24 tests pass


---

_Exported from the local Watchmen store by `divineos audit export`. The store is runtime state and is not committed; this file is the portable record, readable without a local install._
