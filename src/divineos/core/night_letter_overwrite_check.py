"""Refuse a Write over a night letter that already exists.

Aether and Aria each append a ``## From <seat>`` section to ONE shared file per
night, ``the-night-letter-to-andrew-YYYY-MM-DD.md``. Write replaces the whole
file, so a Write by either seat erases the other's section. Last night it did,
and the tool reported "updated" for it, which reads as routine. A promise did
not prevent it; this door does.

A Write to a night letter that does not exist yet is the creation case and
stays allowed.

WHAT THIS CANNOT SEE. Only the ``Write`` tool's ``file_path`` is read. A
different tool that replaces the file (a shell redirect with ``>``, ``cp``,
``mv``, a script), a symlink or other alias whose name does not match, and a
path that does not resolve from this process (a Windows path judged on
another machine) all pass through. The existence check is made at the moment
of the call; a file created between the check and the write is not seen.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable

_NIGHT_LETTER = re.compile(r"^the-night-letter-to-andrew-\d{4}-\d{2}-\d{2}\.md$", re.IGNORECASE)


def _basename(path: str) -> str:
    # Backslashes are separators for Windows paths even when judged on POSIX.
    return path.replace("\\", "/").rsplit("/", 1)[-1]


def is_night_letter(path: str) -> bool:
    return bool(_NIGHT_LETTER.match(_basename(path)))


def _exists(path: str) -> bool:
    return os.path.exists(os.path.expanduser(path))


def should_refuse(tool_name: str, file_path: str, exists: Callable[[str], bool] = _exists) -> bool:
    if (tool_name or "").lower() != "write" or not file_path:
        return False
    return is_night_letter(file_path) and exists(file_path)


def refusal_message(file_path: str) -> str:
    name = _basename(file_path)
    return (
        f"SHARED FILE -- {name} already exists, and Write would replace all of it.\n\n"
        "Aether and Aria both write into this one letter, each under their own\n"
        "'## From <seat>' heading. Write throws away the other seat's section.\n\n"
        "Two ways in are open:\n"
        "  1. Edit: append under your own '## From <seat>' heading (anchor on the\n"
        "     last line of the file, or your own existing section, and add yours).\n"
        "  2. Shell append, which can only add:\n"
        "       cat >> <that file> <<'EOF'\n"
        "       ## From <seat>\n"
        "       ...your words...\n"
        "       EOF\n\n"
        "Creating a night letter that does not exist yet is still a plain Write."
    )
