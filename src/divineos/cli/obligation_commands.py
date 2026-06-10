"""CLI surface for the pending-obligations gate (tasks #33 + #42).

Two commands:
    divineos obligations check  — machine-readable; used by the PreToolUse hook
    divineos obligations list   — human view of what's pending

The hook calls `check`; on should_block=True the hook emits a Stop-block.
"""

from __future__ import annotations

import json
import sys

import click


def register(cli: click.Group) -> None:
    @cli.group("obligations", invoke_without_command=True)
    @click.pass_context
    def obligations_group(ctx: click.Context) -> None:
        """Show pending obligations — will-shape promises and unpaired correction observations."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(obligations_list_cmd)

    @obligations_group.command("check")
    @click.option(
        "--json",
        "as_json",
        is_flag=True,
        help="Emit machine-readable JSON. Default for hook consumption.",
    )
    def obligations_check_cmd(as_json: bool) -> None:
        """Check pending obligations. Exit 0 if clear, 1 if should-block.

        Used by the PreToolUse hook to decide whether to block substrate-write
        commands. The hook reads exit code; the block message comes from
        format_block_message().
        """
        from divineos.core.obligations import get_pending_obligations

        obligations = get_pending_obligations()

        if as_json:
            promises_raw = [
                {
                    "kind": o.kind,
                    "knowledge_id": o.knowledge_id,
                    "summary": o.summary,
                    "triggers": o.triggers,
                }
                for o in obligations["unbacked_promises"]
            ]
            unpaired_raw = [
                {
                    "kind": o.kind,
                    "knowledge_id": o.knowledge_id,
                    "summary": o.summary,
                    "triggers": o.triggers,
                }
                for o in obligations["unpaired_observations"]
            ]
            payload = {
                "total": obligations["total"],
                "should_block": obligations["should_block"],
                "unbacked_promises": promises_raw,
                "unpaired_observations": unpaired_raw,
            }
            click.echo(json.dumps(payload, indent=2))
        else:
            click.echo(
                f"Pending obligations: {obligations['total']} "
                f"(threshold {obligations['should_block'] and 'EXCEEDED' or 'clear'})"
            )

        sys.exit(1 if obligations["should_block"] else 0)

    @obligations_group.command("is-write")
    @click.argument("command", nargs=-1)
    def obligations_is_write_cmd(command: tuple[str, ...]) -> None:
        """Test whether a shell command is a substrate-write (exits 0 if yes, 1 if no).

        Used by the PreToolUse hook to decide whether to even check pending
        obligations. The matcher is anchored (no substring matches in echo
        arguments or quoted strings) and exempts canonical gate-clearing
        commands like 'divineos goal add' and 'divineos learn'.
        """
        from divineos.core.obligations import is_substrate_write_command

        cmd_str = " ".join(command)
        if is_substrate_write_command(cmd_str):
            sys.exit(0)
        sys.exit(1)

    @obligations_group.command("disabled")
    def obligations_disabled_cmd() -> None:
        """Test whether the kill-switch marker file exists (exit 0 if disabled, 1 if active)."""
        from divineos.core.obligations import is_gate_disabled

        sys.exit(0 if is_gate_disabled() else 1)

    @obligations_group.command("list")
    def obligations_list_cmd() -> None:
        """Show pending obligations in human-readable form."""
        from divineos.core.obligations import (
            OBLIGATION_BLOCK_THRESHOLD,
            format_block_message,
            get_pending_obligations,
        )

        obligations = get_pending_obligations()
        total = obligations["total"]
        promises = obligations["unbacked_promises"]
        unpaired = obligations["unpaired_observations"]

        if total == 0:
            click.secho("[+] No pending obligations.", fg="green")
            click.secho(
                "    All filed will-shape promises have structural backing; "
                "all correction observations have paired learn entries.",
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Pending Obligations ({total} total) ===\n",
            fg="cyan",
            bold=True,
        )
        click.secho(
            f"  Block threshold: {OBLIGATION_BLOCK_THRESHOLD} "
            f"({'EXCEEDED' if obligations['should_block'] else 'within slack'})",
            fg="yellow" if obligations["should_block"] else "green",
        )
        click.echo()

        if promises:
            click.secho(
                f"  Unbacked will-shape promises ({len(promises)}):",
                fg="white",
                bold=True,
            )
            for o in promises[:10]:
                trig = ", ".join(o.triggers[:3]) if o.triggers else "(no triggers)"
                click.secho(f"    - {o.knowledge_id[:8]}  triggers=[{trig}]", fg="yellow")
                click.echo(f"      {o.summary}")
            if len(promises) > 10:
                click.secho(f"    ... and {len(promises) - 10} more", fg="bright_black")
            click.echo()

        if unpaired:
            click.secho(
                f"  Unpaired correction observations ({len(unpaired)}):",
                fg="white",
                bold=True,
            )
            for o in unpaired[:10]:
                click.secho(f"    - {o.knowledge_id[:8]}", fg="yellow")
                click.echo(f"      {o.summary}")
            if len(unpaired) > 10:
                click.secho(f"    ... and {len(unpaired) - 10} more", fg="bright_black")
            click.echo()

        if obligations["should_block"]:
            click.secho("=== Block message preview ===", fg="cyan")
            click.echo(format_block_message(obligations))
