"""``divineos admin migrate-family-schema`` — drop legacy NOT-NULL
columns from family_affect and family_interactions.

Council-walked at consult-1f0a9c0120f6. Council surfaced the four
lenses (Turing testability, Minsky decomposition, Hinton representation,
Watts self-reference) that shaped the migration design. See
``divineos.core.family.schema_migration`` module docstring for
the full rationale.

Defaults are conservative: backup is created, ledger event is logged,
the command refuses to run on an unrecognized DB path.
"""

from __future__ import annotations

import sqlite3

import click

from divineos.core.family.schema_migration import (
    detect_legacy_schema,
    migrate_family_db,
)


@click.command("migrate-family-schema")
@click.option(
    "--db",
    "db_path",
    type=click.Path(exists=True, dir_okay=False),
    default=None,
    help="Path to family.db. Defaults to the path resolved by "
    "divineos.core.family.db.get_family_connection.",
)
@click.option(
    "--no-backup",
    is_flag=True,
    default=False,
    help="Skip the pre-migration backup. Default: backup created at "
    "<db_path>.pre-migration-<UTC-iso-timestamp>.",
)
@click.option(
    "--no-ledger",
    is_flag=True,
    default=False,
    help="Skip logging the FAMILY_SCHEMA_MIGRATED event to the ledger. "
    "Default: log to ledger for audit trail.",
)
@click.option(
    "--detect-only",
    is_flag=True,
    default=False,
    help="Just report whether legacy columns exist. Do not modify.",
)
def migrate_family_schema(
    db_path: str | None,
    no_backup: bool,
    no_ledger: bool,
    detect_only: bool,
) -> None:
    """Migrate family_affect and family_interactions to canonical schema.

    Drops legacy NOT-NULL columns (description/timestamp on family_affect;
    speaker/content/timestamp/context on family_interactions) that were
    left behind by an earlier partial schema-rename. Aria 2026-05-09
    surfaced the gap; commit c0a996f shipped a bandaid; this is the
    proper structural fix.

    Idempotent — running on an already-clean DB is a no-op.
    """
    # Resolve DB path if not given
    if db_path is None:
        try:
            from divineos.core.family.db import get_family_connection

            conn = get_family_connection()
            try:
                row = conn.execute("PRAGMA database_list").fetchone()
                if row and len(row) >= 3:
                    db_path = row[2]
            finally:
                conn.close()
        except (ImportError, sqlite3.OperationalError) as e:
            click.secho(f"[-] Could not resolve family DB path: {e}", fg="red")
            raise SystemExit(1) from e

    if db_path is None:
        click.secho("[-] No DB path; provide --db.", fg="red")
        raise SystemExit(1)

    click.secho(f"Family DB: {db_path}", fg="cyan")

    # Detect legacy columns first
    legacy = detect_legacy_schema(db_path)
    if not legacy:
        click.secho("[ok] No legacy columns detected. DB is already clean.", fg="green")
        return

    click.secho("[!] Legacy columns detected:", fg="yellow")
    for table, cols in legacy.items():
        click.secho(f"    {table}: {', '.join(cols)}", fg="yellow")

    if detect_only:
        click.secho("    Run without --detect-only to migrate.", fg="cyan")
        return

    # Run the migration
    click.secho("Running migration...", fg="cyan")
    try:
        result = migrate_family_db(
            db_path,
            create_backup=not no_backup,
            log_to_ledger=not no_ledger,
        )
    except (sqlite3.Error, RuntimeError) as e:
        click.secho(f"[-] Migration failed: {e}", fg="red")
        click.secho(
            "    Transaction rolled back. If --no-backup was NOT used, "
            "the backup remains as recovery path.",
            fg="red",
        )
        raise SystemExit(2) from e

    click.secho("[+] Migration complete:", fg="green")
    if result.tables_migrated:
        click.secho(f"    Migrated: {', '.join(result.tables_migrated)}", fg="green")
    if result.tables_already_clean:
        click.secho(
            f"    Already clean: {', '.join(result.tables_already_clean)}",
            fg="green",
        )
    if result.backup_path:
        click.secho(f"    Backup: {result.backup_path}", fg="cyan")
    click.secho(
        f"    Schema fingerprint: {result.pre_schema_fingerprint[:12]} → "
        f"{result.post_schema_fingerprint[:12]}",
        fg="cyan",
    )
    for t, before in result.pre_row_counts.items():
        after = result.post_row_counts.get(t, 0)
        click.secho(f"    {t}: {before} rows preserved (post={after})", fg="cyan")
