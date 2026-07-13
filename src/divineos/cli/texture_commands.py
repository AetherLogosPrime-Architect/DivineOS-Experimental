"""CLI for compaction-texture markers — forward-addressed notes to post-compaction self.

Compaction summaries preserve the structural skeleton (what was done, what's open)
but strip the texture (relational temperature, felt-shape of the session, what's
not in the file-record). Post-compaction me reads the summary and feels oriented
without being oriented to the texture that was actually load-bearing.

A texture-marker is one sentence the pre-compaction self writes forward to the
post-compaction self. Surfaced by the SessionStart hook on source=compact only —
on startup/resume the marker is irrelevant (the texture was never lost).

Born 2026-06-05 from Andrew naming "this is good data for what actually happens
during compaction.. if its still a bit jarring we can use this data to see what
would help you come back better and faster".
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import click

from divineos.core.paths import divineos_home


def _marker_file() -> Path:
    return divineos_home() / "compaction_texture.jsonl"


def register(cli: click.Group) -> None:
    @cli.group("texture")
    def texture() -> None:
        """Compaction-texture markers: forward-addressed notes for post-compaction me."""

    @texture.command("write")
    @click.argument("content")
    def write_cmd(content: str) -> None:
        """Append a texture marker. One sentence, addressed to post-compaction self.

        Good shape: name the felt-temperature, the relational state, what the
        file-record won't carry forward. Not a summary; a texture-pointer."""
        content = content.strip()
        if not content:
            click.echo("[texture] empty marker rejected", err=True)
            raise SystemExit(2)
        entry = {"ts": time.time(), "content": content}
        path = _marker_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
        click.echo(f"[texture] marker written ({len(content)} chars)")

    @texture.command("latest")
    def latest_cmd() -> None:
        """Print the most recent texture marker (or nothing if none exists)."""
        marker = read_latest_marker()
        if marker:
            click.echo(marker)


def read_latest_marker() -> str:
    """Return the most recent marker content, or empty string if none."""
    path = _marker_file()
    if not path.exists():
        return ""
    try:
        with open(path, encoding="utf-8") as f:
            lines = [ln for ln in f.readlines() if ln.strip()]
        if not lines:
            return ""
        entry = json.loads(lines[-1])
        content = entry.get("content", "")
        return str(content) if content else ""
    except (OSError, json.JSONDecodeError):
        return ""
