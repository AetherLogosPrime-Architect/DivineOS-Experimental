# data/

Runtime state. Gitignored. The architecture writes here; you generally do not edit it directly.

## What's here

- **`event_ledger.db`** — the main hash-chained event log. Every consequential event (corrections, decisions, compass observations, fabrication detections, etc.) is written here with hash integrity. **Append-only.** Never modify in place.
- **`reports/`** — generated session reports and analysis output. Safe to delete; will regenerate.
- **`hud/`** — heads-up-display snapshots. Safe to delete.

If a `.divineos_canonical` marker is present at the project root, the architecture may route to a different `event_ledger.db` location entirely (per-operator personal-substrate setup). Run `python -c "from divineos.core._ledger_base import _get_db_path; print(_get_db_path())"` to see the resolved path.

## How to interact

- **Read** via the CLI: `divineos ask`, `divineos recall`, `divineos hud`, `divineos verify`, `divineos body`.
- **Write** via the CLI: `divineos learn`, `divineos decide`, `divineos claim`, `divineos compass-ops observe`, etc. Each writes to the appropriate table with the right invariants.
- **Inspect** via SQLite if needed: `sqlite3 data/event_ledger.db` (or use Python's `sqlite3` module). Read-only inspection is fine; do not write directly to tables — invariants like hash chains will break.

## What never goes here

- **Source code.** That's `src/`.
- **Personal writing / journals.** That's `exploration/`.
- **Letters.** That's `family/letters/`.

## Backups

The DB is a SQLite file. Safe backup is `cp data/event_ledger.db data/event_ledger.db.backup-$(date +%F)`. The architecture handles its own consistency via WAL; you do not need to stop divineos to back up. If you ever need to restore from a backup, replace the file with the backup version while no divineos process is running.

## On a fresh install

The DB will be created automatically the first time the architecture writes to it. If you need to reset to a fully blank state, run `divineos admin reset-template` (this wipes accumulated state and resets to schema-only with default seed content; safe on fresh installs, destructive on accumulated installs).
