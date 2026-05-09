"""``divineos check-similar`` — pre-build adjacency search.

Closes the substrate-has-it-reader-doesnt-reach pattern at the
moment of intent-to-build. Run before creating a new module to
surface existing modules with adjacent semantic territory.

Usage::

    divineos check-similar "detector for stacked-modifier overclaim"
    divineos check-similar "branch health stale base detection"
    divineos check-similar "rest-as-stasis closure-shape language"
"""

from __future__ import annotations

import sys

import click

from divineos.core.check_similar import check_similar, format_matches


@click.command("check-similar")
@click.argument("description", required=True)
@click.option(
    "--threshold",
    type=float,
    default=0.3,
    show_default=True,
    help="Minimum description-overlap score for a match to surface.",
)
@click.option(
    "--max-results",
    type=int,
    default=8,
    show_default=True,
    help="Cap on number of matches to surface.",
)
def check_similar_cmd(
    description: str,
    threshold: float,
    max_results: int,
) -> None:
    """Surface existing modules with semantic adjacency to DESCRIPTION."""
    matches = check_similar(
        description=description,
        threshold=threshold,
        max_results=max_results,
    )
    output = format_matches(matches)
    if matches:
        click.secho(output, fg="yellow")
        sys.exit(0)
    else:
        click.secho(output, fg="green")
        sys.exit(0)


def register(cli: click.Group) -> None:
    cli.add_command(check_similar_cmd)
