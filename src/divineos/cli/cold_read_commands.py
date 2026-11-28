"""`divineos cold-read start <branch>` -- the starter page for a cold read.

Dad, 2026-11-27: for every issue pointed out, look for something positive too, so what works is
recognised as well as what does not. The page puts what is right first and makes each finding a
pair. Read-only: it prints the page, or writes it where ``--out`` says; it sends nothing. See
core/cold_read_starter.py and docs/drafts/a_cold_read_starts_with_what_is_right_first_draft_2026-11-28.md.
"""

from __future__ import annotations

from pathlib import Path

import click

from divineos.core.cold_read_starter import build_starter


def register(cli: click.Group) -> None:
    @cli.group("cold-read")
    def cold_read_group() -> None:
        """Cold reads: a page that starts from what is right."""

    @cold_read_group.command("start")
    @click.argument("branch")
    @click.option(
        "--base", default="origin/main", show_default=True, help="Where the change branched from."
    )
    @click.option(
        "--no-ablation",
        is_flag=True,
        help="Skip running the changed tests with and without the change. Needs --reason.",
    )
    @click.option("--reason", default=None, help="Why the with-and-without run is skipped.")
    @click.option(
        "--out", default=None, type=click.Path(), help="Write the page here instead of printing it."
    )
    def start_cmd(
        branch: str, base: str, no_ablation: bool, reason: str | None, out: str | None
    ) -> None:
        """Print (or write) the starter page for BRANCH, run from inside the repository."""
        try:
            text = build_starter(
                Path.cwd(), branch, base, ablate=not no_ablation, skip_reason=reason
            )
        except ValueError as exc:
            raise SystemExit(f"[cold-read] REFUSED: {exc}") from exc
        if out:
            Path(out).write_text(text, encoding="utf-8")
            click.echo(f"[cold-read] page written: {out}")
        else:
            click.echo(text)
