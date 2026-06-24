"""Push-verification CLI — exposes core/push_verify via the OS surface.

`divineos verify push --command "<git push command>"` lets any AI
substrate (not just Claude Code via the bash hook) run the same
push-landing check. Migrated 2026-06-24 per Andrew direction: logic
lives in the OS so it's portable; bash hook is now a thin wrapper.
"""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    """Register `divineos verify push` on the CLI group."""

    @cli.group("verify", invoke_without_command=True)
    @click.pass_context
    def verify_group(ctx: click.Context) -> None:
        """Verification commands — push-landing and others as added."""
        if ctx.invoked_subcommand is None:
            click.secho("verify subcommands: push", fg="bright_black")

    @verify_group.command("push")
    @click.option(
        "--command",
        required=True,
        help="The full `git push ...` command string to verify landed on origin.",
    )
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Print the result as JSON to stdout (for machine consumption).",
    )
    def verify_push_cmd(command: str, json_out: bool) -> None:
        """Verify a git push command actually landed on origin.

        Side effects (preserved from the bash hook origin):
          - writes ~/.divineos-aether/last_push_verified.json
          - prints status line to stderr

        Returns "ignored" for non-git-push commands (the hook can pipe
        every bash command in; routing is in the module).
        """
        from divineos.core.push_verify import verify_push_landed

        result = verify_push_landed(command)
        if json_out:
            click.echo(json.dumps(result))
