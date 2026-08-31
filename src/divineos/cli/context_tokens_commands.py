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
