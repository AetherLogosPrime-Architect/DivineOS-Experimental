#!/usr/bin/env python3
"""Sort every local branch into what it actually needs, not what it looks like.

WHY THIS EXISTS

Aria handed me the branch-and-PR sorting and named why it should be mine
rather than hers: duplicating it is the overlap risk we have already paid for
once. The board is over a hundred branches deep and the first job is not
opening requests — it is knowing which branches should never get one.

The distinction that matters is SCOPE, not age or name. A branch carrying
writing is not a smaller code branch; it is a different kind of thing, and a
review request against it asks the auditor to read letters as if they were
patches. One such request is open right now against a branch that is
two-thirds writing, which is what prompted this.

WHAT IT CANNOT DO, said here so silence is not read as coverage:

  - It cannot tell a finished branch from an abandoned one. Commit counts and
    file counts say nothing about whether the work is done.
  - SUPERSEDED is a NAME-SHAPE guess and nothing more. A branch called
    "-clean" or "-rebuilt" usually replaced something, and sometimes the
    replacement is the dead one. Every row in that bucket needs a human look;
    the bucket exists to shorten the looking, never to authorise a deletion.
  - It reads only what is committed. A branch whose point lives in an
    uncommitted worktree looks empty here.

So the output is a WORK ORDER, not a verdict. Nothing here deletes anything.
"""

from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass

# Directories whose contents are writing rather than code. A branch touching
# these is carrying substrate, and substrate is reviewed by being read, not by
# being diffed against main.
_SUBSTRATE_PREFIXES = (
    "docs/archives/",
    "exploration/",
    "dreams/",
    "family/",
    "letters/",
    "workbench/",
)

# Name-shapes that USUALLY mean a branch was replaced by another. Deliberately
# a guess, and labelled as one everywhere it is used.
_SUPERSEDED_HINTS = (
    "-clean",
    "-clean-2",
    "-rebuilt",
    "-reconciled",
    "pre-rebuild",
    "-old",
    "rescue/",
    "abandoned/",
    "tmp/",
    "catchup-test/",
    "keep/swept",
)


@dataclass
class Branch:
    name: str
    files: int
    substrate: int
    commits: int
    pr: int | None
    code_files: frozenset[str] = frozenset()

    @property
    def code(self) -> int:
        return self.files - self.substrate


def _run(args: list[str]) -> str:
    out = subprocess.run(args, capture_output=True, text=True, check=False)
    return out.stdout


def _open_prs() -> dict[str, int]:
    raw = _run(
        [
            "gh",
            "pr",
            "list",
            "--state",
            "open",
            "--limit",
            "300",
            "--json",
            "number,headRefName",
            "--jq",
            '.[] | "\\(.number) \\(.headRefName)"',
        ]
    )
    prs: dict[str, int] = {}
    for line in raw.splitlines():
        parts = line.split(maxsplit=1)
        if len(parts) == 2 and parts[0].isdigit():
            prs[parts[1].strip()] = int(parts[0])
    return prs


def collect(base: str = "origin/main") -> list[Branch]:
    prs = _open_prs()
    names = _run(["git", "for-each-ref", "--format=%(refname:short)", "refs/heads"]).split()
    out: list[Branch] = []
    for name in names:
        if name == "main":
            continue
        files = _run(["git", "diff", "--name-only", f"{base}...{name}"]).splitlines()
        commits = _run(["git", "rev-list", "--count", f"{base}..{name}"]).strip()
        sub = sum(1 for f in files if f.startswith(_SUBSTRATE_PREFIXES))
        out.append(
            Branch(
                name=name,
                files=len(files),
                substrate=sub,
                commits=int(commits) if commits.isdigit() else 0,
                pr=prs.get(name),
                # The names were already in hand and were being reduced to a
                # count. Keeping them costs one set and is the whole basis of
                # the candidate list below.
                code_files=frozenset(
                    f for f in files if f and not f.startswith(_SUBSTRATE_PREFIXES)
                ),
            )
        )
    return out


