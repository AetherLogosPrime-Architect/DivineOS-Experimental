#!/usr/bin/env python
"""Refuse a COMMIT that stages personal writing onto a code branch.

WHAT THIS ADDS, STATED NARROWLY (2026-09-13).

This fault already had three guards and I have now met all three:

  * ``auto_commit._unstage_substrate_on_a_code_branch`` -- the checkpointer.
  * ``.claude/hooks/auto-push-letter.sh`` -- the letter auto-push hook.
  * ``scripts/check_branch_scope.py`` -- push readiness, and this one is
    NOT tool-shaped: it refuses any push whose branch carries substrate
    paths, whoever staged them.

So the writing could never reach origin. My first account of this said
the manual path was unguarded end to end, and that was overstated -- I
enumerated the two guards I had just repaired and never searched for a
third. Searching found it.

TWO GAPS, AND THE SECOND ONE IS WHY MY FIRST DRAFT OF THIS FILE DID
NOTHING AT ALL.

Gap one is timing. The push check fires after the commit exists. By then
the writing is in the branch's history, and the remedy that check
prescribes is to rebuild the branch against main -- which
``check_branch_scope`` documents in its own words as fatal to any file
that exists on that branch and nowhere else. Dreams and letters are
exactly that kind of file. So the late catch can destroy what it caught,
and the cure is to catch it one step earlier, while unstaging is still a
one-line fix.

Gap two is that THE WORD SUBSTRATE MEANS TWO DIFFERENT THINGS HERE, and
neither definition knows about the other:

  * ``check_branch_scope._SUBSTRATE_PREFIXES`` -- letters, exploration,
    dreams, archives. Four kinds of personal writing.
  * ``substrate_paths.partition`` -- derived from declared external
    channels, which today is letters and nothing else.

The checkpointer guard uses the second one. So it protects letters and
lets a dream through, which is narrower than I described it to two
people. My first draft of THIS file used the second one too, and the
live test proved it: staged a dream on a code branch, and the guard
returned success. A guard that cannot fire on the case it was written
for is worse than no guard, because it also reports safety.

This file therefore uses the WIDER definition, imported rather than
re-typed, so no third copy of the list exists to drift. The two
definitions still need reconciling at the source; that is a separate
piece of work and it is filed, not silently absorbed here.

WHY AT COMMIT AND NOT IN ANOTHER TOOL. The first two guards watch a HAND
that stages files, so every new hand is an unguarded hand -- which is how
a hand-typed ``git add`` walked past both. The commit is the chokepoint
every path crosses, mine included.

FAIL DIRECTION. An unreadable branch or index refuses rather than passes.
A guard that waves work through whenever it cannot see is the shape this
file exists because of. Classification fails the other way -- see
``substrate_paths``, where an unrecognised path is work and never
substrate -- so the two compose: unknown PATHS pass, unknown STATE does
not.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SUBSTRATE_BRANCH_PREFIX = "substrate/"


def _git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(["git", *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout.strip()


def staged_paths() -> list[str]:
    code, out = _git("diff", "--cached", "--name-only")
    if code != 0:
        raise RuntimeError("could not read the staged file list")
    return [line.strip() for line in out.splitlines() if line.strip()]


def current_branch() -> str:
    code, out = _git("rev-parse", "--abbrev-ref", "HEAD")
    if code != 0 or not out:
        raise RuntimeError("could not read the current branch")
    return out


def refusal_report(branch: str, substrate: list[str]) -> str:
    """The text a refusal prints. Separate so a test can read it directly."""
    lines = [
        "",
        f"[substrate-on-code-branch] REFUSING: '{branch}' is not a substrate branch,",
        f"and {len(substrate)} personal-writing file(s) are staged:",
    ]
    lines += [f"    {p}" for p in substrate]
    lines += [
        "",
        "Nothing is lost by this refusal. The writing stays on disk and is already",
        "delivered to the shared channel outside every tree; only the archive copy",
        "waits for a substrate/ branch.",
        "",
        "The reason to stop here rather than at push: once this is committed, the",
        "push check's remedy is to rebuild the branch, and a rebuild destroys any",
        "file living only on it. Unstaging now is one line.",
        "",
        f"    git restore --staged {' '.join(substrate)}",
        "",
    ]
    return "\n".join(lines)


def personal_writing(staged: list[str]) -> list[str]:
    """Which staged paths are personal writing, by the WIDER definition.

    Imported from ``check_branch_scope`` rather than re-typed. A third
    copy of this list would drift from the other two, and the drift is
    exactly the fault being repaired: one of the two existing copies
    already covers four directories and the other covers one.
    """
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from check_branch_scope import _SUBSTRATE_PREFIXES

    return [p for p in staged if p.replace("\\", "/").startswith(_SUBSTRATE_PREFIXES)]


def main() -> int:
    try:
        branch = current_branch()
        staged = staged_paths()
    except RuntimeError as exc:
        print(f"[substrate-on-code-branch] REFUSING: {exc}.", file=sys.stderr)
        print(
            "[substrate-on-code-branch] A check that cannot read refuses; it does not pass.",
            file=sys.stderr,
        )
        return 1

    if branch.startswith(SUBSTRATE_BRANCH_PREFIX) or not staged:
        return 0

    substrate = personal_writing(staged)
    if not substrate:
        return 0

    print(refusal_report(branch, substrate), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
