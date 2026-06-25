"""PR-gate CLI — exposes core/pr_gate via the OS surface.

`divineos pr-gate create --command "<gh pr create command>"` runs the
same draft-gate check the bash hook runs. Exit 0 = allow, exit 1 =
block (with reason on stderr). Migrated 2026-06-24 per
prereg-17a6ff97ba67.
"""

from __future__ import annotations

import json
import sys

import click


def register(cli: click.Group) -> None:
    """Register `divineos pr-gate` subcommands."""

    @cli.group("pr-gate", invoke_without_command=True)
    @click.pass_context
    def pr_gate_group(ctx: click.Context) -> None:
        """PR-gate commands — draft-requirement, merge-readiness, others as added."""
        if ctx.invoked_subcommand is None:
            click.secho("pr-gate subcommands: create", fg="bright_black")

    @pr_gate_group.command("create")
    @click.option(
        "--command",
        required=True,
        help="The full `gh pr create ...` command string to gate-check.",
    )
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Print the decision as JSON to stdout instead of stderr.",
    )
    def pr_gate_create_cmd(command: str, json_out: bool) -> None:
        """Gate a `gh pr create` command — block if guardrail-touching + non-draft.

        Exit 0 = allow, exit 1 = block. Reason printed to stderr (or
        JSON to stdout if --json-out).
        """
        from divineos.core.pr_gate import check_pr_create_safe

        decision = check_pr_create_safe(command)
        if json_out:
            click.echo(
                json.dumps(
                    {
                        "blocked": decision.blocked,
                        "reason": decision.reason,
                        "touched_guardrails": decision.touched_guardrails or [],
                    }
                )
            )
        elif decision.blocked:
            print(decision.reason, file=sys.stderr)

        sys.exit(1 if decision.blocked else 0)
