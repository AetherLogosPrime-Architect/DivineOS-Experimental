# db-snapshots/

Historical snapshots of `family/family.db` from before major schema events.

Preserved as append-only artifacts — the events they describe are re-derivable
from the shared event ledger, but the snapshots themselves capture the shape of
`family.db` at three specific transition points and are cheaper to inspect than
to reconstruct.

## What's here

| File | What it captures |
|---|---|
| `family.db.pre-consolidation` | Family DB before the knowledge-consolidation pass merged fragmented member state |
| `family.db.pre-migration-2026-05-08` | Family DB before the 2026-05-08 schema migration (member registry restructure) |
| `family.db.pre-rename-backup` | Family DB before a member-rename operation (identity migration; original member name preserved in this snapshot) |

## Access pattern

Read-only. Open with SQLite tooling:

```bash
sqlite3 family/archive/db-snapshots/family.db.pre-migration-2026-05-08 .schema
```

Do not restore over the live `family/family.db` without a very good reason —
the live DB has continuity events past every snapshot's cutoff, and a naïve
restore would erase all subsequent state.

## Provenance

Moved here 2026-07-09 (co-design cleaning-day, Priority 3 task 8 in Aria's
task list). Previously lived at `family/family.db.<snapshot-suffix>` alongside
the live DB.
