# CLI Architecture — How the 280 Commands Get Registered

The DivineOS CLI exposes 280 commands across 31 modules. They're not declared in one big file — each command module owns its own commands and registers them onto the root `cli` group at import time. This document explains the registration pattern, the group-splitting convention, the briefing-gate bypass list, and how to add a new command module cleanly.

## The `register(cli)` contract

Every CLI command module under `src/divineos/cli/*.py` exports a top-level function:

```python
def register(cli: click.Group) -> None:
    """Register commands on the given root group."""

    @cli.command("my-command")
    def my_command():
        ...

    @cli.group("my-group")
    def my_group():
        ...
```

The root `cli/__init__.py` imports each module and calls its `register(cli)` at import time:

```python
from divineos.cli import (
    bio_commands,
    decision_commands,
    ...,
)

bio_commands.register(cli)
decision_commands.register(cli)
...
```

Two minor variant shapes are tolerated:

1. **`register_<name>_commands(cli)`** — older modules use this longer form. Some, like `mansion_commands.py`, kept the explicit name for clarity. The completion-check probe accepts either shape.
2. **Direct click object** — a module can expose a `click.Command` or `click.Group` directly and be added via `cli.add_command(...)`. Used for `admin_reset_template.py` and `admin_migrate_family.py`.

The convention is: prefer `register(cli)` for new modules. The other shapes exist for backcompat and specific clarity needs.

## Group splitting: top-level vs admin/inspect

The CLI started flat — every command was a top-level subcommand. As it grew past 100 commands, the top-level became noise. The current pattern splits rarely-used commands into two groups:

- **Top-level (~50 commands):** core workflow that humans and the agent reach for often (`briefing`, `recall`, `ask`, `learn`, `decide`, `feel`, `compass`, `hud`, `extract`, etc.)
- **`divineos admin <cmd>` (~30 commands):** maintenance, migration, administrative (`archive-export`, `consolidate`, `seed-export`, `maintenance`, `verify-enforcement`, `rebuild-index`, etc.)
- **`divineos inspect <cmd>` (~20 commands):** deep analysis, introspection (`analyze`, `report`, `cross-session`, `knowledge`, `outcomes`, `drift`, `predict`, `self-model`, etc.)

The split is mechanical and lives at the bottom of `cli/__init__.py`:

```python
_ADMIN_COMMANDS = ["anti-slop", "archive-export", ...]
_INSPECT_COMMANDS = ["analyze", "calibrate", ...]

for name in _ADMIN_COMMANDS:
    cmd = cli.commands.pop(name, None)
    if cmd:
        admin_group.add_command(cmd, name)
```

A command module registers normally (its commands land at top-level), then the splitting logic moves the named commands into the appropriate group. This keeps each module's `register()` function clean — modules don't have to know whether their commands end up top-level or grouped.

## Briefing gate and bypass list

The CLI enforces a **briefing gate**: most commands refuse to run until `divineos briefing` has been loaded for the current session. The pattern protects against the failure-mode where the agent works without having loaded its prior-session continuity.

