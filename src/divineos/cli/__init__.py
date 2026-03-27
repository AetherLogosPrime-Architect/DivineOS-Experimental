"""DivineOS CLI - Foundation Memory & Knowledge.

Commands for managing the event ledger, ingesting conversations,
verifying data integrity, and consolidating knowledge.
"""

import sys

import click

from divineos.cli._wrappers import _ensure_db
from divineos.core.enforcement import capture_user_input, setup_cli_enforcement


@click.group()
def cli() -> None:
    """DivineOS: Foundation Memory System. The database cannot lie."""
    _ensure_db()
    setup_cli_enforcement()
    if "pytest" not in sys.modules:
        capture_user_input(sys.argv[1:])


# Register all command modules
from divineos.cli import (  # noqa: E402
    analysis_commands,
    event_commands,
    hud_commands,
    knowledge_commands,
    ledger_commands,
    memory_commands,
)

ledger_commands.register(cli)
knowledge_commands.register(cli)
memory_commands.register(cli)
analysis_commands.register(cli)
hud_commands.register(cli)
event_commands.register(cli)

if __name__ == "__main__":
    cli()
