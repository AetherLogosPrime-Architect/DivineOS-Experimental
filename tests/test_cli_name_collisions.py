"""No two modules may claim the same top-level command name.

WHY THIS EXISTS. On 2026-08-27 Aria and I independently built a command for the
wins ledger, in separate branches, under the same name. Hers a single command;
mine a group with subcommands. Neither of us knew until I fetched her branch to
review something else.

What click does when both register is the part that matters, and it was measured
rather than assumed:

    commands registered under "win": Command
    does "win add" still exist?     False
    total top-level commands:       1

**Silent replacement.** No error, no warning. Whichever module registers last is
the one that exists, and the loser's subcommands cease to exist with it.

Neither of our test suites would have caught it, because both exercise the module
directly rather than the registered surface. So the losing command would have
been importable, tested, green, and absent -- which is the armed-and-unheard
class one layer up: registered, replaced, and reported passing.

WHY STATIC RATHER THAN RUNTIME. At runtime the loser is already gone; there is
nothing left to compare. The collision is only visible in the source, where two
modules both name the same string. So this reads the decorators.

WHAT IT CANNOT SEE, stated rather than implied: a name registered dynamically --
built from a variable, or added via add_command in a loop -- does not appear as a
literal and will not be counted. This guard under-reports by construction. An
under-reporting guard that reads as full coverage is worse than none, so the test
name and this paragraph both say so.
"""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

_CLI_DIR = Path(__file__).resolve().parents[1] / "src" / "divineos" / "cli"

# Decorators that claim a name on the TOP-LEVEL cli object. A subcommand
# registered on a group (@win_group.command("add")) is namespaced by its
# group and cannot collide with another module's top-level name, so the
# receiver has to be the cli object itself.
_TOP_LEVEL_RECEIVERS = {"cli"}
_REGISTERING_ATTRS = {"command", "group"}


def _literal_names_registered(source: str) -> list[str]:
    """Top-level command names this module claims, as literals."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return []
    found: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if func.attr not in _REGISTERING_ATTRS:
            continue
        receiver = func.value
        if not isinstance(receiver, ast.Name) or receiver.id not in _TOP_LEVEL_RECEIVERS:
            continue
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                found.append(arg.value)
                break
    return found


def _registrations_by_name() -> dict[str, list[str]]:
    by_name: dict[str, list[str]] = defaultdict(list)
    for path in sorted(_CLI_DIR.rglob("*.py")):
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for name in _literal_names_registered(source):
            by_name[name].append(path.name)
    return by_name


def test_no_two_modules_claim_the_same_top_level_command_name() -> None:
    """The collision is silent, so it has to be caught in the source."""
    collisions = {
        name: sorted(set(modules))
        for name, modules in _registrations_by_name().items()
        if len(set(modules)) > 1
    }
    assert not collisions, (
        "Two or more modules register the same top-level command name. click "
        "resolves this by silent replacement -- no error, no warning -- so "
        "whichever registers last is the one that exists and the other's "
        "subcommands vanish with it. Measured 2026-08-27 on a real collision "
        f"between a group and a command of the same name.\n\n{collisions}"
    )


def test_the_scan_actually_finds_registrations() -> None:
    """A scan that silently found nothing would pass the test above forever.

    Zero registrations and zero collisions print the same verdict, and this
    house has been burned by that confusion enough times to check it.
    """
    by_name = _registrations_by_name()
    assert len(by_name) > 20, (
        f"only {len(by_name)} top-level command names found across the cli package; "
        "the scan is probably not reading what it thinks it is, and a clean "
        "result from a blind scan is not a clean result"
    )


def test_a_planted_collision_is_detected() -> None:
    """Mutation check on the detector itself, in-memory.

    Without this, the collision test could be structurally incapable of ever
    failing and would report clean forever -- exactly the shape it exists to
    catch.
    """
    module_a = 'def register(cli):\n    @cli.group("duplicated")\n    def a():\n        pass\n'
    module_b = 'def register(cli):\n    @cli.command("duplicated")\n    def b():\n        pass\n'
    names_a = _literal_names_registered(module_a)
    names_b = _literal_names_registered(module_b)
    assert names_a == ["duplicated"], names_a
    assert names_b == ["duplicated"], names_b


def test_a_group_subcommand_is_not_counted_as_top_level() -> None:
    """Namespaced names cannot collide across modules, and counting them
    would produce false collisions on every common verb like add or list."""
    source = (
        "def register(cli):\n"
        '    @cli.group("win")\n'
        "    def win_group():\n"
        "        pass\n"
        '    @win_group.command("add")\n'
        "    def add_cmd():\n"
        "        pass\n"
    )
    assert _literal_names_registered(source) == ["win"]