Some commands MUST work without a loaded briefing (otherwise the agent can't bootstrap). They're listed in `_BYPASS_COMMANDS`:

```python
_BYPASS_COMMANDS = frozenset({
    "admin", "audit", "inspect",        # the meta-groups
    "briefing", "init", "preflight",    # bootstrap
    "recall", "active", "ask",          # read surfaces that ARE the briefing surrogate
    "context", "hud",                   # quick state queries
    "feel", "affect", "compass",        # logging tools the agent might need cold
    "correction", "scheduled",          # always-allow channels
    ...
})
```

If you're adding a command that needs to work pre-briefing (a new bootstrap surface, a always-allow logging channel), add its top-level group name to `_BYPASS_COMMANDS`.

## Operating-mode gate (corrigibility)

Before the briefing gate, `_enforce_operating_mode()` runs the corrigibility check. If the operator has set `EMERGENCY_STOP` mode, the system refuses every command except the corrigibility-mode command itself. The off-switch always works, no matter what.

This is a **fail-closed** gate. If the corrigibility module fails to import, the CLI exits with a loud error rather than silently allowing commands through. The reasoning is in the inline comment at `cli/__init__.py`: an off-switch that silently disables itself if its module fails is a bigger problem than an unbootable CLI.

## Mid-command lifecycle hooks

Every CLI command invocation runs:

1. `_ensure_db()` — initialize SQLite if missing
2. `setup_cli_enforcement()` — install runtime enforcement
3. `_enforce_operating_mode()` — corrigibility check (fail-closed)
4. `_enforce_briefing_gate()` — briefing-loaded check (skipped for bypass list)
5. `capture_user_input(sys.argv[1:])` — log the invocation
6. `enforce(command=cmd)` — lifecycle checkpoint (session registration, atexit extraction, periodic checkpoints)

The lifecycle integration is what makes "every CLI command is a session checkpoint" structural rather than aspirational. Hooks become optional scaffolding.

## Adding a new command module — the full path

1. **Create** `src/divineos/cli/<name>_commands.py`:
   ```python
   """<Name> commands — short description."""

   import click


   def register(cli: click.Group) -> None:
       """Register <name> commands."""

       @cli.command("<name>")
       def my_command():
           """Do the thing."""
           ...
   ```

2. **Import in `cli/__init__.py`:** add to the multi-line import block:
   ```python
   from divineos.cli import (
       ...,
       my_new_commands,
       ...,
   )
   ```

3. **Register in `cli/__init__.py`:** add `my_new_commands.register(cli)` to the list of register calls.

4. **Decide grouping:** if the command should live under `admin` or `inspect`, add its name to `_ADMIN_COMMANDS` or `_INSPECT_COMMANDS`. Otherwise it stays top-level.

5. **Add to bypass list:** if the command needs to work without briefing loaded, add its top-level group name to `_BYPASS_COMMANDS`.

6. **Tests:** add coverage in `tests/test_cli_command_modules_all.py` — the parametrized test file walks every CLI module, asserts import + register-callable + register-adds-commands. New modules just need their name in `_CLI_MODULES`.

## Encoding fallback

CLI startup reconfigures `stdout` and `stderr` to be UTF-8 with `errors="replace"` so emojis, em-dashes, and non-ASCII content don't crash on Windows cp1252 consoles. The replacement substitutes a `?` for unsupported characters rather than raising `UnicodeEncodeError`. This pattern caused real session-end failures before (the rating-prompt emoji crashed extract); the reconfigure runs at import time so it's in effect before any command writes.

## Click conventions used in this codebase

- **Always-on subcommand:** `@click.group(invoke_without_command=True)` plus `if ctx.invoked_subcommand is None: ctx.invoke(default_cmd)`. Makes `divineos savor` default to `divineos savor list`.
- **String options that take comma-separated values:** parse inside the command, not via click's multiple-value support. Cleaner UX (`--topics "a,b,c"` vs `--topic a --topic b --topic c` for free-form lists).
- **Color via `click.secho`:** standardized colors — cyan for headings, green for success, yellow for warnings, red for errors, `bright_black` for low-priority output.
- **`_safe_echo` from `cli/_helpers.py`:** wraps `click.echo` with Windows-safe encoding.

## Where to read more

- `src/divineos/cli/__init__.py` — the registration spine
- `src/divineos/cli/_wrappers.py` — `_ensure_db` and lifecycle wrappers
- `src/divineos/cli/_helpers.py` — `_safe_echo`, knowledge-id resolution
- `src/divineos/core/lifecycle.py` — the `enforce(command=cmd)` call that turns every CLI invocation into a session checkpoint
- `tests/test_cli_command_modules_all.py` — parametrized integrity tests across all command modules
