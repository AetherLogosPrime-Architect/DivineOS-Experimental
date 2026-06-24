"""Audit-visibility CLI — exposes core/audit_visibility via the OS surface.

`divineos audit-visibility check` runs the same post-commit visibility
check the bash hook runs. Prints the loud banner to stderr if local
auditable work isn't on origin; silent otherwise.

Migrated 2026-06-24 per prereg-69507d1a38db.
"""

from __future__ import annotations

import json
import sys

import click


def register(cli: click.Group) -> None:
    """Register `divineos audit-visibility` subcommands."""

    @cli.group("audit-visibility", invoke_without_command=True)
    @click.pass_context
    def audit_visibility_group(ctx: click.Context) -> None:
        """Audit-visibility commands — check that local auditable work is on origin."""
        if ctx.invoked_subcommand is None:
            click.secho("audit-visibility subcommands: check", fg="bright_black")

    @audit_visibility_group.command("check")
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Print the visibility decision as JSON to stdout (no banner to stderr).",
    )
    def audit_visibility_check_cmd(json_out: bool) -> None:
        """Warn if HEAD touches auditable paths and isn't on origin.

        Exits 0 either way — this is an advisory warning, not a block.
        The visibility-warning class is fail-loud-via-banner, not exit-code.
        """
        from divineos.core.audit_visibility import check_visibility

        result = check_visibility()

        if json_out:
            click.echo(
                json.dumps(
                    {
                        "should_warn": result.should_warn,
                        "branch": result.branch,
                        "reason": result.reason,
                        "banner": result.banner,
                    }
                )
            )
        elif result.should_warn:
            print(result.banner, file=sys.stderr, flush=True)
