"""CLI surface for the dark-matter sweep.

This file is the point, not a follow-up. `core/dark_matter.py` with tests and
no caller would be an instance of the very pattern it detects — the
WIRING-GAP shape filed 2026-05-11: *"modules built as callable code with
dedicated unit tests ship WITHOUT corresponding wire-up; the modules exist,
nothing invokes them."* Shipping the detector unwired would have been the
joke writing itself.
"""

from __future__ import annotations

from pathlib import Path

import click


def register(cli: click.Group) -> None:
    """Register `divineos dark-matter`."""

    @cli.command("dark-matter")
    @click.option(
        "--check",
        is_flag=True,
        help="Exit 1 if anything is found. For push-readiness and CI.",
    )
    @click.option("--root", default=".", help="Repository root to sweep.")
    def dark_matter_cmd(check: bool, root: str) -> None:
        """Find things that exist but nothing reaches.

        Dead hooks that never fire, and commands prescribed in gate text that
        do not resolve against the real command tree.

        Reports its own blind spots on every run, including clean ones — a
        detector trusted as exhaustive is worse than no detector at all.
        """
        from divineos.core.dark_matter import format_report, sweep

        findings = sweep(Path(root))
        click.echo(format_report(findings))
        if check and findings:
            raise click.exceptions.Exit(1)
