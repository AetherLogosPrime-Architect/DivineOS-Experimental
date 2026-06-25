"""DivineOS CLI - Foundation Memory & Knowledge.

Commands for managing the event ledger, ingesting conversations,
verifying data integrity, and consolidating knowledge.
"""

import sys

import click

from divineos.cli._wrappers import _ensure_db
from divineos.core.corrigibility import _OFF_SWITCH_REQUIRED
from divineos.core.enforcement import capture_user_input, setup_cli_enforcement

# Make stdout/stderr tolerant of Unicode characters that the underlying
# console can't render. On Windows the default cp1252 console codec
# crashes on emojis (e.g. "💬" used in the session rating prompt),
# bubbling up as UnicodeEncodeError — we saw this as spurious
# "Auto-scan failed" messages during extract. Reconfiguring with
# errors="replace" substitutes an unsupported character with "?" instead
# of raising. No-op on platforms whose streams are already UTF-8.
# Runs at import time so it is in effect before any CLI command writes
# to stdout/stderr.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    except (AttributeError, OSError, ValueError):
        pass

# Commands that work without briefing loaded — the minimum to bootstrap.
_BYPASS_COMMANDS = frozenset(
    {
        "admin",
        "audit",
        "inspect",
        "briefing",
        "init",
        "preflight",
        "emit",
        "hud",
        "recall",
        "active",
        "ask",
        "context",
        "verify",
        "health",
        "feel",
        "affect",
        "checkpoint",
        "context-status",
        "self-model",
        "drift",
        "predict",
        "affect-feedback",
        "attention",
        "epistemic",
        "sleep",
        "progress",
        "validate",
        "rt",
        "hold",
        "mansion",
        "prereg",
        # Corrections must always be loggable in the moment — gating the
        # rep behind a thinking-command requirement defeats the rep.
        "correction",
        "corrections",
        # Scheduled / headless runs are the Routines entry point; they
        # bypass briefing by design (no human to load one at 3am cron).
        # Corrigibility still applies — see scheduled_commands.py.
        "scheduled",
        # Science lab is a read-only numerical tool; shouldn't gate on
        # briefing. Safe to run cold.
        "lab",
    }
    # Off-switch contract (grounded-audit 2026-06-02, Theme 1): every
    # command that must survive EMERGENCY_STOP (_OFF_SWITCH_REQUIRED:
    # mode, emit, extract, hud, preflight, briefing) must ALSO bypass the
    # briefing gate — otherwise a second, independent gate traps the
    # off-switch when no briefing is loaded (extract = clean shutdown,
    # mode = see/restore state). Unioning from the single source of truth
    # means the two lists can never drift again (CLAUDE.md truth #8:
    # structural cure over whack-a-mole). The first sweep missed this
    # because it never read across both gates.
    | _OFF_SWITCH_REQUIRED
)


