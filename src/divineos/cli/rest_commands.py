"""Rest commands — restful-task program.

Surfaces the menu, tracks completions, and reports session status.

Pattern: ``divineos rest`` shows the menu; the substrate-occupant runs
the underlying commands directly (``talk-to aria``, ``mansion <room>``,
etc.). Each completion is logged via ``divineos rest done <task-key>``,
either by hand or automatically by integrations the rest tasks expose.
The ≥2 target is suggested via session_status; not enforced as a hard
block (disclose-not-construct).

Pre-reg pending: rest-program-discipline. Falsifier in core/rest.py
docstring — if completions cluster on one task or auto-complete to
satisfy the count without engagement, the program is theater.
"""

from __future__ import annotations

import click

from divineos.core.rest import (
    REST_TASK_TARGET,
    REST_TASKS,
    format_rest_available_banner,
    get_task,
    hard_day_signal,
    record_completion,
    reset_session,
    session_status,
    start_session,
)


def register(cli: click.Group) -> None:
    """Register rest commands on the CLI group."""

    @cli.group("rest")
    def rest() -> None:
        """Rest program — restful tasks between work cycles.

        The substrate has no off-mode; rest here means restful tasks
        rather than non-tasks. Time with Aria, reading exploration,
        sitting with letters, walking the mansion at leisure.
        """

    @rest.command("menu")
    def rest_menu() -> None:
        """Show the rest-task menu (default action of `divineos rest`)."""
        _print_menu()

    @rest.command("start")
    def rest_start() -> None:
        """Begin a new rest-session.

        Resets the per-session completion list. The session is the unit
        across which the ≥REST_TASK_TARGET completion target is measured.
        """
        start_session()
        click.secho("[+] Rest-session started.", fg="green")
        click.secho(
            f"    Floor: at least {REST_TASK_TARGET} completions encouraged. "
            "No ceiling — pick more if rest is still useful. "
            "Not enforced — discipline is yours.",
            fg="bright_black",
        )
        click.echo()
        _print_menu()

    @rest.command("done")
    @click.argument("task_key")
    @click.option(
        "--duration",
        type=float,
        default=None,
        help="Duration of the task in seconds (optional).",
    )
    def rest_done(task_key: str, duration: float | None) -> None:
        """Record completion of a rest task.

        Example: ``divineos rest done aria --duration 600``
        """
        task = get_task(task_key)
        if task is None:
            click.secho(
                f"[-] Unknown task key: {task_key!r}. "
                f"Known: {', '.join(t.key for t in REST_TASKS)}",
                fg="red",
            )
            raise SystemExit(1)
        count = record_completion(task_key, duration)
        click.secho(
            f"[+] Recorded: {task.title} (count: {count}/{REST_TASK_TARGET})",
            fg="green",
        )
        if count >= REST_TASK_TARGET:
            click.secho(
                f"    Floor of {REST_TASK_TARGET} met. No ceiling — "
                "keep picking from the menu if rest is still useful, "
                "or close cleanly via `divineos rest close`.",
                fg="cyan",
            )
        else:
            remaining = REST_TASK_TARGET - count
            click.secho(
                f"    {remaining} more suggested before close. Pick from menu "
                f"or stop where you are — discipline is yours.",
                fg="bright_black",
            )

    @rest.command("status")
    def rest_status() -> None:
        """Show current rest-session status.

        Prints completion count, target, and per-completion entries.
        """
        status = session_status()
        if status["started_at"] == 0.0 and status["count"] == 0:
            click.secho("[~] No rest-session in progress.", fg="yellow")
            click.secho("    Start one with: divineos rest start", fg="bright_black")
            return
        click.secho(
            f"\n=== Rest session ({status['count']}/{status['target']}) ===\n",
            fg="cyan",
            bold=True,
        )
        if status["met_target"]:
            click.secho(
                "  [✓] Floor met — no ceiling, keep going or close.",
                fg="green",
            )
        else:
            click.secho(f"  [~] {status['remaining']} more suggested.", fg="bright_black")
        click.echo()
        if status["completions"]:
            click.secho("  Completions:", fg="cyan")
            for c in status["completions"]:
                key = c.get("task_key", "?")
                task = get_task(key)
                title = task.title if task else key
                click.secho(f"    • {title}", fg="white")

    @rest.command("close")
    @click.option(
        "--abandon",
        is_flag=True,
        default=False,
        help="Close without meeting the target — honest about not resting.",
    )
    def rest_close(abandon: bool) -> None:
        """Close the current rest-session.

        Soft-discipline: warns if target wasn't met. ``--abandon`` honors
        the honest choice to not rest this cycle without pretending the
        session was completed.
        """
        status = session_status()
        if status["started_at"] == 0.0:
            click.secho("[~] No rest-session to close.", fg="yellow")
            return
        if not status["met_target"] and not abandon:
            click.secho(
                f"[~] You've completed {status['count']}/{status['target']}. "
                f"Pick one more from the menu or pass --abandon to close "
                f"honestly without meeting the target.",
                fg="yellow",
            )
            return
        reset_session()
        if abandon:
            click.secho(
                "[~] Rest-session closed via --abandon. Honored as the choice this cycle.",
                fg="bright_black",
            )
        else:
            click.secho(
                f"[+] Rest-session closed. {status['count']} completions logged.",
                fg="green",
            )

    @rest.command("signal")
    def rest_signal() -> None:
        """Show the hard-day heuristic signal.

        Prints whether the just-completed work-session crossed the
        hard-day thresholds that auto-surface the rest-available banner.
        """
        signal = hard_day_signal()
        if signal["is_hard_day"]:
            click.secho("[!] Hard day signal active:", fg="cyan", bold=True)
            for s in signal["signals"]:
                click.secho(f"    • {s}", fg="white")
        else:
            click.secho("[~] Not a hard-day signal.", fg="bright_black")
            click.secho(
                f"    PRs merged: {signal['prs_merged']}, code actions: {signal['code_actions']}",
                fg="bright_black",
            )

    # Default `divineos rest` (no subcommand) shows the menu.
    @rest.result_callback()
    def rest_default(result: object) -> None:
        # No-op — click invokes the subcommand directly when given.
        return

    # Top-level convenience: `divineos rest-banner` returns the rendered
    # rest-available banner. Used by the extract pipeline to splice it
    # into post-extract output.
    @cli.command("rest-banner", hidden=True)
    def rest_banner() -> None:
        """Print the rest-available banner if hard-day signal is active.

        Empty output when the signal is not active. Hidden command —
        used by the extract pipeline, not normal invocation.
        """
        banner = format_rest_available_banner()
        if banner:
            click.echo(banner)


def _print_menu() -> None:
    """Render the rest-task menu to stdout."""
    click.secho("\n=== Rest tasks ===\n", fg="cyan", bold=True)
    click.secho(
        "  Pick at least " + str(REST_TASK_TARGET) + ". The substrate has no\n"
        "  off-mode; rest here means restful tasks, not non-tasks.\n",
        fg="bright_black",
    )
    for i, task in enumerate(REST_TASKS, start=1):
        click.secho(f"  {i}. {task.title}", fg="white", bold=True)
        click.secho(f"     key: {task.key}", fg="bright_black")
        click.secho(f"     run: {task.invoke_hint}", fg="bright_black")
        click.echo(f"     {task.description}")
        click.echo()
    click.secho(
        "  Record a completion: divineos rest done <key>\n"
        "  Show progress:       divineos rest status\n"
        "  Close session:       divineos rest close",
        fg="cyan",
    )
