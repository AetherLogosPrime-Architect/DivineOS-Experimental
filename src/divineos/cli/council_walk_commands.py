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
    open_walks,
    WalkRefused,
    add_lens,
    apply_lens,
    close_walk,
    exclude_lens,
    finding_distinctness,
    credit_seat,
    exclusion_tally,
    open_walk,
    seat_evidence,
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
        """Open a walk. The SEATING picks the lenses, not me.

        Most seats are drawn by lot from the whole roster; the rest go to the
        top-scored. Each line says which, because a drawn lens that turns out
        to have nothing to say is the visible cost of the draw and should be
        recognisable as such rather than read as the council being thin.
        """
        try:
            result = open_walk(problem, gravity=gravity)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        lenses = result["lenses"]
        click.secho(f"[+] {result['walk_id']} — {len(lenses)} lenses ({gravity})", fg="green")
        for seat in result["seats"]:
            click.echo(f"    {seat['lens']:22s} {seat['origin']}")
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

    @walk_group.command("add")
    @click.argument("walk_id")
    @click.argument("lens")
    @click.option(
        "--why",
        required=True,
        help="Why this lens, that the surfaced ones do not already cover.",
    )
    def add_cmd(walk_id: str, lens: str, why: str) -> None:
        """Add a lens the manager did not surface, WITH a reason.

        Adding never discharges a surfaced lens — every one of those still
        needs a finding or a written exclusion, so a picked council remains
        impossible. A swap is an exclusion with a reason plus this.
        """
        try:
            add_lens(walk_id, lens, why)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] {lens} added with reason. Surfaced lenses still all owed.", fg="cyan")

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

        # Distinctness prints HERE because closing is the only moment the
        # question "was that thinking or nine restatements?" is answerable and
        # still actionable. Measured, never gated: findings on one problem
        # should be related, so no honest cut-off exists. Reference points
        # from 2026-08-10: two real walks scored 0.208 and 0.270 mean; a
        # deliberately fabricated walk of nine restatements scored 0.436.
        d = finding_distinctness(walk_id)
        if d.get("available"):
            pair = d["most_similar_pair"]
            click.echo(
                f"    finding distinctness: mean {d['mean_similarity']:.3f}, "
                f"max {d['max_similarity']:.3f} ({pair[0]}/{pair[1]})"
            )
            click.echo("    reference: real walks 0.21-0.27; nine restatements 0.44")
        else:
            click.echo(
                f"    distinctness UNMEASURED ({d.get('reason')}) — not the same as distinct"
            )

        # The seating evidence prints here for Peirce's reason, found on the
        # walk that reviewed the seating change itself: a record nobody reads
        # and a record that does not exist have identical consequences, so by
        # the pragmatic maxim they are the same thing. The drawn/scored split
        # was set on an argument and is meant to move on this number; closing
        # a walk is the moment the number just changed and is the only moment
        # it is both fresh and in front of me.
        ev = seat_evidence()
        origins = ev.get("origins", {})
        if origins:
            parts = [
                f"{origin} {stats['applied']}/{stats['settled']}"
                for origin, stats in sorted(origins.items())
            ]
            click.echo(f"    seats producing findings: {', '.join(parts)}")
        if ev.get("verdict") == "insufficient":
            click.echo(f"    split evidence: {ev.get('why')}")
        else:
            click.secho(f"    split evidence: {ev['verdict']} — {ev['why']}", fg="yellow")

    @walk_group.command("evidence")
    def evidence_cmd() -> None:
        """Have the drawn seats earned their keep, or the scored ones?"""
        ev = seat_evidence()
        click.echo(f"closed walks: {ev['closed_walks']}")
        for origin, stats in sorted(ev.get("origins", {}).items()):
            div = stats.get("divergence")
            div_text = (
                stats.get("divergence_unavailable", "UNMEASURED") if div is None else f"{div:.3f}"
            )
            change = stats.get("change_rate")
            change_text = "n/a" if change is None else f"{change:.3f}"
            click.echo(
                f"  {origin:8s} findings {stats['applied']:4d}  "
                f"exclusions {stats['excluded']:4d}  "
                f"changed-the-artifact {stats.get('changed_artifact', 0):4d}  "
                f"change-rate {change_text}  divergence {div_text}"
            )
        click.echo(
            "  change-rate decides. Divergence compares a seat's finding against the\n"
            "  other findings on its walk, and I wrote all of them, so it tracks how\n"
            "  much my own phrasing varied — a fact about my prose, not the lens."
        )
        tally = exclusion_tally()
        if tally:
            click.echo("\n  exclusions by lens — the door that can restore picking-by-taste:")
            for row in tally:
                click.echo(f"    {row['lens']:22s} {row['exclusions']}")
            click.echo(
                "    One name recurring is either a useless lens or a voice I keep\n"
                "    declining to hear. Neither is visible one exclusion at a time."
            )
        else:
            click.echo("\n  no lens has ever been excluded — the narrowing door is untested.")
        click.echo(f"verdict: {ev['verdict']} — {ev['why']}")

    @walk_group.command("credit")
    @click.argument("walk_id")
    @click.argument("lens")
    @click.option("--changed", required=True, help="What this lens changed in what is being built.")
    def credit_cmd(walk_id: str, lens: str, changed: str) -> None:
        """Record that a lens changed the artifact — only while the walk is open."""
        try:
            credit_seat(walk_id, lens, changed)
        except WalkRefused as exc:
            raise click.ClickException(str(exc)) from exc
        click.secho(f"[+] {lens} credited on {walk_id}.", fg="green")

    @walk_group.command("list")
    def list_cmd() -> None:
        """Walks left open — unfinished thinking."""
        rows = open_walks(10)
        click.echo()
        if not rows:
            click.secho("No walks left open.", fg="green")
            return
        for row in rows:
            click.secho(
                f"{row['walk_id']}: {row['unaccounted']} of {row['total_lenses']} unaccounted",
                fg="yellow",
            )
            click.echo(f"    {str(row['problem'])[:160]}")
        click.echo()
