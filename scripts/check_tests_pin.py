#!/usr/bin/env python3
"""Do the tests added in this diff actually pin anything?

WHY THIS EXISTS. On 2026-08-27 I fixed a false-firing doorman and wrote a
regression test to pin the false fire. The test passed. It also passed against
the code BEFORE the fix, because I built its fixture from memory and memory
dropped the load-bearing call. A green regression test guarding nothing, and it
would have shipped.

Aria, splitting the problem when I asked whether my hand-rolled recovery was
repeatable:

    "A test written to pin a fix must be red against the code before the fix.
    That is just red-green, done backwards -- you wrote green-first and then
    asked, at the end, whether it had ever been red. Version control already
    holds the 'before'."

She also named the half this does NOT solve, and it is the half that actually
caught me: **fixture-from-memory.** My abbreviated command was a true statement
about a command that never existed. This instrument would have told me the test
was green on both sides; it would not have told me why. When a test exists to
pin a real event, copy the fixture from the record, not from recollection of it.

WHY NOT THE INSTRUMENTS THAT ALREADY EXIST. Checked before building, across all
forty remote branches, because I built the wins door twice this week by
searching only the room I was standing in.

  scripts/check_test_substance.py asks whether a test is CAPABLE of failing,
  statically, from the syntax tree. My hollow test had a real assertion on a
  real function and passes it cleanly. Different question, and it does not
  subsume this one.

  scripts/run_mutmut.py is the right family and the wrong instrument here --
  Aria opened it rather than recommending it from its name, and its quick mode
  mutates numeric comparisons and boolean returns only. My fix changed WHERE a
  predicate looks. The mutator has no move that produces it.

THE TRAP THIS HAD TO DEFUSE FIRST, and it is why the baseline proof below is not
optional. This package is installed editable, so `import divineos` inside a
base-tree worktree resolves to the CURRENT source anyway. Running the check
naively would grade the fix against itself and report a confident green -- the
wrong-baseline class, which this substrate has paid for three separate times in
one day. So the runner pins the path and then PROVES the module came from the
worktree before trusting a single result.

FAILS TOWARD LOUD. If the worktree cannot be made, or the baseline cannot be
proven, this exits non-zero and says the question could not be asked. It does
not report that the tests pin. Could-not-check and checked-clean are different
answers, and confusing them is the failure this whole session has been about.

WHAT IT CANNOT SEE, said plainly so silence here is not mistaken for coverage:
  - whether a red test is red for the RIGHT reason (fixture-from-memory again)
  - tests whose fixtures live in conftest.py, which is not copied into the base
    tree; a changed conftest may make results misleading rather than wrong
  - anything about tests that were not touched in this diff
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]

_SUBPROCESS_ERRORS = (OSError, subprocess.SubprocessError)


def _git(*args: str, cwd: Path | None = None) -> str | None:
    """Run git, returning stdout, or None when it could not answer."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(cwd or REPO_ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
        )
    except _SUBPROCESS_ERRORS:
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def merge_base(base_ref: str) -> str | None:
    out = _git("merge-base", base_ref, "HEAD")
    return out.strip() if out else None


def changed_test_files(base: str) -> list[str]:
    """Test files added or modified against the base."""
    out = _git("diff", "--name-only", f"{base}...HEAD")
    if out is None:
        return []
    return [
        line.strip()
        for line in out.splitlines()
        if line.strip().startswith("tests/") and line.strip().endswith(".py")
    ]


def test_functions(source: str) -> dict[str, str]:
    """Map every test function's node-id suffix to its source text.

    Class methods are keyed ``Class::method`` so a pytest node id can be
    rebuilt. A file that does not parse yields nothing rather than raising --
    an unparseable base version simply means every function reads as new, which
    is the safe direction.
    """
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return {}
    found: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test"):
                found[node.name] = ast.unparse(node)
        elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name.startswith(
                    "test"
                ):
                    found[f"{node.name}::{sub.name}"] = ast.unparse(sub)
    return found


def new_or_changed_tests(path: str, base: str) -> list[str]:
    """Test names in `path` that are new, or whose body changed since base.

    Compared as unparsed AST rather than raw text so a reformat or a comment
    edit does not present as a changed test and demand a pin it never owed.
    """
    new_source = (REPO_ROOT / path).read_text(encoding="utf-8", errors="replace")
    old_source = _git("show", f"{base}:{path}") or ""
    new_funcs = test_functions(new_source)
    old_funcs = test_functions(old_source)
    return sorted(name for name, body in new_funcs.items() if old_funcs.get(name) != body)


