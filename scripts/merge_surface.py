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


def _git(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
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
                f"[FINDING] {rel} was not what its generator produces. "
                f"It was merged textually rather than re-derived. "
                f"The regenerated file is now in the tree -- review and stage it."
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

    if not (args.hot or args.for_branch or args.verify_generated):
        ap.print_help()
        return COULD_NOT_LOOK

    worst = CLEAN

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
