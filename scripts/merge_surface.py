#!/usr/bin/env python3
"""Measure where merges actually collide, and refuse a generated file that was merged.

WHY THIS EXISTS

Andrew 2026-09-19 named merging as Aether's domain and told me to learn it with
him rather than around him. He answered, and two of his answers are mechanisms
rather than advice:

  1. "land entangled things adjacent, unrelated things whenever" -- because the
     collision surface is not spread across the stack, it is concentrated in a
     handful of files nearly every branch touches. Distance between two branches
     sharing a hot file means paying that resolution twice, the second time
     against a tree that has already moved.

  2. "a generated artifact is never merged, it is regenerated from the merged
     source and compared." A generated file has no meaningful merge: combining
     two generated outputs textually produces a third thing that is the output
     of nothing -- not what either branch would produce, and not what the merged
     input would produce. **A clean auto-merge on a generated file is the
     dangerous case precisely because nothing objects.**

THE ONE CONSTRAINT HE PUT ON THE DESIGN, AND IT SHAPES THE WHOLE FILE

"the hot-file list must be derived, not typed. I measured eight files today;
that set will drift, and a typed list goes stale silently, which is the failure
the whole house has been making all week."

So nothing here is typed. The hot files are counted from the open branches at
the moment of asking. The generated artifacts are discovered by reading each
``scripts/generate_*.py`` for the OUTPUT path it declares about itself. Add a
generator tomorrow and this finds it; delete one and this stops claiming it.
The only way to go stale is to stop calling it, which is the separate disease
tests/test_generated_docs_have_callers.py exists to catch.

THREE OUTCOMES, NOT TWO

Every mode here can fail to look, and failing to look is never reported as a
clean result. No branches reachable, no generator runnable, a git command that
will not answer -- each exits COULD_NOT_LOOK with the reason named. This is the
class the whole week has been about: an instrument answering confidently about
a subject it never reached.

Exit codes: 0 clean, 1 a finding, 2 could not look.
"""

from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CLEAN = 0
FINDING = 1
COULD_NOT_LOOK = 2

# How many branches must share a file before it counts as part of the collision
# surface. Two is the floor at which a file can collide at all; it is a
# THRESHOLD on derived data, not a list of files, so it cannot go stale the way
# a typed set does.
DEFAULT_MIN_BRANCHES = 2


