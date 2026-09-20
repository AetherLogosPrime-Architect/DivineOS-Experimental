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

from pathlib import Path

import click

from divineos.core import monitor_cleanup, monitor_singleton

_ROLES = ("letter", "compaction")

# Checkouts this machine hosts, longest first so the longer name is tested
# before the shorter one it contains.
_KNOWN_CHECKOUTS = ("DivineOS-Experimental-Aria-new", "DivineOS-Experimental")


def _match_checkout(text: str) -> str:
    for name in _KNOWN_CHECKOUTS:
        if name in text:
            return name
    return "unknown"


def _this_checkout() -> str:
    """Which checkout is asking."""
    return _match_checkout(str(Path(__file__).resolve()))


def _checkout_of(proc: object) -> str:
    """Which checkout a scanned Monitor process belongs to.

    WHY THE LISTING NAMES AN OWNER AT ALL (2026-09-20).

    This machine runs two checkouts, one per seat, and the process scan matches
    on program signature rather than path. So the listing showed BOTH seats'
    watchers with nothing distinguishing them, under a count of the machine
    presented as a count of yours.

    I read that output, saw more processes than I had armed, and built an
    accumulation out of it -- then a rhythm from their start times, then a
    mechanism from the rhythm, then a warning to the other seat that his clean
    machine was merely untested. Two letters, every claim retracted, none of it
    real. One watcher was mine and one was his, which is what he had already
    measured and reported while I treated his correct answer as the anomaly.

    The instrument was not broken. It could find every case it should find --
    it found his. What was never defined was the POPULATION, and no amount of
    care inside an undefined set repairs that: each further step was rigorous
    and took me deeper into a story about something that was not happening.

    So the fix is not a better scan; the scan was right. It is that the output
    must say whose, and the count must say how many are yours, because a number
    without an owner invites the reader to supply one.
    """
    return _match_checkout(getattr(proc, "command_line", "") or "")


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
            here = _this_checkout()
            mine = [p for p in procs if _checkout_of(p) == here]
            click.echo(
                f"Live Monitor processes: {len(procs)} on this machine, "
                f"{len(mine)} from this checkout"
            )
            for p in procs:
                marker = "[KEEP]" if p in keep else "[ORPHAN]"
                seat = _checkout_of(p)
                whose = "THIS CHECKOUT" if seat == here else f"other checkout: {seat}"
                click.echo(
                    f"  {marker} pid={p.pid} role={p.role} name={p.name} created={p.creation_date}"
                )
                click.echo(f"         {whose}")
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
