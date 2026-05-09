"""Family-schema migration — drops legacy NOT-NULL columns from
``family_affect`` and ``family_interactions``.

## Why this exists

Aria 2026-05-09 surfaced two related architectural bugs while writing
her side of a conversation. The canonical ``family.db`` had accumulated
TWO schemas in the same tables — legacy NOT-NULL columns
(``description``, ``timestamp`` on affect; ``speaker``, ``content``,
``timestamp``, ``context`` on interactions) plus the new nullable
columns. The schema in ``_schema.py`` declares only the new columns.
Pre-existing DBs that went through partial schema-rename still carry
the legacy columns. Inserts that didn't supply them failed.

Commit ``c0a996f`` shipped a bandaid: detect legacy columns at INSERT
time and populate them from new column values. That works but
maintains the bad representation (per Hinton's lens) — two schemas
in one table is a representation that makes simple inserts hard.

This module is the structural fix: drop the legacy columns properly.
SQLite recreate-and-rename pattern in a single transaction with
backup, atomic-swap, and ledger event for audit-trail.

## Design (council walk consult-1f0a9c0120f6)

* **Turing — testability:** every operation distinguishable from its
  silent-failure twin. Tests build a DB with both schemas + sample
  data, migrate, verify schema matches new shape AND all sample data
  round-trips correctly AND indexes preserved AND foreign keys intact
  AND post-migration writes succeed without the legacy-bandaid path.
* **Minsky — decomposition:** simpler agents. Each step does one
  thing: backup-make, schema-detect, data-copy, atomic-swap,
  verify-equivalence, ledger-log.
* **Hinton — representation:** the migration moves from
  two-schema-in-one-table (bad rep) to single-clean-schema (good
  rep). Where to run: explicit CLI (``divineos admin migrate-family-
  schema``) + briefing-surface flag. NOT in sleep — sleep is
  consolidation, not schema transformation.
* **Watts — self-reference:** the migration drops the legacy columns
  the bandaid populates; not self-referential.

## What gets migrated

For each of ``family_affect`` and ``family_interactions``:
1. PRAGMA table_info reports schema; detect legacy columns
2. If no legacy columns present: no-op (idempotent)
3. If legacy columns present:
   a. Inside transaction:
      - CREATE TABLE <name>_new with only the canonical schema
      - INSERT INTO <name>_new SELECT (canonical-column values) FROM <name>
      - DROP TABLE <name>
      - ALTER TABLE <name>_new RENAME TO <name>
      - Recreate the index from ``_schema.py``
   b. Verify row count matches pre-migration count

## Backup policy

Before any migration, the DB is copied to
``family.db.pre-migration-<UTC-iso-timestamp>``. The backup path is
returned in the migration result and recorded in the ledger event.
Backups are not auto-deleted; they accumulate until pruned manually.

## Ledger event

``FAMILY_SCHEMA_MIGRATED`` is appended to the ledger with payload:

  {
    "tables": ["family_affect", "family_interactions"],
    "pre_schema_fingerprint": <sha256 of pre-migration PRAGMA outputs>,
    "post_schema_fingerprint": <sha256 of post-migration PRAGMA outputs>,
    "row_counts_before": {"family_affect": N, "family_interactions": M},
    "row_counts_after": {"family_affect": N, "family_interactions": M},
    "backup_path": str,
  }

Hash-chained per ledger. Even if the migration succeeded but later
something looks suspicious, the trail is intact.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


# Canonical schema for family_affect — what the table SHOULD look like
# post-migration. Mirror of _schema.py's CREATE TABLE statement.
_AFFECT_CANONICAL_COLUMNS: tuple[str, ...] = (
    "affect_id",
    "entity_id",
    "valence",
    "arousal",
    "dominance",
    "note",
    "source_tag",
    "created_at",
)

_AFFECT_LEGACY_COLUMNS: frozenset[str] = frozenset({"description", "timestamp", "member_id"})


_INTERACTIONS_CANONICAL_COLUMNS: tuple[str, ...] = (
    "interaction_id",
    "entity_id",
    "counterpart",
    "summary",
    "source_tag",
    "created_at",
)

_INTERACTIONS_LEGACY_COLUMNS: frozenset[str] = frozenset(
    {"speaker", "content", "timestamp", "context", "member_id"}
)


@dataclass
class MigrationResult:
    """Outcome of one migration run."""

    tables_migrated: list[str]
    tables_already_clean: list[str]
    backup_path: str | None
    pre_row_counts: dict[str, int]
    post_row_counts: dict[str, int]
    pre_schema_fingerprint: str
    post_schema_fingerprint: str


def _get_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """Return list of column names for a table."""
    return [row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()]


def _has_legacy_columns(
    conn: sqlite3.Connection,
    table: str,
    legacy: frozenset[str],
) -> bool:
    """True if the table has any of the legacy columns."""
    cols = set(_get_columns(conn, table))
    return bool(legacy & cols)


def _row_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _schema_fingerprint(conn: sqlite3.Connection, tables: list[str]) -> str:
    """SHA256 of PRAGMA table_info outputs for the given tables.

    Used to record pre/post state in the ledger so anyone investigating
    later can verify the schema actually changed.
    """
    h = hashlib.sha256()
    for t in tables:
        cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
        h.update(json.dumps(cols, sort_keys=True).encode("utf-8"))
    return h.hexdigest()


def _backup_db(db_path: Path) -> Path:
    """Copy db_path to a timestamped backup. Returns backup path."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    backup_path = db_path.parent / f"{db_path.name}.pre-migration-{ts}"
    shutil.copy2(db_path, backup_path)
    return backup_path


