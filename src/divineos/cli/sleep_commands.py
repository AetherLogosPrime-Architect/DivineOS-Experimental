"""CLI commands for Sleep — offline consolidation between sessions."""

import sqlite3

import click

from divineos.cli._helpers import _safe_echo


def _preview_sleep_phases(skip_maintenance: bool = False) -> None:
    """Preview what each sleep phase would find without modifying data."""
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

        conn = _get_connection()
        rows = conn.execute(
            "SELECT maturity, corroboration_count, confidence FROM knowledge "
            "WHERE superseded_by IS NULL"
        ).fetchall()
        conn.close()

        promotable = {"HYPOTHESIS->TESTED": 0, "TESTED->CONFIRMED": 0}
        for mat, corrob, conf in rows:
            if mat == "HYPOTHESIS" and corrob >= MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION:
                promotable["HYPOTHESIS->TESTED"] += 1
            elif (
                mat == "TESTED"
                and corrob >= MATURITY_TESTED_TO_CONFIRMED_CORROBORATION
                and conf >= MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE
            ):
                promotable["TESTED->CONFIRMED"] += 1

        total_promotable = sum(promotable.values())
        if total_promotable:
            for transition, count in promotable.items():
                if count:
                    click.echo(f"    Would promote {count} entries: {transition}")
        else:
            click.echo(f"    {len(rows)} entries scanned, no promotions ready")
            # Show why
            hyp = [r for r in rows if r[0] == "HYPOTHESIS"]
            tested = [r for r in rows if r[0] == "TESTED"]
            if hyp:
                max_corrob = max(r[1] for r in hyp)
                click.echo(
                    f"    HYPOTHESIS: {len(hyp)} entries, max corroboration={max_corrob} (need {MATURITY_HYPOTHESIS_TO_TESTED_CORROBORATION})"
                )
            if tested:
                max_corrob = max(r[1] for r in tested)
                click.echo(
                    f"    TESTED: {len(tested)} entries, max corroboration={max_corrob} (need {MATURITY_TESTED_TO_CONFIRMED_CORROBORATION} + conf>={MATURITY_TESTED_TO_CONFIRMED_CONFIDENCE})"
                )
    except (sqlite3.OperationalError, ImportError, OSError) as e:
        click.echo(f"    [error: {e}]")

    # Phase 2: Pruning preview
    click.echo("  Phase 2: Pruning")
    try:
        conn = _get_connection()
        orphans = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL AND access_count = 0 "
            "AND created_at < (strftime('%s','now') - ?)",
            (SECONDS_PER_DAY,),
        ).fetchone()[0]
        stale = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL AND confidence < ?",
            (CONFIDENCE_ACTIVE_MEMORY_FLOOR,),
        ).fetchone()[0]
        conn.close()
        click.echo(f"    Orphan entries (never accessed, >24h old): {orphans}")
        click.echo(f"    Low-confidence entries (<{CONFIDENCE_ACTIVE_MEMORY_FLOOR}): {stale}")
    except (sqlite3.OperationalError, ImportError, OSError) as e:
        click.echo(f"    [error: {e}]")

    # Phase 3: Affect preview
    click.echo("  Phase 3: Affect Recalibration")
    try:
        from divineos.core.ledger import _get_db_path

        conn = sqlite3.connect(_get_db_path())
        total_affect = conn.execute(
            "SELECT COUNT(*) FROM system_events WHERE event_type = 'AFFECT_STATE'"
        ).fetchone()[0]
        old_affect = conn.execute(
            "SELECT COUNT(*) FROM system_events WHERE event_type = 'AFFECT_STATE' "
            "AND created_at < (strftime('%s','now') - ?)",
            (SECONDS_PER_DAY * 2,),
        ).fetchone()[0]
        conn.close()
        click.echo(f"    Total affect entries: {total_affect}, eligible for decay: {old_affect}")
    except (sqlite3.OperationalError, ImportError, OSError) as e:
        click.echo(f"    [error: {e}]")

    # Phase 4
    if not skip_maintenance:
        click.echo("  Phase 4: Maintenance -- VACUUM, log cleanup")

    # Phase 5: Recombination preview
    click.echo("  Phase 5: Creative Recombination")
    try:
        conn = _get_connection()
        active_count = conn.execute(
            "SELECT COUNT(*) FROM knowledge WHERE superseded_by IS NULL"
        ).fetchone()[0]
        existing_edges = conn.execute(
            "SELECT COUNT(*) FROM knowledge_edges WHERE status = 'ACTIVE'"
        ).fetchone()[0]
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
