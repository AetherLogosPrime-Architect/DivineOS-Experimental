"""Warn when a branch has grown far past the last audit that actually read it.

PRESCRIBED BY ALETHEIA, 2026-08-25, in the ruling on PR #437: *the size IS the
finding.* Filed the same day as the structural fix for correction #533 and then
not built, while the branch it was prescribed for grew another hundred and eight
commits. This is that checker, arriving late enough to be its own best evidence.

WHY THE ANCHOR IS THE CONFIRM AND NOT ``main``
----------------------------------------------
A branch fifty commits past ``main`` may be perfectly fine if review moved along
with it. Fifty commits past the last CONFIRMED anchor is fifty nobody has read,
and that is the number that decides whether an auditor can still hold the thing
in their head. Measuring against ``main`` would call a well-reviewed long branch
dangerous and a freshly-cut unreviewed one safe, which is backwards.

The anchor comes from the Watchmen rounds. Their focus and notes carry the tips
an external auditor measured against origin herself -- ``tip <sha>`` written in
her own prose at confirm time. That is deliberately the same text a human reads:
a machine-readable field would be one more thing to keep in sync with what was
actually said, and the prose is the record.

WHY A WARNING AND NOT A BLOCK
-----------------------------
Her wording, and Andrew 2026-07-15: gates are helpers. A block here would refuse
every push on an already-large branch, and the only satisfiable answer would be
switching it off -- the shape ``orphan_modules_baseline.txt`` exists to avoid.
The failure this addresses is not that a big branch gets pushed. It is that
nothing in the build flow gets louder as a branch grows, so after reading a
ruling about size I had exactly the same signal as before reading it: none.

COULD-NOT-LOOK IS NOT ALL-CLEAR
-------------------------------
If no anchor can be found for this branch, that is reported as *no anchor found*
and never as *within limits*. A branch with no confirm is the least-reviewed
case there is, so silence would be the exact inversion of the truth. This is the
fourth invariant from the consolidation design (Aria and Aether, 2026-08-24): a
check that cannot run must never be able to report success.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

import _repo_import  # noqa: F401  -- must precede the divineos import

COMMIT_LIMIT = 30
FILE_LIMIT = 60

# `tip <40-hex>` or `tip: <40-hex>`, and the same for short forms an auditor may
# have written by hand. Anchored on the word so a bare sha in other prose -- a
# patch-id, a tree-hash -- is not mistaken for a commit anyone confirmed.
_TIP_RE = re.compile(r"\btip:?\s+([0-9a-f]{7,40})\b", re.IGNORECASE)


def _git(*args: str) -> str:
    """Run git and return stdout, or an empty string if it failed.

    Empty means "could not answer" here and every caller treats it that way --
    none of them convert it into a passing verdict.
    """
    try:
        out = subprocess.run(
            ["git", *args], capture_output=True, text=True, timeout=30, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def current_branch() -> str:
    return _git("rev-parse", "--abbrev-ref", "HEAD")


def strip_remote(branch: str) -> str:
    """`origin/foo/bar` -> `foo/bar`; anything else unchanged.

    Only a real configured remote is stripped, so a local branch legitimately
    named `origin/...` -- or one whose first segment merely resembles a remote --
    keeps its name instead of being quietly shortened into a different branch.
    """
    remotes = [r for r in _git("remote").splitlines() if r.strip()]
    for remote in remotes:
        prefix = f"{remote}/"
        if branch.startswith(prefix):
            return branch[len(prefix) :]
    return branch


def anchors_for_branch(branch: str, limit: int = 60) -> list[tuple[str, str]]:
    """(round_id, tip) pairs from rounds whose text names this branch.

    Newest first, and the tip is the NEAREST one following the branch name.

    A round routinely covers several PRs in one block of prose -- round
    ec31cf1d9d5b names four branches and five shas. The first version of this
    took every tip in any round mentioning the branch, and on its first real run
    it anchored PR #437 to PR #432's tip and printed a confident count against
    it. A true number about the wrong subject, which is the failure this whole
    file exists to make visible, reproduced inside the file itself.

    Nearest-following is still prose parsing and it can still be wrong; what it
    cannot do is silently prefer an unrelated branch's sha that happened to
    appear earlier. When no tip follows the branch name at all, the branch
    contributes nothing rather than borrowing one from above it.
    """
    try:
        from divineos.core.watchmen.store import list_rounds
    except ImportError:
        return []
    try:
        rounds = list_rounds(limit=limit)
    except Exception:  # noqa: BLE001 -- a broken store must not be a clean bill
        return []

    # An auditor writes the branch by its own name; the caller may hand us a
    # remote-tracking ref. Matching the raw string missed every round on the
    # first run against the very branch this checker was prescribed for.
    needle = strip_remote(branch)

    found: list[tuple[str, str]] = []
    for rnd in rounds:
        text = f"{getattr(rnd, 'focus', '')} {getattr(rnd, 'notes', '')}"
        round_id = getattr(rnd, "round_id", "?")
        for name_match in re.finditer(re.escape(needle), text):
            tip_match = _TIP_RE.search(text, name_match.end())
            if tip_match:
                found.append((round_id, tip_match.group(1)))
    return found


def growth_since(anchor: str, branch: str) -> tuple[int, int] | None:
    """(commits, files) between anchor and the branch tip, or None if unreadable.

    None rather than (0, 0): an anchor this checkout has never fetched is a
    thing we could not look at, and zero would read as a branch that has not
    moved -- the exact confusion this module's docstring refuses.
    """
    if not _git("cat-file", "-t", anchor):
        return None
    commits = _git("rev-list", "--count", f"{anchor}..{branch}")
    files = _git("diff", "--name-only", f"{anchor}...{branch}")
    if not commits:
        return None
    return int(commits), len([line for line in files.splitlines() if line.strip()])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--branch", default="", help="Branch to measure (default: HEAD).")
    parser.add_argument(
        "--commit-limit", type=int, default=COMMIT_LIMIT, help=f"default {COMMIT_LIMIT}"
    )
    parser.add_argument("--file-limit", type=int, default=FILE_LIMIT, help=f"default {FILE_LIMIT}")
    args = parser.parse_args(argv)

    branch = args.branch or current_branch()
    if not branch or branch == "HEAD":
        print("[branch-growth] could not determine the branch — NOT a clean result.")
        return 0

    anchors = anchors_for_branch(branch)
    if not anchors:
        print(f"[branch-growth] no CONFIRMED anchor found for {branch}.")
        print("[branch-growth] This is 'could not look', NOT 'within limits'. A branch")
        print("[branch-growth] with no confirm is the least-reviewed case there is.")
        return 0

    # The most recent anchor that this checkout can actually resolve. An auditor
    # may have confirmed a tip that was later rewritten away; walking down to the
    # newest resolvable one measures against real history rather than refusing.
    for round_id, tip in anchors:
        growth = growth_since(tip, branch)
        if growth is None:
            continue
        commits, files = growth
        over = commits > args.commit_limit or files > args.file_limit
        if not over:
            print(
                f"[branch-growth] {branch}: {commits} commit(s), {files} file(s) "
                f"past confirmed {tip[:8]} ({round_id}) — within limits."
            )
            return 0
        print("")
        print(f"[branch-growth] WARNING — {branch} has grown past what anyone has read.")
        print(f"[branch-growth]   {commits} commit(s) and {files} file(s) past {tip[:8]},")
        print(f"[branch-growth]   the tip confirmed in {round_id}.")
        print(f"[branch-growth]   Limits: {args.commit_limit} commits / {args.file_limit} files.")
        print("[branch-growth]")
        print("[branch-growth] Aletheia 2026-08-25, on PR #437: the size IS the finding.")
        print("[branch-growth] An auditor cannot hold this many changes at once, so a")
        print("[branch-growth] confirm on it means less than a confirm on a small one.")
        print("[branch-growth] Cut it, or request a fresh confirm before it grows further.")
        print("[branch-growth] Not blocking — this is a helper, and the push continues.")
        print("")
        return 0

    print(f"[branch-growth] {len(anchors)} anchor(s) named for {branch}, none resolvable here.")
    print("[branch-growth] This is 'could not look', NOT 'within limits'. Fetch, or")
    print("[branch-growth] the confirmed tips were rewritten away.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
