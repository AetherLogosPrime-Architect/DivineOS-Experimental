"""Detect whether a shell command is a `git push` invocation.

Used by the PreToolUse(Bash) `check-branch-on-push` hook to decide
whether to fire the branch-health check before letting a push go
through. Task #93 — wire-up of the existing `divineos check-branch`
CLI surface as a pre-push gate.

## Design (Aether 2026-06-07, learned from the 2026-06-06 gate-cascade)

The matcher is ANCHORED. Substring matches in echo arguments / quoted
data / grep haystacks must not trigger — same lesson as the obligation
gate's `is_substrate_write_command`. The cascade-deadlock pattern
(broken matcher triggers on substring inside other tools' args) is
covered by regression tests.

A command counts as a git-push when, after stripping a single optional
`cd` prefix segment joined by `&&` or `;`, the next segment begins with
`git push` (with `git` and `push` separated by whitespace, no other
tokens in between).

Not matched (intentionally):
- `echo 'git push'`  — substring in quoted data
- `cat << EOF\\ngit push ... \\nEOF`  — heredoc text
- `grep 'git push' some_file`  — searching for the phrase
- `git status` / `git pull` / `git fetch`  — other git subcommands
- `pushd /tmp && git status`  — `push` substring inside `pushd`
"""

from __future__ import annotations

import re

# Anchored: optional leading whitespace, then `git`, then 1+ whitespace,
# then `push`, then a word boundary. The `\b` after push ensures we
# don't match `git pushd` or similar.
_GIT_PUSH_RE = re.compile(r"^\s*git\s+push\b")


def is_git_push_command(command: str) -> bool:
    """True when the shell command's primary action is `git push`.

    Handles single-segment commands and the common `cd <dir> && git push`
    chained form. Substring occurrences inside quoted data, heredocs, or
    other tools' arguments must NOT match — see regression tests.
    """
    if not command or not command.strip():
        return False
    # Split on shell chain separators and check each segment. A real
    # `git push` is always its own segment; substring-in-data is never
    # its own segment.
    for segment in re.split(r"&&|;|\|\|", command):
        segment = segment.strip()
        if not segment:
            continue
        if _GIT_PUSH_RE.match(segment):
            return True
    return False


_CD_PREFIX_RE = re.compile(r"""\s*cd\s+("[^"]+"|'[^']+'|\S+)""")
_GIT_BASH_DRIVE_RE = re.compile(r"^/([A-Za-z])(?:/|$)")


def windows_path_from_git_bash(path: str) -> str:
    """``/c/w507`` -> ``C:/w507``. Anything not in that form comes back unchanged."""
    return _GIT_BASH_DRIVE_RE.sub(lambda m: f"{m.group(1).upper()}:/", path, count=1)


def push_cwd(command: str, *, windows: bool | None = None) -> str | None:
    """The working tree a leading ``cd <path> &&`` names, or None if it names none.

    Lived as inline Python inside check-branch-on-push.sh until 2026-09-24,
    against this module's own rule that the matcher logic lives here, tested.
    Untested, it missed one thing: the hook's interpreter is WINDOWS Python,
    and a path written the Git-Bash way -- ``/c/w507`` -- reads to it as
    ``C:\\c\\w507``. The isdir check failed, the hook fell back to the session
    folder, and Aria's push from a worktree 0 behind main was refused as "12
    behind" because the SESSION folder was 12 behind (her finding, proved by
    pushing again with ``cd "C:/w507"``). A false alarm on every worktree push
    written the bash way, which is how a gate trains its own bypass.

    Returns the path only when it really is a git working tree, so a wrong
    guess falls back to the ambient root rather than checking some other tree.
    """
    import os

    match = _CD_PREFIX_RE.match(command or "")
    if not match:
        return None
    path = match.group(1).strip("\"'")
    if windows if windows is not None else os.name == "nt":
        path = windows_path_from_git_bash(path)
    marker = os.path.join(path, ".git")
    if os.path.isdir(marker) or os.path.isfile(marker):
        return path
    return None
