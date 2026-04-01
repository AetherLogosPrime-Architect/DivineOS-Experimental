"""CLI commands for Planning Commitments."""

import click

from divineos.core.planning_commitments import (
    add_commitment,
    clear_commitments,
    format_commitment_review,
    fulfill_commitment,
    get_pending_commitments,
    review_commitments,
)


@click.group()
def commit_group() -> None:
    """Track and review agent commitments."""


@commit_group.command("add")
@click.argument("text")
@click.option("--context", "-c", default="", help="Context when commitment was made")
def commit_add(text: str, context: str) -> None:
    """Record a commitment the agent made."""
    commitment = add_commitment(text, context=context)
    click.echo(f"Commitment recorded: {commitment.text}")


@commit_group.command("list")
def commit_list() -> None:
    """Show pending commitments."""
    pending = get_pending_commitments()
    if not pending:
        click.echo("No pending commitments.")
        return

    click.echo(f"\n{len(pending)} pending commitment(s):\n")
    for i, c in enumerate(pending, 1):
        click.echo(f"  {i}. {c.text}")
        if c.context:
            click.echo(f"     Context: {c.context}")


@commit_group.command("done")
@click.argument("text")
def commit_done(text: str) -> None:
    """Mark a commitment as fulfilled."""
    if fulfill_commitment(text):
        click.echo("Commitment marked as fulfilled.")
    else:
        click.echo("No matching pending commitment found.")


@commit_group.command("review")
def commit_review() -> None:
    """Review all commitments at session end."""
    result = review_commitments()
    output = format_commitment_review(result)
    if output:
        click.echo(f"\n{output}")
    else:
        click.echo("No commitments to review.")


@commit_group.command("clear")
def commit_clear() -> None:
    """Clear all commitments (after review)."""
    clear_commitments()
    click.echo("Commitments cleared.")


def register(cli: click.Group) -> None:
    """Register commitment commands."""
    cli.add_command(commit_group, "commitment")
