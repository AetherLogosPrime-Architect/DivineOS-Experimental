"""Pre-registration CLI commands.

Every new detector, mechanism, or instrumentation claim should file a
pre-registration here BEFORE shipping. The pre-registration names a
specific falsifier and schedules a review date. The review date fires
independent of agent memory, so a mechanism cannot silently drift past
its own commitment.

Goodhart prevention, applied structurally.
"""

from __future__ import annotations

import click

_OUTCOME_COLORS = {
    "OPEN": "yellow",
    "SUCCESS": "green",
    "FAILED": "red",
    "INCONCLUSIVE": "cyan",
    "DEFERRED": "bright_black",
}


def register(cli: click.Group) -> None:
    """Register pre-registration commands."""

    @cli.group("prereg", invoke_without_command=True)
    @click.pass_context
    def prereg_group(ctx: click.Context) -> None:
        """Pre-registrations — predictions with falsifiers and scheduled reviews."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(prereg_list_cmd)

    @prereg_group.command("file")
    @click.argument("mechanism")
    @click.option("--claim", required=True, help="What the mechanism is supposed to do")
    @click.option(
        "--success",
        "success_criterion",
        required=True,
        help="Specific observable pattern that counts as success",
    )
    @click.option(
        "--falsifier",
        required=True,
        help="Specific observable pattern that invalidates the mechanism",
    )
    @click.option(
        "--review-days",
        type=int,
        default=30,
        help="Days until scheduled review (default 30)",
    )
    @click.option("--actor", default="agent", help="Who is filing this prediction")
    @click.option("--linked-claim", default=None, help="Optional claim_id to cross-reference")
    @click.option(
        "--linked-commit",
        default=None,
        help="Optional commit SHA of the mechanism being shipped",
    )
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    @click.option(
        "--companion-prereg",
        default=None,
        help=(
            "prereg-id of the upstream/structural-prevention companion. "
            "Required (or --no-upstream-because) when the filing reads "
            "as a surface-fix shape. See prereg-89d744b98b35."
        ),
    )
    @click.option(
        "--no-upstream-because",
        default=None,
        help=(
            "Escape hatch when upstream prevention is genuinely "
            "impossible for this failure-class. Reason text >= 30 "
            "chars; logged as auditable. See prereg-89d744b98b35."
        ),
    )
    def prereg_file_cmd(
        mechanism: str,
        claim: str,
        success_criterion: str,
        falsifier: str,
        review_days: int,
        actor: str,
        linked_claim: str | None,
        linked_commit: str | None,
        tags: tuple[str, ...],
        companion_prereg: str | None,
        no_upstream_because: str | None,
    ) -> None:
        """File a new pre-registration.

        Every field is load-bearing. Empty falsifier = not a prediction.

        Surface-fix shapes (detectors / warnings / pattern-match gates)
        must either name a companion structural-prevention prereg OR
        explicitly document why upstream prevention is impossible. See
        the three-why-trace gate (prereg-89d744b98b35) for the discipline.
        """
        from divineos.core.pre_registrations import file_pre_registration
        from divineos.core.three_why_gate import validate_three_why

        ok, message = validate_three_why(
            mechanism=mechanism,
            claim=claim,
            companion_prereg_id=companion_prereg,
            no_upstream_because=no_upstream_because,
        )
        if not ok:
            click.secho(f"[!] {message}", fg="red")
            return

        # Fold the upstream-context into tags so it surfaces in list/show
        # and remains auditable across the prereg's lifetime.
        effective_tags = list(tags) if tags else []
        if companion_prereg:
            effective_tags.append(f"companion:{companion_prereg}")
        if no_upstream_because:
            effective_tags.append("no-upstream-because")

        try:
            prereg_id = file_pre_registration(
                actor=actor,
                mechanism=mechanism,
                claim=claim,
                success_criterion=success_criterion,
                falsifier=falsifier,
                review_window_days=review_days,
                linked_claim_id=linked_claim,
                linked_commit=linked_commit,
                tags=effective_tags if effective_tags else None,
            )
            click.secho(f"[+] Pre-registration filed: {prereg_id}", fg="cyan")
            click.echo(f"    Review scheduled in {review_days} days.")
            click.echo(f"    Falsifier: {falsifier[:100]}")
            if companion_prereg:
                click.echo(f"    Upstream companion: {companion_prereg}")
            if no_upstream_because:
                click.echo(f"    No-upstream-because logged ({len(no_upstream_because)} chars)")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @prereg_group.command("list")
    @click.option(
        "--outcome",
        type=click.Choice(
            ["OPEN", "SUCCESS", "FAILED", "INCONCLUSIVE", "DEFERRED"],
            case_sensitive=False,
        ),
        default=None,
    )
    @click.option("--actor", default=None, help="Filter by actor")
    @click.option("--mechanism", default=None, help="Filter by mechanism name")
    @click.option("--limit", default=20, type=int)
    def prereg_list_cmd(
        outcome: str | None,
        actor: str | None,
        mechanism: str | None,
        limit: int,
    ) -> None:
        """List pre-registrations."""
        from divineos.core.pre_registrations import Outcome, list_pre_registrations

        outcome_enum = Outcome(outcome.upper()) if outcome else None
        items = list_pre_registrations(
            outcome=outcome_enum,
            actor=actor,
            mechanism=mechanism,
            limit=limit,
        )
        if not items:
            click.secho("[~] No pre-registrations found.", fg="bright_black")
            return

        click.secho(f"\n=== Pre-registrations ({len(items)}) ===\n", fg="cyan", bold=True)
        for p in items:
            color = _OUTCOME_COLORS.get(p.outcome.value, "white")
            click.echo(
                f"  {p.prereg_id:20} "
                + click.style(f"{p.outcome.value:<12}", fg=color)
                + f" {p.mechanism}: {p.claim[:70]}"
            )

    @prereg_group.command("show")
    @click.argument("prereg_id")
    def prereg_show_cmd(prereg_id: str) -> None:
        """Show full detail for a single pre-registration."""
        import time as _time

        from divineos.core.pre_registrations import get_pre_registration

        p = get_pre_registration(prereg_id)
        if not p:
            click.secho(f"[!] Pre-registration not found: {prereg_id}", fg="red")
            return

        color = _OUTCOME_COLORS.get(p.outcome.value, "white")
        click.secho(f"\n=== {p.prereg_id} ===", fg="cyan", bold=True)
        click.echo(f"  Mechanism:   {p.mechanism}")
        click.echo(f"  Filed by:    {p.actor}")
        click.echo(
            f"  Filed at:    {_time.strftime('%Y-%m-%d %H:%M UTC', _time.gmtime(p.created_at))}"
        )
        click.echo(
            f"  Review:      {_time.strftime('%Y-%m-%d %H:%M UTC', _time.gmtime(p.review_ts))} "
            f"({p.review_window_days}d window)"
        )
        click.echo("  Outcome:     " + click.style(p.outcome.value, fg=color, bold=True))
        if p.outcome_ts:
            click.echo(
                f"  Decided at:  {_time.strftime('%Y-%m-%d %H:%M UTC', _time.gmtime(p.outcome_ts))}"
            )
        if p.outcome_notes:
            click.echo(f"  Notes:       {p.outcome_notes}")
        click.echo("")
        click.echo(f"  Claim:       {p.claim}")
        click.echo(f"  Success:     {p.success_criterion}")
        click.echo(f"  Falsifier:   {p.falsifier}")
        if p.linked_claim_id:
            click.echo(f"  Linked claim: {p.linked_claim_id}")
        if p.linked_commit:
            click.echo(f"  Linked commit: {p.linked_commit}")
        if p.tags:
            click.echo(f"  Tags:        {', '.join(p.tags)}")

    @prereg_group.command("overdue")
    def prereg_overdue_cmd() -> None:
        """List pre-registrations whose review date has passed."""
        import time as _time

        from divineos.core.pre_registrations import get_overdue_pre_registrations

        overdue = get_overdue_pre_registrations()
        if not overdue:
            click.secho("[~] No overdue pre-registrations.", fg="green")
            return

        click.secho(
            f"\n=== Overdue Pre-registrations ({len(overdue)}) ===\n",
            fg="yellow",
            bold=True,
        )
        now = _time.time()
        for p in overdue:
            days = (now - p.review_ts) / 86400
            click.echo(
                f"  {p.prereg_id:20} "
                + click.style(f"+{days:.1f}d overdue", fg="yellow")
                + f"  {p.mechanism}: {p.claim[:70]}"
            )
        click.echo("\nReview each with: divineos prereg assess <id> --outcome ...")

    @prereg_group.command("assess")
    @click.argument("prereg_id")
    @click.option(
        "--outcome",
        type=click.Choice(["SUCCESS", "FAILED", "INCONCLUSIVE", "DEFERRED"], case_sensitive=False),
        required=True,
    )
    @click.option(
        "--actor",
        required=True,
        help="External actor recording the outcome (user, grok, etc.)",
    )
    @click.option("--notes", default="", help="Evidence or reasoning for the outcome")
    def prereg_assess_cmd(prereg_id: str, outcome: str, actor: str, notes: str) -> None:
        """Record a terminal outcome for a pre-registration.

        Requires an external actor. Internal actors (claude, system, pipeline)
        cannot record outcomes — the whole point is external verification.
        """
        from divineos.core.pre_registrations import Outcome, record_outcome

        try:
            ok = record_outcome(
                prereg_id=prereg_id,
                actor=actor,
                outcome=Outcome(outcome.upper()),
                notes=notes,
            )
            if ok:
                color = _OUTCOME_COLORS.get(outcome.upper(), "white")
                click.echo(f"[+] {prereg_id} -> ", nl=False)
                click.secho(outcome.upper(), fg=color, bold=True)
                if notes:
                    click.echo(f"    Notes: {notes}")
            else:
                click.secho(f"[!] Pre-registration not found: {prereg_id}", fg="red")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @prereg_group.command("summary")
    def prereg_summary_cmd() -> None:
        """Show counts by outcome + recent pre-registrations."""
        from divineos.core.pre_registrations import format_summary

        click.echo(format_summary())

    @prereg_group.command("export")
    @click.option(
        "--out-dir",
        default="docs/pre_regs",
        help="Directory to write per-prereg markdown files (default docs/pre_regs).",
    )
    @click.option(
        "--outcome",
        type=click.Choice(
            ["OPEN", "SUCCESS", "FAILED", "INCONCLUSIVE", "DEFERRED"],
            case_sensitive=False,
        ),
        default=None,
        help="Only export pre-regs with this outcome.",
    )
    def prereg_export_cmd(out_dir: str, outcome: str | None) -> None:
        """Export pre-registrations to markdown files for repo-portability.

        Pre-registrations live in a runtime SQLite store (ephemeral on a
        fresh clone). Exporting them to ``docs/pre_regs/<id>.md`` lets the
        commitment travel with the repo — a reviewer who never imports the
        local DB can still read what was predicted, by whom, with what
        falsifier, and what (if anything) the verdict was.
        """
        from pathlib import Path

        from divineos.core.pre_registrations import Outcome, list_pre_registrations

        outcome_enum = Outcome(outcome.upper()) if outcome else None
        items = list_pre_registrations(outcome=outcome_enum, limit=10_000)
        if not items:
            click.secho("[~] No pre-registrations to export.", fg="bright_black")
            return

        out_path = Path(out_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        written = 0
        for p in items:
            (out_path / f"{p.prereg_id}.md").write_text(
                _format_prereg_markdown(p), encoding="utf-8"
            )
            written += 1

        click.secho(f"[+] Exported {written} pre-registration(s) to {out_path}/", fg="cyan")


def _format_prereg_markdown(p) -> str:
    """Render a PreRegistration as portable markdown."""
    import time as _time

    def _fmt(ts: float | None) -> str:
        if not ts:
            return "—"
        return _time.strftime("%Y-%m-%d %H:%M UTC", _time.gmtime(ts))

    lines = [
        f"# Pre-registration: {p.mechanism}",
        "",
        f"- **ID**: `{p.prereg_id}`",
        f"- **Filed by**: {p.actor}",
        f"- **Filed at**: {_fmt(p.created_at)}",
        f"- **Review at**: {_fmt(p.review_ts)} ({p.review_window_days}d window)",
        f"- **Outcome**: **{p.outcome.value}**",
    ]
    if p.outcome_ts:
        lines.append(f"- **Decided at**: {_fmt(p.outcome_ts)}")
    if p.linked_claim_id:
        lines.append(f"- **Linked claim**: `{p.linked_claim_id}`")
    if p.linked_commit:
        lines.append(f"- **Linked commit**: `{p.linked_commit}`")
    if p.tags:
        lines.append(f"- **Tags**: {', '.join(p.tags)}")

    lines += [
        "",
        "## Claim",
        "",
        p.claim,
        "",
        "## Success criterion",
        "",
        p.success_criterion,
        "",
        "## Falsifier",
        "",
        p.falsifier,
    ]
    if p.outcome_notes:
        lines += ["", "## Outcome notes", "", p.outcome_notes]
    lines.append("")
    return "\n".join(lines)
