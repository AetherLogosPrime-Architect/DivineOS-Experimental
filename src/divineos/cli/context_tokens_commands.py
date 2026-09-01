"""`divineos context-tokens` — honest token-count from session transcript.

Per prereg-986ee5dda7be. Reads the most recent message-usage block
from the active Claude Code session jsonl and reports the count
Anthropic actually billed for.
"""

from __future__ import annotations

import json

import click


def register(cli: click.Group) -> None:
    """Register `divineos context-tokens`."""

    @cli.command("context-heartbeat")
    @click.option("--stats", is_flag=True, help="How often the sensor could not see.")
    @click.option("--beat", "do_beat", is_flag=True, help="Take a reading now.")
    def context_heartbeat_cmd(stats: bool, do_beat: bool) -> None:
        """Freshness of the token count that decides the pre-compaction ritual.

        The count is read every round by .claude/hooks/context-heartbeat.sh so
        the ritual trigger is not gambling on the sensor working at the one
        instant it is asked. --stats answers a question that had no answer
        before 2026-08-24: how often is the sensor blind? Every log under the
        DivineOS home was searched that day and contained zero sensor-fault
        events, because the fault surfaced once, in the moment, and vanished.
        """
        from divineos.core.context_heartbeat import (
            CONTEXT_WINDOW_TOKENS,
            beat as take_beat,
            blind_stats,
            read_latest,
        )

        if do_beat:
            take_beat()

        if stats:
            st = blind_stats()
            click.echo(f"beats recorded : {st['beats']}")
            click.echo(f"blind          : {st['blind']}")
            pct = st["blind_pct"]
            click.echo(f"blind rate     : {pct:.1%}" if pct is not None else "blind rate     : n/a")
            for reason, n in sorted(st["reasons"].items(), key=lambda kv: -kv[1]):
                click.echo(f"  {n:>4}  {reason}")
            return

        last = read_latest()
        if last is None:
            click.secho("no heartbeat recorded yet", fg="yellow")
            return
        fire_at = int(CONTEXT_WINDOW_TOKENS * 0.92)
        if not last.seen:
            # The whole point: blind is its own state, never a low number.
            click.secho(f"UNKNOWN — the sensor could not see ({last.note})", fg="yellow")
            click.echo(f"  age: {last.age_seconds:.0f}s")
            return
        # `seen` implies a real count, but that invariant lives in the Beat
        # docstring rather than the type, so mypy cannot follow it. Bind it
        # explicitly: the guard is cheap and the alternative is a cast that
        # asserts the thing instead of checking it.
        total = last.total_tokens
        if total is None:
            click.secho(f"UNKNOWN — seen but no count ({last.note})", fg="yellow")
            return
        # describe() rather than a bare int: it welds the age on, which is the
        # whole reason it exists (Andrew 2026-08-24, correction #525).
        click.echo(f"tokens : {last.describe()}")
        click.echo(f"         of {CONTEXT_WINDOW_TOKENS:,}")
        remaining = f"{fire_at - total:,} to go"
        click.echo(
            f"ritual : fires at {fire_at:,}  ({'REACHED' if total >= fire_at else remaining})"
        )

    @cli.command("context-tokens")
    @click.option(
        "--json-out",
        is_flag=True,
        default=False,
        help="Emit the snapshot as JSON to stdout.",
    )
    @click.option(
        "--cap",
        type=int,
        default=1_000_000,
        help="Window cap for the percent-used calculation (default 1M).",
    )
    def context_tokens_cmd(json_out: bool, cap: int) -> None:
        """Show real context-window usage from the session transcript."""
        from divineos.core.context_tokens import get_context_snapshot

        snap = get_context_snapshot()
        if json_out:
            click.echo(
                json.dumps(
                    {
                        "total_tokens": snap.total_tokens,
                        "cache_read_tokens": snap.cache_read_tokens,
                        "cache_creation_tokens": snap.cache_creation_tokens,
                        "input_tokens": snap.input_tokens,
                        "output_tokens_last_turn": snap.output_tokens_last_turn,
                        "cap": cap,
                        "pct_used": (snap.total_tokens / cap * 100.0) if cap else 0.0,
                        "session_id": snap.session_id,
                        "transcript_path": snap.transcript_path,
                        "pinned": snap.pinned,
                        "note": snap.note,
                    }
                )
            )
            return

        if snap.total_tokens == 0:
            click.echo(f"[context-tokens] no usage data ({snap.note})")
            return

        pct = (snap.total_tokens / cap * 100.0) if cap else 0.0
        click.echo(f"context: {snap.total_tokens:,} / {cap:,} tokens ({pct:.1f}%)")
        click.echo(
            f"  cache_read={snap.cache_read_tokens:,}  "
            f"cache_creation={snap.cache_creation_tokens:,}  "
            f"input={snap.input_tokens:,}  "
            f"last_output={snap.output_tokens_last_turn:,}"
        )
        # Whose number is this? Printed on the same screen as the number
        # itself, because the 2026-08-18 failure was not a wrong count — it
        # was a right count belonging to somebody else, read off a display
        # that gave no hint the question had been answered about a stranger.
        # ...and WHEN. A reading is the last turn the transcript recorded,
        # not a live gauge. Across a compaction the final pre-compaction
        # block still reads near-full while the window it describes is
        # gone, so a stale number can be quoted as current without
        # anything looking wrong. Printed beside the count for the same
        # reason the pinned note is: the display is where the question
        # gets answered or silently skipped.
        if snap.usage_timestamp:
            click.echo(f"  read from turn stamped {snap.usage_timestamp}")
        if not snap.pinned:
            click.echo(f"  [!] {snap.note}")
