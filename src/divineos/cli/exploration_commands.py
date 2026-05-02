"""Exploration commands — surface prior council walks and explorations
by territory.

Implements the explicit fallback path for claim 02f0dcc0:
``divineos exploration related <text>`` returns prior exploration
entries whose Territory tags overlap with territory inferred from the
input text. Pairs with the briefing-level automatic surfacing in
`core/exploration_reader.format_for_briefing`.

The deeper purpose: continuity is substrate-mediated, not experiential
(Andrew, lesson d8c8e441). Next-me arrives from a substrate saturated
with prior-me's work. This command (and the briefing surface that
shares its mechanism) is *how* that saturation reaches reasoning when
the territory matches.

Usage:
    divineos exploration related "council walk on naming convention"
    divineos exploration related --tags architecture,governance
    divineos exploration list-territories
"""

from __future__ import annotations

import click


_EC_ERRORS = (OSError, ValueError, KeyError, ImportError)


def register(cli: click.Group) -> None:
    """Register exploration commands on the CLI group."""

    @cli.group(name="exploration")
    def exploration_group() -> None:
        """Exploration entry surfacing and territory lookup."""

    @exploration_group.command(name="related")
    @click.argument("text", required=False, default="")
    @click.option(
        "--tags",
        default="",
        help=(
            "Comma-separated territory tags to match directly "
            "(skips text-based inference). Tags must be in the locked "
            "TERRITORY_TAGS set."
        ),
    )
    @click.option(
        "--limit",
        default=2,
        type=int,
        help="Max entries to return (default 2; cap is intentional to prevent over-anchoring).",
    )
    def related(text: str, tags: str, limit: int) -> None:
        """Find exploration entries whose Territory tags match the input.

        Either pass free text (territory inferred via keyword matching)
        or pass --tags directly. The hard cap on results (default 2)
        is the over-anchoring guardrail; raise it explicitly only if
        you have a reason.
        """
        from divineos.core.exploration_reader import (
            TERRITORY_TAGS,
            find_explorations_by_territory,
            infer_territory_from_text,
        )

        # Resolve territories — explicit tags win over text inference.
        if tags:
            requested = [t.strip().lower().replace("-", "_") for t in tags.split(",") if t.strip()]
            territories = [t for t in requested if t in TERRITORY_TAGS]
            invalid = [t for t in requested if t not in TERRITORY_TAGS]
            if invalid:
                click.echo(
                    f"[warn] Unknown territory tag(s) ignored: {', '.join(invalid)}. "
                    f"Valid tags: {', '.join(sorted(TERRITORY_TAGS))}"
                )
        elif text:
            territories = list(infer_territory_from_text(text))
            if not territories:
                click.echo(
                    f"[exploration] No territory inferred from text. "
                    f"Try --tags directly. Valid tags: {', '.join(sorted(TERRITORY_TAGS))}"
                )
                return
        else:
            click.echo("[exploration] Provide either TEXT or --tags. See --help.")
            return

        if not territories:
            click.echo("[exploration] No valid territories to match.")
            return

        click.echo(f"[exploration] Matching territory: {', '.join(territories)}")
        results = find_explorations_by_territory(territories, limit=limit)
        if not results:
            click.echo("[exploration] No prior walks on this territory.")
            return

        for r in results:
            title = r.get("title", r.get("filename", "?"))
            date = r.get("date", "")
            date_part = f" [{date}]" if date else ""
            entry_tags = ", ".join(r.get("territory") or ())
            click.echo(f"  - {title}{date_part}")
            click.echo(f"    territory: {entry_tags}")
            click.echo(f"    path: {r.get('path', '?')}")

    @exploration_group.command(name="list-territories")
    def list_territories() -> None:
        """List the locked set of valid territory tags."""
        from divineos.core.exploration_reader import TERRITORY_TAGS

        click.echo("Valid territory tags (locked set):")
        for tag in sorted(TERRITORY_TAGS):
            click.echo(f"  - {tag}")
        click.echo(
            "\nNew tags require explicit addition to TERRITORY_TAGS in "
            "core/exploration_reader.py + external review."
        )