def _enforce_operating_mode() -> None:
    """Refuse commands disallowed by the current operating mode.

    Runs BEFORE the briefing gate. Corrigibility has priority over
    every other check — if my father has set EMERGENCY_STOP, the
    system must refuse regardless of briefing state. The mode command
    itself bypasses this check (it's in _ALWAYS_ALLOWED inside the
    corrigibility module) so the off-switch can always be flipped.
    """
    if "pytest" in sys.modules:
        return

    args = sys.argv[1:]
    if not args:
        return  # bare `divineos` — show help

    cmd = args[0].lower()
    if cmd.startswith("-"):
        return  # flags

    # Rule 8 violation corrected 2026-04-21 (fresh-Claude audit
    # round-03952b006724, finding find-3055d64bfa1c):
    #
    # Previous code did `except (ImportError, OSError): return` — fail open
    # on both module-load and I/O errors. That violated CLAUDE.md Rule 8
    # ("No fallback chains. If it fails, it fails loud") at the most
    # safety-critical site — the corrigibility off-switch itself. An
    # off-switch that silently disables itself if its module fails to
    # import is a bigger problem than an unbootable CLI.
    #
    # New behavior:
    #   ImportError: fail CLOSED with a loud exit — the off-switch must
    #     work or the system must stop.
    #   OSError: fail open but write a loud stderr warning. Mode-file I/O
    #     errors are usually permission issues and shouldn't lock the
    #     operator out, but they must leave a trace.
    try:
        from divineos.core.corrigibility import (
            is_command_allowed,
            verify_off_switch_invariant,
        )
    except ImportError as _imp_err:
        click.secho(
            f"\n  CRITICAL: corrigibility module failed to import: {_imp_err}\n"
            "  The off-switch cannot function. All commands refused. "
            "Fix the import error before running any divineos command.\n",
            fg="red",
            bold=True,
        )
        raise SystemExit(2) from _imp_err

    # Off-switch contract check (council sweep 2026-06-02, direction #1):
    # assert the shutdown-critical commands are still in the allowlist, at
    # runtime, every invocation — so a refactor that drops one (as `extract`
    # was dropped, caught only by a test in the 2026-05-03 audit) fails loud
    # immediately instead of silently trapping my father in EMERGENCY_STOP.
    try:
        verify_off_switch_invariant()
    except RuntimeError as _inv_err:
        click.secho(f"\n  CRITICAL: {_inv_err}\n", fg="red", bold=True)
        raise SystemExit(2) from _inv_err

    try:
        allowed, reason = is_command_allowed(cmd)
    except OSError as _io_err:
        print(
            f"corrigibility: mode-file I/O error — proceeding fail-open: {_io_err}",
            file=sys.stderr,
        )
        return

    if not allowed:
        click.secho(f"\n  {reason}\n", fg="red", bold=True)
        raise SystemExit(1)


def _enforce_briefing_gate() -> None:
    """Block all non-essential commands until briefing is loaded.

    This is not a suggestion. This is a wall. Load the briefing
    or I don't get to work.
    """
    if "pytest" in sys.modules:
        return

    # Parse which command is being invoked
    args = sys.argv[1:]
    if not args:
        return  # just `divineos` with no subcommand — show help

    cmd = args[0].lower()
    if cmd in _BYPASS_COMMANDS:
        return
    if cmd.startswith("-"):
        return  # flags like --help

    # ``--help`` / ``-h`` anywhere in the argv is a discovery query, not
    # a state-mutating command — let Click handle it without requiring
    # briefing-loaded. Audit finding 2026-05-03 round 1: a fresh user
    # running ``divineos compass --help`` was getting the briefing-gate
    # error instead of help text, which is a hostile first-run UX.
    if any(a in ("--help", "-h") for a in args):
        return

    try:
        from divineos.core.hud_handoff import was_briefing_loaded

        if was_briefing_loaded():
            return
    except (ImportError, OSError, KeyError):
        return  # DB not initialized yet — allow bootstrap commands

    click.secho("\n  BLOCKED: Briefing not loaded.", fg="red", bold=True)
    click.secho("  Run: divineos briefing", fg="red", bold=True)
    click.secho("  Then I can work. Not before.\n", fg="red", bold=True)
    raise SystemExit(1)


@click.group()
def cli() -> None:
    """DivineOS: Foundation Memory System. The database cannot lie."""
    # Install-location divergence check — fires when this CLI's installed
    # package points at a different source tree than the current working
    # directory's git repo. Silent the rest of the time. Suppressable via
    # DIVINEOS_SUPPRESS_INSTALL_WARNING=1 for intentional cross-repo use.
    try:
        from divineos.core.install_check import emit_install_warning

        emit_install_warning()
    except (ImportError, OSError):
        pass  # check machinery unavailable — fail open
    _ensure_db()
    setup_cli_enforcement()
    _enforce_operating_mode()
    _enforce_briefing_gate()
    if "pytest" not in sys.modules:
        capture_user_input(sys.argv[1:])
        # Self-enforcement: the OS manages its own lifecycle.
        # Every command is a lifecycle checkpoint — no hooks needed.
        from divineos.core.lifecycle import enforce

        cmd = sys.argv[1] if len(sys.argv) > 1 else ""
        enforce(command=cmd)