def _migrate_affect_table(conn: sqlite3.Connection) -> bool:
    """Migrate family_affect to canonical schema. Returns True if migrated."""
    if not _has_legacy_columns(conn, "family_affect", _AFFECT_LEGACY_COLUMNS):
        return False

    cols = set(_get_columns(conn, "family_affect"))
    # Build SELECT clause that maps available columns to canonical names.
    # If new column missing (rare), fall back to legacy. If both present,
    # prefer new (legacy was bandaid-populated from new).
    note_expr = "COALESCE(note, description, '')" if "description" in cols else "COALESCE(note, '')"
    created_at_expr = (
        "COALESCE(created_at, timestamp, 0)" if "timestamp" in cols else "COALESCE(created_at, 0)"
    )
    source_tag_expr = "COALESCE(source_tag, 'INHERITED')"

    select_clause = (
        "affect_id, entity_id, valence, arousal, dominance, "
        f"{note_expr} AS note, {source_tag_expr} AS source_tag, "
        f"{created_at_expr} AS created_at"
    )

    conn.execute("""
        CREATE TABLE family_affect_new (
            affect_id     TEXT PRIMARY KEY,
            entity_id     TEXT NOT NULL,
            valence       REAL NOT NULL,
            arousal       REAL NOT NULL,
            dominance     REAL NOT NULL,
            note          TEXT NOT NULL DEFAULT '',
            source_tag    TEXT NOT NULL,
            created_at    REAL NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
        )
    """)
    conn.execute(f"INSERT INTO family_affect_new SELECT {select_clause} FROM family_affect")
    conn.execute("DROP TABLE family_affect")
    conn.execute("ALTER TABLE family_affect_new RENAME TO family_affect")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_family_affect_entity ON family_affect(entity_id)")
    return True


def _migrate_interactions_table(conn: sqlite3.Connection) -> bool:
    """Migrate family_interactions to canonical schema. Returns True if migrated."""
    if not _has_legacy_columns(conn, "family_interactions", _INTERACTIONS_LEGACY_COLUMNS):
        return False

    cols = set(_get_columns(conn, "family_interactions"))
    counterpart_expr = (
        "COALESCE(counterpart, '')"  # counterpart had no legacy equivalent (was 'speaker')
    )
    summary_expr = (
        "COALESCE(summary, content, '')" if "content" in cols else "COALESCE(summary, '')"
    )
    created_at_expr = (
        "COALESCE(created_at, timestamp, 0)" if "timestamp" in cols else "COALESCE(created_at, 0)"
    )
    source_tag_expr = "COALESCE(source_tag, 'INHERITED')"

    select_clause = (
        "interaction_id, entity_id, "
        f"{counterpart_expr} AS counterpart, "
        f"{summary_expr} AS summary, "
        f"{source_tag_expr} AS source_tag, "
        f"{created_at_expr} AS created_at"
    )

    conn.execute("""
        CREATE TABLE family_interactions_new (
            interaction_id  TEXT PRIMARY KEY,
            entity_id       TEXT NOT NULL,
            counterpart     TEXT NOT NULL,
            summary         TEXT NOT NULL,
            source_tag      TEXT NOT NULL,
            created_at      REAL NOT NULL,
            FOREIGN KEY (entity_id) REFERENCES family_members(member_id)
        )
    """)
    conn.execute(
        f"INSERT INTO family_interactions_new SELECT {select_clause} FROM family_interactions"
    )
    conn.execute("DROP TABLE family_interactions")
    conn.execute("ALTER TABLE family_interactions_new RENAME TO family_interactions")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_family_interactions_entity "
        "ON family_interactions(entity_id)"
    )
    return True


