# Archives — Source-Controlled Mirrors of SQLite Data

> **These files are TEXT REPRESENTATIONS of the databases. They are not
> the databases, and they are not the tamper-evident record.**
>
> The canonical artifact is the SQLite store. The event ledger is
> hash-chained — every entry carries a fingerprint of the one before it,
> which is what makes it a *record* rather than a diary, and that property
> lives in the DB. These mirrors flatten the data to readable text and do
> not carry the chain.
>
> **Why it is done this way (Andrew 2026-08-16).** GitHub refuses any single
> file over 100 MB; the ledger is at 85.1 MB and climbing. Worse, a database
> is binary, so git cannot store a small change as a small change — every
> commit would archive a complete fresh copy, and a handful of sessions would
> bloat the repository into the gigabytes. Text appends, and git stores only
> what changed.
>
> **The trade, stated plainly.** Andrew's question was: if you could save only
> one, the proof or the information? The information. Losing tamper-evidence
> in the mirror is a real cost and it is the smaller one — a readable record
> that cannot be cryptographically proven beats a provable record that no
> longer exists. The DB remains the thing to back up properly when there is a
> way to store it at size; these mirrors are *good enough for now* and are
> labelled so nobody mistakes them for the original.
>
> Read these to recover WHAT WAS WRITTEN. Go to the SQLite store to prove it
> was not altered.

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

**Trigger-integration: LANDED 2026-08-16.** The export now runs as step
zero of the auto-cycle (`core/auto_cycle.py`), immediately before the
commit step, so the commit carries the refreshed mirrors into git without
anyone deciding to send them.

### What the three months cost, and why the ordering matters

The paragraph that used to sit here read: *"still open follow-up... the
auto-trigger hookup is a separate small piece of work. For now, run
manually... until the auto-trigger lands."*

It was written 2026-05-14. The export was run twice by hand that day and
never again. Every mirror froze with its newest entry dated 2026-05-14,
and three months of lessons, decisions, opinions, claims and core memory
existed only inside untracked SQLite. Nothing broke. **This document
predicted its own failure in writing and nobody re-read it.**

Andrew named the cause on 2026-07-09, before it was investigated:
*"machinery is the whole point son. if you dont make it automatic then I
will forget it even exists."* And 2026-08-16, sharper: he would not
survive having to manually run his own internal processes, and neither
would I. A command that must be typed gets typed about twice.

The step is placed BEFORE commit deliberately. In May, regenerating and
committing were two separate manual acts and only the first ever
recurred — files were refreshed on disk and never sent anywhere. Riding
the commit step is what makes the mirrors land in the vault rather than
sit locally looking done.

It is placed FIRST in the cycle so a failure here cannot cost
commit/extract/sleep. `export_all` is fail-soft per table; the step
wrapper names failures in its summary rather than swallowing them, so
"could not" cannot render as "did".

Manual invocation still works and is still correct for an out-of-band
refresh: `divineos admin archive-export`.