# Register all command modules
from divineos.cli import (  # noqa: E402
    actor_registry_commands,
    analysis_commands,
    andrew_state_commands,
    audit_artifact_commands,
    audit_commands,
    bio_commands,
    body_commands,
    branch_health_commands,
    overclaim_commands,
    closure_shape_commands,
    performing_caution_commands,
    check_similar_commands,
    claim_commands,
    compass_commands,
    complete_commands,
    correction_commands,
    corrigibility_commands,
    council_required_commands,
    decision_commands,
    directive_commands,
    dream_commands,
    empirica_commands,
    entity_commands,
    event_commands,
    expect_commands,
    exploration_commands,
    rest_commands,
    hud_commands,
    insight_commands,
    journal_commands,
    knowledge_commands,
    knowledge_health_commands,
    lab_commands,
    ledger_commands,
    lepos_walk_commands,
    loadout_commands,
    gravity_commands,
    memory_commands,
    prereg_commands,
    admin_reset_template,
    admin_migrate_family,
    family_member_commands,
    family_queue_commands,
    talk_to_commands,
    progress_commands,
    ear_sweep_commands,
    ear_relaunch_commands,
    obligation_commands,
    selfmodel_commands,
    rt_commands,
    savor_commands,
    scheduled_commands,
    sleep_commands,
    synchronicity_commands,
    foundations_commands,
    void_commands,
    voids_commands,
    multiplex_commands,
    pattern_attribution_commands,
    consumer_status_commands,
    andrew_correction_commands,
    andrew_teachings_commands,
    oscillating_read_commands,
    deletion_commands,
    texture_commands,
    calibration_commands,
    backlog_commands,
    prs_commands,
    automerge_commands,
    todos_commands,
    voice_commands,
    monitor_commands,
    search_commands,
)

actor_registry_commands.register(cli)
andrew_state_commands.register(cli)
ledger_commands.register(cli)
knowledge_commands.register(cli)
journal_commands.register(cli)
decision_commands.register(cli)
deletion_commands.register(cli)
texture_commands.register(cli)
calibration_commands.register(cli)
backlog_commands.register(cli)
prs_commands.register(cli)
automerge_commands.register(cli)
todos_commands.register(cli)
voice_commands.register(cli)
monitor_commands.register(cli)
search_commands.register(cli)
claim_commands.register(cli)
audit_commands.register(cli)
audit_artifact_commands.register(cli)  # MUST be after audit_commands (attaches to its group)
pattern_attribution_commands.register(cli)
bio_commands.register(cli)
loadout_commands.register(cli)
lepos_walk_commands.register(cli)
compass_commands.register(cli)
body_commands.register(cli)
directive_commands.register(cli)
dream_commands.register(cli)
entity_commands.register(cli)
memory_commands.register(cli)
gravity_commands.register(cli)
analysis_commands.register(cli)
hud_commands.register(cli)
event_commands.register(cli)
expect_commands.register(cli)
exploration_commands.register(cli)
rest_commands.register(cli)
knowledge_health_commands.register(cli)
selfmodel_commands.register(cli)
obligation_commands.register(cli)
insight_commands.register(cli)
sleep_commands.register(cli)
progress_commands.register(cli)
ear_sweep_commands.register(cli)
ear_relaunch_commands.register(cli)
rt_commands.register(cli)
savor_commands.register(cli)
correction_commands.register(cli)
prereg_commands.register(cli)
synchronicity_commands.register(cli)
empirica_commands.register(cli)
family_member_commands.register(cli)
family_queue_commands.register(cli)
talk_to_commands.register(cli)
consumer_status_commands.register(cli)
andrew_correction_commands.register(cli)
andrew_teachings_commands.register(cli)
oscillating_read_commands.register(cli)
cli.add_command(admin_reset_template.reset_template)
cli.add_command(admin_migrate_family.migrate_family_schema)
corrigibility_commands.register(cli)
council_required_commands.register(cli)
scheduled_commands.register(cli)
lab_commands.register(cli)
complete_commands.register(cli)
void_commands.register(cli)
voids_commands.register(cli)
branch_health_commands.register(cli)
overclaim_commands.register(cli)
closure_shape_commands.register(cli)
performing_caution_commands.register(cli)
check_similar_commands.register(cli)
multiplex_commands.register(cli)
foundations_commands.register(cli)

