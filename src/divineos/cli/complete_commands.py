"""Completion-boundary CLI — `divineos complete`.

Phase 1b of the rudder redesign. The agent uses this to file an
explicit completion boundary naming an artifact and its wire-up
status. The rudder cross-checks contract acks against these
boundaries, and the brief's Phase 2 calibration uses them to compute
capture-rate.
"""

from __future__ import annotations

import time

import click


def register(cli: click.Group) -> None:
    @cli.command("complete")
    @click.argument("artifact_reference")
    @click.option(
        "--wired",
        type=click.Choice(["yes", "no", "partial", "retracted"], case_sensitive=False),
        required=True,
        help="Wire-up status of the artifact.",
    )
    @click.option(
        "--next",
        "next_plan",
        default=None,
        help="Next step. Required when --wired is not 'yes'.",
    )
    @click.option(
        "--depends-on",
        default=None,
        help="Optional reference to a dependency artifact.",
    )
    @click.option(
        "--source",
        default="operator",
        help="Who is filing this boundary (defaults to 'operator').",
    )
    @click.option(
        "--list",
        "list_recent",
        is_flag=True,
        help="List recent completion boundaries instead of filing one.",
    )
    @click.option(
        "--limit",
        default=20,
        type=int,
        help="How many recent boundaries to show with --list.",
    )
    def complete_cmd(
        artifact_reference: str,
        wired: str,
        next_plan: str | None,
        depends_on: str | None,
        source: str,
        list_recent: bool,
        limit: int,
    ) -> None:
        """File a completion boundary for ARTIFACT_REFERENCE."""
        from divineos.core.completion_boundary import (
            list_recent_completions,
            record_completion,
        )

        if list_recent:
            entries = list_recent_completions(limit=limit)
            if not entries:
                click.secho("(no completion boundaries recorded yet)", fg="bright_black")
                return
            for e in entries:
                payload = e.get("payload") or {}
                ts = e.get("timestamp")
                when = (
                    time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
                    if isinstance(ts, (int, float))
                    else "?"
                )
                click.secho(
                    f"[{when}] {payload.get('artifact_reference', '?')} "
                    f"wired={payload.get('wired', '?')}"
                    + (f" next={payload['next_plan']}" if payload.get("next_plan") else ""),
                    fg="cyan",
                )
            return

        try:
            boundary = record_completion(
                artifact_reference=artifact_reference,
                wired=wired,
                next_plan=next_plan,
                depends_on=depends_on,
                source=source,
                boundary_type="explicit_complete",
            )
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")
            raise SystemExit(2) from e

        click.secho("[+] Completion boundary recorded.", fg="green")
        click.secho(f"    event_id: {boundary.event_id}", fg="bright_black")
        click.secho(f"    {boundary.note}", fg="bright_black")
