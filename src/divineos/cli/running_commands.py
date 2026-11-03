"""CLI: `divineos running` -- what the OS started, and whether anyone still owns it."""

import os
import time
from pathlib import Path

import click


def register(cli: click.Group) -> None:
    @cli.command("running")
    def running_cmd() -> None:
        """What is running that the OS started, and is its starter still alive.

        Read-only: it lists, flags orphans, and never stops or changes anything.
        """
        import divineos
        from divineos.core.running_processes import describe, format_report, read_live_rows

        repo_root = Path(divineos.__file__).resolve().parents[2]
        entries = describe(read_live_rows(), repo_root, time.time(), skip_pid=os.getpid())
        click.echo(format_report(entries))