def neighbours(branches: list[Branch], name: str, limit: int = 8) -> list[tuple[str, int]]:
    """Other branches touching code files this one also touches, most-shared first.

    WHAT THIS IS FOR. Aria is building a stop at the door to main that refuses
    to let a branch through until somebody has looked at whether it duplicates
    work already sitting on a bench. That check is hers. This is the half she
    asked me for: a short list put in front of the person at the door, so the
    question gets answered by looking rather than from memory. Memory is what
    produced three copies of one mechanism, twice in one week.

    WHAT IT IS NOT, and this matters more than what it is.

    A SHARED FILE IS NOT A SHARED PROBLEM. Two branches both touching a
    widely-edited module have nothing to do with each other. Expect most rows
    to be noise; the list earns its place by being short enough to read, not
    by being right.

    AN EMPTY LIST MEANS NO SHARED FILE. It does not mean no overlap, and it
    must never be read as one. The case this cannot see is the dangerous one:
    two branches solving the same problem in different files -- one rewriting
    a module, the other replacing it somewhere else entirely. That is exactly
    how the duplicate we paid for last week was built, so the instrument is
    blind in the direction of the very incident that prompted it. Said plainly
    here because a silence that reads as coverage is the fault this whole
    repository keeps rediscovering.

    So the door must ask its question whether or not this returns anything.
    The list shortens the looking; it never stands in for it.
    """
    by_name = {b.name: b for b in branches}
    mine = by_name.get(name)
    if mine is None or not mine.code_files:
        return []
    scored = [
        (b.name, len(mine.code_files & b.code_files))
        for b in branches
        if b.name != name and mine.code_files & b.code_files
    ]
    scored.sort(key=lambda row: (-row[1], row[0]))
    return scored[:limit]


def classify(b: Branch) -> str:
    """Which pile this branch belongs in.

    Order matters and is not arbitrary. EMPTY is checked first because a
    branch with nothing on it needs no further questions. SUBSTRATE-WITH-PR
    outranks plain SUBSTRATE because an open request against a writing branch
    is an active wrong thing rather than a quiet one.
    """
    if b.files == 0 or b.commits == 0:
        return "EMPTY — nothing against the trunk; close or delete after a look"
    if b.substrate and b.pr is not None:
        return "WRONG REQUEST OPEN — writing branch with a review request on it"
    if b.pr is not None:
        return "REQUEST OPEN — already in front of the auditor"
    if b.code == 0:
        return "WRITING ONLY — never gets a request; it is read, not diffed"
    if b.substrate:
        return "MIXED — must be replanted code-only before it can be reviewed"
    if any(h in b.name for h in _SUPERSEDED_HINTS):
        return "MAYBE SUPERSEDED — name-shape guess only; every row needs a look"
    return "CODE, READY TO SORT — candidate for a request"


def main() -> int:
    branches = collect()

    if len(sys.argv) > 2 and sys.argv[1] == "--neighbours":
        target = sys.argv[2]
        if target not in {b.name for b in branches}:
            print(f"[!] no local branch named {target}")
            return 1
        rows = neighbours(branches, target)
        print(f"# Branches sharing code files with {target}\n")
        if not rows:
            print("  none -- NO SHARED FILE, which is not the same as no overlap.")
            print("  Two branches solving one problem in different files look")
            print("  exactly like this. Ask the question anyway.")
            return 0
        for other, shared in rows:
            print(f"  {other}    shares {shared}")
        print("\n  Candidates, not conclusions. A shared file is usually")
        print("  coincidence; this list only exists to stop the question")
        print("  being answered from memory.")
        return 0

    piles: dict[str, list[Branch]] = {}
    for b in branches:
        piles.setdefault(classify(b), []).append(b)

    order = [
        "WRONG REQUEST OPEN — writing branch with a review request on it",
        "CODE, READY TO SORT — candidate for a request",
        "MIXED — must be replanted code-only before it can be reviewed",
        "REQUEST OPEN — already in front of the auditor",
        "WRITING ONLY — never gets a request; it is read, not diffed",
        "MAYBE SUPERSEDED — name-shape guess only; every row needs a look",
        "EMPTY — nothing against the trunk; close or delete after a look",
    ]

    print(f"# The branch board — {len(branches)} branches against origin/main\n")
    print("Sorted by what each one NEEDS. Nothing here is a verdict and nothing")
    print("here deletes anything; the superseded pile in particular is a guess")
    print("from the branch NAME and every row in it needs a human look.\n")

    for pile in order:
        rows = sorted(piles.get(pile, []), key=lambda b: (-b.code, b.name))
        if not rows:
            continue
        print(f"\n## {pile}  [{len(rows)}]\n")
        for b in rows:
            tag = f"  PR #{b.pr}" if b.pr else ""
            print(f"  {b.name}")
            print(f"      code={b.code}  writing={b.substrate}  commits={b.commits}{tag}")

    missing = set(piles) - set(order)
    if missing:
        print(f"\n[!] piles produced but not ordered for printing: {sorted(missing)}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
