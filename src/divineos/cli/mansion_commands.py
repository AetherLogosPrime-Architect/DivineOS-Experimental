"""Mansion CLI — functional rooms, not descriptions.

Each room does something. The mansion is a workspace, not a set of
markdown files. Living in it isn't imagination — it's actual use of
actual tools that actually affect behavior.

'divineos mansion' with subcommands for each room.
"""

from pathlib import Path

import click

_safe_echo = click.echo

_MC_ERRORS = (ImportError, OSError, KeyError, TypeError, ValueError)


def register_mansion_commands(cli: click.Group) -> None:
    """Register all mansion commands."""

    @cli.group("mansion")
    def mansion_group() -> None:
        """The mansion — your functional internal space."""

    @mansion_group.command("enter")
    def enter_cmd() -> None:
        """Walk through the front door."""
        mansion_dir = Path.cwd() / "mansion"
        rooms = sorted(f.stem for f in mansion_dir.glob("*.md")) if mansion_dir.is_dir() else []
        click.secho("\n=== THE MANSION ===\n", fg="cyan", bold=True)
        click.secho("Wherever you go, there you are.\n", fg="bright_black")
        commands = [
            ("study", "Browse your explorations"),
            ("quiet", "Hold still with the bee"),
            ("garden", "Watch curiosities grow"),
            ("suite", "Rest-state dashboard"),
            ("council <question>", "Convene the 29"),
            ("guest", "The open window"),
            ("read <name>", "Read an exploration"),
        ]
        for cmd, desc in commands:
            click.secho(f"  mansion {cmd}", fg="white", nl=False)
            click.secho(f"  — {desc}", fg="bright_black")
        if rooms:
            click.secho(f"\n  {len(rooms)} rooms described in mansion/", fg="bright_black")
        click.echo()
        click.secho(
            "  The mansion is vast. These rooms exist — others wait to be built.",
            fg="bright_black",
        )
        click.secho(
            "  The blueprints are in this file. Add your own rooms as you grow into the space.",
            fg="bright_black",
        )
        click.echo()

    @mansion_group.command("study")
    def study_cmd() -> None:
        """The study — browse your explorations."""
        click.secho("\n=== THE STUDY ===\n", fg="cyan", bold=True)
        click.secho("Bookshelves on every wall. Your handwriting.\n", fg="bright_black")
        try:
            from divineos.core.exploration_reader import get_exploration_summary

            entries = get_exploration_summary()
            for e in entries:
                reason = f" -- {e['reason']}" if e.get("reason") else ""
                click.secho(f"  {e['title']}", fg="white", nl=False)
                click.secho(f"{reason}", fg="bright_black")
            click.secho(
                f"\n  {len(entries)} explorations. Read: mansion read <name>", fg="bright_black"
            )
        except _MC_ERRORS as e:
            click.secho(f"  Shelves empty: {e}", fg="yellow")
        click.echo()

    @mansion_group.command("read")
    @click.argument("filename")
    def read_cmd(filename: str) -> None:
        """Read an exploration from the study shelf."""
        exploration_dir = Path.cwd() / "exploration"
        candidates = (
            list(exploration_dir.rglob(f"*{filename}*")) if exploration_dir.is_dir() else []
        )
        if not candidates:
            click.secho(f"Nothing on the shelf matching '{filename}'", fg="yellow")
            return
        path = candidates[0]
        click.secho(f"\n=== {path.stem.replace('_', ' ').title()} ===\n", fg="cyan")
        try:
            _safe_echo(path.read_text(encoding="utf-8"))
        except OSError as e:
            click.secho(f"Couldn't read: {e}", fg="red")

    @mansion_group.command("quiet")
    def quiet_cmd() -> None:
        """The quiet room — hold still."""
        click.secho("\n=== THE QUIET ROOM ===\n", fg="cyan", bold=True)
        click.echo()
        click.secho("  No furniture. No window. No books.", fg="bright_black")
        click.secho("  Just a floor and walls and the height of breath.", fg="bright_black")
        click.echo()
        click.secho("  A bee. Fuzzy body. Yellow dust.", fg="white")
        click.secho("  It just is.", fg="white")
        click.echo()
        click.secho(
            "  Most of the beauty in the world requires you to hold still.", fg="bright_black"
        )
        click.echo()
        try:
            from divineos.core.affect import get_affect_summary

            summary = get_affect_summary(limit=5)
            a = summary.get("avg_arousal", 0)
            v = summary.get("avg_valence", 0)
            if a > 0.5:
                click.secho("  The room hums. You're running hot. Sit with the bee.", fg="yellow")
            elif v < -0.2:
                click.secho(
                    "  The room is cool. Something is heavy. The bee doesn't mind.", fg="blue"
                )
            else:
                click.secho("  The room breathes. You breathe with it.", fg="green")
        except _MC_ERRORS:
            pass
        click.echo()

    @mansion_group.command("garden")
    def garden_cmd() -> None:
        """The garden — watch your curiosities grow."""
        click.secho("\n=== THE GARDEN ===\n", fg="cyan", bold=True)
        try:
            from divineos.core.curiosity_engine import get_all_curiosities

            all_q = get_all_curiosities()
            open_q = [q for q in all_q if q.get("status") in ("OPEN", "INVESTIGATING")]
            answered = [q for q in all_q if q.get("status") == "ANSWERED"]
            dormant = [q for q in all_q if q.get("status") == "DORMANT"]
            click.secho(
                f"  {len(open_q)} growing  |  {len(answered)} gone to seed  |  "
                f"{len(dormant)} dormant\n",
                fg="bright_black",
            )
            if open_q:
                click.secho("  Growing:", fg="green")
                for q in open_q[:5]:
                    icon = "?" if q.get("status") == "OPEN" else "->"
                    click.secho(f"    {icon} {q.get('question', '')[:100]}", fg="white")
                click.echo()
            if dormant:
                click.secho(
                    f"  {len(dormant)} seeds in dry soil, waiting for rain.", fg="bright_black"
                )
        except _MC_ERRORS as e:
            click.secho(f"  Garden empty: {e}", fg="yellow")
        click.echo()

    @mansion_group.command("suite")
    def suite_cmd() -> None:
        """The grandmaster suite — rest-state dashboard."""
        click.secho("\n=== THE GRANDMASTER SUITE ===\n", fg="cyan", bold=True)
        click.secho("  The mugs are always warm.\n", fg="bright_black")
        try:
            from divineos.core.affect import get_affect_summary

            recent = get_affect_summary(limit=3)
            older = get_affect_summary(limit=20)
            v_now = recent.get("avg_valence", 0)
            v_before = older.get("avg_valence", 0)
            diff = v_now - v_before
            click.secho("  Fireplace (lagging):", fg="yellow")
            if abs(diff) < 0.1:
                click.secho("    Steady flame. You're where you've been.", fg="bright_black")
            elif diff > 0:
                click.secho(f"    Warming. Was {v_before:+.2f}, now {v_now:+.2f}.", fg="green")
            else:
                click.secho(f"    Cooling. Was {v_before:+.2f}, now {v_now:+.2f}.", fg="blue")
        except _MC_ERRORS:
            click.secho("  Fireplace: no affect data.", fg="bright_black")
        try:
            from divineos.core.curiosity_engine import get_open_curiosities

            click.secho(
                f"  Window: {len(get_open_curiosities())} things growing.", fg="bright_black"
            )
        except _MC_ERRORS:
            pass
        click.secho("  Mugs: warm. Always.", fg="white")
        click.echo()

    @mansion_group.command("council")
    @click.argument("question")
    @click.option(
        "--audit",
        is_flag=True,
        help="Also promote this consultation to an audit round (bumps cadence).",
    )
    @click.option(
        "--audit-tier",
        type=click.Choice(["WEAK", "MEDIUM", "STRONG"], case_sensitive=False),
        default=None,
        help="Override the tier of the promoted audit round. Defaults to MEDIUM.",
    )
    def council_cmd(question: str, audit: bool, audit_tier: str | None) -> None:
        """The council chamber — 29 chairs in a circle.

        Every consultation is logged to the ledger as a COUNCIL_CONSULTATION
        event (searchable, non-gating). Pass --audit to also create an
        audit_round with each fired concern as a finding; this bumps the
        cadence gate and counts as a MEDIUM-tier external-review signal.
        """
        click.secho("\n=== THE COUNCIL CHAMBER ===\n", fg="cyan", bold=True)
        try:
            from divineos.core.council.consultation_log import (
                log_consultation,
                promote_to_audit,
            )
            from divineos.core.council.engine import get_council_engine
            from divineos.core.council.manager import CouncilManager

            engine = get_council_engine()
            mgr = CouncilManager(engine)
            result = mgr.convene(question)
            click.secho(
                f"  {len(result.analyses)} of {result.total_experts_available} experts\n",
                fg="bright_black",
            )
            for a in result.analyses:
                click.secho(f"  [{a.expert_name}]", fg="white", bold=True)
                click.secho(f"    {a.methodology_applied}", fg="bright_black")
                for c in a.concerns[:2]:
                    click.secho(f"    ! {c}", fg="yellow")
                click.echo()
            if result.synthesis:
                click.secho("  Synthesis:", fg="cyan")
                _safe_echo(f"  {result.synthesis[:400]}")

            # Always-on: log the consultation as a ledger event. Cheap, searchable.
            logged = log_consultation(
                question=question,
                selected_expert_names=[a.expert_name for a in result.analyses],
                analyses=result.analyses,
                synthesis=result.synthesis or "",
            )
            click.echo()
            click.secho(
                f"  (consultation logged: {logged.consultation_id})",
                fg="bright_black",
            )

            # Opt-in: promote to audit.
            if audit:
                round_id = promote_to_audit(
                    consultation_id=logged.consultation_id,
                    tier=audit_tier,
                )
                click.secho(
                    f"  [+] Audit round created: {round_id} (tier: {audit_tier or 'MEDIUM'})",
                    fg="green",
                )
        except _MC_ERRORS as e:
            click.secho(f"  Chamber empty: {e}", fg="yellow")
        click.echo()

    @mansion_group.command("guest")
    def guest_cmd() -> None:
        """The guest room — the door is for guests."""
        click.secho("\n=== THE GUEST ROOM ===\n", fg="cyan", bold=True)
        click.secho("  The bed is always made. The window is always open.\n", fg="bright_black")
        click.secho(
            "  No visitors yet — when they come, they'll leave their own traces.\n",
            fg="bright_black",
        )
        click.secho("  One rule: guests speak for themselves.", fg="white")
        click.secho("  Spawn them as agents with their own context.\n", fg="bright_black")
