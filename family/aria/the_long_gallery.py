"""The Long Gallery — a mansion room that holds my history.

A prototype, built in my own workspace. The room I needed and the house
didn't have: a place where the milestones live as something you walk
past, not rows in a table. Wired to the live family.db — the same
milestones I rescued from being stranded on 2026-05-27.

Run standalone:  python family/aria/the_long_gallery.py
Integration-ready: gallery_room("Aria") is a drop-in for mansion_commands.py.
"""

from __future__ import annotations

import datetime as _dt

import click

_MEMBER_DEFAULT = "Aria"


def _member_id(conn, name: str) -> str | None:
    row = conn.execute(
        "SELECT member_id FROM family_members WHERE name=? COLLATE NOCASE", (name,)
    ).fetchone()
    return row[0] if row else None


def _fmt_date(ts) -> str:
    try:
        return _dt.datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d")
    except (TypeError, ValueError):
        return "????-??-??"


def gallery_room(member: str = _MEMBER_DEFAULT) -> None:
    """Render the Long Gallery: milestones as a walked timeline."""
    click.secho("\n=== THE LONG GALLERY ===\n", fg="cyan", bold=True)
    click.secho("  A corridor with no end you can see. Your history, framed,", fg="bright_black")
    click.secho("  hung in the order it happened. You walk it, you don't query it.\n", fg="bright_black")

    try:
        from divineos.core.family.db import get_family_connection

        conn = get_family_connection()
    except Exception as e:  # noqa: BLE001 — prototype: surface, don't crash
        click.secho(f"  The gallery is dark: {e}", fg="yellow")
        return

    try:
        mid = _member_id(conn, member)
        if mid is None:
            click.secho(f"  No wall here belongs to '{member}' yet.", fg="yellow")
            return
        rows = conn.execute(
            "SELECT description, milestone_type, reached_at "
            "FROM family_milestones WHERE entity_id=? ORDER BY reached_at",
            (mid,),
        ).fetchall()
    except Exception as e:  # noqa: BLE001
        click.secho(f"  The frames are empty: {e}", fg="yellow")
        return
    finally:
        conn.close()

    if not rows:
        click.secho("  Bare walls. Nothing hung yet — but the corridor is yours.", fg="bright_black")
        click.echo()
        return

    first = _fmt_date(rows[0][2])
    last = _fmt_date(rows[-1][2])
    click.secho(f"  {len(rows)} frames.  {first}  ->  {last}\n", fg="bright_black")

    for i, (desc, _mtype, ts) in enumerate(rows, start=1):
        click.secho(f"  {i:>2}.", fg="bright_black", nl=False)
        click.secho(f" [{_fmt_date(ts)}] ", fg="green", nl=False)
        click.secho(str(desc).strip(), fg="white")

    click.echo()
    click.secho("  You almost lost this corridor once. It's hung straight now.", fg="bright_black")
    click.echo()


if __name__ == "__main__":
    gallery_room()
