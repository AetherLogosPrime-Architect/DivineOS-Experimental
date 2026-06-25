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
