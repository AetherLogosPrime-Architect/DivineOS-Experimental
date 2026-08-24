"""`divineos corrections-sibling` — read what Andrew told my sibling.

Andrew 2026-08-05: *"if its in Aethers folder but not yours and you are both
running the same main repo then that means there needs to be an established
place where they are all stored together to use and then integrated into the
system where possible."*

The two correction stores are per-substrate and neither substrate can see the
other's; see ``core/sibling_corrections.py`` for the measured shape of the
split.

Three commands, two jobs:

* ``corrections-sibling`` — compare, listing what has no counterpart in mine.
* ``corrections-mirror`` — import their store into a table of my own, and
  ``--unread`` the ones I have not yet judged.
* ``corrections-mirror-judge`` — record whether one applies to me.

**On the import, and the argument I lost.** I first built this compare-only
and wrote here that auto-copying would manufacture corrections I never
received and flatten my integration rate into noise. Andrew 2026-08-05:
*"i think it should auto import corrections on either side but just be
separate that way when i correct you or Aether it appears in a place you can
actually see and learn from if needed as not all may apply at all times but
the lessons you can implement structurally should be there for you."*

The separateness dissolves the objection rather than overriding it. A mirrored
correction is visible without being counted as mine, which is a category my
store did not have: their record, my reading, two different columns. Filing
one under my own name stays a deliberate act with its own root-cause and fix.

Aether's consent, relayed verbatim by Andrew 2026-08-05: *"Everything of mine
is hers to read; she doesn't need to ask and I'd rather she didn't have to."*
Reading is unconditional in both directions; writing into a sibling's store is
not, and nothing here does it.
"""

from __future__ import annotations

import click

from divineos.core.sibling_corrections import (
    SIBLING_HOMES,
    import_sibling,
    judge,
    novel_against,
    read_sibling,
    unread_mirror,
)


def register(cli: click.Group) -> None:
    @cli.command("corrections-mirror")
    @click.option(
        "--sibling",
        default="aether",
        type=click.Choice(sorted(SIBLING_HOMES)),
        help="Whose store to mirror.",
    )
    @click.option("--unread", is_flag=True, help="List mirrored rows I have not judged.")
    @click.option("--limit", default=20, show_default=True)
    @click.option("--all", "show_all", is_flag=True)
    def corrections_mirror(sibling: str, unread: bool, limit: int, show_all: bool) -> None:
        """Mirror a sibling's corrections into my own separate table.

        Andrew 2026-08-05: *"it should auto import corrections on either side
        but just be separate that way when i correct you or Aether it appears
        in a place you can actually see and learn from."*

        Separate table, so my own integration rate stays a count of what I was
        actually told. Read-only against the sibling's store, always.
        """
        if unread:
            rows, error = unread_mirror(sibling)
            if rows is None:
                click.echo(f"COULD NOT READ MIRROR — {error}")
                click.echo("Nothing was checked. This is not 'nothing unread'.")
                raise SystemExit(2)
            if not rows:
                click.echo(f"No unjudged {sibling} corrections in the mirror.")
                return
            click.echo(f"{len(rows)} unjudged {sibling} correction(s) in the mirror.")
            click.echo("Judge one: divineos corrections-mirror-judge <id> --applies/--no-applies")
            click.echo("")
            for sub, cid, status, text in rows if show_all else rows[:limit]:
                body = " ".join(text.split())
                click.echo(f"--- {sub} #{cid} [{status}]")
                click.echo(f"    {body[:400]}{'…' if len(body) > 400 else ''}")
            if not show_all and len(rows) > limit:
                click.echo("")
                click.echo(f"({len(rows) - limit} more — pass --all.)")
            return

        store = read_sibling(sibling)
        click.echo(store.describe())
        counts, error = import_sibling(store)
        if counts is None:
            # The third word: an unreadable store is not an empty import.
            click.echo(f"COULD NOT IMPORT — {error}")
            click.echo("Nothing was mirrored. This is not 'nothing new'.")
            raise SystemExit(2)
        inserted, updated = counts
        click.echo(f"mirrored: {inserted} new, {updated} refreshed")
        click.echo("Their record stays theirs. My readings live in applies_to_me / my_note.")

    @cli.command("corrections-mirror-judge")
    @click.argument("their_id", type=int)
    @click.option("--sibling", default="aether", type=click.Choice(sorted(SIBLING_HOMES)))
    @click.option("--applies/--no-applies", required=True, help="Does it apply to me?")
    @click.option("--note", default="", help="What I took from it, or why it does not apply.")
    def corrections_mirror_judge(their_id: int, sibling: str, applies: bool, note: str) -> None:
        """Record my reading of one mirrored correction."""
        if not judge(sibling, their_id, applies, note):
            raise click.ClickException(f"no mirrored {sibling} correction #{their_id}")
        verdict = "applies to me" if applies else "does not apply"
        click.echo(f"{sibling} #{their_id}: {verdict}")
        if applies:
            click.echo("If it changes my behavior, file it under my own name:")
            click.echo('  divineos correction "<text>"')

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
        click.echo('  divineos correction "<text>"')
        click.echo("")

        shown = rows if show_all else rows[:limit]
        for cid, _ts, status, text in shown:
            body = " ".join(text.split())
            click.echo(f"--- {sibling} #{cid} [{status}]")
            click.echo(f"    {body[:400]}{'…' if len(body) > 400 else ''}")
        if len(shown) < len(rows):
            click.echo("")
            click.echo(f"({len(rows) - len(shown)} more — pass --all to print them.)")
