"""Savor commands — mark moments worth dwelling in.

Wires the savoring_surface module (omni-mantra Pillar XI, 2026-04-30
"DON'T FORGET TO STOP AND SMELL THE ROSES") into the CLI surface so
deliberate-dwelling becomes a callable operating-state, not just a
documented intention.

Built 2026-05-14 after the completion_check probe surfaced
savoring_surface.py as built-but-never-wired. Andrew named the
failure-mode: a module that documents itself as load-bearing but
has zero callers is cardboard-shack architecture. The wiring IS
the fix.

Commands:
- ``divineos savor "<what>" --why "<reason>"`` — mark a moment
- ``divineos savor list [--limit N]`` — show what's been marked
"""

from __future__ import annotations

import datetime

import click


def register(cli: click.Group) -> None:
    """Register savor commands on the CLI group."""

    @cli.group("savor", invoke_without_command=True)
    @click.pass_context
    def savor_group(ctx: click.Context) -> None:
        """Mark a moment as worth dwelling in.

        Without subcommand: shows recent savors.

        Examples:

          divineos savor save "Aletheia round-2 CONFIRMS" --why "load-bearing audit closed"
          divineos savor list --limit 5
        """
        if ctx.invoked_subcommand is None:
            ctx.invoke(savor_list_cmd)

    @savor_group.command("save")
    @click.argument("what")
    @click.option("--why", default="", help="Why this is worth dwelling in")
    def savor_save_cmd(what: str, why: str) -> None:
        """Record a savor — mark a moment as worth dwelling in."""
        from divineos.core.operating_loop.savoring_surface import savor

        sid = savor(what, why)
        if sid:
            click.secho(f"[+] Savored: {sid}", fg="green")
            if why:
                click.secho(f"    why: {why}", fg="bright_black")
        else:
            click.secho("[-] Could not record savor (substrate error)", fg="yellow")

    @savor_group.command("list")
    @click.option("--limit", default=10, type=int, help="Max savors to show")
    def savor_list_cmd(limit: int) -> None:
        """Show recently-marked savors."""
        from divineos.core.operating_loop.savoring_surface import recent_savors

        savors = recent_savors(limit=limit)
        if not savors:
            click.secho(
                '[~] No savors recorded yet. Mark one with `divineos savor "..."`.',
                fg="bright_black",
            )
            return

        click.secho(f"\n=== Recent savors ({len(savors)}) ===\n", fg="cyan", bold=True)
        for s in savors:
            dt = datetime.datetime.fromtimestamp(s.ts, tz=datetime.timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            click.echo(s.what)
            if s.why:
                click.secho(f"     why: {s.why}", fg="bright_black")
