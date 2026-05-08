#!/usr/bin/env python3
"""Test-CLI linkage check — verify that every CLI command referenced in a
test actually registers with the click CLI.

## Why this exists

Audit finding 2026-05-05 (Claude Opus 4.7 audit of PR #264):
the PR shipped a complete test suite for ``divineos commitment fulfillment``
but the actual subcommand never registered with the CLI — every test failed
with ``Error: No such command 'fulfillment'``. The failure mode was:

  * implementation file edited locally
  * edit succeeded
  * file never staged into the commit
  * test file + README updates pushed without the implementation

This is a distinct failure mode from "half-wired" (where producer or
consumer is missing in a wired integration) — this is "test-shipped-
without-implementation," and the wiring-claim detector (F2) does NOT
catch it because the commit doesn't claim wiring.

## What this check does

Walks ``tests/``, finds every ``runner.invoke(cli, [<command>, ...])``
call (and the ``_run("foo", ...)`` shorthand pattern), extracts the
top-level command name, and verifies that command actually registers
with the divineos CLI by checking ``divineos.cli.cli.commands``.

Exit codes:
  0 — every test-referenced command registers
  1 — at least one referenced command is missing
  2 — infrastructure error (CLI didn't import, etc.)

## Limits (honest)

* Static-only. Does not exercise Click's resolution. A command name
  passed via a variable rather than a literal string slips by.
* First-arg only. `runner.invoke(cli, [name_var])` is skipped (no
  literal to check).
* Subcommand names are noted but not deeply validated. The check
  ensures the top-level command exists; if a Group-subcommand is
  invoked (e.g. ``commitment fulfillment``), only ``commitment`` is
  required to register here. The subcommand failure surfaces at
  test-time, which is acceptable for the failure-mode this check
  was designed to catch (top-level command missing entirely).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_INVOKE_RE = re.compile(
    r"""
    runner\.invoke\(\s*cli\s*,\s*\[\s*
    (?:["']([a-z][\w\-]*)["'])     # first list element as a string literal
    """,
    re.VERBOSE,
)
_RUN_RE = re.compile(
    r"""
    \b_run\(\s*
    (?:["']([a-z][\w\-]*)["'])
    """,
    re.VERBOSE,
)


# Files that exercise the check itself contain literal-string synthesized
# invoke patterns for testing. They must be excluded so the check doesn't
# flag its own fixtures.
_SELF_TEST_FILES = frozenset({"test_check_test_cli_linkage.py"})


def _scan_tests(tests_dir: Path) -> dict[str, list[Path]]:
    """Return {command_name: [test_paths_referencing_it]}."""
    refs: dict[str, list[Path]] = {}
    for path in tests_dir.rglob("test_*.py"):
        if path.name in _SELF_TEST_FILES:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        for match in _INVOKE_RE.finditer(text):
            refs.setdefault(match.group(1), []).append(path)
        for match in _RUN_RE.finditer(text):
            refs.setdefault(match.group(1), []).append(path)
    return refs


def _registered_commands() -> set[str]:
    """Return the set of top-level command names registered on the CLI."""
    try:
        from divineos.cli import cli
    except ImportError as e:
        print(f"FAIL: could not import divineos.cli: {e}", file=sys.stderr)
        sys.exit(2)
    return set(cli.commands.keys())


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        print(f"FAIL: tests dir not found at {tests_dir}", file=sys.stderr)
        return 2

    refs = _scan_tests(tests_dir)
    registered = _registered_commands()

    missing = {cmd: paths for cmd, paths in refs.items() if cmd not in registered}
    if not missing:
        print(f"OK: {len(refs)} test-referenced commands all register.")
        return 0

    print(
        f"\n[!] Test-CLI linkage check failed: "
        f"{len(missing)} command(s) referenced in tests but not registered "
        f"on divineos.cli.cli\n"
    )
    for cmd, paths in sorted(missing.items()):
        unique_paths = sorted({str(p.relative_to(repo_root)) for p in paths})
        print(f"  '{cmd}' referenced in:")
        for p in unique_paths:
            print(f"    - {p}")
    print(
        "\nFix: register the missing command(s) in src/divineos/cli/__init__.py\n"
        "(or its registration module), or remove the test references if the\n"
        "command was intentionally renamed/removed."
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
