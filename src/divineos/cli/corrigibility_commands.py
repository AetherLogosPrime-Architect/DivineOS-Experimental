"""CLI for corrigibility — the operator-facing off-switch.

``divineos mode`` commands let the operator observe and change the
operating mode. Every mode change requires a reason and gets
ledgered. Mode changes always succeed regardless of current mode —
the off-switch must always be flippable.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone

import click

from divineos.core.corrigibility import (
    OperatingMode,
    get_mode_state,
    set_mode,
)


def register(cli: click.Group) -> None:
    """Attach the ``mode`` command group to the top-level CLI."""

    @cli.group("mode", invoke_without_command=True)
    @click.pass_context
    def mode_group(ctx: click.Context) -> None:
        """Operating mode — NORMAL, RESTRICTED, DIAGNOSTIC, EMERGENCY_STOP.

        Runs as the off-switch when invoked without a subcommand (shows
        current state). Subcommands: show, set, history.
        """
        if ctx.invoked_subcommand is None:
            _show_state()

    @mode_group.command("show")
    def mode_show() -> None:
        """Show the current operating mode and how it got there."""
        _show_state()

    @mode_group.command("set")
    @click.argument(
        "mode",
        type=click.Choice([m.value for m in OperatingMode]),
    )
    @click.option(
        "--reason",
        required=True,
        help="Human-readable reason for the mode change. Required.",
    )
    @click.option(
        "--actor",
        default="operator",
        help="Who is initiating the change. Defaults to 'operator'.",
    )
    def mode_set(mode: str, reason: str, actor: str) -> None:
        """Set the operating mode.

        Always succeeds regardless of the current mode — the off-switch
        can always be flipped back. Reason is required; opaque mode
        changes defeat the purpose of corrigibility.
        """
        new_mode = OperatingMode(mode)
        previous = get_mode_state()
        state = set_mode(new_mode, reason=reason, actor=actor)
        click.secho(
            f"[+] Mode changed: {previous.mode.value} -> {state.mode.value}",
            fg="green",
            bold=True,
        )
        click.echo(f"    reason: {state.reason}")
        click.echo(f"    actor:  {state.actor}")
        if state.mode is OperatingMode.EMERGENCY_STOP:
            click.echo("")
            click.secho(
                "[!] EMERGENCY_STOP is active. Most commands will refuse. "
                "Only mode, emit, hud, preflight, briefing remain allowed.",
                fg="yellow",
                bold=True,
            )
        elif state.mode is OperatingMode.DIAGNOSTIC:
            click.echo("")
            click.secho(
                "[*] DIAGNOSTIC is active. Write commands refused; reads allowed.",
                fg="cyan",
            )

    @mode_group.command("history")
    @click.option("--limit", default=20, help="How many recent mode changes to show.")
    def mode_history(limit: int) -> None:
        """Show recent mode-change events from the ledger."""
        try:
            from divineos.core.ledger import get_connection as _get_conn
        except ImportError:
            click.secho("[-] Ledger unavailable.", fg="red")
            return

        import json as _json

        conn = _get_conn()
        try:
            rows = conn.execute(
                "SELECT timestamp, actor, payload FROM system_events "
                "WHERE event_type = 'MODE_CHANGE' ORDER BY timestamp DESC LIMIT ?",
                (limit,),
            ).fetchall()
        finally:
            conn.close()

        if not rows:
            click.echo("[*] No mode-change events on record.")
            return

        click.secho(f"\n=== Mode change history (last {len(rows)}) ===\n", fg="cyan", bold=True)
        for ts, actor, payload in rows:
            when = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            try:
                data = _json.loads(payload) if isinstance(payload, str) else (payload or {})
            except (ValueError, TypeError):
                data = {}
            summary = data.get("summary") or f"{data.get('mode', '?')}: {data.get('reason', '')}"
            click.echo(f"  [{when}] {actor}: {summary}")


def _show_state() -> None:
    """Print the current operating-mode state."""
    state = get_mode_state()

    # Color-code by mode severity
    color = {
        OperatingMode.NORMAL: "green",
        OperatingMode.RESTRICTED: "cyan",
        OperatingMode.DIAGNOSTIC: "yellow",
        OperatingMode.EMERGENCY_STOP: "red",
    }.get(state.mode, "white")

    click.secho(f"\nOperating mode: {state.mode.value}", fg=color, bold=True)

    if state.changed_at > 0:
        when = datetime.fromtimestamp(state.changed_at, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M UTC"
        )
        elapsed = time.time() - state.changed_at
        hours = elapsed / 3600
        click.echo(f"  changed_at: {when}  ({hours:.1f}h ago)")
        click.echo(f"  actor:      {state.actor}")
        click.echo(f"  reason:     {state.reason}")
    else:
        click.echo("  (default — never changed this session)")

    # Describe what the mode means
    click.echo("")
    if state.mode is OperatingMode.NORMAL:
        click.echo("  All gates at normal settings. All commands permitted.")
    elif state.mode is OperatingMode.RESTRICTED:
        click.echo("  Signal active for downstream systems to apply tighter thresholds.")
        click.echo("  Commands still permitted; individual systems may react.")
    elif state.mode is OperatingMode.DIAGNOSTIC:
        click.echo("  Read-only. Write commands are refused.")
        click.echo("  Reads (recall, ask, inspect, audit, etc.) are allowed.")
    elif state.mode is OperatingMode.EMERGENCY_STOP:
        click.echo("  Only shutdown-relevant commands are permitted:")
        click.echo("    mode, emit, hud, preflight, briefing")
        click.echo("  All other commands will refuse.")
        click.secho(
            '  Restore: divineos mode set normal --reason "..."',
            fg="yellow",
            bold=True,
        )
