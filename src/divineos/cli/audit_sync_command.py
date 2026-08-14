"""`divineos audit-sync` — bring shared-folder approvals into the local store.

Andrew 2026-08-12: the confirms get given and then get lost, because every
trailer check reads the local store and the approvals land in
``~/.divineos-shared/audit/rounds/``. Nothing carried them across.

This is the manual door. ``stamp-ready`` calls the same sync automatically
before it validates, so in normal use nobody has to remember this command
exists -- which is the point, since remembering is what failed.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("audit-sync")
    @click.option(
        "--shared-dir",
        default=None,
        help="Override the crossing-point (default ~/.divineos-shared/audit).",
    )
    def audit_sync_cmd(shared_dir: str | None) -> None:
        """Import audit findings from the shared crossing-point."""
        from pathlib import Path

        from divineos.core.watchmen.shared_sync import sync_from_shared

        report = sync_from_shared(Path(shared_dir) if shared_dir else None)
        render_sync_report(report, verbose=True)


def render_sync_report(report: object, verbose: bool = False) -> None:
    """Print a sync report. Shared by the command and by stamp-ready."""
    imported = getattr(report, "findings_imported", 0)
    already = getattr(report, "findings_already_present", 0)
    absent = list(getattr(report, "rounds_absent_locally", []) or [])
    errors = list(getattr(report, "errors", []) or [])

    if imported:
        click.secho(
            f"[+] Imported {imported} finding(s) from the shared crossing-point:",
            fg="green",
        )
        for line in getattr(report, "imported", []):
            click.echo(f"      {line}")
    elif verbose:
        click.secho(
            f"[=] Nothing new to import "
            f"({getattr(report, 'rounds_seen', 0)} round(s) seen, "
            f"{already} finding(s) already present).",
            fg="cyan",
        )

    if absent:
        click.secho(
            f"[!] {len(absent)} shared round(s) have no local record, so their "
            "findings cannot be imported:",
            fg="yellow",
        )
        for rid in absent:
            click.echo(f"      {rid}")
        click.secho(
            "    A round created locally would get a different ID and satisfy "
            "no trailer naming the original.",
            fg="bright_black",
        )

    for err in errors:
        click.secho(f"[!] {err}", fg="yellow")
