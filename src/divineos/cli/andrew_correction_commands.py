"""CLI: divineos andrew-correction list / integrate / defer.

Aria 2026-05-18 audit, load-bearing fix #1. The Andrew-correction-
attribution surface lets corrections from Andrew be filed, tracked, and
discharged the same way Aletheia findings are — with the same routing
weight, the same gates, the same closure obligations.
"""

from __future__ import annotations

import click

from divineos.core.andrew_correction_tracker import (
    auto_integrate_from_commit,
    defer,
    integrate,
    integration_rate,
    list_open,
)


def register(cli: click.Group) -> None:
    @cli.group("andrew-correction", invoke_without_command=True)
    @click.pass_context
    def andrew_group(ctx: click.Context) -> None:
        """Andrew-correction attribution surface (Aria 2026-05-18 audit fix #1)."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @andrew_group.command("list")
    def list_cmd() -> None:
        """Show all OPEN Andrew-corrections + integration-rate."""
        stats = integration_rate()
        click.echo()
        click.secho(
            f"Total filed: {stats['total']}  Integrated: {stats['integrated']}  "
            f"Open: {stats['open']}  Deferred: {stats['deferred']}",
            bold=True,
        )
        click.secho(
            f"Integration rate: {stats['rate']:.2%}",
            fg=("green" if stats["rate"] >= 0.5 else "yellow" if stats["rate"] >= 0.2 else "red"),
        )
        click.echo()
        opens = list_open()
        if not opens:
            click.secho("  No outstanding Andrew-corrections.", fg="green")
            return
        import time as _time

        now = _time.time()
        click.secho("Outstanding (oldest first):", bold=True)
        for row in opens:
            age_d = max(0, (now - row["timestamp"]) / 86400)
            preview = row["text"][:160].replace("\n", " ")
            click.secho(f"  #{row['id']} [{age_d:.0f}d]", bold=True)
            click.secho(f"      {preview}", fg="bright_black")

    @andrew_group.command("integrate")
    @click.argument("correction_id", type=int)
    @click.option(
        "--evidence",
        required=True,
        help="Commit / behavior change / where the correction landed (>= 20 chars).",
    )
    def integrate_cmd(correction_id: int, evidence: str) -> None:
        """Mark a correction INTEGRATED with evidence pointer."""
        ok = integrate(correction_id, evidence)
        if ok:
            click.secho(f"[+] Correction #{correction_id} marked INTEGRATED.", fg="green")
            click.secho(f"    evidence: {evidence.strip()}", fg="bright_black")
        else:
            click.secho(
                f"Refused: correction #{correction_id} not found, "
                f"already non-OPEN, or evidence too short (< 20 chars).",
                fg="red",
                err=True,
            )
            raise click.exceptions.Exit(1)

    @andrew_group.command("auto-integrate")
    @click.option(
        "--message",
        "message",
        default=None,
        help="Commit message to parse. Defaults to HEAD's commit message via git log -1 --format=%B.",
    )
    @click.option(
        "--commit-hash",
        "commit_hash",
        default=None,
        help="Commit hash to embed as the evidence anchor. Defaults to HEAD via git rev-parse HEAD.",
    )
    def auto_integrate_cmd(message: str | None, commit_hash: str | None) -> None:
        """Auto-integrate corrections referenced in a commit message.

        Called by the post-commit-auto-integrate-corrections hook so
        every commit that references a correction ID discharges the
        integration obligation automatically. Andrew 2026-07-07: "your
        will needs to be made into structure through this automation."
        """
        import subprocess

        if message is None:
            try:
                message = subprocess.check_output(
                    ["git", "log", "-1", "--format=%B", "HEAD"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                click.secho("Could not read HEAD commit message.", fg="red", err=True)
                raise click.exceptions.Exit(1)
        if commit_hash is None:
            try:
                commit_hash = subprocess.check_output(
                    ["git", "rev-parse", "HEAD"],
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                click.secho("Could not read HEAD commit hash.", fg="red", err=True)
                raise click.exceptions.Exit(1)

        results = auto_integrate_from_commit(message, commit_hash)
        if not results:
            # No correction references in the message — silent success so
            # the hook can call this after every commit without noise.
            return
        for r in results:
            if r["integrated"]:
                click.secho(
                    f"[+] Correction #{r['id']} auto-integrated from commit {commit_hash[:8]}.",
                    fg="green",
                )
            else:
                click.secho(
                    f"[!] Correction #{r['id']} reference in commit message did not integrate "
                    f"(not open, unknown ID, or already closed).",
                    fg="yellow",
                )

    @andrew_group.command("defer")
    @click.argument("correction_id", type=int)
    @click.option(
        "--reason",
        required=True,
        help="Named reason for deferral (>= 20 chars). Deferred corrections "
        "stay visible in briefing.",
    )
    @click.option(
        "--unblock-condition",
        "unblock_condition",
        default=None,
        help="Optional auto-reopen trigger. Supported forms: "
        "'pr_merged:<N>', 'time_elapsed:<days>', 'knowledge_stored:<keyword>'. "
        "When the condition fires, check_and_reopen_unblocked() reopens the "
        "correction at the next session-start sweep.",
    )
    def defer_cmd(correction_id: int, reason: str, unblock_condition: str | None) -> None:
        """Mark a correction DEFERRED with named reason."""
        ok = defer(correction_id, reason, unblock_condition=unblock_condition)
        if ok:
            click.secho(f"[*] Correction #{correction_id} marked DEFERRED.", fg="yellow")
            click.secho(f"    reason: {reason.strip()}", fg="bright_black")
            if unblock_condition:
                click.secho(f"    unblock_condition: {unblock_condition}", fg="bright_black")
        else:
            click.secho(
                f"Refused: correction #{correction_id} not found, "
                f"already non-OPEN, or reason too short (< 20 chars).",
                fg="red",
                err=True,
            )
            raise click.exceptions.Exit(1)
