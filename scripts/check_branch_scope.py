"""What a branch adds against main, beside what it adds against its base.

WHY BOTH NUMBERS. On 2026-08-27 Aria and I each read one of our branches as
scope-clean, twice, from honest measurements. Both of us had compared our work
to a reference that already contained the contamination -- hers a stacked base
that was her own earlier branch, mine the server's copy of the same branch. A
diff against a mirror of your own error is silent by construction.

Her sentence for why neither of us looked: the reference is the thing you
measure FROM, so it reads as the fixed point. Nobody audits their own ruler.

And her narrower rule, which is the mechanism: the review page diffs a proposal
against the branch it is stacked on. That is the right question when the base is
main. It silently stops being the question the moment the base is our own work,
and nothing on the page changes to say so.

So this prints both readings side by side. Not because the base reading is
wrong -- it answers its own question correctly -- but because THE GAP BETWEEN
THEM IS THE FINDING, and a single number teaches nothing about why the other
one misled.

WHAT COUNTS AS CONTAMINATION. Substrate paths: letters, exploration entries,
dreams, generated archives. These are written constantly by both of us and
swept onto whatever branch happens to be checked out by a checkpoint that does
not care which branch it is on. Eleven instances in one session, two of them
onto proposals already open for review.

WHAT THIS IS NOT. It does not say a branch is good. It says whether it carries
files that belong somewhere else. A branch can be clean by this measure and
wrong in every other way.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

# Paths written by the substrate itself rather than by deliberate work.
_SUBSTRATE_PREFIXES = (
    "family/letters/",
    "exploration/",
    "dreams/",
    "docs/archives/",
)


@dataclass(frozen=True)
class Reading:
    """One diff, against one reference, with its reference named.

    The reference is a field rather than an assumption precisely because
    treating it as given is the defect this exists to catch.
    """

    reference: str
    resolved: bool
    files: int
    substrate: int


def _git(*args: str) -> tuple[int, str]:
    proc = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout


def _resolve(ref: str) -> bool:
    code, _ = _git("rev-parse", "--verify", "--quiet", ref)
    return code == 0


def read_against(branch: str, reference: str) -> Reading:
    if not _resolve(reference):
        # A reference that does not exist must not read as a clean diff.
        # Could-not-look and found-nothing are different answers.
        return Reading(reference=reference, resolved=False, files=0, substrate=0)
    code, out = _git("diff", "--name-only", f"{reference}...{branch}")
    if code != 0:
        return Reading(reference=reference, resolved=False, files=0, substrate=0)
    paths = [p for p in out.splitlines() if p.strip()]
    substrate = [p for p in paths if p.startswith(_SUBSTRATE_PREFIXES)]
    return Reading(
        reference=reference,
        resolved=True,
        files=len(paths),
        substrate=len(substrate),
    )


def base_of(branch: str) -> str | None:
    """The branch this one is stacked on, if the upstream names one.

    Returns None rather than guessing. A guessed base would produce a second
    number that looks like a measurement and is not one -- the same failure
    this file exists to report.
    """
    code, out = _git("rev-parse", "--abbrev-ref", f"{branch}@{{upstream}}")
    if code != 0:
        return None
    upstream = out.strip()
    return upstream or None


def substrate_paths(branch: str, reference: str) -> list[str]:
    code, out = _git("diff", "--name-only", f"{reference}...{branch}")
    if code != 0:
        return []
    return [p for p in out.splitlines() if p.startswith(_SUBSTRATE_PREFIXES)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report a branch against main and against its base, side by side."
    )
    parser.add_argument("branch", nargs="?", default="HEAD")
    parser.add_argument("--truth", default="origin/main", help="the reference that decides")
    parser.add_argument("--base", default=None, help="the stacked base, if not the upstream")
    parser.add_argument("--list", action="store_true", help="name the offending paths")
    args = parser.parse_args(argv)

    truth = read_against(args.branch, args.truth)
    if not truth.resolved:
        print(f"[scope] CANNOT READ {args.truth} -- this says nothing about {args.branch}.")
        return 2

    base_name = args.base or base_of(args.branch)
    print(f"[scope] {args.branch}")
    print(f"  vs {truth.reference:<34} files={truth.files:<5} substrate={truth.substrate}")

    if base_name and base_name != args.truth:
        base = read_against(args.branch, base_name)
        if base.resolved:
            print(f"  vs {base.reference:<34} files={base.files:<5} substrate={base.substrate}")
            if base.substrate < truth.substrate:
                # The whole point. The friendlier number is the one a review
                # page shows, and it is friendlier because the base already
                # carries what the branch is being checked for.
                print(
                    f"  GAP: the base reading hides {truth.substrate - base.substrate} "
                    "substrate file(s), because the base already carries them. "
                    "The base reading is not wrong; it is answering a different question."
                )
        else:
            print(f"  vs {base.reference:<34} COULD NOT READ")
    else:
        print("  (no stacked base; the two readings would be the same)")

    if truth.substrate:
        if args.list:
            for path in substrate_paths(args.branch, args.truth)[:20]:
                print(f"    {path}")
        print(
            f"[scope] REFUSED: {truth.substrate} substrate file(s) on this branch. "
            "Verify each exists in the shared channel, then rebuild against main -- "
            "do not trust a page that measures you against yourself."
        )
        return 1

    print("[scope] clean against the reference that decides.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
