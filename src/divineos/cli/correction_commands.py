"""Correction CLI — capture the user's exact words, raw, in the moment.

Purpose: when a correction lands, log it before any framing engages. No
category dropdown, no severity, no 'why'. Just the words and the time.

Bypass-listed in the briefing gate so it works without ceremony — the
whole point is to grab the moment as it happens, not after I've prepared
to reflect on it.
"""

from __future__ import annotations

import time

import click

from divineos.cli._helpers import _safe_echo


def register(cli: click.Group) -> None:
    """Register correction commands on the CLI group."""

    @cli.command("correction")
    @click.argument("text")
    def correction_cmd(text: str) -> None:
        """Log a correction verbatim — no framing, no interpretation."""
        from divineos.core.corrections import log_correction
        from divineos.core.session_manager import get_current_session_id

        try:
            session_id = get_current_session_id() or ""
        except Exception:  # noqa: BLE001 — session_id is optional metadata
            session_id = ""

        entry = log_correction(text, session_id=session_id)
        click.secho("[+] Correction logged.", fg="green")
        click.secho(
            f"    {time.strftime('%H:%M:%S', time.localtime(entry['timestamp']))}",
            fg="bright_black",
        )
        click.secho(
            "    Read it raw later. Don't reframe it now.",
            fg="bright_black",
        )

    @cli.command("corrections")
    @click.option("--limit", default=10, type=int, help="How many to show, newest first.")
    @click.option("--all", "show_all", is_flag=True, help="Show every correction ever logged.")
    def corrections_cmd(limit: int, show_all: bool) -> None:
        """Read past corrections — the user's exact words, in time order."""
        from divineos.core.corrections import load_corrections, recent_corrections

        if show_all:
            entries = load_corrections()
            entries = list(reversed(entries))
        else:
            entries = recent_corrections(limit=limit)

        if not entries:
            click.secho("[~] No corrections logged yet.", fg="bright_black")
            click.secho(
                '    When one happens, run: divineos correction "exact words"',
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Corrections ({len(entries)} shown, newest first) ===\n",
            fg="cyan",
            bold=True,
        )
        for entry in entries:
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("timestamp", 0)))
            click.secho(f"  [{ts}]", fg="bright_black")
            text = (entry.get("text") or "").strip()
            for ln in text.splitlines() or [text]:
                _safe_echo(f"    {ln}")
            click.echo()
