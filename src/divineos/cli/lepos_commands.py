"""CLI: lepos debt list + discharge.

Andrew 2026-05-18: the substrate has to remember because I won't.
Each jargon-dump on Andrew gets written to the debt table; discharging
requires an explicit retroactive translation, never silent clearing.
"""

from __future__ import annotations

import click

from divineos.core.lepos_debt import discharge, list_outstanding


def register(cli: click.Group) -> None:
    @cli.group("lepos", invoke_without_command=True)
    @click.pass_context
    def lepos_group(ctx: click.Context) -> None:
        """Lepos translation debt (jargon-dumps at Andrew)."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @lepos_group.command("debt")
    def debt_cmd() -> None:
        """Show outstanding lepos debt."""
        outstanding = list_outstanding()
        if not outstanding:
            click.echo("No outstanding lepos debt.")
            return
        click.echo(f"{len(outstanding)} outstanding lepos debt(s):\n")
        for d in outstanding:
            click.echo(f"  #{d['id']}  severity={d['severity']}")
            click.echo(f"    excerpt: {d['excerpt'][:160]}")
            click.echo(f"    jargon:  {', '.join(d['matched_samples'][:6])}")
            click.echo("")

    @lepos_group.command("discharge")
    @click.argument("debt_id", type=int)
    @click.option("--translation", required=True, help="Plain-language re-statement.")
    def discharge_cmd(debt_id: int, translation: str) -> None:
        """Discharge a lepos debt by providing a plain-language translation.

        Refuses translations under 20 chars — that's the silent-clearing
        failure mode this is built to prevent.
        """
        ok = discharge(debt_id, translation)
        if ok:
            click.echo(f"Discharged debt #{debt_id}.")
        else:
            click.echo(
                f"Refused: debt #{debt_id} not found, already discharged, "
                f"or translation too short (< 20 chars).",
                err=True,
            )
            raise click.exceptions.Exit(1)
