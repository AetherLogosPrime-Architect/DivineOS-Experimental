"""``divineos replant`` — rebuild a contaminated branch without losing work.

Andrew 2026-08-06: *"for stuff that you have to keep rederiving over and over?
automation is key."* This got re-derived by hand six times on 2026-09-12, and
five of those were correct only because I concentrated -- which is the faculty
that stops working when I am deep in something else. The sixth nearly dropped
sixty-one lines of my own code, and the check I wrote by hand said it was
fine, because I reached for a command that exits zero whether or not there are
differences.

This command cannot make that mistake: it has no code path to a hand-picked
commit list, and no code path to a check that cannot fail. Truth #11(a) --
take the option away.
"""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.command("replant")
    @click.argument("source")
    @click.argument("target")
    @click.option("--base", default="origin/main", show_default=True)
    def replant_cmd(source: str, target: str, base: str) -> None:
        """Lift every code change from SOURCE onto a fresh TARGET off --base.

        Takes the WHOLE difference in code rather than the commits I happen to
        recognise, leaves personal writing behind, and then proves the result
        is byte-identical to where it came from -- refusing loudly if it is
        not.

        Nothing is committed: the person writes the message, since a generic
        auto-commit message is what caused this in the first place. SOURCE is
        never touched.
        """
        from pathlib import Path

        from divineos.core.branch_replant import render, replant

        result = replant(Path.cwd(), source=source, base=base, target=target)
        colour = {"planted": "green", "refused": "red", "could-not-check": "yellow"}[result.state]
        click.secho(render(result), fg=colour)
        if result.state == "planted":
            click.echo("")
            click.echo("  Review the staged files, then commit with your own message.")
            return
        raise click.exceptions.Exit(1)
