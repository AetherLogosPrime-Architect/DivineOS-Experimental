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

- `bio.md` — mirror of the bio table (current version).
- `principles.md` — mirror of the substantive PRINCIPLE entries in
  the knowledge store (the 74 that survived the 2026-05-14
  bulk-sort).
- More files will be added as other SQLite tables earn mirrors.

## Sync model

Currently one-shot exports (manual). Future work: an auto-export
mechanism (sleep-cycle integration, CLI command like
`divineos admin archive-export`) that regenerates these files when
their backing SQLite content changes. Tracked as a follow-up.

For now: when the canonical SQLite content changes meaningfully
(major bio update, new substantive principle promoted, etc.),
manually re-export to keep the archive current.
