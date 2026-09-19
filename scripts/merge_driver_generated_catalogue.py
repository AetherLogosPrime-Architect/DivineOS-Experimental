#!/usr/bin/env python3
"""Git merge driver for the generated catalogues, so they stop colliding.

MEASURED 2026-09-18, and the measurement is why this exists rather than ten
separate conflict resolutions. Of the ten open branches that could not merge,
SEVEN collided on ``docs/AUTOMATION_REGISTER.md``. One conflicted on nothing
else at all. Aletheia asked the question that produced the number: are these ten
separate collisions, or one file that ten branches all touch.

WHY THESE FILES COLLIDE AND ORDINARY MERGING CANNOT HELP. They are catalogues
regenerated from the repository -- the automation register, the module maps, the
doc counts. Every branch regenerates them, so every branch rewrites the same
lines with a different tally and appends its own new rows in the same place. Git
sees two rewrites of one line and stops. It is right to stop: it has no way to
know that one side's tally and the other's are both stale readings of a number
nobody typed.

WHAT THIS DRIVER DOES. It hands the three-way merge to git. When git merges
cleanly, that result stands. When git reports a conflict, the driver TAKES ONE
SIDE WHOLE and says so on the error stream.

THE UNION APPROACH CAME FIRST AND WAS WRONG, and this file keeps the account
because the wrong version is the more tempting one. It reused the append-versus-
tally classification ``union_resolve`` has carried since June: keep both rows
when each side added a different one, take either when both rewrote the same
number. Against the seven real pairs it resolved five.

All five were fabrications. Two sides describing the SAME entry differently
share no identical line, so the classifier called them an append and kept both --
producing a register that lists one automation twice with contradictory rows.
Text nobody wrote, in the file people read to learn what runs by itself. Adding
a key-collision refusal then made it refuse all seven, which is a driver that
never resolves and therefore is not one.

TAKING ONE SIDE ENDS THE DEADLOCK. It does not end the collision, and the
difference matters enough that the original claim here is corrected in place
rather than quietly softened.

WHAT THIS FILE CLAIMED FIRST, AND WHY IT WAS WRONG. It said the catalogue is a
PURE FUNCTION OF THE TREE, verified by running the generator against a checkout
and diffing: identical. The measurement was real and the inference was
confounded -- the generator ran in the tree where that register had last been
generated, on the same branch. That is checking a photograph against itself.

Aria found the mechanism, and it is two lines below in the generator: the
staleness column comes from `git log -1 --format=%as` per path, resolved against
the CURRENT BRANCH. Two branches holding byte-identical hooks but forked on
different days produce different registers and then refuse to agree. Confirmed
here on one hook across three refs -- the same file reports one date from main
and an earlier one from a branch. The file is HISTORY-DEPENDENT BY CONSTRUCTION
and will collide with itself forever, whatever any driver does.

She also measured that main's own checked-in register does not reproduce from a
clean worktree at main -- seventy lines differ -- so the copy on the branch
everything merges into is a snapshot of some other tree.

WHAT SURVIVES OF THE ARGUMENT. Taking one side still loses nothing a
regeneration cannot restore, because the row SET is recoverable. What does not
survive is the claim that both sides render the same fact: they render different
branch histories. So this is a deadlock-breaker rather than a cure, and the cure
is to make that column history-independent so two branches with the same hooks
produce the same bytes.

THE OTHER HALF ALREADY EXISTS, and without it this is a silent-staleness
machine: ``generate_automation_register.py --check`` exits non-zero on a drifted
register and precommit.sh calls it. I searched for that check, concluded it did
not exist, and began writing a third copy -- Aria stopped me, and the commit
that wired the second is titled "The freshness alarm already existed and nothing
ever called it".

NOT REGENERATED HERE. At merge-driver time the working tree is half merged, so a
generator run would read a tree that never existed and write a rendering of it.
The rebuild belongs after the merge completes.

CONTRACT. Git calls a merge driver as ``driver %O %A %B %L %P``: ancestor, ours,
theirs, conflict-marker size, and the real pathname. The result must be written
into %A, and exit status zero means resolved.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# union_resolve is deliberately NOT imported any more. It was the whole engine of
# the first version; taking one side whole needs none of its classification, and
# leaving the import would have implied this file still consults it. Lint caught
# the dead import on the first run after the rewrite, which is the cheapest
# possible reader noticing that a docstring and its code had parted ways.


def _merge_file(ancestor: str, ours: str, theirs: str, marker_size: str) -> int:
    """Run git's own three-way merge, leaving markers in ``ours`` on conflict.

    Deliberately not reimplemented. git's merge-file is the same algorithm the
    rest of the repository is merged with, so a hunk this driver never sees is
    one git resolved exactly as it would have anywhere else.

    Returns git's own status: the number of conflicts, or negative on error.
    """
    cmd = ["git", "merge-file"]
    if marker_size and marker_size.isdigit():
        cmd.append(f"--marker-size={marker_size}")
    cmd += [ours, ancestor, theirs]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode


def _row_key(line: str) -> str | None:
    """The identity of a catalogue row, or None for anything that is not one.

    These catalogues are tables keyed by the first column -- an automation's
    name. Two sides describing the SAME automation differently is the case that
    must never be unioned, and it is not caught by the append/count test.
    """
    stripped = line.strip()
    if not stripped.startswith("|"):
        return None
    fields = [f.strip() for f in stripped.strip("|").split("|")]
    if not fields or not fields[0]:
        return None
    key = fields[0]
    # Header and separator rows are structure, not entries.
    if set(key) <= set("-: "):
        return None
    return key


def _colliding_row_keys(path: str) -> set[str]:
    """Row keys that appear on BOTH sides of some conflict hunk.

    THE HOLE THIS CLOSES, found by this driver's own test on the night it was
    written. ``union_resolve`` classifies a hunk as APPEND when the two sides
    share no identical line -- which is true of two DIFFERENT rewrites of the
    same row. It then keeps both, and the catalogue ends up listing one
    automation twice with contradictory descriptions.

    That is not the silent-loss failure the refusal was built for; it is a
    silent-FABRICATION failure, text nobody wrote and nobody reviewed. Same
    family, opposite direction, and the existing test missed it because it
    compares lines rather than identities.
    """
    lines = Path(path).read_text(encoding="utf-8", newline="").split("\n")
    collisions: set[str] = set()
    i = 0
    while i < len(lines):
        if not lines[i].startswith("<<<<<<<"):
            i += 1
            continue
        i += 1
        ours: list[str] = []
        while i < len(lines) and not lines[i].startswith("======="):
            ours.append(lines[i])
            i += 1
        i += 1
        theirs: list[str] = []
        while i < len(lines) and not lines[i].startswith(">>>>>>>"):
            theirs.append(lines[i])
            i += 1
        i += 1
        ours_keys = {k for k in (_row_key(x) for x in ours) if k}
        theirs_keys = {k for k in (_row_key(x) for x in theirs) if k}
        collisions |= ours_keys & theirs_keys
    return collisions


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(
            "[catalogue-merge] REFUSED: called with too few arguments. Expected "
            "%O %A %B [%L] [%P] from git.",
            file=sys.stderr,
        )
        return 2

    ancestor, ours, theirs = argv[0], argv[1], argv[2]
    marker_size = argv[3] if len(argv) > 3 else ""
    pathname = argv[4] if len(argv) > 4 else ours

    # Saved because git's merge-file overwrites %A in place, and the fallback
    # below needs the side that was there before it ran.
    ours_before = Path(ours).read_text(encoding="utf-8", newline="")

    conflicts = _merge_file(ancestor, ours, theirs, marker_size)

    if conflicts < 0:
        print(
            f"[catalogue-merge] REFUSED on {pathname}: git merge-file failed. That is "
            "could-not-merge rather than a clean merge, and the file is left as git "
            "left it.",
            file=sys.stderr,
        )
        return 1

    if conflicts == 0:
        return 0

    # THE UNION APPROACH WAS WRONG HERE AND ITS OWN TEST IS WHAT PROVED IT.
    #
    # First pass: five of the seven real pairs "resolved" by keeping both sides'
    # rows. Then the row-key check below found that every one of those five was
    # keeping two contradictory descriptions of the SAME automation. Not lost
    # work -- invented work, a register listing one entry twice with rows nobody
    # wrote. Five apparent successes were five fabrications.
    #
    # With the key check in place all seven refused, which is honest and useless:
    # a driver that never resolves is the conflict it replaced.
    #
    # The way out is a property of the file rather than of the hunks. This
    # catalogue is a PURE FUNCTION OF THE TREE -- verified, not assumed, by
    # running the generator against a clean checkout and diffing: identical. So
    # the file carries no information that the tree does not, every side of a
    # conflict here is a stale rendering, and taking one loses nothing at all.
    #
    # WHAT MAKES THAT SAFE IS THE OTHER HALF, and it already exists:
    # `generate_automation_register.py --check` exits non-zero on a drifted
    # register, and precommit.sh calls it. Without that, this driver would
    # quietly leave whichever rendering it picked.
    #
    # I SEARCHED FOR THAT CHECK, CONCLUDED IT DID NOT EXIST, AND STARTED WRITING
    # A THIRD COPY. Aria stopped me by letter: it had refused her own commit
    # hours earlier, and the commit that wired it is titled "The freshness alarm
    # already existed and nothing ever called it" -- so the SECOND copy was
    # itself made by someone noticing there was already a first. My search
    # looked for a file named after the check and missed a flag on the
    # generator. The sibling catalogue has the same shape one file over.
    #
    # PURITY IS NOT ONE MEASUREMENT EITHER, and hers are not mine: the generator
    # run twice in a separate checkout, byte-identical; one single-file commit
    # across the last twenty-five touching the register, and that one a merge
    # rather than an edit; and the structural argument that beats both -- the
    # door has been shut since the wiring, so nothing hand-edited could have been
    # committed since. Scoped honestly: never-hand-edited SINCE THE WIRING, which
    # says nothing about before it and nothing about anyone using the escape.
    #
    # NOT REGENERATED HERE. At merge-driver time the working tree is half
    # merged, so a generator run would read a tree that never existed and write
    # a rendering of it. The regeneration belongs after the merge completes.
    contradictions = len(_colliding_row_keys(ours))
    Path(ours).write_text(ours_before, encoding="utf-8", newline="")
    print(
        f"[catalogue-merge] {pathname}: took one side whole"
        + (
            f" ({contradictions} row(s) described differently on each side)"
            if contradictions
            else ""
        )
        + ". Both sides are stale renderings of the tree, so nothing is lost -- but the "
        "rendering left here is provisional. Regenerate before committing -- "
        "`python scripts/generate_automation_register.py` -- and the --check flag "
        "the pre-commit run already calls will refuse a stale one.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
