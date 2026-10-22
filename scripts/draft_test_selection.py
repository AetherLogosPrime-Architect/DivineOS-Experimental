"""Which tests a draft push should run: the ones that changed, and the ones that touch what changed.

Dad, 2026-10-21: "if you want to run tests on your code while you make a draft that is fine, but we just test that
code and anything directly touching it. we dont run the full suite until its being merged to main." And on
2026-08-22, the other half: "none of these should have made it to draft without passing internal CLI tests".

Both hold at once. A draft push runs only these tests, so a test file changed on a draft is never verified by
nobody (the August gap) and the whole suite is saved for the push that is bound for merge.

Usage (the changed paths, one per line, on stdin):
    git diff --name-only BASE..SHA | python scripts/draft_test_selection.py --ref SHA

stdout: the test files to run, one per line. stderr: what was selected and what has no test touching it.
Exit 0: the list is the answer (it may be empty, and stderr names every changed file nothing touches).
Exit 3: this change cannot be narrowed (a shared test setup file or the project config changed), run everything.
Exit 2: could not read the repository, which is NOT the same as nothing to run.

WHAT IT CAN SEE, said so silence is not read as coverage. It finds tests by reading text with `git grep`: a test
that reaches a module by a name built at run time, by a multi-line `from x import (a, b)` that puts the module name
on a different line, or only through another module is not found. A change that breaks a test which does not name it
is met at ready-for-review, when the whole suite runs. That is the accepted cost, counted in pushes, not guessed.
The gate hands the chosen files to pytest through a space-separated list, so a test path with a space in it would
break; none exist, and that is a named limit, not a handled case.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

#: Changing one of these changes what every test sees, so no narrower list is honest.
RUN_EVERYTHING = ("tests/conftest.py", "pyproject.toml", "pytest.ini", "setup.cfg", "tox.ini")


def _git(repo: Path, *args: str) -> list[str]:
    done = subprocess.run(
        ["git", *args], cwd=str(repo), capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if done.returncode not in (0, 1):  # git grep exits 1 for "no match", which is an answer
        raise RuntimeError(f"git {' '.join(args)} failed ({done.returncode}): {done.stderr.strip()[:200]}")
    return [line for line in done.stdout.splitlines() if line.strip()]


def _paths_from_grep(lines: list[str], ref: str) -> set[str]:
    """`git grep -l REF` prints `REF:path`; keep the path."""
    prefix = f"{ref}:"
    return {line[len(prefix) :] if line.startswith(prefix) else line for line in lines}


def tests_at(repo: Path, ref: str) -> set[str]:
    names = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", "tests")
    return {
        n for n in names if Path(n).name.startswith("test_") and n.endswith(".py") and "_archive" not in Path(n).parts
    }


def dotted_name(path: str) -> str | None:
    """`src/divineos/core/ledger.py` -> `divineos.core.ledger`; a package `__init__` -> the package."""
    p = Path(path)
    if p.suffix != ".py" or p.parts[:1] != ("src",) or len(p.parts) < 2:
        return None
    parts = list(p.with_suffix("").parts[1:])
    if parts and parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts) if parts else None


def importers(repo: Path, ref: str, dotted: str) -> set[str]:
    """Test files that name the module: `divineos.core.x` anywhere, or `from divineos.core import ... x`."""
    parent, _, leaf = dotted.rpartition(".")
    patterns = [rf"{re.escape(dotted)}([^A-Za-z0-9_]|$)"]
    if parent:
        patterns.append(rf"from {re.escape(parent)} import [^#]*\b{re.escape(leaf)}\b")
    args = ["grep", "-l", "-E"]
    for pattern in patterns:
        args += ["-e", pattern]
    args += [ref, "--", "tests"]
    return _paths_from_grep(_git(repo, *args), ref)


def mentions(repo: Path, ref: str, name: str, whole_word: bool = False) -> set[str]:
    flags = ["-l", "-F", "-w"] if whole_word else ["-l", "-F"]
    return _paths_from_grep(_git(repo, "grep", *flags, "-e", name, ref, "--", "tests"), ref)


def select(repo: Path, ref: str, changed: list[str]) -> tuple[set[str], list[str], bool]:
    """(tests to run, changed files nothing touches, can-it-be-narrowed-at-all)."""
    if any(c in RUN_EVERYTHING for c in changed):
        return set(), [], False
    universe = tests_at(repo, ref)
    chosen: set[str] = set()
    untouched: list[str] = []
    for path in changed:
        if path.startswith("tests/") and Path(path).name.startswith("test_") and path in universe:
            chosen.add(path)
            continue
        if path.startswith(("docs/", "family/", "exploration/", "dreams/")) or path.endswith((".md", ".txt")):
            continue  # prose cannot change a test outcome; the push check's fast path says the same
        found: set[str] = set()
        dotted = dotted_name(path)
        if dotted:
            found |= importers(repo, ref, dotted)
        # a hook, a script, a shared test helper or a config file is reached by its file name
        found |= mentions(repo, ref, Path(path).name)
        if path.endswith(".py") and not dotted:
            # a script or a shared test helper is imported by its bare name, without the .py
            found |= mentions(repo, ref, Path(path).stem, whole_word=True)
        found &= universe
        if found:
            chosen |= found
        elif not (path.startswith("tests/") and path not in universe):
            untouched.append(path)
    return chosen, untouched, True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--repo", default=".", help="the repository (default: here)")
    parser.add_argument("--ref", required=True, help="the commit being pushed")
    args = parser.parse_args(argv)
    changed = [line.strip().replace("\\", "/") for line in sys.stdin.read().splitlines() if line.strip()]
    try:
        chosen, untouched, narrowable = select(Path(args.repo), args.ref, changed)
    except (RuntimeError, OSError) as exc:
        print(f"[draft-tests] could not read the repository: {exc}", file=sys.stderr)
        return 2
    if not narrowable:
        print(
            "[draft-tests] a shared setup file changed (conftest or project config): this cannot be narrowed.",
            file=sys.stderr,
        )
        return 3
    # Raw bytes with a bare newline. print() in text mode ends every line with CR+LF on Windows, and the shell
    # that reads this keeps the CR on each file name, so pytest was asked for files that do not exist and "ran no
    # tests" (found by the first real draft push of this change, 2026-10-22).
    for path in sorted(chosen):
        sys.stdout.buffer.write((path + "\n").encode("utf-8"))
    sys.stdout.flush()
    print(f"[draft-tests] {len(changed)} changed file(s), {len(chosen)} test file(s) selected.", file=sys.stderr)
    for path in untouched:
        print(f"[draft-tests] NO TEST NAMES {path}: nothing is verified for it until the full run.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
