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

        # Clear correction-unlogged marker if present — `correction` is
        # the raw-quote counterpart to `learn` and also discharges the
        # UserPromptSubmit-detected correction.
        try:
            from divineos.core.correction_marker import clear_marker

            clear_marker()
        except Exception:  # noqa: BLE001 — marker clearing is best-effort
            pass

        # Also clear the theater/fabrication marker — naming the pattern
        # via `correction` discharges output-drift markers parallel to
        # how it discharges UserPromptSubmit corrections.
        try:
            from divineos.core.theater_marker import clear_marker as _clear_theater

            _clear_theater()
        except Exception:  # noqa: BLE001 — best-effort
            pass

    @cli.command("corrections")
    @click.option("--limit", default=10, type=int, help="How many to show, newest first.")
    @click.option("--all", "show_all", is_flag=True, help="Show every correction ever logged.")
    @click.option("--open", "open_only", is_flag=True, help="Show only OPEN corrections.")
    @click.option(
        "--resolved", "resolved_only", is_flag=True, help="Show only RESOLVED corrections."
    )
    def corrections_cmd(limit: int, show_all: bool, open_only: bool, resolved_only: bool) -> None:
        """Read past corrections with status -- the user's exact words."""
        from divineos.core.corrections import (
            _age_label,
            corrections_with_status,
            open_corrections,
        )

        if open_only:
            entries = open_corrections()[:limit]
            label = "OPEN"
        elif resolved_only:
            all_enriched = corrections_with_status()
            entries = list(reversed([c for c in all_enriched if c["status"] == "RESOLVED"]))[:limit]
            label = "RESOLVED"
        elif show_all:
            entries = list(reversed(corrections_with_status()))
            label = "ALL"
        else:
            entries = list(reversed(corrections_with_status()))[:limit]
            label = "recent"

        if not entries:
            click.secho("[~] No corrections logged yet.", fg="bright_black")
            click.secho(
                '    When one happens, run: divineos correction "exact words"',
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== Corrections ({len(entries)} {label}, newest first) ===\n",
            fg="cyan",
            bold=True,
        )
        for i, entry in enumerate(entries, 1):
            ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(entry.get("timestamp", 0)))
            status = entry.get("status", "OPEN")
            age = _age_label(entry.get("age_days", 0))
            status_color = {"OPEN": "yellow", "ADDRESSED": "cyan", "RESOLVED": "green"}.get(
                status, "white"
            )
            click.secho(f"  [{i}] [{ts}] ({age}) ", fg="bright_black", nl=False)
            click.secho(status, fg=status_color)
            text = (entry.get("text") or "").strip()
            for ln in text.splitlines() or [text]:
                _safe_echo(f"    {ln}")
            if entry.get("evidence"):
                click.secho(f"    evidence: {entry['evidence']}", fg="bright_black")
            click.echo()

    @cli.command("correction-resolve")
    @click.argument("index", type=int)
    @click.option(
        "--evidence",
        "-e",
        required=True,
        help="What addressed this correction (commit, learn entry, etc).",
    )
    @click.option(
        "--status",
        "resolution_status",
        default="RESOLVED",
        type=click.Choice(["ADDRESSED", "RESOLVED"]),
    )
    def correction_resolve_cmd(index: int, evidence: str, resolution_status: str) -> None:
        """Resolve a correction by index (from 'divineos corrections --open')."""
        from divineos.core.corrections import open_corrections, resolve_correction

        open_c = open_corrections()
        if not open_c:
            click.secho("[~] No open corrections to resolve.", fg="bright_black")
            return
        if index < 1 or index > len(open_c):
            click.secho(
                f"[!] Index {index} out of range. Open corrections: 1-{len(open_c)}", fg="red"
            )
            return

        target = open_c[index - 1]
        resolve_correction(
            correction_timestamp=target["timestamp"],
            status=resolution_status,
            evidence=evidence,
        )
        ts = time.strftime("%Y-%m-%d %H:%M", time.localtime(target.get("timestamp", 0)))
        click.secho(f"[+] Correction [{ts}] marked {resolution_status}.", fg="green")
        click.secho(f"    evidence: {evidence}", fg="bright_black")