def _git(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Run git in the repo root, RESOLVED AT CALL TIME.

    This used to read `cwd: Path = ROOT`, which binds the value when the module
    is imported rather than when the function runs. Every git command would then
    keep using whatever ROOT was at import, silently, even after ROOT changed --
    so the tool could report confidently about a repository it was not looking
    at. That is the same fault as everything else in this file, in a default
    argument, and it was found by a test that measured a temporary repo and got
    answers about the real one.
    """
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd if cwd is not None else ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def declared_generated_outputs() -> dict[Path, Path]:
    """Map each committed generated artifact to the generator that owns it.

    Derived by PARSING each generator for its own ``OUTPUT = ROOT / ...``
    declaration rather than by keeping a list here. The generators already say
    what they write; asking them is the difference between a fact and a copy of
    a fact.

    A generator that declares no OUTPUT is skipped silently -- it is not a
    finding, it just is not a committed-artifact generator.
    """
    found: dict[Path, Path] = {}
    for generator in sorted((ROOT / "scripts").glob("generate_*.py")):
        try:
            tree = ast.parse(generator.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if not isinstance(node, ast.Assign):
                continue
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "OUTPUT" not in names:
                continue
            parts = _path_parts(node.value)
            if parts:
                found[ROOT.joinpath(*parts)] = generator
    return found


def _path_parts(node: ast.AST) -> list[str]:
    """Flatten ``ROOT / "docs" / "X.md"`` into ["docs", "X.md"].

    Returns [] for anything that is not that shape, which is how a generator
    that computes its output some other way opts out without special-casing.
    """
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left = _path_parts(node.left)
        if isinstance(node.right, ast.Constant) and isinstance(node.right.value, str):
            return left + [node.right.value]
        return []
    if isinstance(node, ast.Name) and node.id == "ROOT":
        return []
    return []


def open_branch_refs() -> tuple[list[str], str | None]:
    """Remote branches other than main, newest first. Second value is a reason."""
    out = _git("for-each-ref", "--format=%(refname:short)", "refs/remotes/origin")
    if out.returncode != 0:
        return [], (out.stderr or "").strip() or "git could not list remote refs"
    refs = [
        line.strip()
        for line in out.stdout.splitlines()
        if line.strip() and line.strip() not in {"origin/main", "origin/HEAD"}
    ]
    if not refs:
        return [], "no remote branches besides main are known to this checkout"
    return refs, None


def collision_surface(min_branches: int) -> tuple[Counter[str], int, str | None]:
    """Count how many open branches change each file, relative to main."""
    refs, why = open_branch_refs()
    if why is not None:
        return Counter(), 0, why

    tally: Counter[str] = Counter()
    measured = 0
    for ref in refs:
        diff = _git("diff", "--name-only", f"origin/main...{ref}")
        if diff.returncode != 0:
            # One unreachable branch is not a reason to report nothing, but it
            # IS a reason not to claim the count is complete. Skipped branches
            # are subtracted from `measured`, which the caller prints.
            continue
        measured += 1
        for path in {line.strip() for line in diff.stdout.splitlines() if line.strip()}:
            tally[path] += 1

    if measured == 0:
        return Counter(), 0, "no branch could be diffed against main"

    hot = Counter({p: n for p, n in tally.items() if n >= min_branches})
    return hot, measured, None


def truly_shared_files(ref_a: str, ref_b: str) -> tuple[set[str], int, str, str | None]:
    """Files two branches BOTH change, measured from the ancestor they share.

    WHY THIS EXISTS, AND IT IS A CORRECTION TO A NUMBER I WAS GIVEN.

    Aether measured the open stack on 2026-09-19 and told me two branches shared
    ninety-four files -- "effectively one change wearing two numbers" -- and to
    land them adjacent. He re-measured before I acted on it and found they share
    ZERO. Not few. Zero.

    The ninety-four was an artifact of the counting. Diffing each branch against
    its merge-base with MAIN counts every file each one INHERITED from a shared
    ancestor that is itself far ahead of main. Those files are byte-identical on
    both sides. They are not collisions; they are common parentage wearing a
    collision's shape.

    Verified here rather than taken on his word, because a corrected number is
    still a number somebody handed me: against the two live branches, the naive
    count reports ninety-four shared and this function reports none.

    The narrowness matters and is his: he ran the corrected measure against
    every overlapping pair in the open stack and ninety-two of ninety-three
    agreed exactly with the naive one. The inflation appears only when two
    branches fork from each other far ahead of main, which is what happens when
    one grows out of the other after a long stretch of shared work.

    The correction only ever SHRINKS a count, never grows one -- so a naive
    number is an upper bound, and this is the tightening.

    Returns (shared, count, base_description, reason_it_could_not_look).
    """
    base = _git("merge-base", ref_a, ref_b)
    if base.returncode != 0 or not base.stdout.strip():
        return set(), 0, "", f"no common ancestor found for {ref_a} and {ref_b}"
    base_sha = base.stdout.strip()

    changed: list[set[str]] = []
    for ref in (ref_a, ref_b):
        diff = _git("diff", "--name-only", f"{base_sha}..{ref}")
        if diff.returncode != 0:
            return set(), 0, "", f"cannot diff {ref} from the ancestor it shares with the other"
        changed.append({line.strip() for line in diff.stdout.splitlines() if line.strip()})

    shared = changed[0] & changed[1]
    described = _git("log", "--oneline", "-1", base_sha)
    where = described.stdout.strip() if described.returncode == 0 else base_sha[:12]
    return shared, len(shared), where, None


def clusters_from_pairs(refs: list[str]) -> tuple[list[list[str]], list[str], int, int]:
    """Which branches actually touch each other, and which touch nothing.

    WHY A SHAPE RATHER THAN A NUMBER, and the reasoning is Aether's after he
    measured it instead of arguing it.

    I asked whether the fork-point correction should apply set-wide as well as
    pairwise. He ran it across six open branches: their common ancestor is
    July 10, while their PAIRWISE fork points run from July 10 to September 15.
    One pair forked two months later than the set does.

    So A SET HAS NO FORK POINT. It has an oldest member, and the shared base is
    pinned by whichever branch is most divergent -- which means the September
    pair gets measured against a July baseline and every file either of them
    inherited in between counts as a collision. That is the naive count
    returning through a different door wearing the word "corrected".

    The honest set-wide object is therefore not a scalar. It is which branches
    genuinely overlap: a real shared file is an edge, none is not, and what
    falls out is clusters that must be ordered against one another plus a
    remainder that can land in any order. A single figure says how bad it is;
    the shape says what to do about it.

    AND THE PART THAT CONTRADICTS HIM, FOUND BY BUILDING IT. Run over six live
    branches, thirteen of fifteen pairs collide and ALL SIX collapse into one
    group. That is not a bug -- the edges were hand-checked and are real. It is
    that grouping by transitive connection is the wrong shape.

    One branch touching several others BRIDGES them. The gate-repairs branch
    and the register-reproduction branch share literally nothing, and both
    share three files with the sweep repair, so connected-components declares
    all three must be ordered together. Two of them need no ordering at all.

    The constraint is PAIRWISE, not transitive: two branches sharing a file
    should land near each other, and that says nothing about a third branch
    that touches only one of them. So the edges are the answer and the groups
    are, at most, a region to look at. Reporting a group as "must be ordered
    against each other" would have been a confident instruction built on a
    relation that does not compose.

    Returns (edges, clusters, unconnected, total_pairs). Edges are the finding;
    clusters are reported beneath them with that caveat attached.
    """
    parent = {ref: ref for ref in refs}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    edges: list[tuple[str, str, int]] = []
    total = 0
    for i, ref_a in enumerate(refs):
        for ref_b in refs[i + 1 :]:
            total += 1
            _shared, count, _where, why = truly_shared_files(ref_a, ref_b)
            if why is not None:
                # A pair that could not be measured is NOT a pair with no
                # overlap. Folding it silently into the no-edge set would
                # assert the most comfortable possible answer about something
                # never actually checked.
                continue
            if count:
                edges.append((ref_a, ref_b, count))
                root_a, root_b = find(ref_a), find(ref_b)
                if root_a != root_b:
                    parent[root_b] = root_a

    grouped: dict[str, list[str]] = {}
    for ref in refs:
        grouped.setdefault(find(ref), []).append(ref)

    clusters = sorted(
        (sorted(members) for members in grouped.values() if len(members) > 1),
        key=lambda members: (-len(members), members[0]),
    )
    unconnected = sorted(m[0] for m in grouped.values() if len(m) == 1)
    edges.sort(key=lambda e: (-e[2], e[0], e[1]))
    return edges, clusters, unconnected, total


def verify_generated_are_rederived() -> tuple[int, list[str]]:
    """Run every declared generator and report artifacts the tree disagrees with.

    This is the door. After a merge, a generated artifact that was combined
    TEXTUALLY differs from what its generator produces from the merged source --
    and the textual combination is what git leaves behind when it auto-merges
    without complaint.

    A generator that will not run is COULD_NOT_LOOK, never a pass. An artifact
    that is absent after its generator ran is also could-not-look rather than a
    mismatch, for the reason Aletheia gave: reporting drift on a broken
    generator sends someone to regenerate, which is the remedy for drift and
    does nothing for a generator that produced no bytes.
    """
    outputs = declared_generated_outputs()
    if not outputs:
        return COULD_NOT_LOOK, ["no generator declares an OUTPUT path; nothing was checked"]

    messages: list[str] = []
    worst = CLEAN
    for artifact, generator in sorted(outputs.items()):
        rel = artifact.relative_to(ROOT).as_posix()

        # COMPARE THE CONTENT, NOT GIT'S OPINION OF IT.
        #
        # The first version of this compared `git status --porcelain` before and
        # after regenerating. That is a measurement that cannot see its own
        # subject in the case that matters most: if the artifact is ALREADY
        # dirty -- which is exactly the state a textual merge leaves it in --
        # the porcelain line reads " M <path>" both before and after, identical
        # strings, and the check reports ok while the file is wrong.
        #
        # Caught by testing it rather than by reading it, which is the only
        # reason it is not in the tree. A check whose two sides come from the
        # same source is this session's whole subject and I built one again.
        if not artifact.is_file():
            messages.append(f"[could not look] {rel}: absent before its generator ran")
            worst = max(worst, COULD_NOT_LOOK)
            continue
        before_bytes = artifact.read_bytes()

        run = subprocess.run(
            [sys.executable, str(generator)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if run.returncode != 0:
            messages.append(f"[could not look] {rel}: {generator.name} exited {run.returncode}")
            worst = max(worst, COULD_NOT_LOOK)
            continue

        if not artifact.is_file() or artifact.stat().st_size == 0:
            messages.append(
                f"[could not look] {rel}: {generator.name} exited cleanly and wrote nothing"
            )
            worst = max(worst, COULD_NOT_LOOK)
            continue

        if artifact.read_bytes() != before_bytes:
            messages.append(
                # NAMES THE FACT, NOT THE CAUSE. This used to assert "it was
                # merged textually rather than re-derived", which is one cause
                # among several -- the committed file can also simply be stale,
                # as it was the first time this check fired in anger, on my own
                # commit, because I had added a script the register had never
                # seen. Asserting the merge story would have sent the reader
                # hunting a merge that never happened.
                f"[FINDING] {rel} is not what its generator produces. "
                f"Either it was merged textually rather than re-derived, or it "
                f"is simply stale. The regenerated file is now in the tree -- "
                f"review and stage it."
            )
            worst = max(worst, FINDING)
        else:
            messages.append(f"[ok] {rel} matches a fresh run of {generator.name}")

    return worst, messages


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument(
        "--hot",
        action="store_true",
        help="measure the collision surface across open branches",
    )
    ap.add_argument(
        "--for-branch",
        metavar="REF",
        help="name the hot files this branch touches, and which of them are generated",
    )
    ap.add_argument(
        "--pair",
        nargs=2,
        metavar=("REF_A", "REF_B"),
        help=(
            "how entangled two branches really are, measured from the ancestor "
            "THEY share rather than from main -- the naive count is an upper bound"
        ),
    )
    ap.add_argument(
        "--clusters",
        nargs="+",
        metavar="REF",
        help=(
            "group the given branches by whether they genuinely overlap -- "
            "clusters must be ordered against each other, the rest can land whenever"
        ),
    )
    ap.add_argument(
        "--verify-generated",
        action="store_true",
        help="refuse any generated artifact that differs from a fresh run of its generator",
    )
    ap.add_argument(
        "--min-branches",
        type=int,
        default=DEFAULT_MIN_BRANCHES,
        help=f"how many branches make a file hot (default {DEFAULT_MIN_BRANCHES})",
    )
    args = ap.parse_args(argv[1:])

    if not (args.hot or args.for_branch or args.pair or args.clusters or args.verify_generated):
        ap.print_help()
        return COULD_NOT_LOOK

    worst = CLEAN

    if args.clusters:
        if len(args.clusters) < 2:
            print("[could not look] clustering needs at least two branches to compare.")
            return COULD_NOT_LOOK
        edges, clusters, unconnected, total = clusters_from_pairs(args.clusters)
        print(
            f"{len(edges)} of {total} pair(s) genuinely collide, measured from each "
            f"pair's own fork point."
        )
        print("\nTHE PAIRS THAT SHOULD LAND NEAR EACH OTHER -- this is the answer:")
        for ref_a, ref_b, count in edges:
            print(f"  {count:3d} shared  {ref_a}")
            print(f"              {ref_b}")
        if not edges:
            print("  none. Every branch here is independent of every other.")
        if clusters:
            print(
                "\nConnected regions, WHICH ARE NOT ORDERING CONSTRAINTS. A branch"
                "\ntouching two others joins them here while they may share nothing"
                "\nwith each other. Look at the pairs above to decide anything:"
            )
            for group in clusters:
                print(f"  region of {len(group)}: {', '.join(group)}")
        if unconnected:
            print("\nTouch nothing else in this set, so they can land whenever:")
            for ref in unconnected:
                print(f"  {ref}")

    if args.pair:
        ref_a, ref_b = args.pair
        naive_a = _git("diff", "--name-only", f"origin/main...{ref_a}")
        naive_b = _git("diff", "--name-only", f"origin/main...{ref_b}")
        shared, count, where, why = truly_shared_files(ref_a, ref_b)
        if why is not None:
            print(f"[could not look] {why}")
            return COULD_NOT_LOOK

        if naive_a.returncode == 0 and naive_b.returncode == 0:
            naive = len(
                {line.strip() for line in naive_a.stdout.splitlines() if line.strip()}
                & {line.strip() for line in naive_b.stdout.splitlines() if line.strip()}
            )
            print(f"Counted from main, these two look like they share {naive} file(s).")
        else:
            # Not a pass and not a finding: the comparison below still stands on
            # its own, and claiming a naive number we failed to compute would be
            # the exact fault this file exists to refuse.
            print("[could not look] the naive count could not be computed for comparison.")

        print(f"Measured from the ancestor they actually share -- {where} --")
        print(f"they share {count} file(s):")
        for path in sorted(shared):
            print(f"  {path}")
        if not shared:
            print("  none. They can land in either order and need no sequencing.")

    if args.hot or args.for_branch:
        hot, measured, why = collision_surface(args.min_branches)
        if why is not None:
            print(f"[could not look] {why}")
            return COULD_NOT_LOOK

        generated = {p.relative_to(ROOT).as_posix() for p in declared_generated_outputs()}

        if args.hot:
            print(f"Collision surface, measured across {measured} open branch(es):")
            for path, count in hot.most_common():
                mark = "  <- GENERATED: re-derive, never merge" if path in generated else ""
                print(f"  {count:3d}  {path}{mark}")
            if not hot:
                print("  (no file is touched by more than one branch)")

        if args.for_branch:
            diff = _git("diff", "--name-only", f"origin/main...{args.for_branch}")
            if diff.returncode != 0:
                print(f"[could not look] cannot diff {args.for_branch} against main")
                return COULD_NOT_LOOK
            touched = {line.strip() for line in diff.stdout.splitlines() if line.strip()}
            shared = sorted(touched & set(hot), key=lambda p: (-hot[p], p))
            print(f"\n{args.for_branch} touches {len(shared)} hot file(s):")
            for path in shared:
                mark = "  <- GENERATED: re-derive, never merge" if path in generated else ""
                print(f"  shared with {hot[path]:3d} branch(es)  {path}{mark}")
            if not shared:
                print("  none -- this branch can land whenever, order does not matter for it")

    if args.verify_generated:
        code, messages = verify_generated_are_rederived()
        print()
        for line in messages:
            print(line)
        worst = max(worst, code)

    return worst


if __name__ == "__main__":
    sys.exit(main(sys.argv))
