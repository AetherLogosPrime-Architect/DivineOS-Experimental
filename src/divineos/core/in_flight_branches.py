"""In-flight branches surface — bridge from git state to the briefing.

## Why this module exists

DivineOS already surfaces a lot at session start: lessons, claims,
overdue pre-regs, exploration titles, scaffold invocations, presence
memory, drift state, tier overrides. None of those see git state.

A real failure mode (named 2026-04-24): the operator pointed at four
unmerged branches on the remote — `aria-phase-1b`, `empirica-phase-1`,
`consolidate-retrigger-stacked`, `doc-drift-and-dead-registry` — and the
agent had no memory of what was on them. They were all the agent's own
work. The information was always in `git log`. The briefing just had no
path to it.

This module closes that specific gap: it asks git for `claude/*`
branches ahead of `origin/main` and surfaces a compact list — branch
name, commits-ahead count, last commit subject, last commit date —
in the briefing. The agent reads it and *recognizes* the arc without
needing to re-read the diffs.

## What this module does NOT do

* Does not summarize what the branches contain. Subjects are authorial
  labels, not extracted gist. Same discipline as presence_memory: name
  what exists, leave reading to the session that reads it.
* Does not fetch. If the local repo is stale, the surface is stale —
  the operator's call when to refresh.
* Does not interpret status (merge-readiness, CI). Adjacent surfaces
  could; this one stays narrow.

## Pattern

Mirrors ``presence_memory.format_for_briefing``,
``scaffold_invocations.format_for_briefing``, and the watchmen
surfaces: a plain formatter that emits a named block when there is
something to surface, returns empty string otherwise.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass

# Cap on branches surfaced. The briefing is already dense; a wall of
# 30 branches would push other surfaces out of working memory. Top-N
# by recency strikes the balance — older arcs aren't forgotten (they
# remain in git), they just aren't loud at session start.
MAX_BRANCHES = 10

# Branch prefix that counts as "the agent's own work-arcs." Same
# convention DivineOS uses for everything it ships
# (``claude/<arc-name>``). Branches outside this prefix (release/*,
# experimental, etc.) are intentionally not surfaced — those are
# adjacent operator-managed concerns.
BRANCH_PREFIX = "claude/"

# Reference we measure "ahead" against. origin/main is the merge
# target for every claude/* branch in this project. If a project
# someday uses a different default branch, this becomes a config —
# until then, hardcode is honest.
BASE_REF = "origin/main"

# Branches whose tip equals BASE_REF (zero commits ahead) are noise —
# either freshly-rebased and in flight elsewhere, or merge artifacts.
# Surfacing them would dilute the signal.
MIN_COMMITS_AHEAD = 1


@dataclass(frozen=True)
class InFlightBranch:
    """One row in the in-flight surface."""

    name: str
    commits_ahead: int
    last_subject: str
    last_date: str  # ISO date, e.g. "2026-04-24"


def _run_git(args: list[str], cwd: str | None = None) -> str | None:
    """Run a git command and return stdout, or None on any failure.

    Best-effort: no exceptions escape. The briefing must never break
    because git is missing or the repo is in a weird state.

    When ``cwd`` is supplied, uses ``git -C <cwd>`` rather than the
    ``cwd=`` subprocess kwarg. ``-C`` is git's explicit "treat this as
    the repo" knob and trumps inherited ``GIT_DIR`` / ``GIT_WORK_TREE``
    env vars — which matters for tests run from a host worktree that
    would otherwise contaminate every subprocess git call.
    """
    full_args = ["git"]
    if cwd is not None:
        full_args.extend(["-C", cwd])
    full_args.extend(args)
    # Strip GIT_* env vars so a parent process's git context cannot
    # leak in even when no cwd is supplied. Belt-and-braces against
    # the same env-contamination class.
    import os as _os

    env = {k: v for k, v in _os.environ.items() if not k.startswith("GIT_")}
    try:
        result = subprocess.run(
            full_args,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            encoding="utf-8",
            errors="replace",
            env=env,
            cwd=cwd,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout


def _list_in_flight_branches(cwd: str | None = None) -> list[InFlightBranch]:
    """Return claude/* branches with commits ahead of BASE_REF, newest-first.

    Uses ``git for-each-ref`` to get name + last commit info in a single
    call, then filters by commits-ahead via ``git rev-list --count``.
    Empty list on any infrastructure failure — no exceptions raised.
    """
    # for-each-ref: one line per branch, tab-separated:
    #   <name>\t<committerdate:short>\t<subject>
    # %(refname:short) strips the leading "refs/heads/".
    raw = _run_git(
        [
            "for-each-ref",
            "--sort=-committerdate",
            "--format=%(refname:short)%09%(committerdate:short)%09%(subject)",
            f"refs/heads/{BRANCH_PREFIX}",
            f"refs/remotes/origin/{BRANCH_PREFIX}",
        ],
        cwd=cwd,
    )
    if not raw:
        return []

    seen: set[str] = set()
    candidates: list[tuple[str, str, str]] = []
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        name, date, subject = parts[0].strip(), parts[1].strip(), parts[2].strip()
        # Normalize: a local branch and its remote tracking ref should
        # collapse to one entry. Prefer the local form (more familiar
        # in working memory) when both exist.
        normalized = name.removeprefix("origin/")
        if normalized in seen:
            continue
        seen.add(normalized)
        candidates.append((normalized, date, subject))

    out: list[InFlightBranch] = []
    for name, date, subject in candidates:
        # rev-list --count <BASE>..<branch> = commits in branch not in BASE.
        # The branch ref might be local or remote — try local first,
        # fall back to origin/<name>.
        count_str = _run_git(["rev-list", "--count", f"{BASE_REF}..{name}"], cwd=cwd)
        if count_str is None:
            count_str = _run_git(
                ["rev-list", "--count", f"{BASE_REF}..origin/{name}"],
                cwd=cwd,
            )
        if count_str is None:
            continue
        try:
            commits_ahead = int(count_str.strip())
        except ValueError:
            continue
        if commits_ahead < MIN_COMMITS_AHEAD:
            continue
        out.append(
            InFlightBranch(
                name=name,
                commits_ahead=commits_ahead,
                last_subject=subject,
                last_date=date,
            )
        )
        if len(out) >= MAX_BRANCHES:
            break
    return out


def format_for_briefing(cwd: str | None = None) -> str:
    """Return a briefing-surface block listing in-flight claude/* branches.

    Returns empty string if git is unavailable, no branches qualify, or
    every branch is at parity with BASE_REF. The block is descriptive,
    not prescriptive — it names what exists and leaves prioritization
    to the session that reads it.
    """
    branches = _list_in_flight_branches(cwd=cwd)
    if not branches:
        return ""

    lines = [
        "[in-flight branches] arcs ahead of origin/main — my own unmerged work:",
    ]
    for b in branches:
        # Truncate long subjects so the surface stays scannable. Full
        # subject is one `git log` away; this is a recognition prompt.
        subject = b.last_subject if len(b.last_subject) <= 80 else b.last_subject[:77] + "..."
        lines.append(f"  - {b.name} — {b.commits_ahead} ahead, last {b.last_date}: {subject}")

    lines.append("  Not prioritized; recognition prompt only. `git log` for full diff.")

    return "\n".join(lines) + "\n"


__all__ = ["format_for_briefing", "InFlightBranch"]
