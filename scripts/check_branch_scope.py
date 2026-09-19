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
#
# IMPORTED, not restated. Until 2026-09-10 this was a second copy, and the
# checkpoint splitter answered the same question from the declared channels
# instead -- so the splitter filed archives and dreams as WORK while this gate
# refused the branch for carrying SUBSTRATE. One word, two definitions, three
# of four entries in disagreement, and the only symptom was a branch that could
# not be pushed and could not be fixed by the component that made it.
try:
    from divineos.core.substrate_paths import LOCAL_SUBSTRATE_PREFIXES as _SUBSTRATE_PREFIXES
except ImportError:  # pragma: no cover - a checkout without the package installed
    # Loud rather than a silent second copy: a fallback list here would be the
    # exact duplication this import exists to end, and it would drift quietly.
    print(
        "[scope] CANNOT CLASSIFY: divineos.core.substrate_paths is not importable, "
        "so this gate has no definition of substrate. That is could-not-look, not "
        "a clean branch. Install the package (pip install -e .) and re-run.",
        file=sys.stderr,
    )
    raise SystemExit(24)


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


def _worktree_blob(path: str) -> str | None:
    """The blob id git WOULD give the working-tree file at ``path``, or None
    when nothing is there.

    Added 2026-09-16 after this scan skipped eleven files as "nothing to
    lose" and printed an all-clear over what remained. A commit that
    untracks a file removes it from the branch and LEAVES IT ON DISK, and
    that copy can be the only one of its version anywhere. Asking git for
    the branch's blob returns nothing, which is exactly where the loss
    became invisible.

    ``hash-object`` WITHOUT ``-w`` computes the id without writing an
    object. That is load-bearing, not incidental: with the writing form the
    object lands in the store and any later existence probe finds proof the
    check itself manufactured. The scan must never be able to create the
    evidence that a file is safe.

    Honest limit: reading the working tree makes the verdict depend on the
    state of a directory rather than on committed history, so the same
    branch answers differently from a clean checkout. That is correct here,
    because the loss being prevented IS a loss of working-tree content — but
    it means a reviewer elsewhere cannot reproduce this from the repository
    alone.
    """
    candidate = REPO_ROOT / path
    if not candidate.is_file():
        return None
    code, out = _git("hash-object", "--", path)
    if code != 0 or not out.strip():
        return None
    return out.strip()


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


def substrate_directions(branch: str, reference: str) -> dict[str, str]:
    """Map each substrate path to ADDS, REMOVES or REWRITES on this branch.

    TWO HAZARDS WERE SHARING ONE SENTENCE. This check lists paths the branch
    CHANGED, not paths it CARRIES, so a deletion counted as substrate-on-this-
    branch exactly like an addition -- and the refusal said only "substrate
    file(s) on this branch" for both. They are opposite problems with opposite
    remedies: an addition puts substrate where it does not belong and is rebuilt
    away, while a removal propagates to the main line on merge and has to be
    confirmed as intended.

    NOT A FILTER. Dropping deletions from the count is the permitting direction
    and would let a branch quietly delete substrate from everywhere -- the worse
    failure, because an addition stays visible in a diff forever and a removal
    looks like nothing once it lands. The refusal condition is unchanged. Only
    the message learns to say which way it found.

    MEASURED 2026-09-18: a branch deleting a tracked secret-shaped file reached
    an auditor inside an eighty-six file diff, and the only thing telling her to
    read that deletion as the repair rather than a loss was a letter written by
    hand. A guard whose output needs a human escort is making work, not saving
    it.

    RENAMES CARRY TWO NAMES, and the parsing rule here is borrowed rather than
    reinvented -- check_mixed_pattern_merge.py already documents it. A rename
    arrives as a score plus an old and a new path, so the last field is the one
    that exists on the branch now and that is what gets classified. Splitting
    naively would mangle exactly the long hyphenated letter filenames nobody
    re-reads.
    """
    code, out = _git("diff", "--name-status", f"{reference}...{branch}")
    if code != 0:
        return {}
    letters = {"A": "ADDS", "C": "ADDS", "D": "REMOVES", "M": "REWRITES", "R": "REWRITES"}
    directions: dict[str, str] = {}
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            continue
        path = parts[-1].strip()
        if not path.startswith(_SUBSTRATE_PREFIXES):
            continue
        directions[path] = letters.get(parts[0][:1].upper(), "CHANGES")
    return directions


def _other_refs(branch: str) -> list[str]:
    """Every local and remote ref except the one being checked.

    Returns [] when the ref list cannot be read, and the caller treats that as
    could-not-look rather than as nowhere-else -- this whole file's discipline.
    """
    code, out = _git(
        "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads", "refs/remotes"
    )
    if code != 0:
        return []

    # EXCLUDE BY IDENTITY, NOT BY SPELLING. This used to resolve the branch to a
    # short name and paste it into two strings -- a local head and a remote by
    # that name -- then drop those. It worked for a plain branch name and
    # silently excluded NOTHING for any other spelling.
    #
    # Measured 2026-09-16, and this is how it surfaced: the push gate invokes
    # this with a COMMIT identifier. Asked for the short name of a commit, git
    # returns an empty string, so the two refs constructed were a bare prefix
    # with nothing after them. Neither exists. Nothing was excluded, the branch
    # matched its own blobs on every file, and the scan reported eleven
    # substrate files as existing on another ref at the same bytes when every
    # one of them was unique to that branch. Following the advice would have
    # destroyed them.
    #
    # AND LOOK WHERE IT SAT. The comparison below was changed from asking
    # whether a file by that NAME existed elsewhere to comparing blob identity,
    # after Aria asked which of the two it was. That repair went to the half
    # that had been caught and stopped one line short of the half that had not.
    # The exclusion set was still matching by name. Same fault, same function,
    # above the line that documents fixing it.
    head = _resolve_commit(branch)
    if head is None:
        # Could-not-resolve is its own answer. An unresolvable branch and a
        # branch with nothing to exclude previously both produced an empty set,
        # and the scan then ran blind against itself. The caller reads [] as
        # could-not-look, which is the honest verdict here.
        return []

    refs: list[str] = []
    for line in out.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        name, obj = parts[0], parts[1].strip()
        if obj == head:
            # The branch under test, and anything sitting on the same commit.
            # Exactly those -- never by resemblance, because every ref wrongly
            # excluded is one that can no longer prove a file survives.
            continue
        refs.append(name)
    return refs


