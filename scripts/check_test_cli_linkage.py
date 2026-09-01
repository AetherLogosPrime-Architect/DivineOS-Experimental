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


# ---------------------------------------------------------------- painted doors
#
# A comment or docstring that names a `divineos <cmd>` which does not exist is a
# SIGN POINTING AT A DOOR NOBODY BUILT. Andrew 2026-08-24, after two of them
# turned up in a single session: "the whole painted door issue sounds like
# something that could be solved via automation."
#
# The two that session:
#   - a hook comment told the reader to run `divineos context-heartbeat --stats`
#     hours before that command was written;
#   - a doorman's refusal text said it had NO authorization check. That was true
#     for twenty hours, then unrelated work built the door behind the sign and
#     nobody took the sign down. It cost Aria a true report to Andrew: she read
#     it, believed it, and told him she had gone around a guard that would in
#     fact have let her through.
#
# WHY BACKTICKS OR A PROMPT ONLY. Measured across src, hooks, scripts and docs:
# a loose `divineos \w+` match yields 117 unregistered hits over 61 words, nearly
# all of it prose -- "the divineos home", "divineos commands". Requiring a
# backtick or a shell prompt drops that to 15 over 7 words, and all 7 were real.
# A noisy checker gets skimmed, and a checker nobody reads is itself a painted
# door.
#
# WHY docs/ IS NOT SCANNED. Of those 15, thirteen live in design briefs, audit
# reports and proposals -- documents whose entire job is describing something
# that does not exist yet. divineos-retire-design-brief.md naming
# `divineos retire` is a proposal, not a lie. The two in live code are the real
# class: text a reader follows as instruction. Scanning docs would bury 2 true
# positives under 13 correct-by-design ones, which is how a check earns being
# ignored.
_PAINTED_DOOR_RE = re.compile(r"[`$]\s*divineos\s+([a-z][a-z0-9-]{2,})")

# Directories whose text is INSTRUCTION -- a reader does what it says.
_INSTRUCTION_ROOTS = ("src", ".claude/hooks", "scripts")


def _resolves(name: str) -> bool:
    """True if ``divineos <name>`` actually runs.

    Uses click's own resolution, NOT ``cli.commands``. While building this
    check, ``cli.commands`` reported 172 entries and missed every lazily
    registered group -- and the shell probe meant to double-check it matched
    only the first line of output, which is the identical
    "Usage: divineos [OPTIONS]..." banner for both success and "No such
    command". Two instruments agreeing on a wrong answer. The exit code and
    ``get_command`` are the ones that tell the truth.
    """
    import click

    from divineos.cli import cli as _cli

    return _cli.get_command(click.Context(_cli), name) is not None


def _scan_painted_doors(repo_root: Path) -> list[tuple[Path, int, str]]:
    """Return [(path, lineno, command)] for commands named but never built."""
    found: list[tuple[Path, int, str]] = []
    for root in _INSTRUCTION_ROOTS:
        base = repo_root / root
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.suffix not in {".py", ".sh"} or not path.is_file():
                continue
            if path.name == Path(__file__).name:
                continue
            try:
                text = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                for match in _PAINTED_DOOR_RE.finditer(line):
                    name = match.group(1)
                    # A command name never ends in a hyphen. This is a comment
                    # wrapped mid-name -- ``divineos lepos-`` continuing to
                    # ``channel surface`` on the next line. Flagging it would be
                    # a false positive on a command that exists, and one bad
                    # flag is enough to teach a reader to skim the whole check.
                    if name.endswith("-"):
                        continue
                    if not _resolves(name):
                        found.append((path, lineno, name))
    return found


def _registered_commands() -> set[str]:
    """Return the set of top-level command names registered on the CLI.

    The import guard is not decoration. Run under bare python this compared the
    OTHER checkout's registrations against this checkout's tests and printed
    "OK: 42 test-referenced commands all register" on every commit — a real
    check, greenly answering about the wrong repository (2026-08-13).
    """
    try:
        import _repo_import  # noqa: F401  -- must precede the divineos import

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

    painted = _scan_painted_doors(repo_root)
    missing = {cmd: paths for cmd, paths in refs.items() if cmd not in registered}

    if painted:
        print(
            f"\n[!] Painted doors: {len(painted)} reference(s) in live code name a "
            "`divineos` command that does not exist.\n"
            "    Text a reader follows as instruction must point at something real.\n"
        )
        for path, lineno, cmd in sorted(painted, key=lambda t: (str(t[0]), t[1])):
            print(f"  {path.relative_to(repo_root)}:{lineno}  ->  divineos {cmd}")
        print("\nFix: build the command, or change the text to stop naming it.\n")

    if not missing and not painted:
        print(f"OK: {len(refs)} test-referenced commands all register; no painted doors.")
        return 0
    if not missing:
        return 1

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
