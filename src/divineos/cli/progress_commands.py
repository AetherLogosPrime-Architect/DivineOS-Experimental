"""CLI commands for the progress dashboard.

`divineos progress` — show measurable proof the system works.
`divineos rate` — user rates a session (the one metric we can't game).
"""

import sqlite3

import click

_PC_ERRORS = (
    ImportError,
    sqlite3.OperationalError,
    OSError,
    KeyError,
    TypeError,
    ValueError,
)


def register(cli: click.Group) -> None:
    """Register progress commands on the CLI group."""

    @cli.command("progress")
    @click.option("--days", default=30, type=int, help="Lookback period in days.")
    @click.option("--brief", is_flag=True, help="Show 3-line summary only.")
    @click.option("--export", is_flag=True, help="Output shareable markdown.")
    @click.option("--json", "as_json", is_flag=True, help="Output raw data as JSON.")
    def progress_cmd(days: int, brief: bool, export: bool, as_json: bool) -> None:
        """Show measurable progress metrics — real data, no vibes."""
        import dataclasses
        import json

        from divineos.core.progress_dashboard import (
            format_progress_brief,
            format_progress_export,
            format_progress_text,
            gather_progress,
        )

        report = gather_progress(lookback_days=days)

        if as_json:
            data = dataclasses.asdict(report)
            click.echo(json.dumps(data, indent=2))
        elif export:
            click.echo(format_progress_export(report))
        elif brief:
            click.echo(format_progress_brief(report))
        else:
            text = format_progress_text(report)
            try:
                click.echo(text)
            except UnicodeEncodeError:
                click.echo(text.encode("ascii", errors="replace").decode("ascii"))

    @cli.command("rate")
    @click.argument("rating", type=int)
    @click.option("-c", "--comment", default="", help="Optional note about why.")
    @click.option("--session", default="", help="Session ID (default: current).")
    def rate_cmd(rating: int, comment: str, session: str) -> None:
        """Rate a session 1-10. This is YOUR truth — the system cannot write here."""
        if not 1 <= rating <= 10:
            click.secho("Rating must be 1-10.", fg="red")
            return

        try:
            from divineos.core.user_ratings import record_rating

            if not session:
                # Use current session ID from ledger
                try:
                    from divineos.core.ledger import get_events

                    events = get_events(event_type="BRIEFING_LOADED", limit=1)
                    if events:
                        session = events[0].get("session_id", "unknown")[:36]
                    else:
                        session = "unknown"
                except _PC_ERRORS:
                    session = "unknown"

            record_rating(session, rating, comment)
            stars = "*" * rating + "." * (10 - rating)
            click.secho(f"[+] Rated {rating}/10 [{stars}]", fg="green")
            if comment:
                click.secho(f"    {comment}", fg="bright_black")
        except _PC_ERRORS as e:
            click.secho(f"[!] Failed to record rating: {e}", fg="red")

    @cli.command("ratings")
    @click.option("--correlate", is_flag=True, help="Compare against internal metrics.")
    @click.option("--limit", default=10, type=int, help="How many to show.")
    def ratings_cmd(correlate: bool, limit: int) -> None:
        """Show user session ratings and trends."""
        try:
            from divineos.core.user_ratings import (
                correlate_with_internal,
                get_rating_stats,
                get_ratings,
            )

            if correlate:
                result = correlate_with_internal(limit=limit)
                if result["correlation"] == "no_data":
                    click.secho("No ratings yet. Use: divineos rate <1-10>", fg="yellow")
                    return
                click.secho(f"=== Goodhart Check: {len(result['pairs'])} sessions ===", bold=True)
                click.secho(
                    f"  Correlation: {result['correlation']} (avg gap: {result.get('avg_gap', '?')})",
                    fg="green" if result["correlation"] == "strong" else "yellow",
                )
                for p in result["pairs"][:limit]:
                    gap_color = "green" if p["gap"] <= 2 else "yellow" if p["gap"] <= 3 else "red"
                    click.secho(
                        f"  {p['session_id']}  You: {p['user_rating']}/10  "
                        f"System: {p['internal_score']}/10  "
                        f"Gap: {p['gap']}",
                        fg=gap_color,
                    )
                if result["divergences"]:
                    click.secho(
                        f"\n  ⚠ {len(result['divergences'])} divergence(s) — "
                        f"system self-assessment doesn't match your experience.",
                        fg="red",
                    )
                return

            stats = get_rating_stats()
            if stats["count"] == 0:
                click.secho("No ratings yet. Use: divineos rate <1-10>", fg="yellow")
                return

            click.secho(f"=== User Ratings ({stats['count']} sessions) ===", bold=True)
            click.secho(
                f"  Average: {stats['avg']}/10 | "
                f"Range: {stats['min']}-{stats['max']} | "
                f"Recent: {stats['recent_avg']}/10 | "
                f"Trend: {stats['trend']}"
            )
            click.echo()

            ratings = get_ratings(limit=limit)
            for r in ratings:
                import time as _time

                ts = _time.strftime("%Y-%m-%d", _time.localtime(r["created_at"]))
                stars = "*" * r["rating"] + "." * (10 - r["rating"])
                line = f"  {ts}  {r['session_id'][:12]}  [{stars}] {r['rating']}/10"
                if r["comment"]:
                    line += f"  -- {r['comment']}"
                click.echo(line)
        except _PC_ERRORS as e:
            click.secho(f"[!] Failed to load ratings: {e}", fg="red")
