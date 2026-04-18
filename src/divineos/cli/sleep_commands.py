"""CLI commands for Sleep — offline consolidation between sessions."""

import sqlite3

import click

from divineos.cli._helpers import _safe_echo


def _preview_sleep_phases(skip_maintenance: bool = False) -> None:
    """Preview what each sleep phase would find without modifying data.

    Previews call the same underlying helpers as actual phase execution
    wherever possible, so the numbers reported here match what the real
    sleep cycle will produce. Aria Round 3b principle applied to code:
    pointing at the real logic beats reimplementing it — reimplementations
    drift when the logic changes. (Earlier versions of this preview
    queried ad-hoc SQL and diverged badly: predicted 30 promotions when
    actual produced 0, because the preview skipped the validity gate
    that actual runs. 2026-04-17 fix.)
    """
    # Phase 1: Consolidation preview
    click.echo("  Phase 1: Knowledge Consolidation")
    try:
        from divineos.core.constants import (
            CONFIDENCE_ACTIVE_MEMORY_FLOOR,
            MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION,
            MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE,
            MATURITY_TESTED_TO_CONFIRMED_CORROBORATION,
            SECONDS_PER_DAY,
        )
        from divineos.core.knowledge import _get_connection
        from divineos.core.knowledge.crud import get_knowledge
        from divineos.core.knowledge_maintenance import preview_maturity_promotions

        # Use the shared helper — same two gates actual execution uses
        # (check_promotion + validity gate). No ad-hoc SQL that might
        # disagree with the real phase logic.
        entries = get_knowledge(limit=10000, include_superseded=False)
        promotable = preview_maturity_promotions(entries)

        total_promotable = sum(promotable.values())
        if total_promotable:
            for transition, count in promotable.items():
                if count:
                    click.echo(f"    Would promote {count} entries to {transition}")
        else:
            click.echo(f"    {len(entries)} entries scanned, no promotions ready")
            # Show why — these thresholds come from the same constants
            # the shared helper uses
            hyp = [e for e in entries if e.get("maturity") == "HYPOTHESIS"]
            tested = [e for e in entries if e.get("maturity") == "TESTED"]
            if hyp:
                max_corrob = max(e.get("corroboration_count", 0) for e in hyp)
                click.echo(
                    f"    HYPOTHESIS: {len(hyp)} entries, max corroboration={max_corrob} "
                    f"(need {MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION})"
                )
            if tested:
                max_corrob = max(e.get("corroboration_count", 0) for e in tested)
                click.echo(
                    f"    TESTED: {len(tested)} entries, max corroboration={max_corrob} "
                    f"(need {MATURITY_TESTED_TO_CONFIRMED_CORROBORATION} "
                    f"+ conf>={MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE})"
                )
            click.echo("    Note: both corroboration AND warrant-based validity gate must pass")
    except (sqlite3.OperationalError, ImportError, OSError) as e:
        click.echo(f"    [error: {e}]")

    # Phase 2: Pruning preview
    #
    # Actual run calls health_check() and run_knowledge_hygiene() which
    # have side effects (supersessions, confidence adjustments) — so a
    # true dry-run would require those functions to accept a dry_run
    # flag, which is a bigger refactor than this bug warranted.
    # Honest compromise: report CANDIDATES (count of entries matching
    # the simple gating criteria) and name clearly that not all
    # candidates get pruned. Avoids the prior "would prune 25, actually
    # pruned 3" mismatch by changing the language.
    click.echo("  Phase 2: Pruning (candidates, not all will be pruned)")
    try:
        conn = _get_connection()
        try:
            orphans = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL AND access_count = 0 "
                "AND created_at < (strftime('%s','now') - ?)",
                (SECONDS_PER_DAY,),
            ).fetchone()[0]
            stale = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL AND confidence < ?",
                (CONFIDENCE_ACTIVE_MEMORY_FLOOR,),
            ).fetchone()[0]
        finally:
            conn.close()
        click.echo(f"    Orphan candidates (never accessed, >24h old): {orphans}")
        click.echo(f"    Low-confidence candidates (<{CONFIDENCE_ACTIVE_MEMORY_FLOOR}): {stale}")
        click.echo(
            "    Note: actual pruning applies additional filters (access pattern, "
            "contradiction history, noise detection) — a fraction of candidates get pruned"
        )
    except (sqlite3.OperationalError, ImportError, OSError) as e:
        click.echo(f"    [error: {e}]")

    # Phase 3: Affect preview
    #
    # Uses the SAME affect source as actual execution: get_affect_history
    # from the affect module (backed by affect_log table). The prior
    # preview queried system_events for AFFECT_STATE events, which was
    # a legacy path — the table either lacked created_at (error) or
    # held no actual affect data (silent zero). 2026-04-17 fix: point at
    # the same source of truth as _phase_affect.
    click.echo("  Phase 3: Affect Recalibration")
    try:
        import time as _time

        from divineos.core.affect import get_affect_history, init_affect_log
        from divineos.core.sleep import _AFFECT_DECAY_HOURS

        init_affect_log()
        history = get_affect_history(limit=200)
        cutoff = _time.time() - (_AFFECT_DECAY_HOURS * 3600)
        eligible = sum(1 for e in history if e.get("created_at", 0) < cutoff)
        click.echo(
            f"    Total affect entries: {len(history)}, eligible for decay: {eligible} "
            f"(older than {_AFFECT_DECAY_HOURS}h)"
        )
    except (sqlite3.OperationalError, ImportError, OSError) as e:
        click.echo(f"    [error: {e}]")

    # Phase 4
    if not skip_maintenance:
        click.echo("  Phase 4: Maintenance -- VACUUM, log cleanup")

    # Phase 5: Recombination preview
    click.echo("  Phase 5: Creative Recombination")
    try:
        conn = _get_connection()
        try:
            active_count = conn.execute(
                "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
            ).fetchone()[0]
            existing_edges = conn.execute(
                "SELECT COUNT(*) FROM knowledge_edges WHERE status = 'ACTIVE'"
            ).fetchone()[0]
        finally:
            conn.close()
        click.echo(f"    Active entries to scan: {active_count}")
        click.echo(f"    Existing edges: {existing_edges}")
    except (sqlite3.OperationalError, ImportError, OSError) as e:
        click.echo(f"    [error: {e}]")

    # Phase 6
    click.echo("  Phase 6: Curiosity Generation")
    click.echo("")
    click.echo("  No data will be modified in dry-run mode.")


