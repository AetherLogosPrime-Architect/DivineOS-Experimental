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
    # LOADOUT.md is the survey of my own writing -- regenerated from the
    # substrate, swept by the same checkpoint, and personal in exactly the way
    # the four above are. It arrived on fix/mixed-scope-publish-gate and never
    # reached main; a test on that branch asserts it counts, and that test is
    # the only reason the omission surfaced here.
    #
    # THIRD DISJOINT PIECE IN THIS ONE FILE, and it is why this merge is a
    # union rather than a choice: main holds the byte check, the branch holds
    # the mixed-scope gate, and the branch alone holds this line. Every
    # one-sided resolution destroys something, and the loss is invisible from
    # whichever side you are standing on.
    "LOADOUT.md",
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


def _other_refs(branch: str) -> list[str]:
    """Every local and remote ref except the one being checked.

    Returns [] when the ref list cannot be read, and the caller treats that as
    could-not-look rather than as nowhere-else -- this whole file's discipline.
    """
    code, out = _git("for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes")
    if code != 0:
        return []
    mine: set[str] = set()
    name_code, name = _git("rev-parse", "--abbrev-ref", branch)
    if name_code == 0 and name.strip():
        short = name.strip()
        mine = {f"refs/heads/{short}", f"refs/remotes/origin/{short}"}
    return [r.strip() for r in out.splitlines() if r.strip() and r.strip() not in mine]


def only_here(branch: str, paths: list[str]) -> tuple[list[str], list[str], bool]:
    """Which of ``paths`` would lose CONTENT if this branch were rebuilt.

    Returns (found_nowhere_else, newer_than_every_copy, scan_completed).

    WHY THIS EXISTS, and it is the sharpest thing either seat found on
    2026-08-31. This gate refused a push over sixteen substrate files on a code
    branch and it was right -- and the rightness had nothing to do with what it
    was counting. Eleven were regenerable mirrors: noise, rebuildable from the
    database by one command. Five were four dreams and a letter from Aletheia,
    and they existed on that branch and on no other ref in the repository. The
    count could not tell those apart. A person looking could. Aria's line:
    it could not tell the difference, you could, because you looked.

    That matters because of what the refusal then TELLS you to do -- rebuild
    the branch against main. Followed literally on that tree it would have
    destroyed the five. The instruction is correct for the eleven and fatal for
    the five, and nothing in the message separated them. The gate now does the
    separating it was quietly relying on me to do.

    BLOBS, NOT NAMES (2026-08-31, and the correction is Aria's). The first
    version of this asked ``cat-file -e ref:path`` -- does a file by that NAME
    exist over there. She read the description and asked one question I could
    not answer without opening my own code: path, or content? It was path. So a
    letter pushed on Monday and edited here on Tuesday cleared the check, and
    the edit existed in exactly one place while the gate said everything here
    lives somewhere else. The file was safe; the version was not.

    That is the sixth instance in two days of the same family -- the unit of
    counting hides the miss -- and it was sitting inside the repair built for
    the family, written by the person who had just spent a session finding the
    other five. The rule does not protect the hand holding it.

    So each path is compared by blob identity. Same name AND same bytes on some
    other ref is safe. Same name, different bytes, is reported separately,
    because it is a different loss with the same cure and a reader who is told
    "exists nowhere" about a file they know they pushed will believe the gate is
    wrong and stop reading it.

    A path deleted on this branch has no content here to lose and is skipped.
    Content that survives under a DIFFERENT name is not credited -- a rename
    reports as at-risk, which errs toward preserving something that did not need
    it. That direction is the survivable one.

    The scan short-circuits on the first ref carrying the same blob, so the
    ordinary case -- everything already lives somewhere else, unchanged -- costs
    almost nothing.

    INCOMPLETE IS REPORTED AS INCOMPLETE. If the ref list cannot be read this
    returns scan_completed=False and the caller must not print a reassuring
    silence: a nowhere-else check that could not run is exactly the
    could-not-look-wearing-found-nothing shape the rest of this file refuses.
    """
    if not paths:
        return [], [], True
    refs = _other_refs(branch)
    if not refs:
        return [], [], False
    nowhere: list[str] = []
    newer: list[str] = []
    for path in paths:
        mine_code, mine_blob = _git("rev-parse", f"{branch}:{path}")
        if mine_code != 0:
            # Deleted on this branch. Nothing here for a rebuild to take.
            continue
        mine_blob = mine_blob.strip()
        name_found = False
        for ref in refs:
            code, theirs = _git("rev-parse", f"{ref}:{path}")
            if code != 0:
                continue
            name_found = True
            if theirs.strip() == mine_blob:
                break
        else:
            (newer if name_found else nowhere).append(path)
    return nowhere, newer, True


