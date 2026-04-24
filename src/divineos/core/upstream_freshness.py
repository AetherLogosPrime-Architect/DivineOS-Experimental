"""Upstream-freshness surface — bridge from remote-state to the briefing.

## Why this module exists

The pre-push branch-freshness hook (PR #200) catches the silent-revert
precondition at the latest possible moment: when the agent tries to push
a stale-base branch. Useful, but reactive — by the time the hook fires,
the agent has already committed work onto a stale base and now has to
rebase. The auditor's review of #200 named this as a structural
follow-up:

  *"This check enforces discipline; it doesn't prevent the THINKING
  ERROR that leads to stale branches. Upstream prevention would be a
  session-start surface that says: 'origin/main has advanced N commits
  since your local main last fetched.' Same pattern, different target.
  It would close the loop: the agent sees at session start that local
  main is stale, fetches before branching, never hits the freshness
  check because the branch was created from fresh main."*

This module is that surface. At briefing time it fetches origin/main
quietly, compares the local main to the remote tip, and emits a block
when local is behind. Recognition prompt only — the agent reads it,
fetches before branching, never produces the failure mode.

## What this module does NOT do

* Does not auto-fetch outside the briefing window. One fetch per
  briefing call is enough; finer-grained polling is overhead without
  signal.
* Does not auto-pull. Pull strategy varies (fast-forward only, rebase,
  merge); the agent decides. Surface only names what's true.
* Does not block. Recognition prompt — same descriptive-only discipline
  as in_flight_branches and module_inventory.

## Pattern

Mirrors ``in_flight_branches.format_for_briefing`` and
``module_inventory.format_for_briefing``: a plain formatter that emits
a named block when there is something to surface, returns empty
string otherwise. Best-effort — every git interaction wrapped in
try/except returning empty string on failure so the briefing never
breaks because git is missing or the network is down.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

# Branch we measure freshness against. Same constant DivineOS uses
# everywhere — origin/main as the canonical merge target.
BASE_BRANCH = "main"
REMOTE = "origin"

# Hard timeout on the fetch step. Briefings should never stall.
# 5 seconds is generous for a refspec-scoped fetch on broadband; on
# slow networks the surface goes silent rather than blocking.
_FETCH_TIMEOUT_SECONDS = 5

# Hard timeout on follow-up git introspection commands. Once we have
# refs locally these are sub-second operations; the timeout exists
# only to defend against pathological hangs.
_INTROSPECTION_TIMEOUT_SECONDS = 3


@dataclass(frozen=True)
class UpstreamFreshness:
    """Result of comparing local BASE_BRANCH to REMOTE/BASE_BRANCH."""

    local_behind: int
    """Commits in origin/main that local main does not have."""

    local_ahead: int
    """Commits in local main not yet on origin/main. Usually zero —
    if non-zero, the operator has unpushed local-main work, which is
    a different (but related) condition worth naming."""

    remote_subject: str
    """First-line subject of the remote tip commit. Recognition prompt."""


def _run_git(args: list[str], cwd: str | None, timeout: float) -> str | None:
    """Run a git command, returning stdout on success, None on any failure.

    Best-effort: all error paths fold to None. The briefing must never
    crash because of git, network, or environment state.

    Strips ``GIT_*`` env vars to defend against parent-process git
    context contamination — same belt-and-braces as
    ``in_flight_branches._run_git``.
    """
    full_args = ["git"]
    if cwd is not None:
        full_args.extend(["-C", cwd])
    full_args.extend(args)
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    try:
        result = subprocess.run(
            full_args,
            capture_output=True,
            text=True,
            timeout=timeout,
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


def _check_freshness(cwd: str | None = None) -> UpstreamFreshness | None:
    """Fetch origin/main and compute (behind, ahead) counts. None on any failure."""
    # Fetch refs/heads/main from origin into refs/remotes/origin/main.
    # Scoped to the single ref we care about — minimizes work and
    # leaves other remote refs untouched.
    if (
        _run_git(
            ["fetch", "--quiet", REMOTE, BASE_BRANCH],
            cwd=cwd,
            timeout=_FETCH_TIMEOUT_SECONDS,
        )
        is None
    ):
        return None

    remote_ref = f"refs/remotes/{REMOTE}/{BASE_BRANCH}"
    if (
        _run_git(
            ["rev-parse", "--verify", "--quiet", remote_ref],
            cwd=cwd,
            timeout=_INTROSPECTION_TIMEOUT_SECONDS,
        )
        is None
    ):
        return None

    # Local BASE_BRANCH may not exist (some workflows don't keep a
    # local main). When absent, treat as "no signal" and skip — the
    # surface is about local-main staleness, not arbitrary HEAD state.
    local_ref = f"refs/heads/{BASE_BRANCH}"
    if (
        _run_git(
            ["rev-parse", "--verify", "--quiet", local_ref],
            cwd=cwd,
            timeout=_INTROSPECTION_TIMEOUT_SECONDS,
        )
        is None
    ):
        return None

    behind = _run_git(
        ["rev-list", "--count", f"{local_ref}..{remote_ref}"],
        cwd=cwd,
        timeout=_INTROSPECTION_TIMEOUT_SECONDS,
    )
    ahead = _run_git(
        ["rev-list", "--count", f"{remote_ref}..{local_ref}"],
        cwd=cwd,
        timeout=_INTROSPECTION_TIMEOUT_SECONDS,
    )
    if behind is None or ahead is None:
        return None
    try:
        behind_n = int(behind.strip())
        ahead_n = int(ahead.strip())
    except ValueError:
        return None

    subject = _run_git(
        ["log", "-1", "--format=%s", remote_ref],
        cwd=cwd,
        timeout=_INTROSPECTION_TIMEOUT_SECONDS,
    )
    subject_str = (subject or "").strip()

    return UpstreamFreshness(
        local_behind=behind_n,
        local_ahead=ahead_n,
        remote_subject=subject_str,
    )


def format_for_briefing(cwd: str | None = None) -> str:
    """Return a briefing-surface block when local main is stale.

    Returns empty string when:
      * git is unavailable, fetch failed, or refs aren't resolvable
      * local main is not behind origin/main (the common case)

    The block fires when local main is behind. When local is also
    ahead (rare — unpushed local-main work), that's named too because
    it's a related condition: branching off local main wouldn't be
    stale, but the unpushed work itself is a small signal worth
    seeing.
    """
    freshness = _check_freshness(cwd=cwd)
    if freshness is None:
        return ""
    if freshness.local_behind == 0:
        return ""

    plural = "commit" if freshness.local_behind == 1 else "commits"
    subject = freshness.remote_subject
    if len(subject) > 80:
        subject = subject[:77] + "..."

    lines = [
        f"[upstream freshness] local {BASE_BRANCH} is "
        f"{freshness.local_behind} {plural} behind {REMOTE}/{BASE_BRANCH}.",
        f"  Latest on remote: {subject}" if subject else "  (remote subject unavailable)",
        "  Fetch + fast-forward before branching:",
        f"    git fetch {REMOTE} && git checkout {BASE_BRANCH} && git merge --ff-only "
        f"{REMOTE}/{BASE_BRANCH}",
    ]
    if freshness.local_ahead > 0:
        ahead_plural = "commit" if freshness.local_ahead == 1 else "commits"
        lines.append(
            f"  Note: local {BASE_BRANCH} also has {freshness.local_ahead} unpushed "
            f"{ahead_plural}; the merge above will refuse if not fast-forwardable."
        )

    return "\n".join(lines) + "\n"


__all__ = ["format_for_briefing", "UpstreamFreshness"]
