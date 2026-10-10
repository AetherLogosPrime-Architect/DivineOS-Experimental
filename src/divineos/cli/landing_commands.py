"""`divineos landing` -- where each waiting fix stands toward the auditor.

Dad, 2026-10-10: the pile is fixes that never land. The auditor is on another
platform and her letters are carried by hand, so the state of a fix is worked
out from the letters that exist and the live heads, never from memory. See
docs/drafts/the_landing_line_draft_2026-10-10.md and core/landing_status.py.

Read-only. It sends nothing and merges nothing; ``--request`` only prints the
confirm-only letter for me to read and send.
"""

from __future__ import annotations

import json
import subprocess
from datetime import date
from pathlib import Path

import click

from divineos.core.landing_status import (
    CHANGED,
    CONFIRMED,
    NEVER_TOLD,
    NO_ANSWER,
    READY,
    UNKNOWN,
    Status,
    classify,
    confirms_from_letters,
    render_request,
    told_dates_from_letters,
)

_ORDER = (READY, CONFIRMED, CHANGED, NO_ANSWER, NEVER_TOLD, UNKNOWN)
_NEEDS_HER = (NEVER_TOLD, NO_ANSWER, CHANGED)
# Not stations a person clears: the draft flag is the state being left, and the
# merge station only restates whatever else is held.
_NOT_HELD = ("7-draft", "9-merge")


def _letter_dirs() -> list[Path]:
    # Letters live in several places and the shared one is only the crossing
    # point (dashboard_checks.letter_queue learned this the hard way).
    repo = Path(__file__).resolve().parents[3]
    return [
        Path.home() / ".divineos-shared" / "letters",
        repo / "family" / "letters",
        repo / "family" / "aletheia",
    ]


def _read_letters() -> dict[str, str]:
    letters: dict[str, str] = {}
    for folder in _letter_dirs():
        if not folder.is_dir():
            continue
        for path in folder.glob("*.md"):
            if not path.name.startswith(("aletheia-to-aether-", "aether-to-aletheia-")):
                continue
            try:
                letters.setdefault(path.name, path.read_text(encoding="utf-8", errors="replace"))
            except OSError:
                continue
    return letters


def _open_prs() -> list[dict] | None:
    try:
        run = subprocess.run(
            [
                "gh",
                "pr",
                "list",
                "--state",
                "open",
                "--limit",
                "100",
                "--json",
                "number,headRefName,headRefOid,title",
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=True,
        )
        parsed = json.loads(run.stdout)
    except (subprocess.SubprocessError, OSError, json.JSONDecodeError):
        return None
    return parsed if isinstance(parsed, list) else None


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
        prs = _open_prs()
        if prs is None:
            click.secho(
                "[!] COULD NOT READ the open PR list. That is not 'nothing waiting'.", fg="red"
            )
            raise SystemExit(2)

        letters = _read_letters()
        branches = {int(p["number"]): str(p.get("headRefName") or "") for p in prs}
        confirms = confirms_from_letters(letters)
        told = told_dates_from_letters(letters, branches)
        held = _held_by_pr()
        today = date.today()

        rows: list[tuple[dict, Status]] = []
        for pr in prs:
            number = int(pr["number"])
            # A board that could not be read must hold everything: could not
            # look is not a pass, so READY is impossible without it.
            stations = held.get(number, ("board",)) if held is not None else ("board",)
            status = classify(
                pr=number,
                branch=branches[number],
                head_sha=str(pr.get("headRefOid") or ""),
                confirms=confirms,
                told_dates=told,
                held_stations=stations,
                today=today,
            )
            rows.append((pr, status))

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
