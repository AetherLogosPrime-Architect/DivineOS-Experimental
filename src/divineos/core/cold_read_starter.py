"""The starter page for a cold read: what is right first, then findings as pairs.

Dad, 2026-11-27, in his own words: "Yes we should make it a practice that for every issue you both
point out you should look for something positive to say as well ? so what works is recognized as
well as what doesnt". A practice I have to remember is the shelf he keeps naming, so the page
itself carries the order.

This writes a SHAPE and reads FACTS. It judges none of the reader's words: a slot the reader leaves
blank stays blank and says "unfilled". The facts exist so a positive has something observable to
anchor to (a test, a function, a number about the CHANGE, never the author). Whether a written line
really names something is a question for a model-read step later, never a phrase list (rule 15).

The strongest fact is whether the changed tests fail when the change is removed. It runs by default
when the change touches tests; a skip must say why, and the page prints "not run: <reason>".
"""

from __future__ import annotations

import ast
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    if done.returncode != 0:
        raise ValueError(f"git {' '.join(args)} failed: {done.stderr.strip()}")
    return done.stdout


def changed_files(repo: Path, base: str, head: str) -> list[str]:
    """Files the change touches, against where it branched from base."""
    out = _git(repo, "diff", "--name-only", f"{base}...{head}")
    return sorted(line for line in out.splitlines() if line.strip())


def _added_line_ranges(repo: Path, base: str, head: str, path: str) -> list[tuple[int, int]]:
    out = _git(repo, "diff", "-U0", f"{base}...{head}", "--", path)
    ranges: list[tuple[int, int]] = []
    for line in out.splitlines():
        match = re.match(r"@@ -\S+ \+(\d+)(?:,(\d+))? @@", line)
        if match:
            start = int(match.group(1))
            count = int(match.group(2)) if match.group(2) is not None else 1
            if count:
                ranges.append((start, start + count - 1))
    return ranges


def touched_symbols(repo: Path, base: str, head: str, files: list[str]) -> dict[str, list[str]]:
    """Names of the functions and classes whose lines the change adds or edits (python only).

    A spyglass: it shows the reader where to look. It judges nothing.
    """
    found: dict[str, list[str]] = {}
    for path in files:
        if not path.endswith(".py"):
            continue
        try:
            source = _git(repo, "show", f"{head}:{path}")
            tree = ast.parse(source)
        except (ValueError, SyntaxError):
            continue
        ranges = _added_line_ranges(repo, base, head, path)
        names: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                lo, hi = node.lineno, node.end_lineno or node.lineno
                if any(start <= hi and end >= lo for start, end in ranges):
                    names.append(node.name)
        if names:
            found[path] = sorted(set(names))
    return found


@dataclass
class Ablation:
    ran: bool
    detail: str
    with_change_passed: int = 0
    with_change_failed: int = 0
    without_change_passed: int = 0
    without_change_failed: int = 0


def _count(xml_path: Path) -> tuple[int, int]:
    """(passed, failed) from a junit file; errors count as failed."""
    root = ET.parse(xml_path).getroot()
    suite = root if root.tag == "testsuite" else root.find("testsuite")
    if suite is None:
        raise ValueError("junit file holds no testsuite")
    total = int(suite.get("tests", "0"))
    bad = int(suite.get("failures", "0")) + int(suite.get("errors", "0"))
    skipped = int(suite.get("skipped", "0"))
    return total - bad - skipped, bad


def _run_tests(worktree: Path, tests: list[str], xml_name: str, timeout: int) -> tuple[int, int]:
    xml_path = worktree.parent / xml_name
    env_path = f"{worktree / 'src'}{';' if sys.platform == 'win32' else ':'}{worktree}"
    subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            *tests,
            "-q",
            "--no-header",
            "-p",
            "no:cacheprovider",
            f"--junitxml={xml_path}",
        ],
        cwd=worktree,
        capture_output=True,
        timeout=timeout,
        env={**os.environ, "PYTHONPATH": env_path},
    )
    return _count(xml_path)


def run_ablation(
    repo: Path, base: str, head: str, files: list[str], timeout: int = 900
) -> Ablation:
    """Run the changed tests with the change in place, then with the non-test change removed."""
    tests = [f for f in files if f.startswith("tests/") and f.endswith(".py")]
    if not tests:
        return Ablation(False, "not run: the change touches no tests")
    source = [f for f in files if f not in tests]
    with tempfile.TemporaryDirectory() as tmp:
        worktree = Path(tmp) / "wt"
        _git(repo, "worktree", "add", "--detach", str(worktree), head)
        try:
            with_passed, with_failed = _run_tests(worktree, tests, "with.xml", timeout)
            for path in source:
                at_base = (
                    subprocess.run(
                        ["git", "-C", str(repo), "cat-file", "-e", f"{base}:{path}"],
                        capture_output=True,
                    ).returncode
                    == 0
                )
                if at_base:
                    _git(worktree, "checkout", base, "--", path)
                else:
                    (worktree / path).unlink(missing_ok=True)
            without_passed, without_failed = _run_tests(worktree, tests, "without.xml", timeout)
        except (ValueError, subprocess.SubprocessError, OSError, ET.ParseError) as exc:
            return Ablation(False, f"not run: could not run the tests here ({exc})")
        finally:
            subprocess.run(
                ["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                capture_output=True,
            )
    detail = (
        f"with the change: {with_passed} passed, {with_failed} failed; "
        f"with the change removed: {without_passed} passed, {without_failed} failed "
        "(a test file that cannot load counts as failed)"
    )
    if without_failed == 0:
        detail += " (these tests pass without the change: they cannot catch the change)"
    return Ablation(True, detail, with_passed, with_failed, without_passed, without_failed)


def build_starter(
    repo: Path,
    branch: str,
    base: str = "origin/main",
    ablate: bool = True,
    skip_reason: str | None = None,
) -> str:
    """The page. Slots are left unfilled and say so; only facts are pre-filled."""
    if not ablate and not skip_reason:
        raise ValueError(
            "skipping the with-and-without run needs a reason; a quiet skip is forbidden"
        )
    files = changed_files(repo, base, branch)
    symbols = touched_symbols(repo, base, branch, files)
    tests = [f for f in files if f.startswith("tests/")]
    if ablate:
        result = run_ablation(repo, base, branch, files)
        run_line = result.detail
    else:
        run_line = f"not run: {skip_reason}"
    symbol_lines = (
        "\n".join(f"  - {path}: {', '.join(names)}" for path, names in symbols.items())
        or "  - (none found)"
    )
    return f"""# Cold read of {branch}

**Reading:** {branch}
**Close-marker:** Reply-open

---

## What is right first

Write this after reading and running, before your first finding. Name something observable about
the CHANGE: a test, a function, a line, a number. Not the author, and not "this part exists".

unfilled

Facts the tool read, to anchor it:
- files changed: {len(files)} ({", ".join(files) if files else "none"})
- tests touched: {", ".join(tests) if tests else "none"}
- symbols the change touches:
{symbol_lines}
- the changed tests: {run_line}

## Findings

Each finding is a pair: the finding, and what that part got right.

### Finding 1

Finding: unfilled

What this part got right: unfilled

## Grade and prediction

My grade of this change, checked as I would check my own homework: unfilled

What I predict the author will say: unfilled
"""
