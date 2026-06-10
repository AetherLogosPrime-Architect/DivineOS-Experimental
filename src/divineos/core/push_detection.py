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
