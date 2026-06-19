"""Phase 0 wiring-gap probe — empirical study, not the shipped check.

PDSA cycle (Deming) on the wiring-gap detection design. Don't build defensive
machinery on theory; build on what the data shows.

This script:
  1. Walks `src/divineos/core/` for every public function definition
     (non-underscored, top-level or class-level).
  2. For each function, counts non-test callers across the repo.
  3. Reports the distribution of caller counts so we can see the false-
     positive and false-negative landscape before designing the gate.

The point is OBSERVATION (Jacobs), not enforcement. The shipped check —
if there is one — will be a downstream design informed by what we see here.

Usage:
  python scripts/wiring_gap_probe.py             # summary
  python scripts/wiring_gap_probe.py --details   # full per-function listing
  python scripts/wiring_gap_probe.py --zero-callers-only  # just the candidates
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
CORE_DIR = REPO_ROOT / "src" / "divineos" / "core"
TESTS_DIR = REPO_ROOT / "tests"


@dataclass
class FunctionInfo:
    name: str
    file: Path
    line: int
    is_method: bool
    class_name: str = ""
    production_callers: list[str] = field(default_factory=list)
    test_callers: list[str] = field(default_factory=list)


def _is_public(name: str) -> bool:
    """Public = no leading underscore. Dunder methods aren't 'public' in
    the wiring-gap sense; they're protocol implementations."""
    return not name.startswith("_")


def _collect_functions(path: Path) -> list[FunctionInfo]:
    """Walk one .py file and yield public function/method definitions."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return []

    out: list[FunctionInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and _is_public(node.name):
            # Determine if it's a method (parent is ClassDef)
            # ast.walk doesn't track parents; use a separate pass for methods
            out.append(
                FunctionInfo(
                    name=node.name,
                    file=path,
                    line=node.lineno,
                    is_method=False,
                )
            )

    # Second pass: tag methods with their class so we have context
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and _is_public(child.name):
                    for fi in out:
                        if fi.line == child.lineno and fi.name == child.name:
                            fi.is_method = True
                            fi.class_name = node.name

    return out


def _scan_callers(functions: list[FunctionInfo]) -> None:
    """For each function, find call sites across the repo.

    Naive grep-style: looks for `name(` or `.name(` in any .py file under
    src/ and tests/. Then classifies as production vs test by path.

    Limitations (documented as part of the Phase 0 honesty):
      - Indirect calls (assigned to variable, then called) aren't counted
      - String references / getattr aren't counted
      - Method calls where the receiver type isn't statically known still
        count, which inflates counts (false-positive in caller direction =
        false-negative in wiring-gap direction)
    """
    # Build a map of name -> functions with that name (some collide across files)
    by_name: dict[str, list[FunctionInfo]] = {}
    for fi in functions:
        by_name.setdefault(fi.name, []).append(fi)

    # Walk src/ and tests/
    for py_file in REPO_ROOT.glob("src/**/*.py"):
        _scan_one_file(py_file, by_name, is_test=False)
    for py_file in REPO_ROOT.glob("tests/**/*.py"):
        _scan_one_file(py_file, by_name, is_test=True)


def _scan_one_file(
    py_file: Path,
    by_name: dict[str, list[FunctionInfo]],
    is_test: bool,
) -> None:
    """Find call-sites in one file; tag each function as production-called
    or test-called accordingly."""
    try:
        text = py_file.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return

    for name, candidates in by_name.items():
        # Look for `name(` or `.name(` — also catches `from X import name`-then-call shapes
        pattern = re.compile(r"\b" + re.escape(name) + r"\s*\(")
        for match in pattern.finditer(text):
            # Skip if it's the definition line itself
            for fi in candidates:
                if py_file == fi.file:
                    # Estimate by line position — skip if very close to definition
                    line_of_match = text[: match.start()].count("\n") + 1
                    if abs(line_of_match - fi.line) <= 1:
                        continue
                caller_label = str(py_file.relative_to(REPO_ROOT))
                if is_test:
                    if caller_label not in fi.test_callers:
                        fi.test_callers.append(caller_label)
                else:
                    if caller_label not in fi.production_callers:
                        fi.production_callers.append(caller_label)


def _classify(fi: FunctionInfo) -> str:
    """Three buckets from the council walk:
    - SHIPPED-BUT-UNWIRED: zero production callers (might be the bug)
    - WIRED-LIBRARY: 1-2 production callers (likely API+internal usage)
    - WIRED-WELL: 3+ production callers (clearly load-bearing)
    """
    n = len(fi.production_callers)
    # Exclude the function's own file from the count — being called within
    # the module that defines it doesn't count as "wired into the system."
    own_file = str(fi.file.relative_to(REPO_ROOT))
    external_callers = [c for c in fi.production_callers if c != own_file]

    if not external_callers:
        return "SHIPPED-BUT-UNWIRED"
    if len(external_callers) <= 2:
        return "WIRED-LIBRARY"
    return "WIRED-WELL"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--details", action="store_true", help="Full per-function listing")
    parser.add_argument(
        "--zero-callers-only",
        action="store_true",
        help="Only list functions with zero non-test external callers",
    )
    args = parser.parse_args(argv)

    print(f"# Wiring-gap probe — {CORE_DIR.relative_to(REPO_ROOT)}\n")

    all_funcs: list[FunctionInfo] = []
    for py_file in CORE_DIR.glob("**/*.py"):
        all_funcs.extend(_collect_functions(py_file))

    print(f"Found {len(all_funcs)} public function/method definitions.")
    print("Scanning callers across src/ and tests/...\n")
    _scan_callers(all_funcs)

    # Classify
    buckets: dict[str, list[FunctionInfo]] = {
        "SHIPPED-BUT-UNWIRED": [],
        "WIRED-LIBRARY": [],
        "WIRED-WELL": [],
    }
    for fi in all_funcs:
        buckets[_classify(fi)].append(fi)

    # Summary
    print("## Bucket distribution\n")
    for bucket, items in buckets.items():
        pct = 100.0 * len(items) / max(len(all_funcs), 1)
        print(f"  {bucket:24s}  {len(items):4d}  ({pct:5.1f}%)")
    print()

    if args.zero_callers_only or args.details:
        target_bucket = "SHIPPED-BUT-UNWIRED" if args.zero_callers_only else None
        for bucket, items in buckets.items():
            if target_bucket and bucket != target_bucket:
                continue
            print(f"\n## {bucket}\n")
            for fi in sorted(items, key=lambda f: (f.file, f.line)):
                ctx = f"  {fi.class_name}." if fi.is_method else "  "
                rel = fi.file.relative_to(REPO_ROOT)
                print(f"{ctx}{fi.name}  ({rel}:{fi.line})")
                if args.details:
                    if fi.production_callers:
                        print(f"      production callers ({len(fi.production_callers)}):")
                        for c in fi.production_callers[:5]:
                            print(f"        - {c}")
                        if len(fi.production_callers) > 5:
                            print(f"        ... and {len(fi.production_callers) - 5} more")
                    if fi.test_callers:
                        print(f"      test callers: {len(fi.test_callers)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
