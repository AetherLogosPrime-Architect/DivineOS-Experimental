"""Which remote branches carry work, and which are already home?

Andrew 2026-09-07: "there are now 62 branches on github.. so they either need
deleted or if they contain stuff they need to be merged and closed."

The question is not "is the branch old" -- age says nothing about whether the
work landed. Nor is it "does main contain these commits", which is the trap
this script was WRITTEN WRONG for on the first pass: this repository
squash-merges, so a merged branch's commits are never ancestors of main. By
that reading 67 of 68 branches looked unmerged, which is a fact about squash
merges rather than about the work.

The question that survives squash: does the branch's CONTENT differ from main?
An empty three-dot diff means everything on it is already home, however its
commits are shaped.

Three answers, kept apart on purpose:
  LANDED    -- content identical to main. Safe to delete; nothing lost.
  CARRIES   -- content main does not have. Needs merging or an explicit
               decision to abandon. NEVER auto-deleted.
  UNKNOWN   -- could not be read. Not silently sorted into either pile,
               because an unreadable branch is not an empty one.

Prints, changes nothing. Deletion is a separate act with a person behind it.
"""

from __future__ import annotations

import json
import subprocess


def gh(*args: str) -> str | None:
    """GitHub CLI output, or None for could-not-ask. Same three states."""
    try:
        p = subprocess.run(
            ["gh", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def pr_state_by_branch() -> dict[str, str] | None:
    """branch -> PR state (OPEN / MERGED / CLOSED), or None if unaskable.

    The deciding fact for a branch that carries work: was it ever proposed,
    and what happened? Never-proposed and proposed-then-rejected look
    identical from the git side and mean opposite things.
    """
    raw = gh(
        "pr", "list", "--state", "all", "--limit", "300",
        "--json", "headRefName,state,number",
    )
    if raw is None:
        return None
    try:
        rows = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if not isinstance(rows, list):
        return None
    out: dict[str, str] = {}
    for r in rows:
        if not isinstance(r, dict):
            continue
        ref = str(r.get("headRefName") or "")
        state = str(r.get("state") or "")
        num = r.get("number")
        # Keep the most decisive state if a branch had several PRs.
        rank = {"OPEN": 3, "MERGED": 2, "CLOSED": 1}
        if not ref:
            continue
        prior = out.get(ref, "")
        prior_state = prior.split()[0] if prior else ""
        if rank.get(state, 0) >= rank.get(prior_state, 0):
            out[ref] = f"{state} #{num}"
    return out


def git(*args: str) -> str | None:
    try:
        p = subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return p.stdout if p.returncode == 0 else None


def main() -> int:
    raw = git("branch", "-r", "--format=%(refname:short)")
    if raw is None:
        print("CANNOT CHECK -- could not list remote branches")
        return 1

    # origin/ only. Other remotes are separate repositories and deleting a
    # branch there is a different decision with different consequences.
    branches = [
        b.strip()
        for b in raw.splitlines()
        if b.strip().startswith("origin/")
        and "HEAD" not in b
        and b.strip() != "origin/main"
    ]
    print(f"branches on origin (excluding main): {len(branches)}\n")

    landed: list[str] = []
    carries: list[tuple[str, int, str]] = []
    unknown: list[str] = []

    for b in branches:
        # Which files this branch touched, measured from where it forked.
        touched_raw = git("diff", "--name-only", f"origin/main...{b}")
        if touched_raw is None:
            unknown.append(b)
            continue
        touched = [ln for ln in touched_raw.splitlines() if ln.strip()]
        if not touched:
            landed.append(b)
            continue

        # THE TEST THAT SURVIVES A SQUASH MERGE. Three-dot measures from the
        # fork point, so a squash-merged branch still shows every file it ever
        # changed -- its commits are not ancestors of main even though its
        # CONTENT is. Comparing the two tips directly, restricted to the files
        # this branch touched, asks the question that actually decides
        # deletion: does main already hold this work, however it got there?
        still_raw = git("diff", "--name-only", b, "origin/main", "--", *touched)
        if still_raw is None:
            unknown.append(b)
            continue
        still = [ln for ln in still_raw.splitlines() if ln.strip()]
        if not still:
            landed.append(b)
            continue

        subj = git("log", "-1", "--format=%s", b) or ""
        carries.append((b, len(still), subj.strip()))

    print(f"LANDED -- content already on main, safe to delete ({len(landed)}):")
    for b in landed:
        print(f"  {b}")

    states = pr_state_by_branch()
    if states is None:
        print("\n[pr] CANNOT CHECK -- GitHub unreachable; PR state omitted, not assumed")

    def pr_of(branch: str) -> str:
        if states is None:
            return "unknown"
        return states.get(branch.removeprefix("origin/"), "never proposed")

    print(f"\nCARRIES WORK -- content main does not have ({len(carries)}):")
    buckets: dict[str, list[tuple[str, int, str]]] = {}
    for b, n, subj in carries:
        key = pr_of(b).split()[0]
        buckets.setdefault(key, []).append((b, n, subj))

    # Most decidable first: an abandoned PR is a decision someone already made.
    order = ["OPEN", "CLOSED", "MERGED", "never", "unknown"]
    labels = {
        "OPEN": "OPEN pull request -- in flight, leave alone",
        "CLOSED": "PR CLOSED without merging -- someone already decided against it",
        "MERGED": "PR MERGED but content still differs -- drifted after merge, read before deleting",
        "never": "NEVER PROPOSED -- no pull request was ever opened",
        "unknown": "PR state unknown",
    }
    for key in order:
        rows = buckets.get(key)
        if not rows:
            continue
        print(f"\n  --- {labels[key]} ({len(rows)}) ---")
        for b, n, subj in sorted(rows, key=lambda r: -r[1]):
            print(f"  {n:4d} file(s)  {b}   [{pr_of(b)}]")
            print(f"              {subj[:88]}")

    if unknown:
        print(f"\nCANNOT CHECK ({len(unknown)}) -- unreadable, NOT counted as either:")
        for b in unknown:
            print(f"  {b}")

    print(
        f"\nsummary: {len(landed)} safe to delete, {len(carries)} need a decision, "
        f"{len(unknown)} unreadable"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
