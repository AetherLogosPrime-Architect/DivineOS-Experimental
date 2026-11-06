"""One public home for "a shell command that only looks".

Moved here from ``hooks/post_tool_use_checkpoint.py`` (where it was private and had no test of its own) so the
engagement gate and the bell for Dad share ONE base instead of two copies (Aria's attack on the bell, 2026-11-05).
The base is the gate's list, unchanged.

TWO POLICIES, ONE BASE. The engagement gate keeps this list small on purpose: anything not here counts, so the
failure direction is "the gate fires slightly too often", never "a write slipped past". The bell for Dad needs the
opposite direction, because its first false hold ends it (Dad): it must leave harmless work alone. So the bell does
not widen the shared base; it passes its own named extras (``BELL_EXTRA_*``) to the same function. A change to the
base moves the engagement gate; a change to an extra moves only the bell.

Conservative by construction in both: any redirection, heredoc, in-place edit, unknown program, or any chained
segment that is not itself only looking makes the whole command count as not read-only. A compound like
``grep x && python write.py`` is not read-only, because the cheap route out of an exemption is dressing a write as
a read.
"""

from __future__ import annotations

import re

READ_ONLY_COMMANDS: frozenset[str] = frozenset(
    {
        "grep",
        "rg",
        "ls",
        "cat",
        "head",
        "tail",
        "find",
        "wc",
        "echo",
        "printf",
        "pwd",
        "stat",
        "file",
        "diff",
        "which",
        "basename",
        "dirname",
        "sort",
        "uniq",
        "cut",
        "tr",
        "column",
        "true",
        "test",
        "[",
    }
)

# git subcommands that only read. `git add`, `git commit`, `git checkout` and friends are absent deliberately.
READ_ONLY_GIT: frozenset[str] = frozenset(
    {"log", "show", "status", "diff", "branch", "ls-files", "ls-tree", "rev-parse", "grep", "blame"}
)

# What the bell adds on top, named so its widening is visible and separate from the gate's.
BELL_EXTRA_COMMANDS: frozenset[str] = frozenset({"date"})
BELL_EXTRA_PREFIXES: tuple[tuple[str, ...], ...] = (
    ("git", "ls-remote"),
    # Writes only remote-tracking refs; it brings the shared copy in and changes nothing of mine (Aria: let it through).
    ("git", "fetch"),
    ("git", "worktree", "list"),
    ("gh", "pr", "list"),
    ("gh", "pr", "view"),
    ("gh", "pr", "checks"),
    ("gh", "pr", "diff"),
    ("gh", "issue", "list"),
    ("gh", "issue", "view"),
    ("gh", "run", "list"),
    ("gh", "run", "view"),
    # Reads the memory and warms the link; the house's own read of itself.
    ("divineos", "linkage", "warm"),
)

_WRITE_MARKERS = (">", ">>", "|&", "tee ", "sed -i", "sed --in-place")


def is_read_only(
    command: str,
    *,
    extra_commands: frozenset[str] = frozenset(),
    extra_prefixes: tuple[tuple[str, ...], ...] = (),
) -> bool:
    """True only if EVERY segment of this shell command merely looks.

    Reading is thinking, and the engagement counter's own docstring says so. It counted exploration anyway
    (2026-08-14), so four greps into an investigation the gate would interrupt to demand the thinking that the
    greps were.
    """
    if not command or not command.strip():
        return False
    lowered = command.lower()
    if any(marker in lowered for marker in _WRITE_MARKERS):
        return False
    # Heredocs carry arbitrary payloads; never exempt one.
    if "<<" in command:
        return False
    segments = re.split(r"&&|\|\||;|\||\n", command)
    saw_one = False
    for raw in segments:
        seg = raw.strip()
        if not seg:
            continue
        parts = seg.split()
        head = parts[0]
        if head == "cd":
            continue  # positional, not an action
        if any(tuple(parts[: len(prefix)]) == prefix for prefix in extra_prefixes):
            saw_one = True
            continue
        if head == "git":
            if len(parts) < 2 or parts[1] not in READ_ONLY_GIT:
                return False
        elif head == "sed":
            # sed prints unless asked to edit; -i was already rejected above, but require the explicit print flag
            # rather than assuming.
            if "-n" not in parts:
                return False
        elif head not in READ_ONLY_COMMANDS and head not in extra_commands:
            return False
        saw_one = True
    return saw_one
