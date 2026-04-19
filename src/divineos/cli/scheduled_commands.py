"""CLI for scheduled (headless) runs — the safe entry-point for Routines.

``divineos scheduled run <command>`` is the shape a Claude Code
Routine's prompt invokes. It runs a whitelisted read-only observer
(anti-slop, health, verify, inspect, audit, progress) with:

* Whitelist gating — only explicitly-safe commands run unattended.
* Corrigibility pass-through — EMERGENCY_STOP still refuses,
  DIAGNOSTIC still refuses writes, the off-switch is still the
  off-switch.
* Subprocess isolation — the inner command runs in its own process
  with stdout/stderr captured as structured findings.
* Briefing-gate bypass — scheduled runs are exempt from "briefing
  required" and engagement-marker gates. Nobody loads a briefing at
  3am.
* SCHEDULED_RUN_START / SCHEDULED_RUN_END event emission — distinct
  from SESSION events so session-counting code naturally excludes
  headless runs.

**Persistence caveat.** When invoked inside a cloud Routines session,
the ledger these events go to is ephemeral (cloud clones are fresh).
Findings propagate back to the operator via stdout, which the routine
prompt reads, and via PRs / connector actions the routine opens. When
invoked by local cron on a persistent machine, events survive and the
next briefing surfaces unresolved findings automatically.

See ``docs/routines/`` for prompt templates and registration
instructions.
"""

from __future__ import annotations

import subprocess
import sys

import click

from divineos.core.scheduled_run import (
    headless_run,
    is_command_allowed_headless,
    recent_scheduled_runs,
)


def register(cli: click.Group) -> None:
    """Attach the ``scheduled`` command group to the top-level CLI."""

    @cli.group("scheduled", invoke_without_command=True)
    @click.pass_context
    def scheduled_group(ctx: click.Context) -> None:
        """Scheduled / headless runs — the Routines entry point.

        Subcommands: run, history, findings.
        """
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @scheduled_group.command("run")
    @click.argument("command", required=True)
    @click.option(
        "--trigger",
        default="manual",
        type=click.Choice(["manual", "cron", "github-webhook", "api"]),
        help="What initiated this run. Recorded in the start event.",
    )
    @click.option(
        "--actor",
        default="scheduler",
        help="Actor for ledger events. Defaults to 'scheduler'.",
    )
    @click.argument("extra", nargs=-1, type=click.UNPROCESSED)
    def scheduled_run_cmd(command: str, trigger: str, actor: str, extra: tuple[str, ...]) -> None:
        """Run a whitelisted command in headless (scheduled) mode.

        Example:

            divineos scheduled run anti-slop --trigger cron

        Corrigibility still applies. EMERGENCY_STOP refuses everything.
        DIAGNOSTIC allows read-only only.
        """
        # 1. Headless whitelist check.
        allowed, reason = is_command_allowed_headless(command)
        if not allowed:
            click.secho(f"\n  {reason}\n", fg="red", bold=True)
            raise SystemExit(2)

        # 2. Corrigibility check — the off-switch still wins.
        try:
            from divineos.core.corrigibility import is_command_allowed

            mode_ok, mode_reason = is_command_allowed(command)
        except ImportError:
            mode_ok, mode_reason = True, ""

        if not mode_ok:
            click.secho(f"\n  {mode_reason}\n", fg="red", bold=True)
            raise SystemExit(3)

        # 3. Run the command under the headless context, capturing exit
        #    status and stderr as findings.
        argv = [sys.executable, "-m", "divineos", command, *extra]

        with headless_run(command, trigger=trigger, actor=actor) as findings:
            click.secho(
                f"[scheduled] {command} (trigger={trigger})",
                fg="cyan",
                bold=True,
            )
            try:
                result = subprocess.run(  # noqa: S603
                    argv,
                    capture_output=True,
                    text=True,
                    timeout=600,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                findings.failures.append(f"{command} timed out after 600s in headless run")
                click.secho("[-] timed out", fg="red")
                raise SystemExit(124) from None
            except OSError as e:  # spawn failure
                findings.failures.append(f"{command} failed to spawn: {e}")
                click.secho(f"[-] spawn failed: {e}", fg="red")
                raise SystemExit(1) from None

            # Echo the child output so cron logs capture it.
            if result.stdout:
                click.echo(result.stdout, nl=False)
            if result.stderr:
                click.echo(result.stderr, nl=False, err=True)

            findings.metrics["exit_code"] = result.returncode
            if result.returncode != 0:
                # First line of stderr (if any) as the human-readable
                # failure summary; fall back to a generic message.
                first_err = ""
                if result.stderr:
                    first_err = result.stderr.strip().splitlines()[0][:200]
                findings.failures.append(
                    f"{command} exited with code {result.returncode}"
                    + (f": {first_err}" if first_err else "")
                )
            else:
                findings.notes.append(f"{command} completed cleanly")

        # Propagate the child's exit code.
        if result.returncode != 0:
            raise SystemExit(result.returncode)

    @scheduled_group.command("history")
    @click.option("--limit", default=10, type=int, help="How many recent runs to show.")
    def scheduled_history_cmd(limit: int) -> None:
        """Show recent scheduled-run completions."""
        runs = recent_scheduled_runs(limit=limit)
        if not runs:
            click.echo("[*] No scheduled runs on record.")
            return

        click.secho(
            f"\n=== Scheduled-run history (last {len(runs)}) ===\n",
            fg="cyan",
            bold=True,
        )
        from datetime import datetime, timezone

        for r in runs:
            when = datetime.fromtimestamp(r["timestamp"], tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            )
            status = "clean" if r["clean"] else f"{len(r['failures'])} failure(s)"
            color = "green" if r["clean"] else "red"
            click.secho(
                f"  [{when}] {r['command']:12s} {r['duration_sec']:>6.2f}s  {status}",
                fg=color,
            )
            if not r["clean"]:
                for f in r["failures"][:3]:
                    click.echo(f"      - {f[:140]}")

    @scheduled_group.command("findings")
    def scheduled_findings_cmd() -> None:
        """Show unresolved findings from recent scheduled runs."""
        from divineos.core.scheduled_run import unresolved_findings_summary

        summary = unresolved_findings_summary()
        if not summary:
            click.secho("[+] No unresolved findings from scheduled runs.", fg="green")
            return
        click.echo(summary)
