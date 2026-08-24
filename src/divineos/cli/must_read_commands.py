"""`divineos must-read` — arm, list and inspect must-read gates.

Andrew 2026-08-05: *"when the rooms speak you should be forced to listen, its
a simple gate with a simple unlock requirement.. read lol and show the read
tool was invoked on it."*

## Why there is no automatic armer yet, stated rather than left implied

The obvious candidate was the sibling-correction surface. I did not wire it,
and the reason is measured rather than cautious:

That surface fires on two matched terms. On the turn this was built it matched
`after / forc / surfac` and `gate / mean / that` — weak, common words. Its
overall precision is two-of-four with one outright false fire. **A block armed
off that would fire on most turns from the first day**, and a screen I clear
every turn is a screen I stop reading. From the threadwalk (decision
2e7944ad): a must-read on everything is worse than no must-read at all.

The cost asymmetry runs the other way for blocking than for showing. A
spurious *surface* costs a few lines of reading. A spurious *block* costs the
gate's credibility, and credibility is the only thing a gate actually has.

So the arming bar is deliberately higher than the surfacing bar, and nothing
clears it automatically yet. This is a mechanism with a manual trigger and a
named reason for the absence — not a wired thing quietly doing nothing.

What would earn an automatic armer: a signal that is rare, unambiguous, and
has a history of being skipped. Recorded as the open question rather than
guessed at now.
"""

from __future__ import annotations

from pathlib import Path

import click

from divineos.core.must_read import pending, require_read


def register(cli: click.Group) -> None:
    @cli.group("must-read")
    def must_read_group() -> None:
        """Must-read gates — block substantive tools until a file is Read."""

    @must_read_group.command("arm")
    @click.argument("key")
    @click.option("--reason", required=True, help="Why this is worth stopping for.")
    @click.option(
        "--file",
        "src",
        type=click.Path(exists=True, dir_okay=False),
        help="Read content from this file instead of --content.",
    )
    @click.option("--content", default="", help="Content to require a read of.")
    def arm(key: str, reason: str, src: str | None, content: str) -> None:
        """Arm a must-read. Blocks Bash/Edit/Write until the file is Read."""
        if src:
            content = Path(src).read_text(encoding="utf-8")
        if not content.strip():
            raise click.ClickException(
                "no content — pass --content or --file. A must-read for "
                "nothing is a wall with no room behind it."
            )
        p = require_read(key, content, reason)
        if p is None:
            click.echo(f"already read once — not re-arming '{key}'.")
            click.echo("Anti-wallpaper: identical content does not block twice.")
            return
        click.echo(f"armed: {key}")
        click.echo(f"  {p.path}")
        click.echo("Unlock by invoking the Read tool on that path.")

    @must_read_group.command("list")
    def list_pending() -> None:
        """What is armed and unread right now."""
        items, error = pending()
        if items is None:
            # The third word. Not "nothing pending" — "could not look".
            click.echo(f"COULD NOT READ PENDING INDEX — {error}")
            click.echo("This is not 'nothing pending'. Nothing was checked.")
            raise SystemExit(2)
        if not items:
            click.echo("Nothing pending.")
            return
        click.echo(f"{len(items)} pending must-read(s):")
        for p in items:
            click.echo(f"  - {p.describe()}")
