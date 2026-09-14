"""CLI for the file Andrew can actually read.

    divineos for-dad "what happened, in words he can use"
    divineos for-dad --status

Named for who it is for. The whole failure this exists against is work being
described to the wrong reader, so the command says the reader out loud.
"""

from __future__ import annotations

import sys
from pathlib import Path

import click

from divineos.core.andrew_digest import add_entry, digest_path, is_restatement, read_state


@click.command("for-dad")
@click.argument("text", required=False, default="")
@click.option("--status", is_flag=True, help="What has landed that he has not been told about.")
def for_dad(text: str, status: bool) -> None:
    """Write an entry into the file kept for Andrew.

    Entries are allowed with nothing landed at all -- some of what he most needs
    to hear is not attached to any commit.
    """
    repo = Path.cwd()
    state = read_state(repo)

    if status:
        if not state.readable:
            click.secho("Could not read the history -- this says nothing either way.", fg="yellow")
            sys.exit(0)
        if not state.landed:
            click.secho("Nothing has landed since he was last told.", fg="green")
            sys.exit(0)
        click.secho(f"{len(state.landed)} thing(s) landed and he has not been told:", fg="yellow")
        for subject in state.landed[:15]:
            click.echo(f"  {subject}")
        sys.exit(0)

    body = (text or "").strip()
    if not body:
        click.secho('Nothing to write. Pass the words: divineos for-dad "..."', fg="red", err=True)
        sys.exit(1)

    if is_restatement(body, state.landed):
        # The laziest failure, refused by name. Pasting a commit subject here
        # produces the gibberish faster and makes this mechanism complicit.
        click.secho(
            "That is a commit subject, not something written for him. The commits "
            "are already the record; this file is the part they cannot carry.",
            fg="red",
            err=True,
        )
        sys.exit(1)

    if not add_entry(repo, body):
        click.secho("Could not write the file -- nothing was recorded.", fg="red", err=True)
        sys.exit(1)

    click.secho(f"Written for him, at the top of {digest_path(repo).name}.", fg="green")


def register(cli: click.Group) -> None:
    """Register the for-dad command on the CLI group."""
    cli.add_command(for_dad)