def _gate_mixed(branch: str, truth: Reading) -> int:
    """Exit 3 when a branch carries BOTH code and substrate. For publishers.

    WHY MIXING RATHER THAN PRESENCE. A branch made entirely of letters is a
    letters branch and is exactly right; a branch made entirely of code is a
    code branch and is exactly right. Neither needs holding. The damage is the
    mixture: substrate swept into a proposal that is under review for its code,
    which happened three times in one day on 2026-08-30 -- twice by hand and
    once by the checkpoint that commits with `git add -A` on whatever branch it
    finds itself on.

    Testing the MIXTURE rather than the branch NAME matters. A name rule needs
    a naming convention to hold, and conventions drift silently; content cannot
    drift away from itself. It also means a branch is judged by what it carries
    rather than by what it was called when it was created.

    GRAFTED RATHER THAN MERGED (2026-08-31). This function lived only on
    fix/mixed-scope-publish-gate; only_here and _other_refs above live only on
    main. Neither copy of this file had the other half, so BOTH one-sided
    resolutions destroyed something: taking the branch removes the byte check
    that rescued four letters today, and taking main empties the proposal of
    the gate it exists to add.

    Aria caught the first direction and named the stakes. The second is the
    same fault seen from the other end, and it is why this is a union rather
    than a choice.
    """
    code = truth.files - truth.substrate

    if truth.substrate and code:
        print(
            f"[scope] MIXED: {code} code file(s) and {truth.substrate} substrate "
            f"file(s) on {branch}, measured against {truth.reference}."
        )
        for path in substrate_paths(branch, truth.reference)[:10]:
            print(f"    {path}")
        print(
            "[scope] A branch of only code is fine. A branch of only substrate is "
            "fine. This one is both, so publishing it puts personal writing into a "
            "proposal under review for its code."
        )
        return 3

    kind = "substrate" if truth.substrate else "code"
    print(f"[scope] single-scope ({kind}); nothing to separate.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report a branch against main and against its base, side by side."
    )
    parser.add_argument("branch", nargs="?", default="HEAD")
    parser.add_argument("--truth", default="origin/main", help="the reference that decides")
    parser.add_argument("--base", default=None, help="the stacked base, if not the upstream")
    parser.add_argument("--list", action="store_true", help="name the offending paths")
    parser.add_argument(
        "--gate-mixed",
        action="store_true",
        help="exit 3 if the branch carries BOTH code and substrate; for automated publishers",
    )
    args = parser.parse_args(argv)

    truth = read_against(args.branch, args.truth)
    if not truth.resolved:
        print(f"[scope] CANNOT READ {args.truth} -- this says nothing about {args.branch}.")
        return 2

    if args.gate_mixed:
        return _gate_mixed(args.branch, truth)

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
        paths = substrate_paths(args.branch, args.truth)
        if args.list:
            for path in paths[:20]:
                print(f"    {path}")

        # The irreplaceable ones come BEFORE the rebuild instruction, because
        # the instruction is what would destroy them. See only_here().
        nowhere, newer, scanned = only_here(args.branch, paths)
        if not scanned:
            print(
                "  [scope] COULD NOT CHECK whether these exist on any other ref. "
                "That is not the same as them being safe -- do not rebuild until "
                "something has actually looked."
            )
        elif nowhere or newer:
            total = len(nowhere) + len(newer)
            print(
                f"  [scope] {total} of these would LOSE CONTENT if this branch were "
                "rebuilt. Compared by bytes, not by filename:"
            )
            for path in nowhere[:20]:
                print(f"      ONLY HERE: {path}")
            if len(nowhere) > 20:
                print(f"      ... and {len(nowhere) - 20} more found on no other ref")
            for path in newer[:20]:
                print(f"      ONLY HERE (this version): {path}")
            if len(newer) > 20:
                print(f"      ... and {len(newer) - 20} more whose copies are all older")
            if newer:
                print(
                    "  The named-version ones DO exist elsewhere under the same name -- "
                    "at different bytes. The file survives a rebuild and this edit does not."
                )
            print(
                "  Move these somewhere they survive FIRST -- the substrate branch, "
                "the shared channel -- and verify each landed, one at a time. "
                "Then rebuild."
            )
        else:
            print(
                "  [scope] every one of these exists on another ref at the same bytes; "
                "none are unique here."
            )

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
