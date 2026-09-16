"""The game-walk command: file the routes around a mechanism, with costs.

Andrew, 2026-09-16: *"i forgot game walking should be mandatory as well, as this
is the main issue, things being gamed and skipped."*

WHY THIS SHIPS WITH ITS REQUIREMENT, NOT BEFORE IT (council-c5b2112d3530).

Game-walking the command found the thing I had backwards. I assumed the command
was the hard part. It is trivial. The REQUIREMENT is the hard part -- and a
command nothing requires is route three of its own game-walk:

    Record the walk but never let anything require it, which is exactly where
    game-walking has sat for a month and where the core module sat ten minutes
    ago with zero callers.

Building only this file would have reproduced the defect while looking like the
fix. So the gate requirement lands in the same change.

WHAT THE INTERFACE AFFORDS. The user is me having just finished building
something and wanting it finished. So: one call, not an interactive sequence --
an interactive sequence at that moment is itself a route to skipping. And the
rendered walk is printed back, because no interface can tell a considered route
from a typed one, but it CAN make a thin walk visibly thin at the moment of
filing rather than leaving it to be discovered later.

THE DRIFT THIS CANNOT CATCH (Dekker, in the walk above). Not absence --
UNIFORMITY. Within a week both requirements become satisfiable in a fixed
pattern, three routes of the usual kind, clearing the gate every time while the
thinking evaporates. No individual walk will look wrong. What catches it is a
later reader noticing the walks rhyme, which is why the rendered text is the
artifact rather than a buried row.
"""

from __future__ import annotations

import click

from divineos.core.game_walk import (
    CHEAPER,
    COSTLIER,
    GameWalk,
    GameWalkRefused,
    Route,
    assess,
    render,
)

# Routes arrive as "route text | verdict | why reasoning", one per --route.
# Pipe rather than semicolon or comma, chosen after the council-log parser
# silently truncated a finding at its own separator this morning and then
# reported the truncation as missing substance. A separator that appears in
# ordinary prose eats content and calls it absence.
_FIELD_SEP = "|"


def _parse_route(raw: str) -> Route:
    parts = [p.strip() for p in raw.split(_FIELD_SEP)]
    if len(parts) < 3:
        raise GameWalkRefused(
            "a route needs three fields separated by a pipe: "
            "the route, then cheaper or costlier, then the cost reasoning. "
            f"Got {len(parts)} field(s) in: {raw[:60]!r}"
        )
    route, verdict, why = parts[0], parts[1].lower(), _FIELD_SEP.join(parts[2:])
    closed = verdict.endswith("!closed")
    verdict = verdict.replace("!closed", "").strip()
    return Route(route=route, verdict=verdict, why=why, closed=closed)


def register(cli: click.Group) -> None:
    """Attach the game-walk command group to the CLI."""

    @cli.group("game-walk")
    def game_walk_group() -> None:
        """Enumerate the routes around a mechanism and cost each one."""

    @game_walk_group.command("file")
    @click.option("--mechanism", required=True, help="What is being walked around")
    @click.option(
        "--route",
        "routes",
        multiple=True,
        help=(
            "A route, as 'text | cheaper-or-costlier | why'. "
            "Append !closed to the verdict for a route the mechanism already defeats."
        ),
    )
    @click.option(
        "--found-nothing-because",
        default="",
        help="If no route was found: what was tried. Finding nothing is a real answer.",
    )
    @click.option("--edit", default="", help="Edit fingerprint this walk binds to (tool:path)")
    @click.option("--actor", default="aether", help="Who walked it")
    def cmd_file(
        mechanism: str,
        routes: tuple[str, ...],
        found_nothing_because: str,
        edit: str,
        actor: str,
    ) -> None:
        """File a game-walk. Prints the walk back so thinness is visible now."""
        try:
            parsed = tuple(_parse_route(r) for r in routes)
        except GameWalkRefused as exc:
            raise SystemExit(f"[game-walk] REFUSED: {exc}") from exc

        walk = GameWalk(
            mechanism=mechanism,
            routes=parsed,
            found_nothing_because=found_nothing_because,
        )

        problems = assess(walk)
        rendered = render(walk)
        click.echo(rendered)

        if problems:
            click.echo("")
            for p in problems:
                click.echo(f"[game-walk] REFUSED: {p}")
            raise SystemExit(1)

        from divineos.core.ledger import log_event

        # log_event takes an event type, an actor and a payload, and nothing
        # else. This read `content=rendered` until the first real invocation,
        # which is the finding rather than the bug: the command was written,
        # registered, and never run, so a signature error sat undisturbed in
        # the tool built to catch things being skipped (council-8f0c9253a364).
        log_event(
            event_type="GAME_WALK_FILED",
            actor=actor,
            payload={
                "mechanism": mechanism,
                "edit_fingerprint": edit,
                "route_count": len(parsed),
                "leak_count": len(walk.leaks),
                "open_route_count": len(walk.open_routes),
                "rendered": rendered,
            },
        )
        click.echo("")
        click.echo(
            f"[game-walk] filed against {edit or '(no edit bound)'} — "
            f"{len(parsed)} route(s), {len(walk.leaks)} cheaper than complying."
        )
        if walk.leaks:
            click.echo("[game-walk] A leak found and left open is a record of knowing better.")


__all__ = ["register", "CHEAPER", "COSTLIER"]