def _discard_scratch(path: Path) -> None:
    """Delete a scratch directory. Failure here cannot change any verdict.

    One place rather than two, so the reason is stated once and the swallow is
    auditable. Everything this removes is a temp holder created by this run;
    by the time it is called, every verdict is already computed and printed.
    """
    shutil.rmtree(path, ignore_errors=True)  # fail-soft: scratch only, see docstring above


def _worktree_env(worktree: Path) -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(worktree / "src")
    env["PYTHONNOUSERSITE"] = "1"
    return env


_PROBE_NAME = "test__pin_baseline_probe.py"
_STAMP_NAME = ".pin_baseline_resolved"

# Generated into the base worktree and never committed. It establishes the
# import origin INSIDE pytest, on pytest's own sys.path, in the same invocation
# style as every real test this run will grade.
_PROBE_SOURCE = '''"""Generated by scripts/check_tests_pin.py. Disposable.

Proves, in the process that will actually run the graded tests, that `divineos`
resolves inside this worktree rather than the live editable checkout.
"""

from pathlib import Path

import divineos

WORKTREE = Path(__file__).resolve().parents[1]


def test_import_came_from_this_worktree():
    resolved = Path(divineos.__file__).resolve()
    (WORKTREE / "{stamp}").write_text(str(resolved), encoding="utf-8")
    assert resolved.is_relative_to(WORKTREE), f"divineos resolved to {{resolved}}"
'''


def prove_baseline(worktree: Path, python: str) -> str | None:
    """Confirm `divineos` imports from the WORKTREE, not the live checkout.

    Returns the resolved path, or None if it could not be proven.

    THE PROOF IS TAKEN WHERE IT IS SPENT, and it did not start that way. The
    first version probed with `python -c` and then graded tests with
    `python -m pytest`. Aria, 2026-08-28, going at the live install rather than
    the code:

        "The proof is taken in one process and spent in another, and nothing
        checks they still agree."

    pytest builds its own import path -- ``pythonpath = ["src"]`` in
    pyproject.toml lands at sys.path[0] on pytest's authority, and
    tests/conftest.py does a further insert. Neither happens in a `-c` probe.
    They agreed, so the answer was right; the SUBJECT was the room next door.
    Wrong-subject, which is how a true measurement gets reported with the wrong
    scope.

    She also confirmed empirically what this relies on rather than granting it:
    this package installs path-style (a `.pth`, which loses to PYTHONPATH), not
    finder-style (a `sys.meta_path` hook, which runs before sys.path is
    consulted and beats PYTHONPATH outright). A sibling package in the same
    site-packages IS finder-style, so the hostile mode is installed one line
    away rather than hypothetical -- which is why the refusal text below names
    it.
    """
    probe = worktree / "tests" / _PROBE_NAME
    stamp = worktree / _STAMP_NAME
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_text(_PROBE_SOURCE.format(stamp=_STAMP_NAME), encoding="utf-8")
        proc = subprocess.run(
            [
                python,
                "-m",
                "pytest",
                f"tests/{_PROBE_NAME}",
                "-q",
                "--no-header",
                "-p",
                "no:cacheprovider",
            ],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            check=False,
            timeout=300,
            env=_worktree_env(worktree),
        )
    except (*_SUBPROCESS_ERRORS, ValueError):
        return None
    if proc.returncode != 0:
        return None
    if not stamp.is_file():
        # The run reported success without the probe having executed. Treat an
        # unexplained pass as unproven: a green with no stamp behind it is the
        # armed-and-unheard shape wearing an exit code.
        return None
    return stamp.read_text(encoding="utf-8").strip() or None


def _run_one(worktree: Path, python: str, node_id: str) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            [python, "-m", "pytest", node_id, "-q", "--no-header", "-p", "no:cacheprovider"],
            cwd=str(worktree),
            capture_output=True,
            text=True,
            check=False,
            timeout=1800,
            env=_worktree_env(worktree),
        )
    except _SUBPROCESS_ERRORS:
        return None


