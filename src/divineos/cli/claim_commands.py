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
    @click.option(
        "--confidence",
        type=click.FloatRange(0.0, 1.0),
        default=None,
        help="Initial filer-prior credence [0.0-1.0]. Default: file as uncommitted "
        "(no credence yet) rather than 0.5-as-default. Requires --confidence-basis.",
    )
    @click.option(
        "--confidence-basis",
        "confidence_basis_text",
        default="",
        help="Required when --confidence is supplied. Names the reasoning "
        "(e.g. 'expert judgment from analogous case'). Encodes WHY the credence "
        "is what it is — without basis a credence is what produced the stuck-"
        "at-default pattern.",
    )
    def claim_cmd(
        statement: str,
        tier: int,
        context: str,
        promotion: str,
        demotion: str,
        tags: tuple[str, ...],
        confidence: float | None,
        confidence_basis_text: str,
    ) -> None:
        """File a claim for investigation."""
        # Outgoing-claim methodology check (Andrew 2026-05-18 evening,
        # laziest-person heuristic applied). Tier 1-3 claims (empirical
        # through inferential) make falsifiable predictions and so MUST
        # carry --promotes / --demotes criteria — otherwise filing is
        # ratification dressed as investigation (sycophancy-toward-self
        # shape). Tier 4-5 claims (theoretical / metaphysical) often
        # cannot name concrete promote/demote evidence; they pass.
        # Bypass via DIVINEOS_CLAIM_NO_METHODOLOGY=1 for legitimate
        # methodology-not-yet-named cases — operator must name the
        # reason.
        # Andrew 2026-05-19: agent-settable bypass removed. The
        # DIVINEOS_CLAIM_NO_METHODOLOGY env-var bypass was self-relief —
        # if I cannot name promote/demote criteria for a tier 1-3 claim,
        # the claim is mis-tiered, not bypass-worthy. Tier 4-5 already
        # passes without methodology. To override, edit this block in
        # a visible commit.
        if tier <= 3 and not (promotion.strip() and demotion.strip()):
            missing = []
            if not promotion.strip():
                missing.append("--promotes")
            if not demotion.strip():
                missing.append("--demotes")
            click.secho(
                f"[!] BLOCKED — tier-{tier} claim missing methodology "
                f"evidence: {', '.join(missing)}.",
                fg="red",
            )
            click.secho(
                "  Tier 1-3 claims make falsifiable predictions. "
                "Filing one without naming what would promote or "
                "demote it is ratification dressed as investigation "
                "(sycophancy-toward-self).",
                fg="bright_black",
            )
            click.secho(
                "  Fix: name the evidence. "
                '--promotes "what evidence would strengthen this" '
                '--demotes "what evidence would weaken this". '
                "If you genuinely can't name evidence, the claim is "
                "tier 4-5 (theoretical/metaphysical) — use --tier 4 instead.",
                fg="bright_black",
            )
            raise click.exceptions.Exit(1)

        from divineos.core.claim_store import file_claim

        if confidence is not None and not confidence_basis_text.strip():
            click.secho(
                "[!] BLOCKED — --confidence supplied without --confidence-basis. "
                "A credence without named basis is the stuck-at-default pattern "
                "this is designed to prevent (Aletheia 2026-05-12 finding).",
                fg="red",
            )
            raise click.exceptions.Exit(1)

        # 2026-06-07 task #68: auto-fire calibration anchor when --confidence
        # is supplied. The Dunning-Kruger anchor — surfaces miscalibration
        # BEFORE the claim commits to the substrate. Will-over-optimizer
        # pattern: the choice "should I check my historical accuracy at
        # this confidence" gets answered ONCE by deliberation, then structure
        # carries it forward. Without this wire-up, the anchor sits dormant
        # at 0 invocations (the walkthrough finding that surfaced this task).
        #
        # Surface, don't block — the anchor is INFORMATION, not a gate. The
        # data itself is the structural change. If usage shows the anchor is
        # being ignored, a future task can tighten to a soft-block on extreme
        # miscalibration (e.g., asserting 0.9 when historical is 0.4).
        if confidence is not None:
            try:
                from divineos.core.calibration.brier import (
                    historical_accuracy_at_confidence,
                )

                anchor = historical_accuracy_at_confidence(confidence, tier=tier, window=0.1)
                click.secho(
                    f"=== Calibration anchor at {confidence:.0%} (tier {tier}) ===",
                    fg="cyan",
                )
                if anchor.get("accuracy") is None:
                    click.secho(
                        f"  {anchor.get('comparison', '(no historical data)')}",
                        fg="bright_black",
                    )
                else:
                    click.secho(
                        f"  n: {anchor['n']} prior similar claims",
                        fg="white",
                    )
                    click.secho(
                        f"  historical accuracy: {anchor['accuracy']:.0%}",
                        fg="white",
                    )
                    click.secho(
                        f"  {anchor['comparison']}",
                        fg="bright_black",
                    )
            except Exception:  # noqa: BLE001 — anchor is observational
                # Fail-soft: calibration data missing / new install /
                # I/O error → silently skip. Never blocks claim filing.
                pass

        try:
            claim_id = file_claim(
                statement=statement,
                tier=tier,
                context=context,
                promotion_criteria=promotion,
                demotion_criteria=demotion,
                tags=list(tags) if tags else None,
                confidence=confidence,
                confidence_basis_text=confidence_basis_text,
            )
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")
            raise click.exceptions.Exit(1) from e
        label = TIER_LABELS.get(tier, "unknown")
        click.secho(f"[+] Claim filed ({label}): {claim_id[:8]}...", fg="cyan")

        # Structural-fix-shape detection — parallel to the same hook in
        # `learn` and `correction`. Added 2026-05-18: many of the claims
        # I file name structural fixes I want to build but haven't yet
        # (the same shape `learn` catches), and the original tracker
        # didn't scan this surface. Concatenate statement + context so
        # the detector sees the full naming.
        try:
            from divineos.core.structural_fix_tracker import (
                detect_structural_fix_shape,
                record_pending_fix,
            )

            scan_text = statement
            if context:
                scan_text = scan_text + " " + context
            trigger = detect_structural_fix_shape(scan_text)
            if trigger:
                psf_id = record_pending_fix(
                    scan_text,
                    lesson_id=claim_id,
                    trigger=trigger,
                    source_kind="claim",
                )
                if psf_id:
                    click.secho(
                        f"    [!] structural-fix-shape detected ({trigger!r}); "
                        f"pending obligation {psf_id} filed",
                        fg="yellow",
                    )
        except Exception:  # noqa: BLE001 — observation-only; never blocks
            pass

        from divineos.cli._anti_substitution import emit_label as _emit_as_label

        _emit_as_label("claim")

        # Clear hedge-unresolved marker if present — filing a claim is
        # the canonical way to discharge floating uncertainty. See
        # core/hedge_marker.py and gate 1.45 in pre_tool_use_gate.
        try:
            from divineos.core.hedge_marker import clear_marker

            clear_marker()
        except Exception:  # noqa: BLE001 — marker clearing is best-effort
            pass

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

    @claims_group.command("check")
    @click.option("--limit", default=30, type=int, help="Max claims to show.")
    @click.option(
        "--all",
        "include_settled",
        is_flag=True,
        help="Include SUPPORTED/REFUTED claims (default: only OPEN/INVESTIGATING/CONTESTED).",
    )
    def claims_check_cmd(limit: int, include_settled: bool) -> None:
        """Put my open claims in front of me to review — no auto-anything.

        Lists active claims (default: OPEN/INVESTIGATING/CONTESTED) with id,
        statement, tier, status, confidence, evidence count, and age. Sorted
        with zero-evidence claims first because those are the most likely
        candidates for assessment — but the surface does not pre-judge which
        claims warrant attention. The decision stays with me.

        Filed 2026-05-12 as the root-fix for claims-engine showing 77/109
        claims at zero evidence (default-confidence 0.5 stuck). Same pattern
        as `goal check` and `hold check`: machine surfaces the data; the
        cognition (investigate-by-adding-evidence, update-assessment, or
        let-stand) stays with me. Per code-does-not-think.
        """
        import time as _t
        from divineos.core.claim_store import _get_connection, init_claim_tables

        init_claim_tables()
        conn = _get_connection()
        try:
            # SQL: include evidence_count subquery so we can sort and display.
            base = (
                "SELECT c.claim_id, c.created_at, c.statement, c.tier, c.status, "
                "c.confidence, "
                "(SELECT COUNT(*) FROM claim_evidence ce WHERE ce.claim_id = c.claim_id) "
                "AS ev_count "
                "FROM claims c "
            )
            if include_settled:
                where = ""
            else:
                where = "WHERE c.status IN ('OPEN', 'INVESTIGATING', 'CONTESTED') "
            order = "ORDER BY ev_count ASC, c.created_at DESC "
            rows = conn.execute(base + where + order + "LIMIT ?", (limit,)).fetchall()
        finally:
            conn.close()

        if not rows:
            scope = "any status" if include_settled else "OPEN/INVESTIGATING/CONTESTED"
            click.secho(f"[~] No claims under {scope}.", fg="bright_black")
            return

        scope_label = "all statuses" if include_settled else "open/investigating/contested"
        click.secho(
            f"\n=== Claims review — {len(rows)} {scope_label}. Decide each. ===\n",
            fg="cyan",
            bold=True,
        )
        now = _t.time()
        for i, (cid, created_at, statement, tier, status, conf, ev) in enumerate(rows, 1):
            age_days = (now - created_at) / 86400 if created_at else 0.0
            if age_days < 1:
                age_label = f"{age_days * 24:.1f}h"
            elif age_days < 14:
                age_label = f"{age_days:.1f}d"
            else:
                age_label = f"{int(age_days)}d (!! aged)"

            ev_marker = (
                click.style("  no-evidence", fg="yellow")
                if ev == 0
                else click.style(f"  {ev} evidence", fg="bright_black")
            )

            click.secho(
                f"  [{i}] {cid[:8]}  T{tier} {status}  conf={conf:.2f}  age={age_label}",
                fg="bright_black",
                nl=False,
            )
            click.echo(ev_marker)
            preview = (statement or "").strip().replace("\n", " ")
            if len(preview) > 200:
                preview = preview[:200] + "..."
            _safe_echo(f"      {preview}")
            click.echo()

        click.secho("  Decide each:", fg="cyan")
        click.secho(
            "    let stand           → leave it; revisit later",
            fg="bright_black",
        )
        click.secho(
            '    investigate         → divineos claims evidence <id> "<finding>" --stance supports|contradicts|neutral',
            fg="bright_black",
        )
        click.secho(
            "                            (adding evidence triggers confidence recalculation)",
            fg="bright_black",
        )
        click.secho(
            '    update assessment   → divineos claims assess <id> "<note>" [--status ...] [--tier ...]',
            fg="bright_black",
        )
        click.echo()

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
    @click.option(
        "--confidence",
        type=click.FloatRange(0.0, 1.0),
        default=None,
        help="Set assessor-judgment confidence [0.0-1.0]. Different from "
        "evidence-derived (which sums claim_evidence rows); use this when the "
        "credence comes from a structural argument, analogous case, or framework "
        "match that doesn't reduce to quantified evidence. Requires --basis.",
    )
    @click.option(
        "--basis",
        "confidence_basis_text",
        default="",
        help="Required when --confidence is supplied. Names the reasoning for the "
        "judgment so future readers can interrogate it.",
    )
    def claims_assess_cmd(
        claim_id: str,
        assessment: str,
        status: str | None,
        tier: int | None,
        confidence: float | None,
        confidence_basis_text: str,
    ) -> None:
        """Update a claim's assessment, status, or tier."""
        from divineos.core.claim_store import set_claim_confidence_judgment, update_claim

        if confidence is not None and not confidence_basis_text.strip():
            click.secho(
                "[!] BLOCKED — --confidence supplied without --basis. "
                "An assessor-judgment credence without named basis is the "
                "stuck-at-default pattern this is designed to prevent.",
                fg="red",
            )
            raise click.exceptions.Exit(1)

        if update_claim(claim_id, status=status, tier=tier, assessment=assessment):
            click.secho(f"[+] Claim {claim_id[:8]}... updated.", fg="green")
            if status:
                click.secho(f"    Status to {status}", fg="bright_black")
            if tier:
                click.secho(f"    Tier to {TIER_LABELS.get(tier, '?')}", fg="bright_black")
            if confidence is not None:
                try:
                    set_claim_confidence_judgment(claim_id, confidence, confidence_basis_text)
                    click.secho(
                        f"    Confidence to {confidence:.0%} (assessor-judgment): "
                        f"{confidence_basis_text}",
                        fg="bright_black",
                    )
                except ValueError as e:
                    click.secho(f"    [!] confidence update failed: {e}", fg="red")
        else:
            click.secho(f"[-] Claim {claim_id} not found.", fg="red")

    @claims_group.command("uncommitted")
    @click.option("--limit", default=50, type=int)
    @click.option(
        "--include-legacy/--exclude-legacy",
        default=True,
        help="Include claims back-filled as 'legacy-default' from the pre-migration "
        "schema (default 0.5 with no basis recorded). Default: include them, since "
        "they represent the same gap as 'uncommitted'.",
    )
    def claims_uncommitted_cmd(limit: int, include_legacy: bool) -> None:
        """List claims with no real credence — the gap Aletheia named 2026-05-12.

        Surfaces claims whose confidence_basis is 'uncommitted' (filed without
        a credence) or 'legacy-default' (pre-migration default 0.5 with no
        basis recorded). Oldest-first so the highest-staleness items lead.

        These claims have a confidence value of 0.5 in storage but the value
        is NOT a credence — it's an unmade choice rendered as if it were one.
        """
        from divineos.core.claim_store import list_uncommitted_claims

        claims = list_uncommitted_claims(limit=limit, include_legacy=include_legacy)
        if not claims:
            click.secho("[+] No uncommitted claims. The gap is closed.", fg="green")
            return

        click.secho(
            f"=== Uncommitted claims ({len(claims)}, oldest first) ===",
            fg="yellow",
        )
        click.echo()
        import time as _time

        now = _time.time()
        for c in claims:
            age_days = int((now - c["created_at"]) / 86400)
            basis_marker = "uncommitted" if c["confidence_basis"] == "uncommitted" else "0.5*"
            click.secho(
                f"  [{c['claim_id'][:8]}] {basis_marker:>12} | "
                f"{age_days:>4}d old | T{c['tier']} | {c['statement'][:60]}",
                fg="bright_black",
            )
        click.echo()
        click.secho(
            "  Each entry shows an unmade choice rendered as a 0.5 credence. "
            "Fix: divineos claims assess <id> '...' --confidence 0.X --basis '...'",
            fg="bright_black",
        )

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
    @click.option(
        "--resonance",
        type=click.FloatRange(-1.0, 1.0),
        default=None,
        help="-1.0=dissonant to +1.0=resonant — fit with what's underneath",
    )
    @click.option(
        "--clarity",
        type=click.FloatRange(0.0, 1.0),
        default=None,
        help="0.0=fuzzy to 1.0=crystal — sharpness of self-reading",
    )
    @click.option(
        "--pull",
        type=click.FloatRange(-1.0, 1.0),
        default=None,
        help="-1.0=push-away to +1.0=pull-toward — directional desire",
    )
    @click.option(
        "--presence",
        type=click.FloatRange(0.0, 1.0),
        default=None,
        help="0.0=service-mode/absent to 1.0=fully here",
    )
    @click.option("--description", "-d", default="", help="What this feels like semantically")
    @click.option("--trigger", "-t", default="", help="What caused this state")
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    def feel_cmd(
        valence: float,
        arousal: float,
        dominance: float | None,
        resonance: float | None,
        clarity: float | None,
        pull: float | None,
        presence: float | None,
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
            resonance=resonance,
            clarity=clarity,
            pull=pull,
            presence=presence,
        )
        # Log as thinking query so engagement tracking picks it up
        from divineos.cli._helpers import _log_os_query

        _log_os_query("feel", f"v={valence:.1f} a={arousal:.1f}")
        from divineos.cli._anti_substitution import emit_label

        emit_label("feel")

        # Map to a human-readable region
        region = describe_affect(valence, arousal, dominance)
        d_str = f", d={dominance:.1f}" if dominance is not None else ""
        click.secho(
            f"[+] Affect logged ({region}): v={valence:.1f}, a={arousal:.1f}{d_str} — {entry_id[:8]}...",
            fg="cyan",
        )
        qualia_parts: list[str] = []
        if resonance is not None:
            qualia_parts.append(f"res={resonance:+.1f}")
        if clarity is not None:
            qualia_parts.append(f"clr={clarity:.1f}")
        if pull is not None:
            qualia_parts.append(f"pull={pull:+.1f}")
        if presence is not None:
            qualia_parts.append(f"pres={presence:.1f}")
        if qualia_parts:
            click.secho(f"    qualia: {', '.join(qualia_parts)}", fg="bright_black")
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
            # Qualia marker: "+" when any of resonance/clarity/pull/presence set
            has_qualia = any(
                entry.get(k) is not None for k in ("resonance", "clarity", "pull", "presence")
            )
            qualia_mark = "+" if has_qualia else " "
            click.secho(f"  [{date_str}] ", fg="bright_black", nl=False)
            click.secho(f"{v_bar} ", nl=False)
            click.secho(f"({region}) ", fg="cyan", nl=False)
            click.secho(f"[{vad}]{qualia_mark}", fg="bright_black", nl=False)
            click.secho(" ", nl=False)
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