def _resolve_commit(rev: str) -> str | None:
    """The commit a revision names, or None when it cannot be resolved.

    Separate from the caller so the failure has somewhere to be returned from
    rather than collapsing into an empty result that reads as success.
    """
    code, out = _git("rev-parse", "--verify", "--quiet", f"{rev}^{{commit}}")
    if code != 0 or not out.strip():
        return None
    return out.strip()


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

    A PATH DELETED ON THIS BRANCH IS NOT AUTOMATICALLY SAFE, and the version
    of this sentence that said so cost eleven files on 2026-09-16. It read:
    "a path deleted on this branch has no content here to lose and is
    skipped." It was written in good faith, it reads as obviously true, and
    it survived every reading by being readable. It is false whenever a
    commit untracked the file and left it in the working tree -- the shape of
    every take-the-substrate-off-the-code-branch commit. Git reports no blob
    while the only current copy sits on disk. So the disk is asked before any
    path is dropped, and only a path gone from BOTH is skipped.

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
        if mine_code == 0:
            mine_blob = mine_blob.strip()
        else:
            # NOT "nothing to lose" -- that was the 2026-09-16 defect, and it
            # nearly cost eleven files. A commit that UNTRACKS a file removes
            # it from the branch and leaves it in the working tree, so git
            # reports no blob here while the only current copy of the content
            # sits on disk. Ask the disk before concluding there is nothing.
            disk_blob = _worktree_blob(path)
            if disk_blob is None:
                # Gone from the branch AND from disk. Genuinely nothing here
                # for a rebuild to take.
                continue
            mine_blob = disk_blob
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
        paths = substrate_paths(args.branch, args.truth)
        directions = substrate_directions(args.branch, args.truth)
        if args.list:
            for path in paths[:20]:
                print(f"    {directions.get(path, 'CHANGES'):<9} {path}")

        # WHICH WAY, said before anything else, because the two directions are
        # opposite problems and the remedies differ. An addition puts substrate
        # where it does not belong and is rebuilt away. A removal propagates to
        # the main line on merge and has to be confirmed as intended.
        adds = sum(1 for p in paths if directions.get(p) == "ADDS")
        removes = sum(1 for p in paths if directions.get(p) == "REMOVES")
        rewrites = len(paths) - adds - removes
        parts = []
        if adds:
            parts.append(f"{adds} ADDED here")
        if removes:
            parts.append(f"{removes} REMOVED from everywhere on merge")
        if rewrites:
            parts.append(f"{rewrites} rewritten")
        if parts:
            print(f"  [scope] direction: {', '.join(parts)}.")
        if removes and not adds:
            print(
                "  Every one is a REMOVAL. That is the shape of a branch taking "
                "substrate OFF the main line, which may be exactly the repair "
                "intended -- and is still refused, because a deletion that "
                "merges is invisible afterwards. Confirm it was meant."
            )

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
                # SAYS WHAT IT MEASURED, not what it means. The earlier
                # wording here asserted these "would LOSE CONTENT", and that
                # is a second claim the scan cannot support: bytes-nowhere-else
                # does not imply information-would-be-lost, because a DERIVED
                # file can be rebuilt from whatever produces it. Found 2026-09-16
                # by this scan firing on eleven archive exports an hour after the
                # scan was repaired -- every one regenerates from the database,
                # and the rebuild is NEWER than the copy on disk. A byte
                # comparison cannot see a generator and must not speak as if it
                # can. The REFUSAL is unchanged and the paths are still named;
                # only the claim narrowed.
                f"  [scope] {total} of these exist on NO OTHER REF at these "
                "bytes. Compared by bytes, not by filename:"
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
            # The one question this scan cannot answer, asked out loud so the
            # reader answers it deliberately rather than inferring loss from
            # absence. Most files are NOT derived and moving them is the right
            # move; `docs/archives/` is the one place in this repository that
            # rebuilds itself, and on 2026-09-16 all eleven of its exports fired
            # here while regenerating from the database NEWER than the copies on
            # disk. Named narrowly on purpose: a general "it might be derived"
            # is an invitation to answer yes because yes lets you proceed.
            print(
                "  FIRST, though: is any of these DERIVED -- rebuilt by a "
                "command from something upstream? This scan compares bytes and "
                "cannot see a generator, so it cannot tell a one-of-a-kind file "
                "from a stale snapshot. docs/archives/ is regenerated by "
                "`divineos admin archive-export`. Most other paths are not "
                "regenerable and moving them IS the right move."
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
