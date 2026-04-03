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


# Register all command modules
from divineos.cli import (  # noqa: E402
    analysis_commands,
    claim_commands,
    compass_commands,
    decision_commands,
    directive_commands,
    entity_commands,
    event_commands,
    hud_commands,
    journal_commands,
    knowledge_commands,
    knowledge_health_commands,
    ledger_commands,
    memory_commands,
    selfmodel_commands,
)

ledger_commands.register(cli)
knowledge_commands.register(cli)
journal_commands.register(cli)
decision_commands.register(cli)
claim_commands.register(cli)
compass_commands.register(cli)
directive_commands.register(cli)
entity_commands.register(cli)
memory_commands.register(cli)
analysis_commands.register(cli)
hud_commands.register(cli)
event_commands.register(cli)
knowledge_health_commands.register(cli)
selfmodel_commands.register(cli)

if __name__ == "__main__":
    cli()
