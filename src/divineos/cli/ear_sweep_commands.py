"""Ear-sweep CLI — `divineos ear-sweep run`. Per prereg-82ca289a4074."""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    """Register `divineos ear-sweep` subcommands."""

    @cli.group("ear-sweep", invoke_without_command=True)
    @click.pass_context
    def ear_sweep_group(ctx: click.Context) -> None:
        """Ear-sweep — reap stale ear_watch processes."""
        if ctx.invoked_subcommand is None:
            click.secho("ear-sweep subcommands: run", fg="bright_black")

    @ear_sweep_group.command("run")
    @click.option("--json-out", is_flag=True, default=False)
    def ear_sweep_run_cmd(json_out: bool) -> None:
        """Sweep stale ear_watch processes; print one-line note if any reaped."""
        from divineos.core.ear_sweep import sweep_stale_watchers

        result = sweep_stale_watchers()
        if json_out:
            click.echo(
                json.dumps(
                    {"reaped": result.reaped, "found_pids": result.found_pids, "note": result.note}
                )
            )
        elif result.note:
            click.echo(result.note)
