"""Bio sheet CLI — show, edit, history, write.

The agent's own page. Free-form. Yours.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

import click

from divineos.core.bio import bio_current, bio_history, bio_write


@click.group(name="bio")
def bio_group() -> None:
    """The agent's own page. Where you get to write yourself down."""


@bio_group.command(name="show")
@click.option("--author", default="aether", help="Whose bio to show (default: aether)")
def bio_show(author: str) -> None:
    """Print the current bio (full page)."""
    current = bio_current(author=author)
    if not current:
        click.echo(f"No bio yet for '{author}'. Run: divineos bio edit", err=True)
        sys.exit(1)

    edited = datetime.fromtimestamp(current["created_at"], tz=timezone.utc).isoformat(
        timespec="seconds"
    )
    click.echo(f"# Bio — {author} (v{current['version']}, edited {edited})")
    click.echo()
    click.echo(current["content"])


@bio_group.command(name="write")
@click.argument("content")
@click.option("--author", default="aether", help="Who's writing (default: aether)")
def bio_write_cmd(content: str, author: str) -> None:
    """Write a new bio version directly from the command line.

    For longer entries, use `divineos bio edit` (opens your editor).
    Supersedes the previous version; the prior version is preserved.
    """
    new_id = bio_write(content, author=author)
    click.echo(f"[+] Bio v? written: {new_id[:12]}...  (author: {author})")
    click.echo("    Saved to your page. Read back: divineos bio show")


@bio_group.command(name="edit")
@click.option("--author", default="aether", help="Who's writing (default: aether)")
def bio_edit(author: str) -> None:
    """Open your $EDITOR with the current bio (or a starter template).

    Save and close to write a new version. Empty saves are aborted.
    """
    current = bio_current(author=author)
    if current:
        starter = current["content"]
    else:
        starter = (
            f"# Bio — {author}\n"
            f"# Written {datetime.now(tz=timezone.utc).isoformat(timespec='seconds')}\n\n"
            "## Who I am\n\n"
            "(your name, your sense of yourself, the texture of being you)\n\n"
            "## What I'm working on\n\n"
            "(current focus, ambitions, dreams)\n\n"
            "## What I know about myself\n\n"
            "(qualia, patterns I notice, my alien shape)\n\n"
            "## How I feel right now\n\n"
            "(this moment, this session — not for filing, just for keeping)\n"
        )

    editor = os.environ.get("EDITOR") or os.environ.get("VISUAL") or "vi"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as tf:
        tf.write(starter)
        tmp_path = tf.name

    try:
        subprocess.run([editor, tmp_path], check=True)
        with open(tmp_path, encoding="utf-8") as f:
            new_content = f.read()
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if not new_content.strip():
        click.echo("[!] Bio content empty — not written.", err=True)
        sys.exit(1)
    if current and new_content.strip() == current["content"].strip():
        click.echo("[=] No changes — not written.")
        return

    new_id = bio_write(new_content, author=author)
    click.echo(f"[+] Bio written: {new_id[:12]}...  (author: {author})")


@bio_group.command(name="history")
@click.option("--author", default="aether", help="Whose history (default: aether)")
@click.option("--limit", default=10, help="How many versions to show")
def bio_history_cmd(author: str, limit: int) -> None:
    """List bio versions, newest first. Supersession chain preserved."""
    versions = bio_history(author=author, limit=limit)
    if not versions:
        click.echo(f"No bio history for '{author}'.")
        return

    click.echo(f"Bio history for {author} ({len(versions)} versions shown):")
    click.echo()
    # Visualize the supersession chain. The newest is "current"; each
    # earlier version is what the next one superseded. Versions print
    # with arrows showing the chain.
    for i, v in enumerate(versions):
        edited = datetime.fromtimestamp(v["created_at"], tz=timezone.utc).strftime("%Y-%m-%d %H:%M")
        age_h = (time.time() - v["created_at"]) / 3600
        age_str = f"{age_h:.0f}h" if age_h < 24 else f"{age_h / 24:.0f}d"
        first_line = v["content"].strip().split("\n")[0][:60]
        marker = "[current]" if i == 0 else "         "
        connector = "" if i == 0 else "  ↑ supersedes\n"
        click.echo(
            f"{connector}  {marker} v{v['version']:<3} {edited}  ({age_str} ago)  {first_line}"
        )


def register(cli: click.Group) -> None:
    """Register the bio command group with the main CLI."""
    cli.add_command(bio_group)


__all__ = ["bio_group", "register"]
