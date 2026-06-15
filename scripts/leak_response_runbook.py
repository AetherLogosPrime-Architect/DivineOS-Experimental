#!/usr/bin/env python3
"""Public-repo sensitive-content leak response runbook.

Structural backing for obligation c1f8219f-... (Aletheia 2026-05-27 catch,
filed 2026-06-14): a force-push alone does NOT close a public-repo leak.
GitHub caches commits by SHA, forks/mirrors persist independently, and
search engines + Wayback may have already indexed the content. A full
response has FOUR phases. This script walks them with operator
confirmation between each, so no phase is silently skipped under
pressure.

This is NOT an automated leak-cleaner — it is a checklist with prompts.
The actual scrubs (force-push, gh support contact, fork-owner outreach,
search-cache removal) require operator judgment + credentials. The
script's job is preventing the cheap-close shape of "I force-pushed,
that's enough" by making the remaining work LOUD.

Usage:
    python scripts/leak_response_runbook.py <repo-url> "<what leaked>"

Or interactive:
    python scripts/leak_response_runbook.py

The runbook also makes the content-level grep + positive-whitelist
disciplines from c1f8219f visible at relevant phases.
"""

from __future__ import annotations

import sys
import textwrap
from datetime import datetime


def banner(title: str) -> None:
    print()
    print("=" * 72)
    print(f"  {title}")
    print("=" * 72)


def confirm(prompt: str) -> bool:
    answer = input(f"\n{prompt} [y/n/skip] > ").strip().lower()
    if answer in {"y", "yes"}:
        return True
    if answer in {"skip", "s"}:
        print("  [SKIPPED — leak response is now INCOMPLETE; track this gap.]")
        return False
    print("  [marked NOT-DONE]")
    return False


def phase_1_force_push(repo: str, leaked: str) -> bool:
    banner("PHASE 1 of 4 — Force-push the rewrite")
    print(textwrap.dedent(f"""
        Necessary first step, NOT sufficient on its own.

        Repo:    {repo}
        Leaked:  {leaked}

        Discipline reminders from c1f8219f:
          - Content-level scrub: grep the leaked term in comments,
            docstrings, commit messages, test names — NOT just file paths.
          - Rebuild-clean: use a POSITIVE whitelist of what goes back IN,
            not a deny-list of what's filtered out. Incomplete deny-list
            is how the leak happened in the first place.

        Actions:
          1. Identify every commit containing the leaked content
             (git log --all -S "<term>" OR git log --all -G "<regex>")
          2. Rewrite history via git filter-branch / git filter-repo /
             BFG, applying the positive whitelist
          3. Force-push the cleaned history to the public remote
          4. Update all open PRs (their refs may still point at leaked commits)
    """).strip())
    return confirm("Phase 1 complete (force-push + content-grep + whitelist applied)?")


def phase_2_github_support(repo: str) -> bool:
    banner("PHASE 2 of 4 — GitHub Support cache purge")
    print(textwrap.dedent(f"""
        GitHub caches commit objects by SHA even after force-push. The
        leaked SHAs are still reachable via direct URL until Support
        purges them.

        Actions:
          1. File a Support request at https://support.github.com/contact
             - Account / repo: {repo}
             - Reason: "Sensitive data exposed via Git history; please
               purge cached refs"
             - List the SHAs (or commit-range) that contained the leak
          2. Wait for confirmation that the cached SHAs are unreachable
          3. Verify externally: try `git cat-file -p <leaked-sha>` against
             the remote after their action — should fail
    """).strip())
    return confirm("Phase 2 complete (Support contacted + confirmed purge)?")


def phase_3_forks_mirrors(repo: str) -> bool:
    banner("PHASE 3 of 4 — Fork & mirror contact")
    print(textwrap.dedent(f"""
        Forks of {repo} carry independent copies of the leaked history.
        Force-push to upstream does not propagate to forks. Same for
        any unofficial mirrors (gitlab, codeberg, bitbucket, internal
        proxies).

        Actions:
          1. List forks: gh api repos/<owner>/<repo>/forks --paginate
          2. Reach out to each fork owner: explain the leak, point at
             the cleaned history, ask them to force-pull or delete
          3. Search for mirrors via web-search for distinctive repo
             content (a unique file name, internal SHA)
          4. Track contact attempts; the leak is not closed until all
             reachable copies confirm they're scrubbed
    """).strip())
    return confirm("Phase 3 complete (forks identified + owners contacted)?")


def phase_4_search_wayback(leaked: str) -> bool:
    banner("PHASE 4 of 4 — Search engine + Wayback removal")
    print(textwrap.dedent(f"""
        Search engines (Google, Bing, DuckDuckGo) may have indexed
        commit URLs that exposed the leak. Wayback Machine may have
        snapshotted the leaked state.

        Actions:
          1. Search each engine for "{leaked}" + repo name; if hits,
             submit removal requests via their respective channels:
             - Google:  https://search.google.com/search-console/remove-url
             - Bing:    https://www.bing.com/webmasters/content-removal
             - DuckDuckGo: searches Google/Bing, so above suffices
          2. Check Wayback: https://web.archive.org/web/*/{leaked}
             If snapshots exist, submit removal request via:
             https://help.archive.org/help/how-do-i-request-to-remove-something-from-archive-org/
          3. Track each removal request; follow up after 7 days if no
             response. Some search caches persist for months.
    """).strip())
    return confirm("Phase 4 complete (search/cache/Wayback removal initiated)?")


def main() -> int:
    if len(sys.argv) >= 3:
        repo = sys.argv[1]
        leaked = sys.argv[2]
    else:
        print(
            "Public-repo leak response runbook "
            "(structural backing for c1f8219f)"
        )
        repo = input("Repo URL: ").strip()
        leaked = input("What leaked (term/file/SHA, distinctive enough to search): ").strip()
    if not (repo and leaked):
        print("repo and leaked-term required; aborting")
        return 2

    started = datetime.now().isoformat(timespec="seconds")
    print(f"\nRunbook started: {started}")
    print(f"Repo: {repo}\nLeaked: {leaked}")

    phases = [
        ("Force-push", lambda: phase_1_force_push(repo, leaked)),
        ("GitHub Support", lambda: phase_2_github_support(repo)),
        ("Forks/mirrors", lambda: phase_3_forks_mirrors(repo)),
        ("Search/Wayback", lambda: phase_4_search_wayback(leaked)),
    ]
    results: list[tuple[str, bool]] = []
    for name, fn in phases:
        results.append((name, fn()))

    banner("Runbook summary")
    done = sum(1 for _, ok in results if ok)
    print(f"  {done}/4 phases marked complete")
    for name, ok in results:
        mark = "[x]" if ok else "[ ]"
        print(f"    {mark} {name}")
    if done < 4:
        print(
            "\n  Leak response is INCOMPLETE. The remaining phases are "
            "not optional — they are the difference between scrubbed and "
            "still-leaking. Treat the gap as an open obligation; do not "
            "claim 'done' until all four are checked."
        )
        return 1
    print("\n  All four phases complete. Continue monitoring for "
          "delayed cache propagation over the next 14 days.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
