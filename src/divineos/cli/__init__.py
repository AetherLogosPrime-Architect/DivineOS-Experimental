"""DivineOS CLI - Foundation Memory & Knowledge.

Commands for managing the event ledger, ingesting conversations,
verifying data integrity, and consolidating knowledge.
"""

import sys

import click

from divineos.cli._wrappers import _ensure_db
from divineos.core.enforcement import capture_user_input, setup_cli_enforcement

# Commands that work without briefing loaded — the minimum to bootstrap.
_BYPASS_COMMANDS = frozenset(
    {
        "admin",
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
    }
)


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
    _ensure_db()
    setup_cli_enforcement()
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
    analysis_commands,
    body_commands,
    claim_commands,
    compass_commands,
    decision_commands,
    directive_commands,
    entity_commands,
    event_commands,
    hud_commands,
    insight_commands,
    journal_commands,
    knowledge_commands,
    knowledge_health_commands,
    ledger_commands,
    memory_commands,
    progress_commands,
    selfmodel_commands,
    rt_commands,
    sleep_commands,
)

ledger_commands.register(cli)
knowledge_commands.register(cli)
journal_commands.register(cli)
decision_commands.register(cli)
claim_commands.register(cli)
compass_commands.register(cli)
body_commands.register(cli)
directive_commands.register(cli)
entity_commands.register(cli)
memory_commands.register(cli)
analysis_commands.register(cli)
hud_commands.register(cli)
event_commands.register(cli)
knowledge_health_commands.register(cli)
selfmodel_commands.register(cli)
insight_commands.register(cli)
sleep_commands.register(cli)
progress_commands.register(cli)
rt_commands.register(cli)


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


# Commands to move into 'admin' group
_ADMIN_COMMANDS = [
    "backfill-warrants",
    "clean",
    "clear-lessons",
    "compress",
    "consolidate",
    "consolidate-stats",
    "digest",
    "diff",
    "distill",
    "hooks",
    "ingest",
    "knowledge-compress",
    "knowledge-hygiene",
    "maintenance",
    "migrate-types",
    "rebuild-index",
    "reclassify-directions",
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
