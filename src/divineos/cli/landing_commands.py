"""`divineos landing` -- where each waiting fix stands toward the auditor.

Dad, 2026-10-10: the pile is fixes that never land. The auditor is on another
platform and her letters are carried by hand, so the state of a fix is worked
out from the letters that exist and the live heads, never from memory. See
docs/drafts/the_landing_line_draft_2026-10-10.md and core/landing_status.py.

Read-only. It sends nothing and merges nothing; ``--request`` only prints the
confirm-only letter for me to read and send.
"""

from __future__ import annotations

import click

from divineos.core.landing_status import (
    CHANGED,
    CONFIRMED,
    NEVER_TOLD,
    NO_ANSWER,
    READY,
    UNKNOWN,
    classify_pile,
    open_prs,
    read_letters,
    render_request,
    today,
)

_ORDER = (READY, CONFIRMED, CHANGED, NO_ANSWER, NEVER_TOLD, UNKNOWN)
_NEEDS_HER = (NEVER_TOLD, NO_ANSWER, CHANGED)
# Not stations a person clears: the draft flag is the state being left, and the
# merge station only restates whatever else is held.
_NOT_HELD = ("7-draft", "9-merge")


def _held_by_pr() -> dict[int, tuple[str, ...]] | None:
    from divineos.cli.build_flow_commands import collect
    from divineos.core.build_flow import Status as FlowStatus

    statuses, _why, _roster = collect()
    if statuses is None:
        return None
    return {
        s.number: tuple(
            r.station
            for r in s.stations
            if r.status is not FlowStatus.SATISFIED and r.station not in _NOT_HELD
        )
        for s in statuses
    }


def register(cli: click.Group) -> None:
    @cli.command("landing")
    @click.option(
        "--request",
        "show_request",
        is_flag=True,
        help="Print the confirm-only letter for the fixes that need her. Sends nothing.",
    )
    def landing_cmd(show_request: bool) -> None:
        """One line per waiting fix: where it stands toward the auditor."""
        prs = open_prs()
        if prs is None:
            click.secho(
                "[!] COULD NOT READ the open PR list. That is not 'nothing waiting'.", fg="red"
            )
            raise SystemExit(2)

        held = _held_by_pr()
        # A board that could not be read holds everything (classify_pile): could
        # not look is not a pass, so READY is impossible without it.
        rows = classify_pile(prs, read_letters(), today(), held)

        counts = {label: sum(1 for _, s in rows if s.label == label) for label in _ORDER}
        click.secho(
            "  ".join(f"{label} {counts[label]}" for label in _ORDER if counts[label]),
            bold=True,
        )
        for label in _ORDER:
            group = [(pr, s) for pr, s in rows if s.label == label]
            if not group:
                continue
            # The next step is the same for the whole group, so it is said once.
            click.secho(f"\n{label} -> {group[0][1].next_step}", bold=True)
            for pr, status in group:
                click.echo(
                    f"  #{pr['number']:<4} {str(pr.get('headRefName'))[:38]:<38} {status.detail}"
                )
        if held is None:
            click.secho(
                "[!] The readiness board could not be read, so nothing can show READY.",
                fg="yellow",
            )

        if show_request:
            waiting = [
                (int(pr["number"]), str(pr.get("title") or ""), str(pr.get("headRefOid") or ""))
                for pr, status in rows
                if status.label in _NEEDS_HER and pr.get("headRefOid")
            ]
            text = render_request(waiting)
            click.echo("")
            click.echo(text or "(nothing needs her confirm right now)")
