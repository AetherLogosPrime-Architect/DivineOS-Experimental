"""CLI for substrate_eviction — the remedy the scope gate names.

The gate refuses a push with "land those files on the substrate branch and
rebuild this one against main with the code only." On 2026-09-10 I performed
that by hand six times in one evening and got it backwards once, turning a
169-file objection into a 2,142-file one.

Usage::

    divineos evict-substrate              # do it
    divineos evict-substrate --dry-run    # say what it would move, touch nothing

There is deliberately no way to skip the verification step. See the module
docstring: the person running this is tired and at their sixth blocked push,
and that is exactly who would reach for such a flag.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from divineos.core.substrate_eviction import (
    DEFAULT_REFERENCE,
    DEFAULT_SUBSTRATE_BRANCH,
    EvictionRefused,
    added_substrate,
    modified_substrate,
    recent_refusals,
    describe,
    evict,
)


@click.command("evict-substrate")
@click.option(
    "--reference",
    default=DEFAULT_REFERENCE,
    show_default=True,
    help="The branch this one is measured against — the same one the gate uses.",
)
@click.option(
    "--branch",
    default=DEFAULT_SUBSTRATE_BRANCH,
    show_default=True,
    help="Where the letters go.",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Name what would move. Touches nothing, writes nothing.",
)
def evict_substrate(reference: str, branch: str, dry_run: bool) -> None:
    """Move the letters this branch adds onto the substrate branch.

    Nothing leaves the machine. Files stay in the working tree exactly where
    they are; only which branch carries them changes.
    """
    repo = Path.cwd()

    # WHY THE LETTERS ARE HERE AT ALL, printed before what to do about them.
    # A checkpoint refusing to route them is what puts them on a code branch,
    # and until tonight that refusal went to a logger with no handler -- so the
    # cleanup never knew what it was cleaning up after. This is the one place
    # guaranteed to be stood in front of once a refusal has happened.
    for row in recent_refusals():
        when = datetime.fromtimestamp(float(row.get("at") or 0), tz=timezone.utc).strftime(
            "%H:%M UTC"
        )
        click.secho(
            f"[{when}] a checkpoint could not route the letters: {row.get('reason', '')}",
            fg="yellow",
            err=True,
        )

    try:
        if dry_run:
            paths = added_substrate(repo, reference) + modified_substrate(repo, reference)
            if not paths:
                click.secho(f"Nothing to move: this branch adds no letters over {reference}.")
                return
            click.secho(f"Would move {len(paths)} letter(s) onto {branch}:", fg="yellow")
            for p in paths[:20]:
                click.echo(f"  {p}")
            if len(paths) > 20:
                click.echo(f"  ... and {len(paths) - 20} more")
            click.secho("Nothing was touched.", fg="green")
            return

        result = evict(repo, reference=reference, branch=branch)
    except EvictionRefused as exc:
        # The refusal is the feature. Loud, and it says what did not happen.
        click.secho(f"[refused] {exc}", fg="red", err=True)
        sys.exit(1)

    click.secho(describe(result, reference), fg="green")
    if result.evicted:
        click.echo("Commit the result when you are ready; nothing is committed for you.")


def register(cli: click.Group) -> None:
    """Register the evict-substrate command on the CLI group."""
    cli.add_command(evict_substrate)