def register(cli: click.Group) -> None:
    """Register sleep commands."""

    @cli.command("sleep")
    @click.option("--dry-run", is_flag=True, help="Show what would happen without modifying data.")
    @click.option("--skip-maintenance", is_flag=True, help="Skip VACUUM/log/cache phase.")
    @click.option("--phase", type=str, default=None, help="Run only a specific phase.")
    def sleep_cmd(dry_run: bool, skip_maintenance: bool, phase: str | None) -> None:
        """Offline consolidation — process accumulated experience.

        Runs six phases: knowledge consolidation, pruning, affect recalibration,
        maintenance, creative recombination, then prints a dream report.
        """
        from divineos.core.sleep import (
            DreamReport,
            _phase_affect,
            _phase_consolidation,
            _phase_curiosity,
            _phase_maintenance,
            _phase_pruning,
            _phase_recombination,
            run_sleep,
        )

        if dry_run:
            click.secho("Sleep dry-run -- previewing what each phase would find:\n", fg="cyan")
            _preview_sleep_phases(skip_maintenance)
            return

        # Single phase mode
        if phase:
            phase_map = {
                "consolidation": ("Phase 1: Knowledge Consolidation", _phase_consolidation),
                "pruning": ("Phase 2: Pruning", _phase_pruning),
                "affect": ("Phase 3: Affect Recalibration", _phase_affect),
                "maintenance": ("Phase 4: Maintenance", _phase_maintenance),
                "recombination": ("Phase 5: Creative Recombination", _phase_recombination),
                "curiosity": ("Phase 6: Curiosity Generation", _phase_curiosity),
            }
            if phase not in phase_map:
                click.secho(
                    f"Unknown phase: {phase}. Choose from: {', '.join(phase_map.keys())}",
                    fg="red",
                )
                return
            label, phase_fn = phase_map[phase]
            click.secho(f"Running {label}...\n", fg="cyan")
            report = DreamReport()
            phase_fn(report)
            _safe_echo(report.summary())
            return

        # Full sleep cycle
        click.secho("Going to sleep...\n", fg="cyan")
        click.echo("  Phase 1: Knowledge Consolidation...")
        click.echo("  Phase 2: Pruning...")
        click.echo("  Phase 3: Affect Recalibration...")
        if not skip_maintenance:
            click.echo("  Phase 4: Maintenance...")
        click.echo("  Phase 5: Creative Recombination...")
        click.echo("  Phase 6: Curiosity Generation...")
        click.echo("")

        report = run_sleep(skip_maintenance=skip_maintenance)

        _safe_echo(report.summary())

        # Store dream report as a ledger event
        try:
            from divineos.event.event_emission import emit_event

            emit_event(
                "SLEEP_CYCLE",
                {
                    "duration_seconds": report.duration_seconds,
                    "entries_scanned": report.entries_scanned,
                    "total_promoted": report.total_promoted,
                    "affect_decayed": report.affect_decayed,
                    "connections_found": report.connections_found,
                    "phase_errors": list(report.phase_errors.keys()),
                },
                actor="system",
                validate=False,
            )
        except (ImportError, OSError, sqlite3.OperationalError, KeyError, TypeError, ValueError):
            pass  # Don't fail the sleep command over event logging
