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


def is_tag_only_push(command: str) -> bool:
    """True when a `git push` sends ONLY tags, judged from the command text.

    WHY THIS EXISTS, and it is Aria's finding (2026-08-31). There are TWO push
    gates in this house. The git-level one now reads git's pre-push protocol on
    stdin and asks whether every ref begins with refs/tags -- the object rather
    than the name. The Claude-level hook never has: it detects a push from the
    command string and then runs a branch-health check on the CHECKED-OUT
    branch, which for a tag push is a verdict about something the push does not
    touch.

    So her tag push was refused, my repair landed in the other gate, and from
    my side the path looked open. Her sentence: there is a second copy of the
    refusal living somewhere the fix does not reach. I believed the path was
    open because I had fixed A gate, not because I had checked THE gate that
    refused her -- honest and not truthful, which is the distinction Aletheia
    wrote down for exactly this.

    WHAT THIS CAN AND CANNOT KNOW, stated because the boundary is the honesty
    of it. At the command level `git push origin v1.0` is indistinguishable
    from pushing a branch named v1.0; git resolves that against the ref
    namespace and this function cannot.

        recognised as tag-only   explicit refs/tags/... refspecs, and --tags
        NOT recognised           a bare tag name, which stays fully checked

    The unrecognised case falls to the STRICT side, which is the right
    direction for a skip: an unrecognised tag push costs a branch check it did
    not need, while a wrongly-skipped branch push silently disarms the gate.
    Archival history tags are pushed by explicit refspec, so the case that
    actually recurs is the one this covers.
    """
    if not is_git_push_command(command):
        return False

    for segment in re.split(r"&&|;|\|\|", command):
        segment = segment.strip()
        if not _GIT_PUSH_RE.match(segment):
            continue

        saw_tag_ref = False
        for arg in segment.split()[2:]:  # drop `git push`
            if arg == "--tags":
                saw_tag_ref = True
            elif arg.startswith("refs/tags/"):
                saw_tag_ref = True
            elif arg.startswith("refs/"):
                return False  # an explicit non-tag ref: not tag-only
            # Anything else is a flag, a remote, or a ref this cannot
            # classify. None of those PROVE tag-only, so none of them set
            # the flag -- only the explicit forms above do.
        return saw_tag_ref

    return False