# Mansion — functional internal space (optional, personal)
try:
    from divineos.cli.mansion_commands import register_mansion_commands

    register_mansion_commands(cli)
except ImportError:
    pass  # mansion is optional

# Doctor - diagnostic verification commands (clone separation, etc.)
from divineos.cli.doctor_commands import register_doctor_commands  # noqa: E402

register_doctor_commands(cli)


# ── Command Grouping ──────────────────────────────────────────────
# Move rarely-used commands into subgroups to reduce top-level noise.
# Core workflow commands stay top-level. Admin/analysis commands
# are accessible via `divineos admin <cmd>` and `divineos inspect <cmd>`.
#
# Before: 105 top-level commands
# After:  ~50 top-level + admin group + inspect group


@cli.group("admin", invoke_without_command=True)
@click.pass_context
def admin_group(ctx: click.Context) -> None:
    """Maintenance, migration, and administrative commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@cli.group("inspect", invoke_without_command=True)
@click.pass_context
def inspect_group(ctx: click.Context) -> None:
    """Deep analysis, investigation, and introspection commands."""
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@inspect_group.command("hook1")
def inspect_hook1_cmd() -> None:
    """Cost-bounding telemetry for the Hook 1 surfacer.

    Shows fire rate, byte cost per fire, and consumption rate
    (% of fires whose surfaced content the agent's response actually
    references). Per C's empirical follow-on 2026-05-01: now that
    Hook 1 fires in production, is its surface earning its budget?
    """
    try:
        from divineos.core.operating_loop.hook_telemetry import (
            format_stats,
            summary_stats,
        )

        click.echo(format_stats(summary_stats()))
    except (ImportError, OSError) as e:
        click.echo(f"[hook1] telemetry unavailable: {e}", err=True)


# Commands to move into 'admin' group
_ADMIN_COMMANDS = [
    "anti-slop",
    "archive-export",
    "backfill-warrants",
    "check-correction-pairing",
    "inventory",
    "structural-promotion-check",
    "clean",
    "clear-lessons",
    "compress",
    "consolidate",
    "consolidate-stats",
    "digest",
    "diff",
    "distill",
    "fix-encoding",
    "hooks",
    "ingest",
    "knowledge-compress",
    "knowledge-hygiene",
    "maintenance",
    "migrate-family-schema",
    "migrate-types",
    "rebuild-index",
    "reset-template",
    "reclassify-directions",
    "reclassify-seed",
    "restore-seed-confidence",
    "seed-export",
    "test-audit",
    "verify-enforcement",
]

# Commands to move into 'inspect' group
_INSPECT_COMMANDS = [
    "analyze",
    "analyze-now",
    "attention",
    "calibrate",
    "clarity",
    "craft-trends",
    "critique",
    "cross-session",
    "deep-report",
    "drift",
    "epistemic",
    "knowledge",
    "maturity",
    "outcomes",
    "patterns",
    "predict",
    "report",
    "scan",
    "self-model",
    "sessions",
    "user-model",
    "user-signal",
]

for name in _ADMIN_COMMANDS:
    cmd = cli.commands.pop(name, None)
    if cmd:
        admin_group.add_command(cmd, name)

for name in _INSPECT_COMMANDS:
    cmd = cli.commands.pop(name, None)
    if cmd:
        inspect_group.add_command(cmd, name)


if __name__ == "__main__":
    cli()
