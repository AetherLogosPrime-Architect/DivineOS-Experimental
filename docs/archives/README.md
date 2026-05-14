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

Currently one-shot manual exports (per-table python scripts run
2026-05-14). Auto-export-on-change is the follow-up work — a CLI
command like `divineos admin archive-export [--table X | --all]`
that regenerates archives when the canonical SQLite content
changes.

## Sync model

Currently one-shot exports (manual). Future work: an auto-export
mechanism (sleep-cycle integration, CLI command like
`divineos admin archive-export`) that regenerates these files when
their backing SQLite content changes. Tracked as a follow-up.

For now: when the canonical SQLite content changes meaningfully
(major bio update, new substantive principle promoted, etc.),
manually re-export to keep the archive current.
