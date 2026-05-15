"""CLI for the show-fix triage walk.

Thin layer over divineos.core.claim_triage. Verification logic lives
in the core module.
"""

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    @cli.group("triage")
    def triage_group() -> None:
        """Show-fix triage walk — track claims by VERIFIED/SUSPECT/REMOVED."""
        pass

    @triage_group.command("add")
    @click.argument("claim")
    @click.option(
        "--status",
        type=click.Choice(["VERIFIED", "SUSPECT", "REMOVED"], case_sensitive=False),
        required=True,
    )
    @click.option("--notes", default="", help="Evidence / reasoning for the status.")
    @click.option("--test", "test_path", default="", help="Falsifier test path (VERIFIED only).")
    @click.option(
        "--actor",
        default="aether",
        help=(
            "Who is filing this triage entry (Aletheia Finding 50). "
            "VERIFIED requires external actor (aletheia, grok, user, "
            "council) — aether cannot self-mark VERIFIED on own work "
            "(Aletheia gap 2)."
        ),
    )
    def triage_add(
        claim: str, status: str, notes: str, test_path: str, actor: str
    ) -> None:
        """Record a claim's triage status."""
        from divineos.core.claim_triage import TriageStatus, add_entry

        try:
            entry = add_entry(
                claim=claim,
                status=TriageStatus(status.upper()),
                actor=actor,
                notes=notes,
                test_path=test_path,
            )
        except ValueError as e:
            click.secho(f"[!] Triage entry refused: {e}", fg="red")
            raise SystemExit(1)
        click.secho(f"[+] Triage entry: {entry['status']} — {entry['claim'][:80]}", fg="cyan")
        _safe_echo(
            "  [triage] records a status — VERIFIED means the falsifier "
            "passed; SUSPECT means it has not been verified yet; REMOVED "
            "means the original claim was wrong and is retracted."
        )

    @triage_group.command("list")
    @click.option(
        "--status",
        type=click.Choice(["VERIFIED", "SUSPECT", "REMOVED"], case_sensitive=False),
        default=None,
    )
    def triage_list(status: str | None) -> None:
        """List triage entries, optionally filtered by latest status."""
        from divineos.core.claim_triage import TriageStatus, list_entries

        filt = TriageStatus(status.upper()) if status else None
        entries = list_entries(filt)
        if not entries:
            click.echo("(no entries)")
            return
        for e in entries:
            click.echo(f"  [{e.get('status', '?')}] {e.get('claim', '')[:120]}")
            if e.get("test_path"):
                click.echo(f"      test: {e['test_path']}")
            if e.get("notes"):
                click.echo(f"      notes: {e['notes'][:100]}")

    @triage_group.command("summary")
    def triage_summary() -> None:
        """Show counts by current status — the honest 'what else is broken' number."""
        from divineos.core.claim_triage import summary

        counts = summary()
        click.echo(f"  VERIFIED: {counts['VERIFIED']}")
        click.secho(f"  SUSPECT:  {counts['SUSPECT']}", fg="yellow")
        click.echo(f"  REMOVED:  {counts['REMOVED']}")
