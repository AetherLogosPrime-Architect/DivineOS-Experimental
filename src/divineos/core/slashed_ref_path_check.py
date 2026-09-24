"""Refuse a git argument the Windows shell will rewrite before git sees it.

On this machine every native Windows program is started through a shell that
converts arguments it takes for POSIX path lists. One shape of git argument
looks like one to it, and comes out the other side as a different string:

    origin/main:.claude/settings.json  ->  origin\\main;.claude\\settings.json

Git then answers "not a valid object name", and a probe written as "does this
branch carry this file?" reports MISSING -- could-not-look arriving dressed as
found-nothing. Measured 2026-09-23, every row against a control:

    eb27fe23:.claude/hooks/x.sh           ok        (no slash in the ref)
    HEAD:.claude/settings.json            ok
    origin/main:src/divineos/__init__.py  ok        (path does not start with a dot)
    origin/main:./README.md               ok        (dot then slash)
    origin/main:.claude/settings.json     MANGLED
    origin/main:.gitignore                MANGLED
    refs/heads/aria/x:.gitignore          MANGLED
    "origin/main:.gitignore" (quoted)     MANGLED   -- quoting does not protect it
    git -C . cat-file -e origin/main:.x   MANGLED
    any of the above, MSYS_NO_PATHCONV=1  ok

Dot-folders are ``.claude/`` and ``.github/``: the hooks, the settings and the
workflows -- the files a guardrail question is asked about. It happened to Aria
on 2026-08-31, to Aether minutes after reading her letter about it, to Aether
again on 2026-09-03, and to Aria on 2026-09-23, when four branches were reported
missing a hook and one of them had it. Written up every time, guarded never.

WHY NOT THE GLOBAL SWITCH. ``MSYS_NO_PATHCONV=1`` everywhere would take the
option away, but the same conversion is what turns ``/c/DIVINE OS/...`` into
``C:\\DIVINE OS\\...`` for every native program the house runs. So the refusal
is narrow and the remedy is per-command. The upstream half is
``scripts/which_refs_carry.py``, which asks git directly with no shell between
and cannot be rewritten (prereg-2a5427d47ff8; this check is
prereg-bdf587a7bea7).

WHAT THIS CANNOT SEE. A target assembled in a variable, a script that runs git
itself, a subprocess: none of those pass through this text. The walk
(walk-6e8e2c7e5ca4) named that gap, and the tests pin it rather than imply it.
"""

from __future__ import annotations

import os
import re
import shlex
import sys
from collections.abc import Mapping

# A ref containing a slash, then a colon, then a dot followed by anything that
# is not a slash. The dot-slash case is excluded on measurement, not taste:
# origin/main:./README.md goes through untouched.
_REWRITTEN_SHAPE = re.compile(r"^[^:\s/]+(?:/[^:\s/]+)+:\.[^/]")

# Only arguments to these programs are at risk from this shape. The rewrite
# applies to any native program's argv, but the ref:path grammar is git's and
# every recorded incident was git; widening this is one edit with its own
# evidence (Lovelace, on the walk).
_COMMAND_WORDS = frozenset({"git", "git.exe"})

_OPT_OUTS = ("MSYS_NO_PATHCONV=1", "MSYS2_ARG_CONV_EXCL=")


def conversion_is_live(env: Mapping[str, str] | None = None, platform: str | None = None) -> bool:
    """True where the shell rewrites arguments: an MSYS shell, or Windows.

    On a POSIX box nothing is rewritten, so nothing is refused there.
    """
    env = os.environ if env is None else env
    platform = sys.platform if platform is None else platform
    if env.get("MSYS_NO_PATHCONV") == "1" or "MSYS2_ARG_CONV_EXCL" in env:
        return False
    return bool(env.get("MSYSTEM")) or platform.startswith("win")


def rewritten_arguments(command: str) -> list[str]:
    """The arguments in this command that the shell would rewrite for git.

    Reads the shell's own word-splitting, so a quoted argument is judged by
    what git would receive -- which is the point, since quoting does not stop
    the rewrite. A command whose quoting cannot be read falls back to a
    whitespace split: approximate rather than crash, the convention every gate
    here follows. Fires only when a git command word is present, so an echo or
    a letter mentioning the shape in prose is left alone.
    """
    if not command or any(opt in command for opt in _OPT_OUTS):
        return []
    try:
        tokens = shlex.split(command, posix=True)
    except ValueError:
        tokens = command.split()
    if not any(tok.rsplit("/", 1)[-1].lower() in _COMMAND_WORDS for tok in tokens):
        return []
    return [tok for tok in tokens if _REWRITTEN_SHAPE.match(tok)]


def should_refuse(
    command: str, env: Mapping[str, str] | None = None, platform: str | None = None
) -> bool:
    return conversion_is_live(env, platform) and bool(rewritten_arguments(command))


def refusal_message(command: str) -> str:
    args = rewritten_arguments(command)
    shown = ", ".join(args[:3])
    garbled = args[0].replace("/", "\\").replace(":", ";", 1) if args else ""
    return (
        "SLASHED REF + DOT PATH -- the Windows shell will rewrite this before git sees it.\n\n"
        f"  argument: {shown}\n"
        f"  git would receive: {garbled}\n\n"
        "Git would answer 'not a valid object name', and anything reading that as\n"
        "'the file is not there' would be reporting that it could not look. It\n"
        "happened four times between 2026-08-31 and 2026-09-23 before this existed.\n\n"
        "Remedy -- any one of:\n"
        "  MSYS_NO_PATHCONV=1 <the same command>\n"
        "  python scripts/which_refs_carry.py <path> [<ref> ...]   (asks git directly;\n"
        "      says carries / does not / could not look, with a control)\n"
        "  write the path as ./<path> -- but only from the repository root, since\n"
        "      ./ is read relative to the directory the command runs in\n\n"
        "MINE, and here is why. I knew about this and it happened anyway, the\n"
        "fourth time while writing up a finding about something else. Knowing a\n"
        "quirk does not survive the moment of typing the one-liner; a door does."
    )
