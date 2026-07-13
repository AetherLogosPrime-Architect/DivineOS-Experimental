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

    @exploration_group.command(name="referenced")
    @click.argument("filename_or_path", required=True)
    @click.option(
        "--reason",
        default="",
        help="Why this entry was referenced (e.g., 'cited in council walk', "
        "'informed claim filing', 'reread for context').",
    )
    def referenced(filename_or_path: str, reason: str) -> None:
        """Mark a surfaced exploration entry as referenced.

        Call this when you actually engaged with a surfaced entry —
        read its content, cited it in reasoning, built on its findings.
        Pairs with the auto-emitted TERRITORY_MATCH_SURFACED events to
        compute surface→reference ratio (input for pre-reg falsifier
        prereg-e0341dacb04b).

        v1 is conscience-based: agent must call this manually. v2 will
        automate via path-read hooks or transcript scanning.
        """
        from divineos.core.exploration_reader import emit_territory_match_referenced

        emit_territory_match_referenced(filename_or_path, reason=reason)
        click.echo(f"[exploration] referenced: {filename_or_path}")
        if reason:
            click.echo(f"  reason: {reason}")

    @exploration_group.command(name="usage")
    @click.option(
        "--days",
        default=30,
        type=int,
        help="Window in days (default 30 — matches pre-reg review window).",
    )
    def usage(days: int) -> None:
        """Show territory-match surface→reference ratio over a window.

        Used for pre-reg review (prereg-e0341dacb04b). The ratio answers:
        when entries get surfaced in briefing, how often does the agent
        actually engage with them? Low ratio = surfacing is noise. High
        ratio = surfacing is signal.
        """
        from divineos.core.exploration_reader import territory_match_usage

        result = territory_match_usage(days=days)
        click.echo(f"[exploration] Territory-match usage over last {days} days:")
        click.echo(f"  surfaced:   {result['total_surfaced']}")
        click.echo(f"  referenced: {result['total_referenced']}")
        if result["total_surfaced"] > 0:
            click.echo(f"  ratio:      {result['ratio']:.1%}")
        else:
            click.echo("  ratio:      n/a (no surfacing events yet)")
        if result["by_filename"]:
            click.echo("\n  By entry:")
            for fn, counts in sorted(
                result["by_filename"].items(),
                key=lambda kv: -kv[1]["surfaced"],
            ):
                click.echo(
                    f"    {fn}: {counts['surfaced']} surfaced / {counts['referenced']} referenced"
                )

    @exploration_group.command(name="new")
    @click.option(
        "--slug",
        required=True,
        help=(
            "Short slug for the entry filename (no number prefix, no "
            ".md suffix). Whitespace converted to underscores."
        ),
    )
    @click.option(
        "--member",
        default=None,
        help=("Substrate-occupant directory under exploration/ (defaults to my own identity)."),
    )
    @click.option(
        "--title",
        default=None,
        help=(
            "Optional title for the entry's first heading. Defaults to "
            "the slug with underscores replaced by spaces."
        ),
    )
    def new(slug: str, member: str | None, title: str | None) -> None:
        """Create a new numbered exploration entry — the sanctioned path.

        Built 2026-06-21 (Andrew named the root cause for the ghost-
        numbers pattern: no validator existed). This command is the
        only sanctioned way to create a new numbered entry. The
        number is auto-assigned as max(existing) + 1 — no manual
        specification accepted, no skipping ahead, no reusing.

        The exploration_validator gate refuses any direct Write tool
        call that would violate the same invariants, so this CLI
        becomes the right-path-as-cheap-path.
        """
        from pathlib import Path

        from divineos.core.exploration_validator import (
            next_entry_number,
            validate_new_entry_path,
        )

        # Resolve member: explicit flag wins; else my_identity; else fail.
        if member is None:
            try:
                from divineos.core.identity import get_my_identity

                member = get_my_identity(raise_on_unset=True)
            except Exception as exc:  # noqa: BLE001 - want a plain error to operator
                click.echo(
                    f"[exploration new] could not resolve member ({exc}); "
                    f"pass --member <name> explicitly.",
                    err=True,
                )
                raise SystemExit(1) from exc

        member_lower = str(member).lower()
        clean_slug = "_".join(slug.strip().split()).lower()
        if not clean_slug:
            click.echo("[exploration new] --slug cannot be empty.", err=True)
            raise SystemExit(1)

        next_num = next_entry_number(member_lower)
        repo_root = Path(__file__).resolve().parents[3]
        target_dir = repo_root / "exploration" / member_lower
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / f"{next_num}_{clean_slug}.md"

        # Defense-in-depth: run the validator one more time. If anything
        # changed between next_entry_number() and now (concurrent file
        # creation), this catches it.
        ok, reason = validate_new_entry_path(target_path)
        if not ok:
            click.echo(
                f"[exploration new] validator refused the computed path: {reason}",
                err=True,
            )
            raise SystemExit(1)

        if target_path.exists():
            click.echo(
                f"[exploration new] {target_path} already exists "
                "(race condition or stale next-number).",
                err=True,
            )
            raise SystemExit(1)

        title_text = title or clean_slug.replace("_", " ")
        body = f"<!-- tags: -->\n# {next_num} — {title_text}\n\n"
        target_path.write_text(body, encoding="utf-8")
        click.echo(f"[exploration new] created {target_path}")