def classify(worktree: Path, python: str, path: str, names: list[str]) -> list[tuple[str, str]]:
    """Run each named test ALONE at the base tree and classify what happened.

    One at a time on purpose. A single collection error in a batch marks the
    whole batch failed, which would read as "everything pins" -- the exact
    false-green this instrument exists to prevent.
    """
    results: list[tuple[str, str]] = []
    for name in names:
        proc = _run_one(worktree, python, f"{path}::{name}")
        if proc is None:
            results.append((name, "UNVERIFIABLE"))
            continue
        if proc.returncode == 0:
            results.append((name, "PINS-NOTHING"))
            continue
        combined = (proc.stdout + proc.stderr).lower()
        if "error" in combined and "failed" not in combined:
            # Import or collection error: the test could not even run against
            # the old tree. That IS a form of red, but a weak one -- it pins the
            # existence of new code, not the behaviour under test. Named
            # separately so a weak pin never reads as a strong one.
            results.append((name, "WEAK-PIN (did not collect at base)"))
        else:
            results.append((name, "PINS"))
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Do new tests fail against the old code?")
    parser.add_argument("--base", default="origin/main", help="Base ref (default origin/main)")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    args = parser.parse_args(argv)

    base = merge_base(args.base)
    if base is None:
        print(
            f"[pin] CANNOT VERIFY -- no merge base with {args.base}. This says nothing "
            "about whether the tests pin; it says the question could not be asked."
        )
        return 2

    targets: dict[str, list[str]] = {}
    for path in changed_test_files(base):
        names = new_or_changed_tests(path, base)
        if names:
            targets[path] = names

    if not targets:
        print("[pin] no test functions added or changed against the base -- nothing to check.")
        return 0

    total = sum(len(v) for v in targets.values())
    print(f"[pin] {total} test function(s) added or changed, across {len(targets)} file(s).")

    holder = Path(tempfile.mkdtemp(prefix="pin-base-"))
    worktree = holder / "base"
    if _git("worktree", "add", "--detach", str(worktree), base) is None:
        _discard_scratch(holder)
        print("[pin] CANNOT VERIFY -- could not create a worktree at the base tree.")
        return 2

    findings: list[tuple[str, str, str]] = []
    try:
        proven = prove_baseline(worktree, sys.executable)
        if proven is None:
            print(
                "[pin] CANNOT VERIFY -- divineos did not resolve inside the base worktree,\n"
                "so the tests would have run against CURRENT source and every result would\n"
                "be meaningless. That is the wrong-baseline shape, and this refuses rather\n"
                "than guessing.\n"
                "\n"
                "LIKELIEST CAUSE, named here so this refusal survives being inherited: the\n"
                "editable install may have changed shape. A path-style install drops a\n"
                "`.pth` file, which loses to PYTHONPATH -- that is what this relies on. A\n"
                "finder-style install drops `__editable___<pkg>_*_finder.py` into\n"
                "site-packages and hooks sys.meta_path, which runs BEFORE sys.path is\n"
                "consulted, and against that PYTHONPATH is decoration.\n"
                "\n"
                "Check site-packages for `__editable___divineos_*_finder.py`. If it now\n"
                "exists, this check needs a different mechanism, not a nudge.\n"
                "\n"
                "SCOPE, corrected by measuring rather than by repeating: finder-style\n"
                "installs DO exist on this machine -- divineos_consciousness,\n"
                "automated_module_pipeline and swebench all carry finder files -- but in\n"
                "the SYSTEM interpreter's site-packages, not in the virtualenv this check\n"
                "runs under, where only path-style .pth files exist. So the hostile mode\n"
                "is real and adjacent, and it is not sitting in the same directory this\n"
                "code resolves through. An earlier version of this note said it was, on\n"
                "the strength of a family letter I had not checked.\n"
                "\n"
                "A check that begins refusing everything looks broken rather than\n"
                "informative, and the satisfiable move becomes switching it off. Hence the\n"
                "cause is printed with the refusal."
            )
            return 2
        print(f"[pin] baseline proven: divineos resolves inside the worktree ({proven})")

        for path, names in targets.items():
            # The NEW test file goes into the OLD tree. That is the whole trick.
            dest = worktree / path
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / path, dest)
            for name, verdict in classify(worktree, sys.executable, path, names):
                findings.append((path, name, verdict))
    finally:
        _git("worktree", "remove", "--force", str(worktree))
        _discard_scratch(holder)

    if args.json:
        print(json.dumps([{"file": f, "test": t, "verdict": v} for f, t, v in findings], indent=2))
    else:
        for path, name, verdict in findings:
            print(f"  {verdict:34} {path}::{name}")

    hollow = [f for f in findings if f[2] == "PINS-NOTHING"]
    if hollow:
        print(
            f"\n[pin] {len(hollow)} test(s) PASS against the code before this change.\n"
            "A regression test green on both sides guards nothing. It is not a weaker\n"
            "test -- it is indistinguishable from coverage while providing none, which\n"
            "is worse than no test at all.\n"
            "\n"
            "Check the FIXTURE first. The known cause is building it from memory of a\n"
            "real event rather than copying the record: a true statement about a\n"
            "command that never existed."
        )
        return 1

    print(f"\n[pin] all {len(findings)} added/changed test(s) fail against the base. They pin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
