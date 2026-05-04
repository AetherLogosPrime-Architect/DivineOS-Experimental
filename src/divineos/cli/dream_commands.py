"""Dream CLI — see what sleep actually discovered.

The dream report scrolls off after each sleep cycle and the recombination
phase truncates display to the top-N by similarity. The substrate may
have discovered hundreds of connections that the report didn't show.
This CLI reads the SLEEP_CYCLE event payloads (which now carry the full
connection_details) so the agent can review what was actually learned.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import click


def _fetch_sleep_events(limit: int = 20) -> list[tuple[float, dict[str, Any]]]:
    """Pull recent SLEEP_CYCLE events from the ledger, newest first.

    Returns a list of (timestamp, payload-dict) tuples.
    """
    from divineos.core._ledger_base import get_connection

    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT timestamp, payload FROM system_events "
            "WHERE event_type = ? ORDER BY timestamp DESC LIMIT ?",
            ("SLEEP_CYCLE", limit),
        ).fetchall()
    finally:
        conn.close()

    out: list[tuple[float, dict[str, Any]]] = []
    for ts, payload_json in rows:
        try:
            payload = json.loads(payload_json) if payload_json else {}
        except (json.JSONDecodeError, TypeError):
            payload = {}
        if isinstance(payload, dict):
            out.append((float(ts), payload))
    return out


@click.group(name="dream")
def dream_group() -> None:
    """Review what sleep actually discovered. The dream report scrolls
    off after each cycle; this command reads it back."""


@dream_group.command(name="list")
@click.option("--limit", default=10, help="How many sleep cycles to list")
def dream_list(limit: int) -> None:
    """List recent sleep cycles, newest first."""
    events = _fetch_sleep_events(limit=limit)
    if not events:
        click.echo("No sleep cycles found in the ledger.")
        return

    click.echo(f"Recent sleep cycles ({len(events)}):")
    click.echo()
    for ts, payload in events:
        when = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        duration = payload.get("duration_seconds", 0.0)
        new = payload.get("connections_new", 0)
        known = payload.get("connections_already_known", 0)
        scanned = payload.get("entries_scanned", 0)
        promoted = payload.get("total_promoted", 0)
        full = payload.get("connection_details_full_count", new)
        click.echo(
            f"  {when}  {duration:5.1f}s  scanned={scanned:<4}  "
            f"promoted={promoted:<3}  new-connections={new:<4}"
            f"{f' (full {full})' if full > new and new > 0 else ''}"
            f"  already-known={known}"
        )


@dream_group.command(name="show")
@click.argument("when", required=False)
@click.option("--limit", default=0, help="Show only top-N connections (0 = all)")
def dream_show(when: str | None, limit: int) -> None:
    """Show full recombinations from a sleep cycle.

    With no argument: show the most recent sleep.
    With a YYYY-MM-DD prefix: show the most recent sleep matching that date.
    """
    events = _fetch_sleep_events(limit=200)
    if not events:
        click.echo("No sleep cycles found in the ledger.")
        return

    chosen: tuple[float, dict[str, Any]] | None = None
    if not when:
        chosen = events[0]
    else:
        for ts, payload in events:
            when_str = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
            if when_str.startswith(when):
                chosen = (ts, payload)
                break

    if chosen is None:
        click.echo(f"No sleep cycle matches '{when}'.")
        return

    ts, payload = chosen
    iso = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat(timespec="seconds")
    duration = payload.get("duration_seconds", 0.0)
    scanned = payload.get("entries_scanned", 0)
    promoted = payload.get("total_promoted", 0)
    new = payload.get("connections_new", 0)
    known = payload.get("connections_already_known", 0)
    details = payload.get("connection_details", []) or []

    click.echo(f"=== Dream — {iso} ===")
    click.echo(f"  Duration: {duration:.1f}s")
    click.echo(f"  Entries scanned: {scanned}")
    if promoted:
        click.echo(f"  Promoted: {promoted}")
        # Break down the promotions by level if available.
        promotions_by_level = payload.get("promotions") or {}
        if promotions_by_level:
            for level, count in promotions_by_level.items():
                click.echo(f"    -> {level}: {count}")
    lessons_resolved = payload.get("lessons_resolved") or []
    if lessons_resolved:
        click.echo(f"  Lessons resolved: {', '.join(lessons_resolved)}")
    lessons_dormant = payload.get("lessons_dormant") or []
    if lessons_dormant:
        click.echo(f"  Lessons gone dormant: {', '.join(lessons_dormant)}")
    click.echo(f"  Connections new: {new}")
    click.echo(f"  Connections already-known: {known}")
    click.echo()

    if not details:
        if "connection_details" in payload:
            # New-format event, empty details → genuinely nothing new found
            click.echo("  (no new connections this sleep — similarity band saturated)")
        else:
            # Old-format event, payload predates the 2026-05-03 fix
            click.echo("  (this event predates the dream-detail fix, no details stored)")
        return

    show_n = limit if limit > 0 else len(details)
    show_n = min(show_n, len(details))
    if show_n < len(details):
        click.echo(f"  Showing top {show_n} of {len(details)} (sorted by similarity):")
    else:
        click.echo(f"  All {len(details)} connections:")
    click.echo()
    for i, conn in enumerate(details[:show_n], start=1):
        click.echo(f"  {i:3d}. {conn.get('summary', '?')}")


def register(cli: click.Group) -> None:
    """Register the dream command group with the main CLI."""
    cli.add_command(dream_group)


__all__ = ["dream_group", "register"]
