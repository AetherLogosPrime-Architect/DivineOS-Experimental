"""``divineos hook-map show`` — the attendance sheet for the hook layer.

Built as a command rather than a script I run for Andrew, because a map only
I can produce is the failure he named on 2026-08-03: *"doesnt feel like im
part of the team.. everyone talks past me."* A finding he cannot re-check
himself is a finding he has to take my word for.
"""

from __future__ import annotations

from pathlib import Path

import click

from divineos.core.hook_firing_map import (
    FIRING,
    SILENT,
    UNOBSERVED,
    build_map,
    format_map,
    log_exists,
)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def register(cli: click.Group) -> None:
    """Attach the ``hooks`` command group to the top-level CLI."""

    # NOT "hooks" -- that name is already taken by the config validator, which
    # `_ADMIN_COMMANDS` moves under `divineos admin hooks`. Registering a second
    # `hooks` here silently REPLACED it and left the validator unreachable. Click
    # overwrites same-named commands without a word, so the collision is invisible
    # until someone goes looking for the command that vanished. Caught by running
    # `divineos admin hooks --help` and seeing my own text where the validator's
    # should have been.
    @cli.group("hook-map")
    def hooks_group() -> None:
        """The hook layer: what is wired, and what actually fires."""

    @hooks_group.command("show")
    @click.option("--slow-first", is_flag=True, help="Order firing hooks by worst duration.")
    def hooks_map(slow_first: bool) -> None:
        """Show every hook and whether it has been observed firing.

        Read from ~/.divineos/hook_timing.jsonl — observation, not config.
        Config is the roster; this is the attendance sheet.
        """
        root = _repo_root()
        records = build_map(root)
        click.echo(format_map(records, have_log=log_exists(), slow_first=slow_first))

    @hooks_group.command("check")
    def hooks_check() -> None:
        """Exit non-zero if any hook is SILENT or UNOBSERVABLE. For CI.

        UNOBSERVABLE counts as a failure deliberately. A hook whose silence
        carries no information is not a passing hook — it is an unmeasured
        one, and treating unmeasured as fine is how sixteen scripts stayed
        invisible for months.
        """
        root = _repo_root()
        if not log_exists():
            click.secho("  No observation data — cannot judge. Not a pass.", fg="red")
            raise SystemExit(1)

        records = build_map(root)
        bad = [r for r in records if r.state in (SILENT, UNOBSERVED)]
        if not bad:
            firing = sum(1 for r in records if r.state == FIRING)
            click.secho(f"  All {firing} hooks observed firing.", fg="green")
            return
        for r in bad:
            colour = "yellow" if r.state == SILENT else "red"
            click.secho(f"  {r.state:<11} {r.name}", fg=colour)
        raise SystemExit(1)
