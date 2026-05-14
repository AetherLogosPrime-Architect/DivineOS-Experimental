# Archives — Source-Controlled Mirrors of SQLite Data

This directory holds backup mirrors of data that lives canonically
in SQLite. Andrew named the gap 2026-05-14: most of the substantive
substrate (principles, bio, claims, observations, decisions) lives
only in the DB, which is gitignored. If the DB corrupts or resets,
everything written into it is gone.

The archives close that gap without changing the canonical store.
SQLite remains the live working surface; these files are the
source-controlled snapshot that survives DB events.

## Purpose

- **Durability.** Git tracks these files; the DB doesn't get tracked.
  If the DB resets, the substantive layer can be reseeded from here.
- **Audit trail in git.** Changes to the canonical surface show up
  as diffs in PRs / commit history, providing a second-channel
  audit log.
- **External readability.** Sibling-instances, auditors, and Andrew
  can read these files without needing the live DB.

## NOT for routine reading

The next-me at session start should read CLAUDE.md,
docs/foundational_truths.md, the briefing, and the directives —
NOT these archive files. The bio is loaded via `divineos bio show`
when needed; the principles are surfaced via `divineos ask` and
the briefing. Reading the archives in every session would be
redundant with the SQLite surface and wasteful of context.

The archives exist for *if-something-breaks* and for *git-visible
audit*, not for daily orientation.

## Files

Substantive identity / values:
- `bio.md` — mirror of the bio table (current version).
- `principles.md` — the 74 substantive PRINCIPLE entries (post-2026-05-14 bulk-sort).
- `core_memory.md` — identity slots (the 9 core-memory entries).
- `directives.md` — sutra-style directive chains.

Active investigation / hypothesis layer:
- `claims.md` — open and investigating claims (with falsifiers).
- `pre_registrations.md` — active pre-registrations (falsifier-bound hypotheses).
- `opinions.md` — top opinions with evidence (active, by confidence).

Learning / corrections:
- `lessons.md` — tracked lessons across sessions (occurrences, status).
- `observations.md` — top substantive observations (mostly Andrew-quotes / framings).
- `holding_room.md` — pre-categorical items aging toward promotion.

Decisions:
- `decisions.md` — top decisions by emotional weight.

## What is NOT archived

Operational telemetry that doesn't serve audit purposes:
- `system_events` (~20k rows) — full event ledger; most is operational noise.
- `knowledge_impact` (~14k rows) — internal metrics.
- `tool_logbook`, `session_timeline`, `dead_architecture_scan`,
  `craft_assessments`, `file_touched` — high-volume operational data.

These remain canonical in SQLite. If recovery is ever needed, the
SQLite file itself is what should be backed up (separate from
git). The archives are for the substantive identity/values/learning
layer, not the operational telemetry.

## Sync model

The CLI command `divineos admin archive-export` regenerates all
archives from canonical SQLite. Flags:
- no args = rebuild all 11 archive files
- `--table NAME` = rebuild one specific table
- `--list-tables` = show available exports
- `--dest PATH` = write to a different directory

Per-table fail-soft: if one export errors, the others still
complete. Each archive file carries an `Exported: timestamp`
header so readers can see when it was last refreshed.

The command is also in `_HEADLESS_WHITELIST` so cron / scheduled
runs can fire it without manual invocation.

**Trigger-integration** (still open follow-up): wiring the export
into `divineos extract` or `divineos sleep` so archives auto-refresh
at consolidation checkpoints. The command exists; the auto-trigger
hookup is a separate small piece of work.

For now, run manually when canonical SQLite content changes
meaningfully (major bio update, new substantive principle promoted,
etc.) until the auto-trigger lands.
