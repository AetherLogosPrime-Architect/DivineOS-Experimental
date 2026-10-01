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


# Options of `git push` that take a separate value, so the value is not the remote.
_VALUE_OPTIONS = {"-o", "--push-option", "--repo", "--receive-pack", "--exec"}
# Options that send branches whatever refspecs follow.
_BRANCH_SENDING_OPTIONS = {"--all", "--mirror", "--branches"}


def _destination_is_tag(refspec: str) -> bool:
    """The DESTINATION half decides: ``refs/tags/x:refs/heads/main`` lands a branch."""
    refspec = refspec.lstrip("+")
    destination = refspec.split(":", 1)[1] if ":" in refspec else refspec
    return destination.startswith("refs/tags/")


def _segment_pushes_only_tags(segment: str) -> bool:
    import shlex

    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    args = tokens[2:]  # after `git push`
    tags_flag = False
    positionals: list[str] = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in _BRANCH_SENDING_OPTIONS:
            return False  # both-empty: unparseable and sends-a-branch both mean the same thing to the caller -- run the branch check
        if arg == "--tags":
            tags_flag = True
        elif arg in _VALUE_OPTIONS:
            i += 1
        elif not arg.startswith("-"):
            positionals.append(arg)
        i += 1
    refspecs = positionals[1:]  # the first positional is the remote
    if not refspecs:
        return tags_flag
    j = 0
    while j < len(refspecs):
        if refspecs[j] == "tag" and j + 1 < len(refspecs):
            j += 2  # `git push origin tag v1` names a tag by keyword
            continue
        if not _destination_is_tag(refspecs[j]):
            return False
        j += 1
    return True


def pushes_only_tags(command: str) -> bool:
    """True only when every ref the push could send lands under ``refs/tags/``.

    A tag is a snapshot. It never merges, so asking a branch question of it --
    is it fresh, would it delete anything from main -- refuses it for being
    what it is. Aria 2026-09-24: an archive tag of a local-only fix was
    refused as "twelve behind main", and the fix stayed on one disk.

    Could-not-tell answers False, so the branch check runs: a parse failure,
    ``--all``/``--mirror``/``--branches``, or a bare name such as
    ``archive/foo``, which git may resolve to a branch. Spell a tag push
    ``refs/tags/<name>`` and it is recognised.
    """
    segments = [s.strip() for s in re.split(r"&&|;|\|\|", command or "")]
    pushes = [s for s in segments if _GIT_PUSH_RE.match(s)]
    return bool(pushes) and all(_segment_pushes_only_tags(s) for s in pushes)


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
