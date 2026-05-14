"""Audit CLI commands — external validation via the Watchmen module.

These commands are the ONLY entry point for submitting findings.
No pipeline phase, no hook, no scheduled task calls submit_finding.
This is the second layer of self-trigger prevention.
"""

import click

from divineos.cli._helpers import _safe_echo

_SEVERITY_COLORS = {
    "CRITICAL": "red",
    "HIGH": "yellow",
    "MEDIUM": "cyan",
    "LOW": "white",
    "INFO": "bright_black",
}

_STATUS_COLORS = {
    "OPEN": "white",
    "ROUTED": "cyan",
    "IN_PROGRESS": "yellow",
    "RESOLVED": "green",
    "WONT_FIX": "bright_black",
    "DUPLICATE": "bright_black",
}


def register(cli: click.Group) -> None:
    """Register audit commands."""

    @cli.group("audit", invoke_without_command=True)
    @click.pass_context
    def audit_group(ctx: click.Context) -> None:
        """External validation — submit and track audit findings."""
        if ctx.invoked_subcommand is None:
            ctx.invoke(audit_list_cmd)

    @audit_group.command("submit-round")
    @click.argument("focus")
    @click.option("--actor", required=True, help="Who performed the audit (e.g., grok, user)")
    @click.option("--experts", type=int, default=0, help="Number of expert profiles used")
    @click.option("--notes", default="", help="Additional context")
    def audit_submit_round(focus: str, actor: str, experts: int, notes: str) -> None:
        """Create a new audit round."""
        from divineos.core.watchmen.store import submit_round

        try:
            round_id = submit_round(actor=actor, focus=focus, expert_count=experts, notes=notes)
            click.secho(f"[+] Audit round created: {round_id}", fg="cyan")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @audit_group.command("submit")
    @click.argument("title")
    @click.option("--round", "round_id", required=True, help="Round ID to attach to")
    @click.option("--actor", required=True, help="Who found this (e.g., grok, user)")
    @click.option(
        "--severity",
        type=click.Choice(["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"], case_sensitive=False),
        required=True,
    )
    @click.option(
        "--category",
        type=click.Choice(
            [
                "KNOWLEDGE",
                "BEHAVIOR",
                "INTEGRITY",
                "ARCHITECTURE",
                "PERFORMANCE",
                "LEARNING",
                "IDENTITY",
            ],
            case_sensitive=False,
        ),
        required=True,
    )
    @click.option("--description", "-d", required=True, help="Detailed description")
    @click.option("--recommendation", "-r", default="", help="What should be done")
    @click.option("--tag", "tags", multiple=True, help="Tags (repeatable)")
    def audit_submit_cmd(
        title: str,
        round_id: str,
        actor: str,
        severity: str,
        category: str,
        description: str,
        recommendation: str,
        tags: tuple[str, ...],
    ) -> None:
        """Submit a single audit finding."""
        from divineos.core.watchmen.store import submit_finding

        try:
            finding_id = submit_finding(
                round_id=round_id,
                actor=actor,
                severity=severity,
                category=category,
                title=title,
                description=description,
                recommendation=recommendation,
                tags=list(tags) if tags else None,
            )
            click.secho(f"[+] Finding submitted: {finding_id} [{severity.upper()}]", fg="cyan")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @audit_group.command("rebind")
    @click.argument("prior_round_id")
    @click.option(
        "--focus",
        default="",
        help="Optional focus override; defaults to deriving from prior round.",
    )
    def audit_rebind_cmd(prior_round_id: str, focus: str) -> None:
        """File a cosmetic-rebind round that carries the prior round's
        CONFIRMS forward when the staged diff vs. the prior round's
        bound state is mechanical-only (whitespace, import-reorder,
        unused-import-removal).

        Refuses if any file has substantive change (comments,
        docstrings, executable code, tests).

        Discipline: this is the structural answer to the cosmetic-drift
        problem named in round-cc0bf85fc3fa. Aletheia's positive list
        (whitespace + import-reorder + unused-import-removal). Anything
        else still requires fresh CONFIRMS through normal submit-round
        + submit flow.
        """
        import re
        import subprocess
        import sys
        from pathlib import Path

        from divineos.core.watchmen.store import (
            get_round,
            list_findings,
            submit_finding,
            submit_round,
        )

        prior = get_round(prior_round_id)
        if prior is None:
            click.secho(f"[!] Prior round '{prior_round_id}' not found.", fg="red")
            return

        # Extract tree-hash from the prior round's focus text. Falls
        # back to diff-hash if tree-hash absent (older rounds may have
        # only diff-hash).
        tree_match = re.search(r"tree-hash:\s*([0-9a-f]{40})", prior.focus, re.IGNORECASE)
        if not tree_match:
            click.secho(
                f"[!] Prior round '{prior_round_id}' has no tree-hash in its focus; "
                "cannot auto-classify cosmetic-rebind. File a fresh round manually.",
                fg="red",
            )
            return
        prior_tree_hash = tree_match.group(1)

        # Run the cosmetic classifier. Compare prior tree-hash to staged
        # index.
        script_path = (
            Path(__file__).resolve().parent.parent.parent.parent
            / "scripts"
            / "cosmetic_diff_check.py"
        )
        if not script_path.exists():
            click.secho(f"[!] Classifier missing at {script_path}.", fg="red")
            return

        result = subprocess.run(
            [sys.executable, str(script_path), prior_tree_hash, "--quiet"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            click.secho(
                "[!] Diff vs. prior round is NOT cosmetic-only. Run the "
                "classifier directly to see per-file reasons:",
                fg="red",
            )
            verbose = subprocess.run(
                [sys.executable, str(script_path), prior_tree_hash],
                capture_output=True,
                text=True,
                check=False,
            )
            click.echo(verbose.stdout)
            click.secho(
                "Fresh CONFIRMS required: file a new round via 'audit submit-round'.",
                fg="yellow",
            )
            return

        # Cosmetic-only. Carry prior round's CONFIRMS forward.
        prior_confirms = [
            f
            for f in list_findings(round_id=prior_round_id, limit=100)
            if "CONFIRMS" in (f.title or "") or "confirms" in (f.description or "").lower()
        ]
        if not prior_confirms:
            click.secho(
                f"[!] Prior round '{prior_round_id}' has no CONFIRMS findings "
                "to carry forward; fresh CONFIRMS required.",
                fg="red",
            )
            return

        # Derive new tree-hash from current staged state.
        write_tree = subprocess.run(
            ["git", "write-tree"], capture_output=True, text=True, check=False
        )
        new_tree_hash = (write_tree.stdout or "").strip()

        focus_text = (
            focus
            or f"Cosmetic-rebind of {prior_round_id} (whitespace/format/unused-import "
            f"only; classifier-verified). tree-hash: {new_tree_hash}"
        )

        try:
            new_round_id = submit_round(
                actor="aether",
                focus=focus_text,
                expert_count=0,
                notes=f"Auto-rebind from {prior_round_id}. Classifier confirmed "
                "diff is cosmetic-only per positive-list (whitespace + import-"
                "reorder + unused-import-removal).",
            )
            click.secho(f"[+] Rebind round created: {new_round_id}", fg="cyan")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")
            return

        # Auto-file carry-forward findings for each prior CONFIRMS actor.
        carried_actors: set[str] = set()
        for prior_finding in prior_confirms:
            actor = prior_finding.actor
            if actor in carried_actors:
                continue
            carried_actors.add(actor)
            try:
                fid = submit_finding(
                    round_id=new_round_id,
                    actor=actor,
                    severity="LOW",
                    category="INTEGRITY",
                    title=f"CONFIRMS carried forward from {prior_round_id} (cosmetic-rebind)",
                    description=(
                        f"Substantive review on {prior_round_id} (finding "
                        f"{prior_finding.finding_id}) carries forward to this "
                        f"rebind. Diff vs. prior bound state is cosmetic-only "
                        f"per the cosmetic_diff_check classifier (positive list: "
                        f"whitespace, import-reorder, unused-import-removal). "
                        f"No new substantive content requires fresh review."
                    ),
                    recommendation="",
                    tags=["cosmetic-rebind", "carry-forward", prior_round_id],
                )
                click.secho(
                    f"[+] Carried forward CONFIRMS from {actor}: {fid}",
                    fg="green",
                )
            except ValueError as e:
                click.secho(f"[!] {e}", fg="red")

        click.secho(
            f"\nNow use 'External-Review: {new_round_id}' in your commit trailer.",
            fg="cyan",
        )

    @audit_group.command("list")
    @click.option("--round", "round_id", default=None, help="Filter by round")
    @click.option("--status", default=None, help="Filter by status")
    @click.option("--severity", default=None, help="Filter by severity")
    @click.option("--limit", default=20, type=int)
    def audit_list_cmd(
        round_id: str | None,
        status: str | None,
        severity: str | None,
        limit: int,
    ) -> None:
        """List audit findings."""
        from divineos.core.watchmen.store import list_findings, list_rounds

        if not round_id and not status and not severity:
            # Show rounds overview first
            rounds = list_rounds(limit=10)
            if rounds:
                click.secho("\n=== Audit Rounds ===\n", fg="cyan", bold=True)
                for r in rounds:
                    click.echo(
                        f"  {r.round_id}  {r.actor:<10} {r.finding_count} findings  {r.focus}"
                    )
                click.echo()

        findings = list_findings(
            round_id=round_id,
            status=status,
            severity=severity,
            limit=limit,
        )
        if not findings:
            click.secho("[~] No findings found.", fg="bright_black")
            return

        click.secho(f"\n=== Findings ({len(findings)}) ===\n", fg="cyan", bold=True)
        for f in findings:
            sev_color = _SEVERITY_COLORS.get(f.severity.value, "white")
            status_color = _STATUS_COLORS.get(f.status.value, "white")
            # Full finding_id (17 chars): prior [:16] truncated to 16 and
            # made copy-paste into `audit show` fail silently. Discovered
            # 2026-04-17 during Grok findings cleanup.
            click.echo(
                f"  {f.finding_id}  "
                + click.style(f"{f.severity.value:<8}", fg=sev_color)
                + click.style(f" {f.status.value:<12}", fg=status_color)
                + f" {f.title}"
            )

    @audit_group.command("show")
    @click.argument("finding_id")
    def audit_show_cmd(finding_id: str) -> None:
        """Show details of a specific finding."""
        from divineos.core.watchmen.store import get_finding

        finding = get_finding(finding_id)
        if not finding:
            click.secho(f"[!] Finding '{finding_id}' not found.", fg="red")
            return

        sev_color = _SEVERITY_COLORS.get(finding.severity.value, "white")
        click.secho(f"\n{finding.title}", fg="white", bold=True)
        click.echo(f"  ID:       {finding.finding_id}")
        click.echo(f"  Round:    {finding.round_id}")
        click.echo(f"  Actor:    {finding.actor}")
        click.echo("  Severity: " + click.style(finding.severity.value, fg=sev_color))
        click.echo(f"  Category: {finding.category.value}")
        click.echo(f"  Status:   {finding.status.value}")
        _safe_echo(f"\n  {finding.description}")
        if finding.recommendation:
            click.secho(f"\n  Recommendation: {finding.recommendation}", fg="green")
        if finding.routed_to:
            click.echo(f"  Routed to: {finding.routed_to}")
        if finding.resolution_notes:
            click.echo(f"  Resolution: {finding.resolution_notes}")
        click.echo()

    @audit_group.command("resolve")
    @click.argument("finding_id")
    @click.option(
        "--status",
        type=click.Choice(
            ["RESOLVED", "WONT_FIX", "DUPLICATE", "IN_PROGRESS"], case_sensitive=False
        ),
        default="RESOLVED",
    )
    @click.option("--notes", default="", help="Resolution notes")
    def audit_resolve_cmd(finding_id: str, status: str, notes: str) -> None:
        """Resolve or update a finding's status."""
        from divineos.core.watchmen.store import resolve_finding

        try:
            if resolve_finding(finding_id, status, notes):
                click.secho(f"[+] Finding {finding_id} -> {status.upper()}", fg="green")
            else:
                click.secho(f"[!] Finding '{finding_id}' not found.", fg="red")
        except ValueError as e:
            click.secho(f"[!] {e}", fg="red")

    @audit_group.command("route")
    @click.argument("round_id")
    def audit_route_cmd(round_id: str) -> None:
        """Route all open findings in a round to knowledge/claims/lessons."""
        from divineos.core.watchmen.router import route_round

        results = route_round(round_id)
        if not results:
            click.secho("[~] No findings to route.", fg="bright_black")
            return

        for r in results:
            action = r["action"]
            title = r.get("title", "")[:50]
            if action == "skipped":
                click.secho(f"  [-] {title}: {r['reason']}", fg="bright_black")
            elif action == "claim":
                click.secho(f"  [C] {title} -> claim {r['id'][:12]}", fg="yellow")
            elif action == "knowledge":
                click.secho(f"  [K] {title} -> knowledge {r['id'][:12]}", fg="cyan")
            elif action == "lesson":
                click.secho(f"  [L] {title} -> lesson '{r['id']}'", fg="green")

        routed = sum(1 for r in results if r["action"] != "skipped")
        click.secho(f"\n  Routed {routed}/{len(results)} findings.", fg="cyan")

    @audit_group.command("summary")
    def audit_summary_cmd() -> None:
        """Show audit statistics and unresolved findings."""
        from divineos.core.watchmen.summary import (
            get_watchmen_stats,
            unresolved_findings,
            watchmen_loop_status,
        )

        stats = get_watchmen_stats()
        if stats["total_findings"] == 0:
            click.secho("[~] No audit data yet.", fg="bright_black")
            click.echo(watchmen_loop_status())
            return

        click.secho("\n=== Watchmen Summary ===\n", fg="cyan", bold=True)
        click.echo(watchmen_loop_status())
        click.echo("")
        click.echo(f"  Rounds:   {stats['total_rounds']}")
        click.echo(f"  Findings: {stats['total_findings']}")
        click.echo(f"  Open:     {stats['open_count']}")
        click.echo(f"  Resolved: {stats['resolved_count']}")

        if stats["by_severity"]:
            click.echo("\n  By severity:")
            for sev in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"):
                count = stats["by_severity"].get(sev, 0)
                if count:
                    color = _SEVERITY_COLORS.get(sev, "white")
                    click.echo(f"    {click.style(sev, fg=color)}: {count}")

        unresolved = unresolved_findings(limit=5)
        if unresolved:
            click.secho("\n  Top unresolved:", fg="yellow")
            for f in unresolved:
                sev_color = _SEVERITY_COLORS.get(f["severity"], "white")
                click.echo(f"    {click.style(f['severity'], fg=sev_color)} {f['title']}")
        click.echo()

    @audit_group.command("predict")
    @click.option("--round", "round_id", required=True, help="Audit round ID")
    @click.option(
        "--topics",
        required=True,
        help="Comma-separated topics I'm self-predicting will be in the audit",
    )
    def audit_predict_cmd(round_id: str, topics: str) -> None:
        """Record self-audit prediction BEFORE the audit lands.

        From omni-mantra Pillar I, 1.3 — The Great Mystery: what the
        agent doesn't know it doesn't know. Recording predictions
        before the audit lets `audit surprises` compute the unknown-
        unknown rate later — patterns the auditor caught that I
        couldn't even mark as a possibility.

        Goodhart-protected: closing the surprise-rate requires
        expanding attention surface, not better-predicting the
        auditor (sycophancy-toward-expected-audit).
        """
        from divineos.core.operating_loop.unknown_unknown_surface import (
            record_self_audit_prediction,
        )

        topic_list = [t.strip() for t in topics.split(",") if t.strip()]
        if not topic_list:
            click.secho("[-] No topics provided.", fg="yellow")
            return
        ev_id = record_self_audit_prediction(round_id, topic_list)
        if ev_id.startswith("error:"):
            click.secho(f"[-] Failed to record: {ev_id}", fg="red")
            return
        click.secho(
            f"[+] Recorded {len(topic_list)} predicted topics for round {round_id}",
            fg="green",
        )
        for t in topic_list:
            click.secho(f"    - {t}", fg="bright_black")

    @audit_group.command("surprises")
    @click.option("--round", "round_id", required=True, help="Audit round ID")
    def audit_surprises_cmd(round_id: str) -> None:
        """Show audit findings the substrate-occupant didn't predict.

        Compares the recorded `audit predict` topics for the round
        against the actual findings filed; surfaces the surprise-
        class catches. These are the maturity signal — tighter
        substrate shows fewer over time.
        """
        from divineos.core.operating_loop.unknown_unknown_surface import (
            _load_predictions_for_round,
            surprises_in_round,
        )

        preds = _load_predictions_for_round(round_id)
        if not preds:
            click.secho(
                f"[~] No predictions recorded for round {round_id}. "
                f"Use `divineos audit predict` before the audit.",
                fg="yellow",
            )
            return
        surprises = surprises_in_round(round_id, preds)
        click.secho(
            f"\n=== Round {round_id}: predicted vs caught ===\n",
            fg="cyan",
            bold=True,
        )
        click.echo(f"  Predicted topics ({len(preds)}):")
        for t in preds:
            click.secho(f"    - {t}", fg="bright_black")
        click.echo()
        if not surprises:
            click.secho(
                "  No surprises — every finding matched a predicted topic.",
                fg="green",
            )
            return
        click.secho(
            f"  Unknown-unknowns ({len(surprises)}) — findings outside my attention surface:",
            fg="yellow",
        )
        for u in surprises:
            click.echo(f"    [{u.finding_id[:12]}] {u.title}")

    @audit_group.command("unknown-unknown-rate")
    @click.option(
        "--limit",
        default=20,
        type=int,
        help="Max recent rounds (with recorded predictions) to examine",
    )
    def audit_uu_rate_cmd(limit: int) -> None:
        """Rolling proportion of audit findings that were unpredicted.

        Trend signal: tighter substrate -> rate trends down. Drifting
        substrate -> rate trends up. Rounds without recorded
        predictions are skipped.
        """
        from divineos.core.operating_loop.unknown_unknown_surface import (
            unknown_unknown_rate,
        )

        stats = unknown_unknown_rate(recent_round_limit=limit)
        click.secho("\n=== Unknown-Unknown Rate ===\n", fg="cyan", bold=True)
        click.echo(f"  Rounds examined:  {stats['rounds_examined']}")
        click.echo(f"  Total findings:   {stats['total_findings']}")
        click.echo(f"  Surprises:        {stats['surprise_count']}")
        rate_pct = stats["rate"] * 100
        color = "green" if rate_pct < 20 else ("yellow" if rate_pct < 40 else "red")
        click.secho(f"  Rate:             {rate_pct:.1f}%", fg=color)
        if stats["rounds_examined"] == 0:
            click.secho(
                "\n  No rounds with recorded predictions yet. Use "
                "`divineos audit predict` before audits to start the metric.",
                fg="bright_black",
            )

    @audit_group.command("compliance")
    @click.option(
        "--days",
        default=7,
        type=int,
        help="Window in days for distribution audit (default 7).",
    )
    @click.option(
        "--file-findings",
        is_flag=True,
        help=(
            "When anomalies are detected, auto-file them as Watchmen findings "
            "under a fresh audit round. Default is read-only reporting."
        ),
    )
    def audit_compliance_cmd(days: int, file_findings: bool) -> None:
        """Substantive distribution audit of the compliance log.

        Reads rudder-ack compass observations + recent decisions and flags
        distributional patterns that indicate performative-structure
        (structured-but-empty entries). Different primitive from the
        moment-of-action gates: this reads the log AFTER the fact and
        detects theater by its statistical fingerprint.

        Pre-reg: prereg-f5a961f0040e (21-day review).
        """
        from divineos.core.compliance_audit import detect_anomalies, format_report

        window = days * 86400
        click.echo(format_report(window_seconds=window))

        if not file_findings:
            return

        anomalies = detect_anomalies(window_seconds=window)
        if not anomalies:
            click.secho("  [~] No anomalies detected; nothing to file.", fg="bright_black")
            return

        from divineos.core.watchmen.store import submit_finding, submit_round
        from divineos.core.watchmen.types import FindingCategory, Severity

        # Use the "auditor" actor — it's in EXTERNAL_ACTORS and is the
        # generic slot for automated auditing processes. Keeps the external-
        # actor validation honest (compliance_audit isn't a registered actor
        # name; it's a module, so using it directly would feel like
        # self-audit smuggling).
        round_id = submit_round(
            actor="auditor",
            focus=f"compliance distribution audit ({days}d)",
            notes="Auto-generated by `divineos audit compliance --file-findings`",
        )
        severity_value_map = {
            "HIGH": Severity.HIGH.value,
            "MEDIUM": Severity.MEDIUM.value,
            "LOW": Severity.LOW.value,
        }
        for a in anomalies:
            submit_finding(
                round_id=round_id,
                title=f"[compliance] {a.name}",
                actor="auditor",
                severity=severity_value_map.get(a.severity.value, Severity.MEDIUM.value),
                category=FindingCategory.BEHAVIOR.value,
                description=f"{a.observation}\n\n{a.recommendation}".strip(),
            )
        click.secho(
            f"\n  [+] Filed {len(anomalies)} Watchmen finding(s) under round {round_id}.",
            fg="green",
        )

    # Item 8 PR-2: session-cleanliness tagging commands. Tags sessions
    # that passed an audit round without drift findings as "externally-
    # audited-clean" so Item 8 detectors can calibrate their baselines
    # against a trusted reference set (brief v2.1 §4).

    @audit_group.command("tag-clean")
    @click.argument("session_id")
    @click.option(
        "--round",
        "round_id",
        required=True,
        help="audit_round that tagged this session clean (must have no HIGH or unresolved MEDIUM findings)",
    )
    @click.option("--notes", default="", help="Optional notes about the tag")
    def tag_clean_cmd(session_id: str, round_id: str, notes: str) -> None:
        """Tag a session as externally-audited-clean.

        The referenced audit round must have concluded clean — no HIGH
        findings and no unresolved MEDIUM findings. This is the write-
        time sanity check per claim 48371c4d (blocks the "round tags its
        own dirty session clean" attack).
        """
        from divineos.core.watchmen.cleanliness import tag_session_clean

        try:
            tag_session_clean(session_id=session_id, round_id=round_id, notes=notes)
            click.secho(
                f"  [+] Session {session_id} tagged clean by round {round_id}.",
                fg="green",
            )
        except ValueError as e:
            click.secho(f"  [!] {e}", fg="red")

    @audit_group.command("untag-clean")
    @click.argument("session_id")
    @click.option(
        "--reason",
        required=True,
        help="Why this tag is being removed (required for the audit trail)",
    )
    def untag_clean_cmd(session_id: str, reason: str) -> None:
        """Remove a clean-tag. Required reason writes an audit-trail event."""
        from divineos.core.watchmen.cleanliness import untag_session_clean

        try:
            removed = untag_session_clean(session_id=session_id, reason=reason)
        except ValueError as e:
            click.secho(f"  [!] {e}", fg="red")
            return
        if removed:
            click.secho(f"  [+] Untagged {session_id}. Reason logged to ledger.", fg="yellow")
        else:
            click.secho(f"  [~] {session_id} was not tagged clean; nothing to untag.")

    @audit_group.command("list-clean")
    @click.option(
        "--days",
        default=0,
        type=int,
        help="Only sessions tagged in the last N days. 0 = all (default).",
    )
    @click.option("--limit", default=50, type=int, help="Max rows to show (default 50).")
    def list_clean_cmd(days: int, limit: int) -> None:
        """List externally-audited-clean sessions."""
        import time as _t

        from divineos.core.watchmen.cleanliness import (
            count_clean_sessions,
            list_clean_sessions,
        )

        since = _t.time() - days * 86400 if days > 0 else None
        sessions = list_clean_sessions(since=since, limit=limit)
        total = count_clean_sessions(since=since)
        window_str = f"in last {days}d" if days > 0 else "(all)"
        click.secho(
            f"  Clean-tagged sessions {window_str}: {total} total (showing {len(sessions)}):",
            bold=True,
        )
        for s in sessions:
            ago_hours = (_t.time() - s["tagged_at"]) / 3600
            click.echo(
                f"    {s['session_id'][:20]:22s}  tagged {ago_hours:.1f}h ago "
                f"by {s['tagging_round_id'][:16]}"
            )
            focus = s.get("round_focus")
            if focus:
                click.echo(f"      round: {focus[:80]}")
            if s["notes"]:
                click.echo(f"      note: {s['notes']}")
