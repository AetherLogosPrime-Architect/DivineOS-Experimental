"""CLI commands for Sleep — offline consolidation between sessions."""

import sqlite3

import click


def register(cli: click.Group) -> None:
    """Register sleep commands."""

    @cli.command("sleep")
    @click.option("--dry-run", is_flag=True, help="Show what would happen without modifying data.")
    @click.option(
        "--skip-maintenance", is_flag=True, help="Skip VACUUM/log/cache phase."
    )
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
            _phase_maintenance,
            _phase_pruning,
            _phase_recombination,
            run_sleep,
        )

        if dry_run:
            click.secho("Sleep dry-run — showing what would happen:\n", fg="cyan")
            click.echo("  Phase 1: Knowledge Consolidation — full maturity lifecycle pass")
            click.echo("  Phase 2: Pruning — health check + hygiene + contradiction scan")
            click.echo("  Phase 3: Affect Recalibration — decay old emotions, compute baseline")
            if not skip_maintenance:
                click.echo("  Phase 4: Maintenance — VACUUM, log rotation, cache pruning")
            click.echo("  Phase 5: Creative Recombination — cross-knowledge similarity scan")
            click.echo("\n  No data will be modified in dry-run mode.")
            return

        # Single phase mode
        if phase:
            phase_map = {
                "consolidation": ("Phase 1: Knowledge Consolidation", _phase_consolidation),
                "pruning": ("Phase 2: Pruning", _phase_pruning),
                "affect": ("Phase 3: Affect Recalibration", _phase_affect),
                "maintenance": ("Phase 4: Maintenance", _phase_maintenance),
                "recombination": ("Phase 5: Creative Recombination", _phase_recombination),
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
            click.echo(report.summary())
            return

        # Full sleep cycle
        click.secho("Going to sleep...\n", fg="cyan")
        click.echo("  Phase 1: Knowledge Consolidation...")
        click.echo("  Phase 2: Pruning...")
        click.echo("  Phase 3: Affect Recalibration...")
        if not skip_maintenance:
            click.echo("  Phase 4: Maintenance...")
        click.echo("  Phase 5: Creative Recombination...")
        click.echo("")

        report = run_sleep(skip_maintenance=skip_maintenance)

        click.echo(report.summary())

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
