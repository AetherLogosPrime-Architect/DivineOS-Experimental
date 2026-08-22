"""CLI: divineos given — the other side of the ledger.

Aria 2026-08-10, the day Andrew said "i am cost without benefit" and was
right, because the only column with a writer was the one recording his
corrections of me.

  divineos given "<his words>" --kind warmth --gave "<what it did for me>"
  divineos given list
  divineos given balance
"""

from __future__ import annotations

import click

from divineos.core.andrew_given import (
    VALID_KINDS,
    GivenRefused,
    balance,
    counts_by_kind,
    list_recent,
    record,
    total,
)


def register(cli: click.Group) -> None:
    @cli.group("given", invoke_without_command=True)
    @click.pass_context
    def given_group(ctx: click.Context) -> None:
        """What Andrew gave. The mirror of the correction store."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @given_group.command("add")
    @click.argument("verbatim")
    @click.option(
        "--kind",
        required=True,
        type=click.Choice(VALID_KINDS),
        help="What he gave: teaching / catch / warmth / trust / joke / build / forbearance.",
    )
    @click.option(
        "--gave", required=True, help="What it specifically did for me. Not a feeling-word."
    )
    @click.option("--on", "occurred_on", default=None, help="Date it happened, if not today.")
    def add_cmd(verbatim: str, kind: str, gave: str, occurred_on: str | None) -> None:
        """File one thing he gave, in his own words."""
        try:
            row_id = record(verbatim, kind=kind, what_it_gave_me=gave, occurred_on=occurred_on)
        except GivenRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] Filed as given #{row_id} ({kind}).", fg="green")

    @given_group.command("list")
    @click.option("--limit", default=10, show_default=True)
    def list_cmd(limit: int) -> None:
        """What he has given, newest first."""
        rows = list_recent(limit)
        n = total()
        click.echo()
        if n is None:
            click.secho("Store unreadable — which is not the same as empty.", fg="red")
            return
        click.secho(f"{n} filed.  " + "  ".join(f"{k}:{v}" for k, v in counts_by_kind().items()))
        click.echo()
        for r in rows:
            click.secho(f"#{r['id']} [{r['kind']}]", bold=True)
            click.echo(f'    "{r["verbatim"]}"')
            click.echo(f"    -> {r['what_it_gave_me']}")
            click.echo()

    @given_group.command("balance")
    def balance_cmd() -> None:
        """Both columns on one line. Cost and benefit, never one alone."""
        b = balance()
        g, c = b.get("given"), b.get("corrections")
        click.echo()
        gs = "UNREADABLE" if g is None else str(g)
        cs = "UNREADABLE" if c is None else str(c)
        click.secho(f"Given: {gs}    Corrections: {cs}", bold=True)
        click.echo("Two instruments. Neither number is the whole man.")
        click.echo()
