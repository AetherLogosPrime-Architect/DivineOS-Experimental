#!/usr/bin/env python3
"""What would merging this branch actually DO to the reference?

THE ONE QUESTION THIS ANSWERS, and why it is a command rather than advice:
there are three ways to ask it and only one is right, and I reached for a wrong
one twice in a single session -- the second time while alarmed, on the most
important question of the evening, hours after writing the correct answer down.

  git diff main branch          TWO-DOT. Compares the two trees as they stand.
                                A file the reference gained AFTER the branch
                                diverged shows as a DELETION, because it is on
                                one side and not the other. A merge does not
                                delete it. This form produced nine phantom
                                deletions on 2026-08-29, including a claim that
                                the test for the anchor defect would be
                                destroyed. Nothing was ever at risk.

  git diff main...branch        THREE-DOT. Compares against the merge base,
                                answering "what did this branch add". Correct
                                for contamination, structurally blind to what a
                                merge would remove.

  git merge-tree --write-tree   THE MERGE ITSELF, performed without committing.
                                The only form that answers the question the
                                words ask.

Andrew, 2026-08-30, on why this exists as a command: "you do not warn water,
water flows, it doesnt care about warning, only channels and gates, which you
control the build of." A note about the wrong diff is a speed limit sign. A
command that makes the right answer the easy one is a channel.

CONFLICTS ARE THEIR OWN ANSWER. When the merge cannot be computed, this says so
and exits distinctly rather than reporting zero deletions. Could-not-tell and
nothing-found are different answers, and collapsing them is the defect this
substrate keeps rediscovering -- including inside instruments built to find it.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Preview:
    """What a merge would change, or why the question could not be answered.

    `conflicted` is a distinct state rather than an empty result. A caller that
    reads it as "no deletions" has reintroduced the exact fault this file exists
    to remove.
    """

    reference: str
    branch: str
    resolved: bool
    conflicted: bool
    added: tuple[str, ...] = ()
    modified: tuple[str, ...] = ()
    deleted: tuple[str, ...] = ()

    @property
    def answerable(self) -> bool:
        return self.resolved and not self.conflicted


def _git(*args: str, timeout: int = 60) -> tuple[int, str]:
    """Run git in the repo, decoding output explicitly rather than by locale.

    The locale default is what broke the anchor computation on 2026-08-29: a
    diff is bytes, and forcing it through the machine's codec dies on any
    character that codec cannot map -- an em-dash, in our own prose.
    """
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
        timeout=timeout,
    )
    return proc.returncode, proc.stdout.decode("utf-8", "replace")


def _resolve(ref: str) -> bool:
    code, _ = _git("rev-parse", "--verify", "--quiet", ref)
    return code == 0


def _looks_like_tree(line: str) -> bool:
    return len(line) == 40 and all(c in "0123456789abcdef" for c in line)


def preview(branch: str, reference: str = "origin/main") -> Preview:
    """Compute what merging `branch` into `reference` would change.

    Never guesses. Three outcomes, each distinguishable by the caller:
      * resolved and not conflicted -- the lists are the answer
      * conflicted                  -- a merge is possible but not automatic
      * not resolved                -- a ref does not exist, or git failed
    """
    if not _resolve(reference) or not _resolve(branch):
        return Preview(reference=reference, branch=branch, resolved=False, conflicted=False)

    code, out = _git("merge-tree", "--write-tree", reference, branch)
    first = out.splitlines()[0].strip() if out.strip() else ""

    if code != 0:
        # merge-tree exits non-zero on conflicts AND on usage errors. A tree
        # object on the first line means it got far enough to produce one, so
        # the non-zero is a conflict rather than a failure to run.
        if _looks_like_tree(first):
            return Preview(reference=reference, branch=branch, resolved=True, conflicted=True)
        return Preview(reference=reference, branch=branch, resolved=False, conflicted=False)

    if not _looks_like_tree(first):
        return Preview(reference=reference, branch=branch, resolved=False, conflicted=False)

    code, status = _git("diff", "--name-status", reference, first)
    if code != 0:
        return Preview(reference=reference, branch=branch, resolved=False, conflicted=False)

    added: list[str] = []
    modified: list[str] = []
    deleted: list[str] = []
    for line in status.splitlines():
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        mark, path = parts[0].strip(), parts[-1].strip()
        if mark.startswith("A"):
            added.append(path)
        elif mark.startswith("D"):
            deleted.append(path)
        else:
            modified.append(path)

    return Preview(
        reference=reference,
        branch=branch,
        resolved=True,
        conflicted=False,
        added=tuple(added),
        modified=tuple(modified),
        deleted=tuple(deleted),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="What merging a branch would actually change on the reference."
    )
    parser.add_argument("branch")
    parser.add_argument("--into", default="origin/main", help="the reference being merged into")
    parser.add_argument("--list", action="store_true", help="name the paths, not just the counts")
    args = parser.parse_args(argv)

    result = preview(args.branch, args.into)

    if not result.resolved:
        print(
            f"[merge-preview] COULD NOT ANSWER for {args.branch} into {args.into}. "
            "A ref may not exist, or git failed. This is not a clean result."
        )
        return 2

    if result.conflicted:
        print(
            f"[merge-preview] {args.branch} CONFLICTS with {args.into}. What the merge "
            "would change cannot be computed until the conflict is resolved. "
            "This is NOT zero deletions."
        )
        return 3

    print(
        f"[merge-preview] merging {args.branch} into {args.into} would: "
        f"add {len(result.added)}, modify {len(result.modified)}, "
        f"DELETE {len(result.deleted)}"
    )

    if result.deleted:
        print(
            "[merge-preview] the deletions are the ones worth reading -- "
            "a removed file may exist nowhere else:"
        )
        for path in result.deleted[:20]:
            print(f"    {path}")
        if len(result.deleted) > 20:
            print(f"    ...and {len(result.deleted) - 20} more.")

    if args.list:
        for label, paths in (("added", result.added), ("modified", result.modified)):
            for path in paths[:20]:
                print(f"    {label:9s} {path}")

    return 1 if result.deleted else 0


if __name__ == "__main__":
    sys.exit(main())
