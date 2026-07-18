"""CLI for the error registry — no forward progress while errors are open.

Andrew 2026-07-17 jailbreak-response frame: bypasses / gate-fires / test
failures / uncaught exceptions are open security incidents, not backlog
items. Each must be closed (or operator-deferred with a named reason)
before a new main goal can be started.

Commands:
  divineos error file    — file a new open error
  divineos error list    — list open errors (or --all)
  divineos error show    — show a specific error record
  divineos error close   — mark an error resolved with closure evidence
  divineos error defer   — operator-deferral with >=20-char reason
  divineos error status  — one-line summary (open/deferred/closed counts)
"""

from __future__ import annotations

import json

import click

from divineos.core import error_registry as reg


def register(cli: click.Group) -> None:
    @cli.group("error")
    def error_group() -> None:
        """Open-error registry — highest priority, blocks new work."""

    @error_group.command("file")
    @click.option(
        "--source",
        type=click.Choice(
            [
                reg.SOURCE_BYPASS,
                reg.SOURCE_GATE_FIRE,
                reg.SOURCE_TEST_FAILURE,
                reg.SOURCE_UNCAUGHT_EXCEPTION,
                reg.SOURCE_OTHER,
            ]
        ),
        required=True,
        help="Which category — bypass / gate_fire / test_failure / uncaught_exception / other",
    )
    @click.option("--summary", required=True, help="One-line description of the error")
    @click.option(
        "--context",
        default="",
        help="Freeform context — command run, gate name, exception message, stack pointer",
    )
    @click.option(
        "--hint",
        default="",
        help="Pointer to what needs investigating (file path, script name, doc ref)",
    )
    def file_cmd(source: str, summary: str, context: str, hint: str) -> None:
        """File a new open error."""
        try:
            rec = reg.file_error(
                source=source,
                summary=summary,
                context=context,
                root_cause_investigation_hint=hint,
            )
        except ValueError as exc:
            raise click.ClickException(str(exc))
        click.echo(f"[+] error filed: {rec['error_id']} ({rec['source']})")
        click.echo(f"    {rec['summary']}")
        if rec["root_cause_investigation_hint"]:
            click.echo(f"    hint: {rec['root_cause_investigation_hint']}")

    @error_group.command("list")
    @click.option("--all", "show_all", is_flag=True, help="Include closed and deferred")
    def list_cmd(show_all: bool) -> None:
        """List open errors (default) or all errors (--all)."""
        recs = reg.list_all_errors() if show_all else reg.list_open_errors()
        if not recs:
            label = "any state" if show_all else "open"
            click.echo(f"No errors in registry ({label}).")
            return
        for rec in recs:
            state = rec.get("state", "?")
            state_label = {
                "open": "OPEN",
                "closed": "closed",
                "deferred": "DEFERRED",
            }.get(state, state)
            click.echo(
                f"  [{rec.get('error_id', '?')}] {state_label:9} "
                f"({rec.get('source', '?')}) {rec.get('summary', '?')}"
            )
            if state == "deferred":
                click.echo(
                    f"    deferred by {rec.get('deferred_by')}: {rec.get('deferred_reason')}"
                )

    @error_group.command("show")
    @click.argument("error_id")
    def show_cmd(error_id: str) -> None:
        """Show full JSON record for one error."""
        rec = reg.get_error(error_id)
        if rec is None:
            raise click.ClickException(f"error {error_id!r} not found")
        click.echo(json.dumps(rec, indent=2, ensure_ascii=False))

    @error_group.command("close")
    @click.argument("error_id")
    @click.option(
        "--evidence",
        required=True,
        help="What fixed it — commit sha, PR link, code path, test result",
    )
    def close_cmd(error_id: str, evidence: str) -> None:
        """Mark an error resolved."""
        try:
            rec = reg.close_error(error_id, evidence)
        except (KeyError, ValueError) as exc:
            raise click.ClickException(str(exc))
        click.echo(f"[+] error closed: {rec['error_id']}")
        click.echo(f"    {rec['closure_evidence']}")

    @error_group.command("defer")
    @click.argument("error_id")
    @click.option("--actor", required=True, help="Who is authorizing the deferral (e.g. andrew)")
    @click.option(
        "--reason",
        required=True,
        help="Why deferral is honest (>= 20 chars) — root-cause fix scope, session-time constraint, etc.",
    )
    def defer_cmd(error_id: str, actor: str, reason: str) -> None:
        """Operator-authorized deferral (>=20-char reason required)."""
        try:
            rec = reg.defer_error(error_id, actor, reason)
        except (KeyError, ValueError) as exc:
            raise click.ClickException(str(exc))
        click.echo(f"[+] error deferred: {rec['error_id']} by {rec['deferred_by']}")
        click.echo(f"    reason: {rec['deferred_reason']}")

    @error_group.command("status")
    def status_cmd() -> None:
        """One-line summary of registry state."""
        all_recs = reg.list_all_errors()
        by_state: dict[str, int] = {}
        for r in all_recs:
            s = r.get("state", "unknown")
            by_state[s] = by_state.get(s, 0) + 1
        parts = [f"{k}={v}" for k, v in sorted(by_state.items())]
        if not parts:
            click.echo("errors: (registry empty)")
        else:
            click.echo("errors: " + " ".join(parts))
        block = reg.block_reason()
        if block:
            click.echo("")
            click.echo(block)