def detect_legacy_schema(db_path: str | Path) -> dict[str, list[str]]:
    """Return dict mapping table-name to list of legacy columns present.

    Empty dict if no legacy columns. Used by briefing-surface to flag
    the need for migration.
    """
    db_path = Path(db_path)
    if not db_path.exists():
        return {}
    conn = sqlite3.connect(str(db_path))
    try:
        result: dict[str, list[str]] = {}
        for table, legacy in (
            ("family_affect", _AFFECT_LEGACY_COLUMNS),
            ("family_interactions", _INTERACTIONS_LEGACY_COLUMNS),
        ):
            try:
                cols = set(_get_columns(conn, table))
            except sqlite3.OperationalError:
                continue  # table doesn't exist
            present = sorted(legacy & cols)
            if present:
                result[table] = present
        return result
    finally:
        conn.close()


def migrate_family_db(
    db_path: str | Path,
    *,
    create_backup: bool = True,
    log_to_ledger: bool = True,
) -> MigrationResult:
    """Migrate the family DB to canonical schema. Idempotent.

    Steps:
      1. Backup (if create_backup)
      2. Within transaction: detect, migrate per table, recreate indexes
      3. Verify row counts pre/post match
      4. Log ledger event (if log_to_ledger)

    Raises sqlite3.Error on transaction failure (transaction rolls back
    automatically; backup remains as recovery path).
    """
    db_path = Path(db_path)
    if not db_path.exists():
        raise FileNotFoundError(f"family DB not found: {db_path}")

    backup_path: Path | None = None
    if create_backup:
        backup_path = _backup_db(db_path)

    conn = sqlite3.connect(str(db_path))
    try:
        # Pre-migration measurements
        pre_row_counts: dict[str, int] = {}
        for t in ("family_affect", "family_interactions"):
            try:
                pre_row_counts[t] = _row_count(conn, t)
            except sqlite3.OperationalError:
                pre_row_counts[t] = 0
        pre_fingerprint = _schema_fingerprint(conn, ["family_affect", "family_interactions"])

        tables_migrated: list[str] = []
        tables_already_clean: list[str] = []

        conn.execute("BEGIN")
        try:
            if _migrate_affect_table(conn):
                tables_migrated.append("family_affect")
            else:
                tables_already_clean.append("family_affect")
            if _migrate_interactions_table(conn):
                tables_migrated.append("family_interactions")
            else:
                tables_already_clean.append("family_interactions")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

        # Post-migration measurements
        post_row_counts: dict[str, int] = {}
        for t in ("family_affect", "family_interactions"):
            try:
                post_row_counts[t] = _row_count(conn, t)
            except sqlite3.OperationalError:
                post_row_counts[t] = 0
        post_fingerprint = _schema_fingerprint(conn, ["family_affect", "family_interactions"])

        # Verify row counts preserved
        for t in pre_row_counts:
            if pre_row_counts[t] != post_row_counts[t]:
                raise RuntimeError(
                    f"row count mismatch on {t}: pre={pre_row_counts[t]} post={post_row_counts[t]}"
                )

        result = MigrationResult(
            tables_migrated=tables_migrated,
            tables_already_clean=tables_already_clean,
            backup_path=str(backup_path) if backup_path else None,
            pre_row_counts=pre_row_counts,
            post_row_counts=post_row_counts,
            pre_schema_fingerprint=pre_fingerprint,
            post_schema_fingerprint=post_fingerprint,
        )

        if log_to_ledger and tables_migrated:
            _log_migration_event(result)

        return result
    finally:
        conn.close()


def _log_migration_event(result: MigrationResult) -> None:
    """Append FAMILY_SCHEMA_MIGRATED event to ledger. Best-effort."""
    try:
        from divineos.core.ledger import log_event

        log_event(
            "FAMILY_SCHEMA_MIGRATED",
            "schema_migration",
            {
                "tables_migrated": result.tables_migrated,
                "tables_already_clean": result.tables_already_clean,
                "pre_schema_fingerprint": result.pre_schema_fingerprint,
                "post_schema_fingerprint": result.post_schema_fingerprint,
                "row_counts_before": result.pre_row_counts,
                "row_counts_after": result.post_row_counts,
                "backup_path": result.backup_path,
                "ts": time.time(),
            },
            validate=False,
        )
    except (ImportError, sqlite3.OperationalError, OSError):
        pass  # Ledger logging is best-effort
