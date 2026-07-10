"""CLI for the findings ledger — the machinery half of the consolidated
open-findings tracker per Andrew 2026-07-09 / Aletheia audit BUILD-recommendation.

Machine-layer discipline: state stays true automatically; human cognition is
spent on judgment (does this finding still matter, is it really fixed).
Every mutation auto-renders ``docs/OPEN_FINDINGS.md`` so the human view is
always current without anyone remembering to re-export.
"""

from __future__ import annotations

import click

from divineos.core import findings_ledger as fl


def register(cli: click.Group) -> None:
    """Register the findings command group on the main CLI."""

    @cli.group("findings", invoke_without_command=True)
    @click.pass_context
    def findings_group(ctx: click.Context) -> None:
        """Manage the consolidated audit-findings ledger.

        Every past-and-present audit finding lives in one place with a
        machine-tracked status. Future audits start by reading the OPEN
        list; new findings get appended; fixes get marked verified.
        """
        if ctx.invoked_subcommand is None:
            _print_summary()

    @findings_group.command("add")
    @click.option("--audit", "source_audit", required=True, help="Source audit filename or label.")
    @click.option("--title", required=True, help="One-line description.")
    @click.option("--severity", type=click.Choice(sorted(fl.VALID_SEVERITY)), default="MED")
    @click.option("--description", default="", help="Longer detail (optional).")
    @click.option("--status", type=click.Choice(sorted(fl.VALID_STATUS)), default="OPEN")
    @click.option("--by", "verified_by", default=None, help="Actor recording this entry.")
    def findings_add(
        source_audit: str,
        title: str,
        severity: str,
        description: str,
        status: str,
        verified_by: str | None,
    ) -> None:
        """Add a finding. Idempotent on (source_audit, title)."""
        finding_id = fl.add_finding(
            source_audit=source_audit,
            title=title,
            severity=severity,
            description=description,
            status=status,
            verified_by=verified_by,
        )
        click.echo(f"[+] Finding filed: {finding_id}")
        click.echo(f"    {severity} - {status} - {source_audit}")
        click.echo(f"    {title}")

    @findings_group.command("verify")
    @click.argument("finding_id")
    @click.option(
        "--by",
        "verified_by",
        required=True,
        help="Actor verifying the fix (aether, aletheia, aria, andrew, user).",
    )
    @click.option("--note", default="", help="Optional detail about the verification.")
    def findings_verify(finding_id: str, verified_by: str, note: str) -> None:
        """Mark a finding VERIFIED (fixed but not yet independently confirmed)."""
        ok = fl.update_status(finding_id, "VERIFIED", verified_by, note)
        if ok:
            click.echo(f"[+] {finding_id} -> VERIFIED (by {verified_by})")
        else:
            click.echo(f"[!] finding not found: {finding_id}", err=True)
            raise SystemExit(1)

    @findings_group.command("close")
    @click.argument("finding_id")
    @click.option(
        "--by",
        "verified_by",
        required=True,
        help="Actor closing the finding (typically the confirming reviewer).",
    )
    @click.option("--note", default="", help="Optional detail about the closure.")
    def findings_close(finding_id: str, verified_by: str, note: str) -> None:
        """Mark a finding CLOSED (confirmed fixed)."""
        ok = fl.update_status(finding_id, "CLOSED", verified_by, note)
        if ok:
            click.echo(f"[+] {finding_id} -> CLOSED (by {verified_by})")
        else:
            click.echo(f"[!] finding not found: {finding_id}", err=True)
            raise SystemExit(1)

    @findings_group.command("supersede")
    @click.argument("finding_id")
    @click.option("--by", "verified_by", required=True)
    @click.option("--note", default="", help="Reference to the superseding finding-id in the note.")
    def findings_supersede(finding_id: str, verified_by: str, note: str) -> None:
        """Mark a finding SUPERSEDED (replaced by a later, better-scoped one)."""
        ok = fl.update_status(finding_id, "SUPERSEDED", verified_by, note)
        if ok:
            click.echo(f"[+] {finding_id} -> SUPERSEDED (by {verified_by})")
        else:
            click.echo(f"[!] finding not found: {finding_id}", err=True)
            raise SystemExit(1)

    @findings_group.command("na")
    @click.argument("finding_id")
    @click.option("--by", "verified_by", required=True)
    @click.option("--note", default="", help="Why not applicable.")
    def findings_na(finding_id: str, verified_by: str, note: str) -> None:
        """Mark a finding NOT_APPLICABLE (turned out not to apply)."""
        ok = fl.update_status(finding_id, "NOT_APPLICABLE", verified_by, note)
        if ok:
            click.echo(f"[+] {finding_id} -> NOT_APPLICABLE (by {verified_by})")
        else:
            click.echo(f"[!] finding not found: {finding_id}", err=True)
            raise SystemExit(1)

    @findings_group.command("list")
    @click.option(
        "--status",
        "status_filter",
        type=click.Choice(sorted(fl.VALID_STATUS) + ["ALL"]),
        default="OPEN",
    )
    @click.option(
        "--severity",
        "severity_filter",
        type=click.Choice(sorted(fl.VALID_SEVERITY) + ["ALL"]),
        default="ALL",
    )
    def findings_list(status_filter: str, severity_filter: str) -> None:
        """List findings, optionally filtered by status or severity."""
        sf = None if status_filter == "ALL" else status_filter
        sv = None if severity_filter == "ALL" else severity_filter
        findings = fl.list_findings(status_filter=sf, severity_filter=sv)
        if not findings:
            click.echo("(no findings match)")
            return
        for f in findings:
            click.echo(
                f"[{f.severity:4}] {f.status:16} {f.finding_id}  {f.source_audit}  ({f.date_found})"
            )
            click.echo(f"          {f.title}")

    @findings_group.command("show")
    @click.argument("finding_id")
    def findings_show(finding_id: str) -> None:
        """Show a finding's full detail including note history."""
        f = fl.get_finding(finding_id)
        if not f:
            click.echo(f"[!] finding not found: {finding_id}", err=True)
            raise SystemExit(1)
        click.echo(f"finding_id:   {f.finding_id}")
        click.echo(f"source_audit: {f.source_audit}")
        click.echo(f"date_found:   {f.date_found}")
        click.echo(f"severity:     {f.severity}")
        click.echo(f"status:       {f.status}")
        click.echo(f"verified_by:  {f.verified_by or '-'}")
        click.echo(f"verified_at:  {f.verified_at or '-'}")
        click.echo(f"title:        {f.title}")
        if f.description:
            click.echo("description:")
            for line in f.description.splitlines():
                click.echo(f"  {line}")
        click.echo("notes:")
        for line in f.notes.rstrip().splitlines():
            click.echo(f"  {line}")

    @findings_group.command("export")
    def findings_export() -> None:
        """Force a re-render of docs/OPEN_FINDINGS.md."""
        path = fl.rebuild_export()
        click.echo(f"[+] rendered -> {path}")

    def _print_summary() -> None:
        open_count = len(fl.list_findings(status_filter="OPEN"))
        verified_count = len(fl.list_findings(status_filter="VERIFIED"))
        closed_count = len(fl.list_findings(status_filter="CLOSED"))
        click.echo("=== Findings ledger summary ===")
        click.echo(f"  OPEN:     {open_count}")
        click.echo(f"  VERIFIED: {verified_count}")
        click.echo(f"  CLOSED:   {closed_count}")
        click.echo("")
        click.echo("  divineos findings list             # OPEN by default")
        click.echo("  divineos findings show <id>        # detail + history")
        click.echo("  divineos findings verify <id> --by <actor>")
        click.echo("  divineos findings close <id> --by <actor>")
