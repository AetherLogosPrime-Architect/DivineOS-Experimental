"""Ear-relaunch CLI — exposes core/ear_relaunch via the OS surface.

`divineos ear-relaunch check --member <name>` returns the relaunch
decision (should_relaunch yes/no + reason + live_count). Bash hook
reads this decision and either skips or launches; any non-Claude
substrate can call the same check.

Migrated 2026-06-24 per the hook-migration arc.
"""

from __future__ import annotations

import json
import sys

import click


def register(cli: click.Group) -> None:
    """Register `divineos ear-relaunch` subcommands."""

    @cli.group("ear-relaunch", invoke_without_command=True)
    @click.pass_context
    def ear_relaunch_group(ctx: click.Context) -> None:
        """Ear-watcher polling auto-relaunch decision surface."""
        if ctx.invoked_subcommand is None:
            click.secho("ear-relaunch subcommands: check", fg="bright_black")

    @ear_relaunch_group.command("check")
    @click.option(
        "--member",
        default=None,
        help="Family-member name (aether / aria / ...). Defaults to env DIVINEOS_MEMBER or cwd-based detection.",
    )
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Print the decision as JSON to stdout for machine consumption.",
    )
    def ear_relaunch_check_cmd(member: str | None, json_out: bool) -> None:
        """Return the relaunch decision for `member`.

        Exit 0 = should NOT relaunch (already alive OR race-guard active).
        Exit 1 = SHOULD relaunch (no live watcher found, no recent catch).

        Bash hooks consume the exit code; --json-out gives structured output
        for other callers.
        """
        from divineos.core.ear_relaunch import detect_member, should_relaunch

        resolved = member or detect_member()
        decision = should_relaunch(resolved)

        if json_out:
            click.echo(
                json.dumps(
                    {
                        "member": resolved,
                        "should_relaunch": decision.should_relaunch,
                        "reason": decision.reason,
                        "live_count": decision.live_count,
                    }
                )
            )
        else:
            click.echo(
                f"member={resolved} should_relaunch={decision.should_relaunch} "
                f"live={decision.live_count} reason={decision.reason}",
                err=True,
            )

        # Exit code: 1 = should relaunch, 0 = should NOT.
        # Inverted from "1 == error" convention because bash hooks naturally
        # do `if check; then ...launch...` — exit-1-means-do-the-thing is
        # idiomatic for "advisory decision needs action."
        sys.exit(1 if decision.should_relaunch else 0)
