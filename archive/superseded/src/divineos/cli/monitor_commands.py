"""CLI surface for the Monitor singleton + orphan-cleanup subsystem.

Two subcommands:

- ``divineos monitor status`` — descriptive read of which Monitor
  roles are currently armed (via kernel mutex existence) and how
  many processes match each role's scan signature.
- ``divineos monitor cleanup-orphans`` — find stale Monitor
  processes (older duplicates within a role, plus legacy bash
  inline matches). Descriptive by default; ``--kill`` is required to
  actually terminate.

Andrew 2026-06-13 explicitly chose this shape: destruction needs
operator consent at the invocation, not at install time.
"""

from __future__ import annotations

import click

from divineos.core import monitor_cleanup, monitor_singleton

_ROLES = ("letter", "compaction")


def register(cli: click.Group) -> None:
    @cli.group("monitor", invoke_without_command=True)
    @click.pass_context
    def monitor_group(ctx: click.Context) -> None:
        """Monitor singleton + orphan-cleanup tools."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(monitor_status_cmd)

    @monitor_group.command("status")
    def monitor_status_cmd() -> None:
        """Show which Monitor roles are armed (mutex-held) and process counts."""
        procs = monitor_cleanup._scan_processes()
        keep, orphans = monitor_cleanup.classify_orphans(procs)

        click.echo("=== Monitor status ===")
        click.echo("")
        click.echo("Kernel-mutex holders (the live ones):")
        for role in _ROLES:
            held = monitor_singleton.is_held(role)
            label = "armed" if held else "not armed"
            click.echo(f"  {role:>10}: {label}")
        click.echo("")

        if procs:
            click.echo(f"Live Monitor processes: {len(procs)}")
            for p in procs:
                marker = "[KEEP]" if p in keep else "[ORPHAN]"
                click.echo(
                    f"  {marker} pid={p.pid} role={p.role} name={p.name} created={p.creation_date}"
                )
            if orphans:
                click.echo("")
                click.echo(
                    f"  Run `divineos monitor cleanup-orphans --kill` to terminate "
                    f"the {len(orphans)} orphan(s)."
                )
        else:
            click.echo("Live Monitor processes: 0")

    @monitor_group.command("cleanup-orphans")
    @click.option(
        "--kill",
        is_flag=True,
        default=False,
        help="Actually terminate the orphans. Without this flag, just prints what would happen.",
    )
    def monitor_cleanup_orphans_cmd(kill: bool) -> None:
        """Find stale Monitor processes (older duplicates + legacy bash matches)."""
        procs = monitor_cleanup._scan_processes()
        keep, orphans = monitor_cleanup.classify_orphans(procs)

        if not orphans:
            click.echo("No orphan Monitor processes found.")
            if keep:
                click.echo(f"Live: {len(keep)} process(es) (kept).")
            return

        click.echo(f"Found {len(orphans)} orphan Monitor process(es):")
        for p in orphans:
            cmdline_preview = (p.command_line or "")[:100]
            if len(p.command_line or "") > 100:
                cmdline_preview += "..."
            click.echo(f"  pid={p.pid} role={p.role} name={p.name} created={p.creation_date}")
            click.echo(f"    cmd: {cmdline_preview}")

        if not kill:
            click.echo("")
            click.echo("Dry-run mode. Re-run with --kill to terminate.")
            return

        click.echo("")
        killed = 0
        failed = 0
        for p in orphans:
            ok = monitor_cleanup.kill_pid(p.pid)
            status = "killed" if ok else "FAILED"
            click.echo(f"  pid={p.pid} role={p.role}: {status}")
            if ok:
                killed += 1
            else:
                failed += 1
        click.echo("")
        click.echo(f"Killed {killed}, failed {failed}.")
