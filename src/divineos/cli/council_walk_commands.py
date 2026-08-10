"""CLI: divineos walk — a council walk that refuses to close while a lens is open.

Andrew 2026-08-10: "unless you build enforcement which i have asked repeatedly
to be done.. you will continue to fake it, rendering the system pointless."

  divineos walk open "<problem>" --gravity high
  divineos walk apply <walk-id> <Lens> --finding "..."
  divineos walk exclude <walk-id> <Lens> --reason "..."
  divineos walk status <walk-id>
  divineos walk close <walk-id>
"""

from __future__ import annotations

import click

from divineos.core.council_walk import (
    GRAVITY_FLOORS,
    WalkRefused,
    apply_lens,
    close_walk,
    exclude_lens,
    open_walk,
    status,
)


def register(cli: click.Group) -> None:
    @cli.group("walk", invoke_without_command=True)
    @click.pass_context
    def walk_group(ctx: click.Context) -> None:
        """Council walks with enforced completion."""
        if ctx.invoked_subcommand is None:
            click.echo(ctx.get_help())

    @walk_group.command("open")
    @click.argument("problem")
    @click.option(
        "--gravity",
        type=click.Choice(sorted(GRAVITY_FLOORS)),
        default="normal",
        show_default=True,
        help="Lens floor: normal 5, high 9, severe 12, critical 15 (Andrew's ladder).",
    )
    def open_cmd(problem: str, gravity: str) -> None:
        """Open a walk. The MANAGER picks the lenses, not me."""
        try:
            result = open_walk(problem, gravity=gravity)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        lenses = result["lenses"]
        click.secho(f"[+] {result['walk_id']} — {len(lenses)} lenses ({gravity})", fg="green")
        for lens in lenses:
            click.echo(f"    {lens}")
        click.echo("\nEvery one needs a finding or a written exclusion before this can close.")

    @walk_group.command("apply")
    @click.argument("walk_id")
    @click.argument("lens")
    @click.option("--finding", required=True, help="What this lens actually produced.")
    def apply_cmd(walk_id: str, lens: str, finding: str) -> None:
        """Record what a lens produced when walked."""
        try:
            apply_lens(walk_id, lens, finding)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] {lens} applied.", fg="green")

    @walk_group.command("exclude")
    @click.argument("walk_id")
    @click.argument("lens")
    @click.option("--reason", required=True, help="Why excluding helps more than including.")
    def exclude_cmd(walk_id: str, lens: str, reason: str) -> None:
        """Exclude a lens WITH a reason. Silent narrowing is what this stops."""
        try:
            exclude_lens(walk_id, lens, reason)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] {lens} excluded with reason.", fg="yellow")

    @walk_group.command("status")
    @click.argument("walk_id")
    def status_cmd(walk_id: str) -> None:
        """Show every lens and its state."""
        try:
            st = status(walk_id)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo()
        click.secho(f"{walk_id} — {'CLOSED' if st['closed'] else 'OPEN'}", bold=True)
        click.echo(f"  {st['problem']}\n")
        for row in st["lenses"]:
            colour = {"APPLIED": "green", "EXCLUDED": "yellow"}.get(str(row["state"]), "red")
            click.secho(f"  [{row['state']:<8}] {row['lens']}", fg=colour)
        if st["open_lenses"]:
            click.echo(f"\n{len(st['open_lenses'])} still unaccounted for.")

    @walk_group.command("close")
    @click.argument("walk_id")
    def close_cmd(walk_id: str) -> None:
        """Close the walk. Refuses while any lens is open."""
        try:
            st = close_walk(walk_id)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] {walk_id} closed — {len(st['lenses'])} lenses accounted for.", fg="green")
