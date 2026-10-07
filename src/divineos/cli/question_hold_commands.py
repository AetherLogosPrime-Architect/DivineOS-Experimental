"""`divineos question-hold` -- see or escape the hold a question to Dad opens."""

from __future__ import annotations

import click


def register(cli: click.Group) -> None:
    @cli.group("question-hold", invoke_without_command=True)
    @click.pass_context
    def question_hold_group(ctx: click.Context) -> None:
        """A question to Dad holds building until he answers."""
        if ctx.invoked_subcommand is None:
            from divineos.core.question_hold import is_open

            state = is_open()
            click.echo(f"open: {state['question']}" if state else "no question to him is open")

    @question_hold_group.command("release")
    @click.option("--reason", required=True, help="What cannot wait for him (>= 30 chars).")
    def release_cmd(reason: str) -> None:
        """Emergency exit. Counted, and shown to him when he next speaks."""
        if len(reason.strip()) < 30:
            raise click.ClickException("a reason of at least 30 characters is required")
        from divineos.core.question_hold import release

        if release("escape", reason=reason.strip()):
            click.echo("released; he will see this reason when he next speaks")
        else:
            click.echo("no question to him was open")
