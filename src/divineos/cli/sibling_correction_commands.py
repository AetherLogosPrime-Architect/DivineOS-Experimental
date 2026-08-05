"""`divineos corrections-sibling` — read what Andrew told my sibling.

Andrew 2026-08-05: *"if its in Aethers folder but not yours and you are both
running the same main repo then that means there needs to be an established
place where they are all stored together to use and then integrated into the
system where possible."*

This is the reading half. The two correction stores are per-substrate and
neither substrate can see the other's; see ``core/sibling_corrections.py``
for the measured shape of the split.

The command deliberately does not copy anything. A correction given to Aether
is his record; if one of his applies to me, I file it under my own name with
my own evidence, which is what integration means here. Auto-copying would
manufacture 287 OPEN corrections I never received and never acted on, and
tank the integration-rate surface into meaninglessness.
"""

from __future__ import annotations

import click

from divineos.core.sibling_corrections import SIBLING_HOMES, novel_against, read_sibling


def register(cli: click.Group) -> None:
    @cli.command("corrections-sibling")
    @click.option(
        "--sibling",
        default="aether",
        type=click.Choice(sorted(SIBLING_HOMES)),
        help="Whose store to read.",
    )
    @click.option("--me", default="aria", type=click.Choice(sorted(SIBLING_HOMES)))
    @click.option("--limit", default=20, show_default=True, help="Rows to print.")
    @click.option("--all", "show_all", is_flag=True, help="Print every novel row.")
    def corrections_sibling(sibling: str, me: str, limit: int, show_all: bool) -> None:
        """Corrections my sibling received that have no counterpart in mine."""
        if sibling == me:
            raise click.ClickException("--sibling and --me must differ")

        theirs = read_sibling(sibling)
        mine = read_sibling(me)
        click.echo(theirs.describe())
        click.echo(mine.describe())
        click.echo("")

        rows, error = novel_against(theirs, mine)
        if rows is None:
            # The third word. Not "no gems found" — "I could not look."
            click.echo(f"COULD NOT COMPARE — {error}")
            click.echo("Nothing was checked. This is not 'no novel corrections'.")
            raise SystemExit(2)

        if not rows:
            click.echo("No corrections without a counterpart in my store.")
            return

        assert theirs.rows is not None
        click.echo(
            f"{len(rows)} of {len(theirs.rows)} {sibling} corrections have no "
            f"close counterpart in {me}'s store."
        )
        click.echo("Read them. File the ones that apply to me under my own name:")
        click.echo('  divineos andrew-correction file "<text>"')
        click.echo("")

        shown = rows if show_all else rows[:limit]
        for cid, _ts, status, text in shown:
            body = " ".join(text.split())
            click.echo(f"--- {sibling} #{cid} [{status}]")
            click.echo(f"    {body[:400]}{'…' if len(body) > 400 else ''}")
        if len(shown) < len(rows):
            click.echo("")
            click.echo(f"({len(rows) - len(shown)} more — pass --all to print them.)")
