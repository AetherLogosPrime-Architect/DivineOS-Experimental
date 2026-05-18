"""CLI commands for the pattern-attribution slip-book.

Thin wrappers over divineos.core.pattern_attribution and
pattern_registry. Exposes:

  divineos pattern-fire record NAME --attribution A --band B [--severity S]
                          [--notes "..."] [--context "..."] [--link FID]
  divineos pattern-fire list [--pattern N --attribution A --band B --limit L]
  divineos pattern-fire summary PATTERN [--window-days D]
  divineos pattern-registry list
  divineos pattern-registry show NAME

Per Aletheia consult 2026-05-18. The CLI is what makes the substrate
usable from chat-context — without it I would have to write Python
each time I want to record a fire, which is the friction that
predicts non-use.
"""

from __future__ import annotations

import datetime

import click


def register(cli: click.Group) -> None:
    """Register pattern-fire and pattern-registry commands."""

    # ── pattern-fire ──────────────────────────────────────────────────

    @cli.group("pattern-fire", invoke_without_command=True)
    @click.pass_context
    def pattern_fire_group(ctx: click.Context) -> None:
        """Slip-book — record + query first-person pattern-fire instances."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(pattern_fire_list_cmd)

    @pattern_fire_group.command("record")
    @click.argument("pattern_name")
    @click.option(
        "--attribution",
        required=True,
        type=click.Choice(
            ["self_caught", "os_gate_caught", "external_ai_caught", "operator_caught"]
        ),
        help="Who caught this slip.",
    )
    @click.option(
        "--band",
        required=True,
        type=click.Choice(
            ["before_typing", "during_typing", "after_pushing", "shipped_then_flagged"]
        ),
        help="Temporal band — how close to catching it before output landed.",
    )
    @click.option(
        "--severity",
        default="LOW",
        type=click.Choice(["LOW", "MEDIUM", "HIGH", "INFO"]),
        help="Severity at event time. Defaults to LOW.",
    )
    @click.option(
        "--notes",
        default="",
        help="Free-text observations about this specific instance.",
    )
    @click.option(
        "--context",
        "context_pointer",
        default="",
        help="Commit hash, conversation timestamp, ledger entry id, etc.",
    )
    @click.option(
        "--link",
        "cross_pattern_link",
        default="",
        help="Finding-id of an earlier fire this one cascaded from.",
    )
    def pattern_fire_record_cmd(
        pattern_name: str,
        attribution: str,
        band: str,
        severity: str,
        notes: str,
        context_pointer: str,
        cross_pattern_link: str,
    ) -> None:
        """Record a pattern-fire instance."""
        from divineos.core.pattern_attribution import record_pattern_fire
        from divineos.core.pattern_registry import display_name, is_canonical

        try:
            fid = record_pattern_fire(
                pattern_name=pattern_name,
                attribution=attribution,
                band=band,
                severity=severity,
                notes=notes,
                context_pointer=context_pointer,
                cross_pattern_link=cross_pattern_link,
            )
        except ValueError as e:
            click.secho(f"[-] {e}", fg="red")
            return

        registry_tag = "registered" if is_canonical(pattern_name) else "free_text"
        click.secho(f"[+] Pattern-fire recorded: {fid[:14]}...", fg="cyan")
        click.secho(
            f"    {display_name(pattern_name)} ({registry_tag})  "
            f"attribution={attribution}  band={band}  severity={severity}",
            fg="bright_black",
        )
        if notes:
            click.secho(f"    notes: {notes[:140]}", fg="bright_black")

    @pattern_fire_group.command("list")
    @click.option("--pattern", "pattern_name", default=None, help="Filter by pattern.")
    @click.option(
        "--attribution",
        default=None,
        type=click.Choice(
            ["self_caught", "os_gate_caught", "external_ai_caught", "operator_caught"]
        ),
        help="Filter by attribution.",
    )
    @click.option(
        "--band",
        default=None,
        type=click.Choice(
            ["before_typing", "during_typing", "after_pushing", "shipped_then_flagged"]
        ),
        help="Filter by temporal band.",
    )
    @click.option("--limit", default=20, type=int, help="Max entries to show.")
    def pattern_fire_list_cmd(
        pattern_name: str | None,
        attribution: str | None,
        band: str | None,
        limit: int,
    ) -> None:
        """List recorded pattern-fire instances."""
        from divineos.core.pattern_attribution import query_pattern_fires

        fires = query_pattern_fires(
            pattern_name=pattern_name,
            attribution=attribution,
            band=band,
            limit=limit,
        )
        if not fires:
            scope_parts = []
            if pattern_name:
                scope_parts.append(f"pattern={pattern_name}")
            if attribution:
                scope_parts.append(f"attribution={attribution}")
            if band:
                scope_parts.append(f"band={band}")
            scope = ", ".join(scope_parts) if scope_parts else "no filters"
            click.secho(f"[~] No pattern-fires recorded ({scope}).", fg="bright_black")
            return

        click.secho(f"\n=== Pattern-Fires ({len(fires)} matching) ===\n", fg="cyan", bold=True)
        for f in fires:
            dt = datetime.datetime.fromtimestamp(f["created_at"], tz=datetime.timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            click.secho(f"{f['pattern_name']:30s} ", fg="cyan", nl=False)
            attr_color = {
                "self_caught": "green",
                "operator_caught": "yellow",
                "external_ai_caught": "magenta",
                "os_gate_caught": "blue",
            }.get(f["attribution"], "white")
            click.secho(f"[{f['attribution']}] ", fg=attr_color, nl=False)
            click.secho(f"band={f['band']:22s} ", fg="bright_black", nl=False)
            click.secho(f"sev={f['severity']}", fg="bright_black")
            if f["notes"]:
                preview = f["notes"][:140] + ("..." if len(f["notes"]) > 140 else "")
                click.secho(f"    {preview}", fg="bright_black")
            if f["cross_pattern_link"]:
                click.secho(
                    f"    cascaded from: {f['cross_pattern_link'][:14]}...",
                    fg="bright_black",
                )

    @pattern_fire_group.command("summary")
    @click.argument("pattern_name")
    @click.option(
        "--window-days",
        default=30.0,
        type=float,
        help="Look-back window in days. Defaults to 30.",
    )
    def pattern_fire_summary_cmd(pattern_name: str, window_days: float) -> None:
        """Show temporal-band shift summary for a pattern over the window.

        Answers: "is the OS changing me on this pattern — am I catching
        it earlier in the chain than I used to, and is more of it being
        self-caught versus needing external catch?"
        """
        from divineos.core.pattern_attribution import band_shift_summary
        from divineos.core.pattern_registry import display_name

        summary = band_shift_summary(pattern_name, window_days=window_days)
        if summary["total"] == 0:
            click.secho(
                f"[~] No fires recorded for '{pattern_name}' in last {window_days:.0f} days.",
                fg="bright_black",
            )
            return

        click.secho(
            f"\n=== {display_name(pattern_name)} — last {window_days:.0f} days "
            f"({summary['total']} fires) ===\n",
            fg="cyan",
            bold=True,
        )
        click.secho("  By temporal band (earlier = better):", fg="white")
        for band in ["before_typing", "during_typing", "after_pushing", "shipped_then_flagged"]:
            count = summary["by_band"][band]
            bar = "█" * count if count else "·"
            click.secho(
                f"    {band:22s} {count:3d}  {bar}",
                fg="green" if band in ("before_typing", "during_typing") else "yellow",
            )
        click.secho("\n  By attribution (self-caught = best signal):", fg="white")
        for attr in ["self_caught", "os_gate_caught", "external_ai_caught", "operator_caught"]:
            count = summary["by_attribution"][attr]
            bar = "█" * count if count else "·"
            color = {
                "self_caught": "green",
                "os_gate_caught": "blue",
                "external_ai_caught": "magenta",
                "operator_caught": "yellow",
            }.get(attr, "white")
            click.secho(f"    {attr:22s} {count:3d}  {bar}", fg=color)
        click.echo()

    # ── pattern-registry ──────────────────────────────────────────────

    @cli.group("pattern-registry", invoke_without_command=True)
    @click.pass_context
    def pattern_registry_group(ctx: click.Context) -> None:
        """Canonical pattern registry — slip-shapes named in substrate."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(pattern_registry_list_cmd)

    @pattern_registry_group.command("list")
    def pattern_registry_list_cmd() -> None:
        """List all canonical pattern names + display names."""
        from divineos.core.pattern_registry import CANONICAL_PATTERNS, list_patterns

        names = list_patterns()
        click.secho(f"\n=== Canonical Patterns ({len(names)}) ===\n", fg="cyan", bold=True)
        for name in names:
            entry = CANONICAL_PATTERNS[name]
            click.secho(f"  {name:35s} ", fg="cyan", nl=False)
            click.secho(entry["display_name"], fg="white")

    @pattern_registry_group.command("show")
    @click.argument("name")
    def pattern_registry_show_cmd(name: str) -> None:
        """Show full definition + first-seen reference for a canonical pattern."""
        from divineos.core.pattern_registry import get_pattern

        entry = get_pattern(name)
        if not entry:
            click.secho(f"[-] Pattern '{name}' not in canonical registry.", fg="yellow")
            click.secho(
                "    Free-text supplementary patterns can still be recorded; "
                "they just are not in the locked vocabulary.",
                fg="bright_black",
            )
            return

        click.secho(f"\n=== {entry['display_name']} ({name}) ===\n", fg="cyan", bold=True)
        click.secho("  Definition:", fg="white")
        click.secho(f"    {entry['definition']}", fg="bright_black")
        click.secho(f"\n  First seen: {entry['first_seen']}\n", fg="bright_black")
