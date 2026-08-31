"""What the hook stack costs per tool call — the number nobody could see.

``core/hook_budget.py`` has existed since 2026-08-21 with no entry point at
all. Reading it meant writing a throwaway script, so in practice it was read
by whoever had just decided to go looking. That is the wrong shape for the one
instrument that answers "why did the screen sit there for two minutes" — a
measurement nobody can invoke is a measurement nobody takes.

Andrew reported freezes for days. The answer was computable the whole time.
"""

from __future__ import annotations

import os
from pathlib import Path

import click


def _default_log() -> Path:
    home = os.environ.get("DIVINEOS_HOME") or os.path.join(os.path.expanduser("~"), ".divineos")
    return Path(home) / "hook_timing.jsonl"


def register(cli: click.Group) -> None:
    """Register the hook-budget command."""

    @cli.command("hook-budget")
    @click.option(
        "--log",
        "log_path",
        default=None,
        type=click.Path(),
        help="Timing log to read (default: $DIVINEOS_HOME/hook_timing.jsonl).",
    )
    @click.option(
        "--tail-bytes",
        default=None,
        type=int,
        help="How much of the log tail to read. Larger windows see more hangs.",
    )
    def hook_budget_cmd(log_path: str | None, tail_bytes: int | None) -> None:
        """What the whole hook stack costs per tool call, hangs included.

        Reports through ``analyse()`` rather than composing the pieces here,
        because the pieces come apart: the duration statistics are drawn only
        from runs that finished, and a caller who forgets to also count the
        unfinished ones gets a confident report about the healthy half of a
        stack that is hanging. That is not hypothetical -- it is the error
        this command exists downstream of.
        """
        from divineos.core.hook_budget import _DEFAULT_TAIL_BYTES, analyse, format_report

        path = Path(log_path) if log_path else _default_log()
        if not path.is_file():
            click.secho(f"[!] no timing log at {path}", fg="yellow")
            click.secho("    Hooks record timing via .claude/hooks/_lib.sh.", fg="yellow")
            raise click.exceptions.Exit(1)

        report = analyse(path, tail_bytes=tail_bytes or _DEFAULT_TAIL_BYTES)
        click.echo(format_report(report))
        if report.over_budget or report.has_hangs:
            raise click.exceptions.Exit(1)
