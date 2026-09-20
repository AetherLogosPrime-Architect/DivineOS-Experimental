"""Enumerate the divineos commands our gates print, and say which exit list --
if either -- would let a blocked actor run them.

WHY THIS IS A SCRIPT AND NOT A NUMBER IN A LETTER. The first time this
enumeration was run it lived only in a session, and the pointer given for it
was wrong -- the reader fetched two branches, read the rationale document
through, and found nothing, because there was nothing to find. An enumeration
that cannot be re-run is a claim, not a measurement.

THERE ARE TWO EXIT LISTS AND THE FIRST RUN ONLY KNEW ABOUT ONE.

  scripts/hook_bypass_commands.txt   -- the canonical, documented, wide list,
                                        read by the PreToolUse gate and by
                                        every hook that sources _lib.sh.
  _REMEDY_PATTERNS in
  .claude/hooks/lib/remedy_allowlist.sh -- a narrow hand-written pattern, read
                                        by the gates that source that library.

The first run of this survey compared against the narrow one alone and
reported thirty-seven commands as uncovered. Most of those are on the wide
list. A count measured against one of two instruments is not a count of holes;
it is a count of what one instrument does not know about.

WHAT THIS ANSWERS, AND WHAT IT DOES NOT. It answers which registered commands
appear in gate text, and which list each one is on. It does NOT answer whether
a command SHOULD be on either. A gate that merely mentions a command while
explaining itself, or runs one as its own internal work, is not sending a
blocked actor through it. That judgement is per-command and belongs to a
reader, so the output is candidates rather than holes.

THE MENTION-VERSUS-USE BOUNDARY BIT THE FIRST VERSION OF THIS. Matching the
word divineos anywhere produced phrases like "divineos from the" and "divineos
reads the" -- prose containing the word, counted as the word being used. The
fix is to stop pattern-matching at the program and ask the program for its own
registry, which is what _registered_commands does.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOOK_DIR = REPO / ".claude" / "hooks"
NARROW_LIST = HOOK_DIR / "lib" / "remedy_allowlist.sh"
WIDE_LIST = REPO / "scripts" / "hook_bypass_commands.txt"

# divineos followed by up to two more bare words. The pair wins when it is a
# real two-word command, so compass-ops observe is one command rather than
# compass-ops plus noise.
_CANDIDATE = re.compile(r"\bdivineos\s+([a-z][a-z0-9-]*)(?:\s+([a-z][a-z0-9-]*))?")


def _registered_commands() -> set[str]:
    """Ask the CLI for its own command names, one and two words deep."""
    from divineos.cli import cli as root

    names: set[str] = set()
    for name, cmd in root.commands.items():
        names.add(name)
        for sub in getattr(cmd, "commands", {}):
            names.add(f"{name} {sub}")
    return names


def _narrow_pattern() -> str:
    """Read the pattern out of the shell library rather than retyping it.

    A copy retyped here would drift from the live one silently, and this survey
    would then report on a rule nobody enforces.
    """
    for line in NARROW_LIST.read_text(encoding="utf-8").splitlines():
        if line.startswith("_REMEDY_PATTERNS="):
            return line.split("=", 1)[1].strip().strip("'")
    raise SystemExit(f"no _REMEDY_PATTERNS found in {NARROW_LIST}")


def _wide_prefixes() -> list[str]:
    """The canonical list, as prefixes after the leading program name."""
    prefixes: list[str] = []
    for line in WIDE_LIST.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        head, _, rest = line.partition(" ")
        if head == "divineos" and rest.strip():
            prefixes.append(rest.strip())
    return prefixes


def _on_narrow(command: str, pattern: str) -> bool:
    """Ask grep, so the answer comes from the same engine the gate uses."""
    proc = subprocess.run(
        ["grep", "-qE", pattern],
        input=f"divineos {command}\n",
        text=True,
        capture_output=True,
    )
    return proc.returncode == 0


def _on_wide(command: str, prefixes: list[str]) -> bool:
    return any(command == p or command.startswith(f"{p} ") for p in prefixes)


def main() -> int:
    # THE ROOT COMES FROM THIS FILE'S OWN POSITION, so a copy dropped in a
    # scratch directory surveys whatever is beside it -- right kind of object,
    # wrong object. Aether hit exactly that running the sibling survey from his
    # scratchpad: it did not error, it answered about a directory that was not
    # the repository. A location it cannot confirm must not produce a survey.
    for marker in (REPO / "scripts", REPO / "src" / "divineos", HOOK_DIR):
        if not marker.is_dir():
            print(f"REFUSED: {REPO} does not look like the repository (missing {marker.name}).")
            print("  Run this from inside the repository rather than from a copy.")
            return 2

    registered = _registered_commands()
    if not registered:
        print("REFUSED: the CLI reported no commands, so the filter is broken.")
        return 2

    narrow = _narrow_pattern()
    wide = _wide_prefixes()
    if not wide:
        print(f"REFUSED: {WIDE_LIST.name} yielded no prefixes, so the filter is broken.")
        return 2

    found: dict[str, set[str]] = {}
    scanned = 0
    for path in sorted(HOOK_DIR.rglob("*")):
        if path.suffix not in {".sh", ".py"} or not path.is_file():
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8", errors="replace")
        for one, two in _CANDIDATE.findall(text):
            pair = f"{one} {two}" if two else ""
            command = pair if pair in registered else one
            if command not in registered:
                continue
            found.setdefault(command, set()).add(path.relative_to(REPO).as_posix())

    if scanned == 0:
        print("REFUSED: no hook files were scanned, so a clean result means nothing.")
        return 2

    both, wide_only, narrow_only, neither = [], [], [], []
    for command in sorted(found):
        n = _on_narrow(command, narrow)
        w = _on_wide(command, wide)
        if n and w:
            both.append(command)
        elif w:
            wide_only.append(command)
        elif n:
            narrow_only.append(command)
        else:
            neither.append(command)

    print(f"scanned {scanned} hook file(s)")
    print(f"{len(found)} registered command(s) appear in gate text")
    print(f"  on both exit lists:        {len(both)}")
    print(f"  canonical list only:       {len(wide_only)}")
    print(f"  narrow allowlist only:     {len(narrow_only)}")
    print(f"  on neither:                {len(neither)}")

    if narrow_only:
        print()
        print("ON THE NARROW LIST BUT NOT THE CANONICAL ONE.")
        print("  A gate sourcing one library waves these through; a gate")
        print("  sourcing the other refuses them. Same house, two answers.")
        for command in narrow_only:
            print(f"  divineos {command}")

    print()
    print("ON NEITHER -- CANDIDATES, NOT HOLES. Each needs the question:")
    print("  does some gate's own refusal message name this as the way through?")
    print("  If it is a command a hook runs as its own work, the answer is no.")
    for command in neither:
        where = sorted(found[command])
        shown = ", ".join(where[:3]) + (f" (+{len(where) - 3} more)" if len(where) > 3 else "")
        print(f"  divineos {command}")
        print(f"      seen in: {shown}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
