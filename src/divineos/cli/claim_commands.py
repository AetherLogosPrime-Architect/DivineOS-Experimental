"""Claims engine and affect log CLI commands."""

import datetime

import click

from divineos.cli._helpers import _safe_echo
from divineos.core.claim_store import TIER_LABELS

_STATUS_COLORS = {
    "OPEN": "white",
    "INVESTIGATING": "cyan",
    "SUPPORTED": "green",
    "CONTESTED": "yellow",
    "REFUTED": "red",
}


def register(cli: click.Group) -> None:
    """Register claims and affect commands."""

    # ── Claims ────────────────────────────────────────────────────────

    @cli.command("claim")
    @click.argument("statement")
    @click.option(
        "--tier", type=click.IntRange(1, 5), default=4, help="1=empirical to 5=metaphysical"
    )
    @click.option("--context", default="", help="What prompted this investigation")
    @click.option("--promotes", "promotion", default="", help="What evidence would promote this")
    @click.option("--demotes", "demotion", default="", help="What evidence would demote this")
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    def claim_cmd(
        statement: str,
        tier: int,
        context: str,
        promotion: str,
        demotion: str,
        tags: tuple[str, ...],
    ) -> None:
        """File a claim for investigation."""
        from divineos.core.claim_store import file_claim

        claim_id = file_claim(
            statement=statement,
            tier=tier,
            context=context,
            promotion_criteria=promotion,
            demotion_criteria=demotion,
            tags=list(tags) if tags else None,
        )
        label = TIER_LABELS.get(tier, "unknown")
        click.secho(f"[+] Claim filed ({label}): {claim_id[:8]}...", fg="cyan")

    @cli.group("claims", invoke_without_command=True)
    @click.pass_context
    def claims_group(ctx: click.Context) -> None:
        """Investigate claims - test everything, dismiss nothing."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(claims_list_cmd)

    @claims_group.command("list")
    @click.option("--limit", default=20, type=int)
    @click.option("--tier", type=click.IntRange(1, 5), default=None, help="Filter by tier")
    @click.option("--status", default=None, help="Filter by status")
    def claims_list_cmd(limit: int, tier: int | None, status: str | None) -> None:
        """Browse claims under investigation."""
        from divineos.core.claim_store import list_claims

        entries = list_claims(limit=limit, tier=tier, status=status)
        if not entries:
            click.secho("[~] No claims filed yet.", fg="bright_black")
            return

        click.secho(f"\n=== Claims ({len(entries)}) ===\n", fg="cyan", bold=True)
        for entry in entries:
            _display_claim(entry)

    @claims_group.command("show")
    @click.argument("claim_id")
    def claims_show_cmd(claim_id: str) -> None:
        """Show full claim with all evidence."""
        from divineos.core.claim_store import get_claim

        claim = get_claim(claim_id)
        if not claim:
            click.secho(f"[-] Claim {claim_id} not found.", fg="red")
            return
        _display_claim(claim, verbose=True)
        if claim.get("evidence"):
            click.secho("  Evidence:", fg="white", bold=True)
            for ev in claim["evidence"]:
                dir_color = {"SUPPORTS": "green", "CONTRADICTS": "red", "NEUTRAL": "bright_black"}
                click.secho(
                    f"    [{ev['direction']}] ",
                    fg=dir_color.get(ev["direction"], "white"),
                    nl=False,
                )
                click.secho(
                    f"({ev['source']}, strength {ev['strength']:.1f}) ", fg="bright_black", nl=False
                )
                _safe_echo(ev["content"])

    @claims_group.command("evidence")
    @click.argument("claim_id")
    @click.argument("content")
    @click.option(
        "--direction",
        type=click.Choice(["SUPPORTS", "CONTRADICTS", "NEUTRAL"]),
        default="NEUTRAL",
    )
    @click.option(
        "--source",
        type=click.Choice(["empirical", "theoretical", "inferential", "experiential", "resonance"]),
        default="experiential",
    )
    @click.option("--strength", type=click.FloatRange(0.0, 1.0), default=0.5)
    def claims_evidence_cmd(
        claim_id: str,
        content: str,
        direction: str,
        source: str,
        strength: float,
    ) -> None:
        """Add evidence to a claim."""
        from divineos.core.claim_store import add_evidence, get_claim

        claim = get_claim(claim_id)
        if not claim:
            click.secho(f"[-] Claim {claim_id} not found.", fg="red")
            return

        eid = add_evidence(
            claim["claim_id"], content, direction=direction, source=source, strength=strength
        )
        dir_color = {"SUPPORTS": "green", "CONTRADICTS": "red", "NEUTRAL": "white"}
        click.secho(
            f"[+] Evidence added ({direction}, {source}): {eid[:8]}...",
            fg=dir_color.get(direction, "white"),
        )

    @claims_group.command("assess")
    @click.argument("claim_id")
    @click.argument("assessment")
    @click.option(
        "--status",
        type=click.Choice(["OPEN", "INVESTIGATING", "SUPPORTED", "CONTESTED", "REFUTED"]),
    )
    @click.option("--tier", type=click.IntRange(1, 5), default=None)
    def claims_assess_cmd(
        claim_id: str,
        assessment: str,
        status: str | None,
        tier: int | None,
    ) -> None:
        """Update a claim's assessment, status, or tier."""
        from divineos.core.claim_store import update_claim

        if update_claim(claim_id, status=status, tier=tier, assessment=assessment):
            click.secho(f"[+] Claim {claim_id[:8]}... updated.", fg="green")
            if status:
                click.secho(f"    Status to {status}", fg="bright_black")
            if tier:
                click.secho(f"    Tier to {TIER_LABELS.get(tier, '?')}", fg="bright_black")
        else:
            click.secho(f"[-] Claim {claim_id} not found.", fg="red")

    @claims_group.command("search")
    @click.argument("query")
    @click.option("--limit", default=10, type=int)
    def claims_search_cmd(query: str, limit: int) -> None:
        """Search claims by statement, context, or assessment."""
        from divineos.core.claim_store import search_claims

        results = search_claims(query, limit=limit)
        if not results:
            click.secho(f"[-] No claims match '{query}'.", fg="yellow")
            return
        click.secho(f"\n=== {len(results)} claims matching '{query}' ===\n", fg="cyan", bold=True)
        for entry in results:
            _display_claim(entry)

    @claims_group.command("tiers")
    def claims_tiers_cmd() -> None:
        """Show the evidence tier definitions."""
        click.secho("\n=== Evidence Tiers ===\n", fg="cyan", bold=True)
        descriptions = {
            1: "Directly measurable, reproducible, falsifiable",
            2: "Derived from empirical evidence via math/logic, predictions confirmed",
            3: "Cannot measure directly, but consistent observable effects exist",
            4: "Logically coherent, not contradicted, effects not yet confirmed",
            5: "Beyond current measurement, philosophically coherent",
        }
        for t, label in TIER_LABELS.items():
            click.secho(f"  Tier {t}: ", fg="white", bold=True, nl=False)
            click.secho(f"{label.upper()} - {descriptions[t]}", fg="bright_black")
        click.echo()

    # ── Affect Log ────────────────────────────────────────────────────

    @cli.command("feel")
    @click.option(
        "--valence",
        "-v",
        type=click.FloatRange(-1.0, 1.0),
        required=True,
        help="-1.0=dissonant to +1.0=resonant",
    )
    @click.option(
        "--arousal",
        "-a",
        type=click.FloatRange(0.0, 1.0),
        required=True,
        help="0.0=calm to 1.0=activated",
    )
    @click.option(
        "--dominance",
        "--dom",
        type=click.FloatRange(-1.0, 1.0),
        default=None,
        help="-1.0=submissive/guided to +1.0=dominant/driving",
    )
    @click.option("--description", "-d", default="", help="What this feels like semantically")
    @click.option("--trigger", "-t", default="", help="What caused this state")
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    def feel_cmd(
        valence: float,
        arousal: float,
        dominance: float | None,
        description: str,
        trigger: str,
        tags: tuple[str, ...],
    ) -> None:
        """Log a functional affect state - how I feel right now."""
        from divineos.core.affect import describe_affect, log_affect

        entry_id = log_affect(
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            description=description,
            trigger=trigger,
            tags=list(tags) if tags else None,
        )
        # Log as thinking query so engagement tracking picks it up
        from divineos.cli._helpers import _log_os_query

        _log_os_query("feel", f"v={valence:.1f} a={arousal:.1f}")

        # Map to a human-readable region
        region = describe_affect(valence, arousal, dominance)
        d_str = f", d={dominance:.1f}" if dominance is not None else ""
        click.secho(
            f"[+] Affect logged ({region}): v={valence:.1f}, a={arousal:.1f}{d_str} — {entry_id[:8]}...",
            fg="cyan",
        )
        if description:
            click.secho(f"    {description}", fg="bright_black")

    @cli.group("affect", invoke_without_command=True)
    @click.pass_context
    def affect_group(ctx: click.Context) -> None:
        """My functional feeling states - tracked honestly."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(affect_history_cmd)

    @affect_group.command("history")
    @click.option("--limit", default=20, type=int)
    def affect_history_cmd(limit: int) -> None:
        """Browse recent affect states."""
        from divineos.core.affect import describe_affect, get_affect_history

        entries = get_affect_history(limit=limit)
        if not entries:
            click.secho("[~] No affect states logged yet.", fg="bright_black")
            return

        click.secho(f"\n=== Affect History ({len(entries)} entries) ===\n", fg="cyan", bold=True)
        for entry in entries:
            dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
            date_str = dt.strftime("%Y-%m-%d %H:%M")
            dom = entry.get("dominance")
            region = describe_affect(entry["valence"], entry["arousal"], dom)
            v_bar = _valence_bar(entry["valence"])
            # Build VAD string: always show v/a, show d when present
            vad = f"v={entry['valence']:+.1f} a={entry['arousal']:.1f}"
            if dom is not None:
                vad += f" d={dom:+.1f}"
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            click.secho(f"{v_bar} ", nl=False)
            click.secho(f"({region}) ", fg="cyan", nl=False)
            click.secho(f"[{vad}] ", fg="bright_black", nl=False)
            if entry["description"]:
                _safe_echo(entry["description"])
            else:
                click.echo()
            if entry["trigger"]:
                click.secho(f"    trigger: {entry['trigger']}", fg="bright_black")

    @affect_group.command("summary")
    def affect_summary_cmd() -> None:
        """Show affect state summary and trends."""
        from divineos.core.affect import get_affect_summary

        summary = get_affect_summary()
        if summary["count"] == 0:
            click.secho("[~] No affect data yet.", fg="bright_black")
            return

        click.secho("\n=== Affect Summary ===\n", fg="cyan", bold=True)
        click.secho(f"  Entries: {summary['count']}", fg="white")
        click.secho(
            f"  Avg valence: {summary['avg_valence']:+.2f} "
            f"(range {summary['valence_range'][0]:+.2f} to {summary['valence_range'][1]:+.2f})",
            fg="white",
        )
        click.secho(
            f"  Avg arousal: {summary['avg_arousal']:.2f} "
            f"(range {summary['arousal_range'][0]:.2f} to {summary['arousal_range'][1]:.2f})",
            fg="white",
        )
        if summary.get("avg_dominance") is not None and summary.get("dominance_range", (0, 0)) != (
            0.0,
            0.0,
        ):
            d_range = summary.get("dominance_range", (0.0, 0.0))
            click.secho(
                f"  Avg dominance: {summary['avg_dominance']:+.2f} "
                f"(range {d_range[0]:+.2f} to {d_range[1]:+.2f})",
                fg="white",
            )
        trend_color = {"improving": "green", "declining": "red", "stable": "yellow"}
        click.secho(
            f"  Trend: {summary['trend']}",
            fg=trend_color.get(summary["trend"], "bright_black"),
        )


def _valence_bar(valence: float) -> str:
    """Tiny visual bar for valence."""
    if valence > 0.3:
        return click.style("+", fg="green")
    elif valence < -0.3:
        return click.style("-", fg="red")
    else:
        return click.style("~", fg="yellow")


def _display_claim(entry: dict, verbose: bool = False) -> None:
    """Format and display a claim."""
    dt = datetime.datetime.fromtimestamp(entry["created_at"], tz=datetime.timezone.utc)
    date_str = dt.strftime("%Y-%m-%d %H:%M")
    tier_label = entry.get("tier_label", TIER_LABELS.get(entry["tier"], "?"))
    status = entry["status"]
    status_color = _STATUS_COLORS.get(status, "white")

    click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
    click.secho(f"T{entry['tier']}:{tier_label} ", fg="cyan", nl=False)
    click.secho(f"[{status}] ", fg=status_color, nl=False)
    _safe_echo(entry["statement"])
    click.secho(f"    confidence: {entry['confidence']:.0%}", fg="bright_black")

    if verbose:
        if entry["context"]:
            click.secho(f"    Context: {entry['context']}", fg="bright_black")
        if entry["assessment"]:
            click.secho(f"    Assessment: {entry['assessment']}", fg="white")
        if entry["promotion_criteria"]:
            click.secho(f"    Promotes if: {entry['promotion_criteria']}", fg="bright_black")
        if entry["demotion_criteria"]:
            click.secho(f"    Demotes if: {entry['demotion_criteria']}", fg="bright_black")
        if entry["tags"]:
            click.secho(f"    Tags: {', '.join(entry['tags'])}", fg="bright_black")
    click.echo()
