"""CLI smoke test: ``--help`` works for every command + subcommand.

Audit finding 2026-05-03 round 3: of 236 CLI commands, only ~52 are
referenced by name in ``tests/``. Many commands are tested by calling
their underlying API directly, but argparse decoration bugs, Click
parameter bugs, and missing-import-during-CLI-load bugs (like the
silent ``mansion`` ImportError that was hiding for weeks) only
surface when the user actually invokes the command.

This test invokes ``--help`` on every command (and every group's
subcommand) via Click's ``CliRunner``, asserting the exit code is 0.
A small test that catches load-time regressions for every command.

Cost: <2s on a healthy tree.
"""

from __future__ import annotations

from click.testing import CliRunner

from divineos.cli import cli


def _walk_commands(group, parents: list[str]) -> list[list[str]]:
    """Yield argv-prefixes for every command and subcommand reachable
    from ``group``. Each element is a list of name segments to be
    invoked as ``<segments> --help``.
    """
    out: list[list[str]] = []
    if hasattr(group, "commands"):
        for name in sorted(group.commands):
            cmd = group.commands[name]
            path = parents + [name]
            out.append(path)
            # Recurse into Click groups
            if hasattr(cmd, "commands"):
                out.extend(_walk_commands(cmd, path))
    return out


def test_root_help_works():
    """``divineos --help`` returns exit 0."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0, result.output


def test_every_command_help_works():
    """Every top-level command and subcommand responds to ``--help``
    with exit code 0. Catches load-time regressions: import errors,
    decorator bugs, Click parameter mistakes, missing options.
    """
    runner = CliRunner()
    paths = _walk_commands(cli, [])
    failures: list[tuple[list[str], int, str]] = []

    for path in paths:
        result = runner.invoke(cli, path + ["--help"])
        if result.exit_code != 0:
            output = result.output.strip().split("\n")[0] if result.output else ""
            failures.append((path, result.exit_code, output))

    if failures:
        msg_lines = [f"{len(failures)} command(s) failed --help:"]
        for path, code, out in failures[:20]:
            msg_lines.append(f"  {' '.join(path)}: exit={code}  {out!r}")
        if len(failures) > 20:
            msg_lines.append(f"  ...and {len(failures) - 20} more")
        raise AssertionError("\n".join(msg_lines))


def test_command_count_meets_expectation():
    """Sanity check: the smoke test is exercising a non-trivial number
    of commands. If this number drops sharply, something probably got
    silently un-registered (the ``mansion = optional`` shape from the
    audit).
    """
    paths = _walk_commands(cli, [])
    assert len(paths) >= 100, (
        f"Only {len(paths)} commands reachable from divineos --help. "
        f"Expected ~230+. Did a group's import silently fail?"
    )
