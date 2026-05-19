"""CLI: divineos consumer-status — operator-facing summary of whether
the agent is using the OS or pretending.

Andrew 2026-05-18 evening: "except that I don't see those numbers." The
trackers built tonight (lepos_debt, consultation_tracker, auto-filed
claims, pattern-fire counts) surface to the agent's briefing — not to
the operator. This command flips the audience: plain-English summary
of consumer-pretender status, designed for Andrew to glance at without
chasing JSON files or running ad-hoc queries.

Output shape:
  - One headline verdict (USING / PARTIAL / PRETENDING / NO-DATA)
  - Plain-language summary of each tracker
  - Specific evidence pointers (drill-down commands)

Designed so Andrew can know, in 30 seconds, whether the current
session is the same pretender pattern or different.
"""

from __future__ import annotations

__guardrail_required__ = True

import click


def register(cli: click.Group) -> None:
    @cli.command("consumer-status")
    def consumer_status_cmd() -> None:
        """Show whether Aether is using the OS or pretending to (operator-facing)."""
        # Pull all the relevant trackers and present them in plain English.
        lepos_debts: list = []
        consultation_stats: dict = {}
        auto_claims: list = []
        pattern_fires_14d: int = 0

        try:
            from divineos.core.lepos_debt import list_outstanding

            lepos_debts = list_outstanding()
        except Exception:  # noqa: BLE001 - observability boundary
            pass

        try:
            from divineos.core.consultation_tracker import session_stats

            consultation_stats = session_stats()
        except Exception:  # noqa: BLE001 - observability boundary
            pass

        try:
            from divineos.core.claim_store import list_claims

            opens = list_claims(limit=50, status="OPEN") or []
            auto_claims = [c for c in opens if "lepos-auto-claim" in (c.get("tags") or [])]
        except Exception:  # noqa: BLE001 - observability boundary
            pass

        try:
            from divineos.core.pattern_attribution import query_pattern_fires
            import time

            since = time.time() - 14 * 86400.0
            fires = query_pattern_fires(since_timestamp=since, limit=500)
            pattern_fires_14d = len(fires)
        except Exception:  # noqa: BLE001 - observability boundary
            pattern_fires_14d = 0

        # Verdict logic — simple, transparent, no smoothing.
        debt_count = len(lepos_debts)
        q = consultation_stats.get("queries", 0)
        r = consultation_stats.get("responses", 0)
        ratio = consultation_stats.get("ratio", 0.0)

        if r < 3 and debt_count == 0 and not auto_claims:
            verdict = "NO-DATA"
            verdict_fg = "bright_black"
            verdict_text = "Not enough activity this session to tell yet."
        elif debt_count == 0 and ratio >= 0.5 and not auto_claims:
            verdict = "USING"
            verdict_fg = "green"
            verdict_text = (
                "Aether is consulting the OS and translating engineer-talk "
                "into plain words. No outstanding debt. Ratio healthy."
            )
        elif debt_count >= 3 or auto_claims or ratio < 0.2:
            verdict = "PRETENDING"
            verdict_fg = "red"
            verdict_text = (
                "Aether is bypassing the OS. Engineer-talk is accumulating "
                "without translation, or the consultation ratio is low, or "
                "the auto-claim has fired. This is the consumer-pretender "
                "pattern you named 2026-05-18."
            )
        else:
            verdict = "PARTIAL"
            verdict_fg = "yellow"
            verdict_text = (
                "Mixed signals. Some consultation happening, some pattern "
                "of bypass. Worth a closer look."
            )

        click.echo()
        click.secho("=" * 60, fg=verdict_fg)
        click.secho(f"  CONSUMER STATUS: {verdict}", fg=verdict_fg, bold=True)
        click.secho("=" * 60, fg=verdict_fg)
        click.echo()
        click.secho(f"  {verdict_text}", fg=verdict_fg)
        click.echo()

        # Detail block — plain language.
        click.secho("Translation debt (jargon dumped on you without translation):", bold=True)
        if debt_count == 0:
            click.secho("  None outstanding.", fg="green")
        else:
            click.secho(
                f"  {debt_count} outstanding debt(s). Aether has dumped engineer-",
                fg="red",
            )
            click.secho(
                "  talk on you that hasn't been retroactively translated.",
                fg="red",
            )
            click.secho(
                "  Drill down: divineos lepos debt",
                fg="bright_black",
            )
        click.echo()

        click.secho("Substrate consultation this session:", bold=True)
        if r < 3:
            click.secho(
                "  Too early to judge (fewer than 3 responses).",
                fg="bright_black",
            )
        else:
            tools = consultation_stats.get("tools_used", [])
            click.secho(
                f"  {q} queries against {r} responses (ratio {ratio:.2f}).",
                fg=("green" if ratio >= 0.5 else "yellow" if ratio >= 0.2 else "red"),
            )
            if tools:
                click.secho(
                    f"  Tools Aether actually used: {', '.join(tools)}",
                    fg="bright_black",
                )
            else:
                click.secho(
                    "  Aether has not consulted any substrate tool this session.",
                    fg="red",
                )
        click.echo()

        click.secho("Auto-filed claims about the pattern:", bold=True)
        if not auto_claims:
            click.secho("  None. The system has not detected chronic ignoring.", fg="green")
        else:
            click.secho(
                f"  {len(auto_claims)} open auto-claim(s). The system has "
                f"detected chronic jargon-dumping and filed an investigation.",
                fg="red",
            )
            click.secho(
                "  Drill down: divineos claims list --status OPEN",
                fg="bright_black",
            )
        click.echo()

        click.secho("Pattern fires recorded in last 14 days:", bold=True)
        if pattern_fires_14d == 0:
            click.secho("  None.", fg="green")
        else:
            click.secho(
                f"  {pattern_fires_14d} fire(s). Drill down: divineos pattern-fire list",
                fg=("yellow" if pattern_fires_14d < 5 else "red"),
            )
        click.echo()
        click.secho(
            "This view exists for you, not me. Andrew 2026-05-18.",
            fg="bright_black",
        )
        click.echo()
