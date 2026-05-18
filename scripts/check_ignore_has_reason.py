#!/usr/bin/env python3
"""Block pytest --ignore= flags that don't carry a # REASON: comment.

Aletheia Finding 74 (2026-05-17): the bypass-discipline-failure pattern
recurred twice in one day. Bypass-too-broad catches less than intended;
the test you mask hides the next bug. Honest-naming-after-the-fact is
useful but not preventive. Substrate-level prevention is structural —
this check, run at precommit + pre-push, refuses to ship code that uses
``--ignore=`` against pytest without an adjacent ``# REASON:`` comment
naming what is being masked and why.

The comment must appear within 3 lines above the --ignore usage and
contain the literal token ``REASON:``. The comment body should name:
  - what specifically is being masked
  - the failure-shape being suppressed (claim/pre-reg/finding ID)
  - the unblocking condition (when this --ignore can be removed)

A bypass without a REASON comment is the pattern Finding 74 closes.

Usage:
    python scripts/check_ignore_has_reason.py        # scan whole repo
    python scripts/check_ignore_has_reason.py FILE   # scan one file

Exit codes:
    0 — all --ignore usages carry REASON comments (or none present)
    1 — one or more --ignore usages lack REASON comments
    2 — infrastructure error
"""

from __future__ import annotations

# Module-level guardrail marker — Aletheia Finding 74 (2026-05-17).
# This file is on scripts/guardrail_files.txt; CI test_guardrail_marker_consistency
# verifies every guardrail-listed module sets this to True.
__guardrail_required__ = True


import re
import sys
from pathlib import Path

# Files to scan. Tests and lockfiles are excluded — the check is about
# CI/script invocations that gate the substrate, not test code itself.
_SCAN_DIRS = ("scripts", ".github", ".claude/hooks", "setup")
_SCAN_GLOBS = ("*.sh", "*.py", "*.yml", "*.yaml", "*.ps1")

# Pattern: pytest --ignore=PATH (with or without quotes)
_IGNORE_PAT = re.compile(r"--ignore=\S+")

# Looking-up window: how many lines above the --ignore to scan for REASON.
_LOOKBACK_LINES = 3


def _gather_files(root: Path) -> list[Path]:
    """Return all files under _SCAN_DIRS matching _SCAN_GLOBS.

    Excludes this checker file itself: its job is to describe the
    ``pytest --ignore=`` pattern, so it naturally contains pattern-shaped
    text in its docstring + error messages. Scanning it would produce
    only self-referential noise.
    """
    self_file = Path(__file__).resolve()
    files: list[Path] = []
    for sub in _SCAN_DIRS:
        d = root / sub
        if not d.exists():
            continue
        for pattern in _SCAN_GLOBS:
            files.extend(p for p in d.rglob(pattern) if p.resolve() != self_file)
    return sorted(set(files))


def _looks_like_pytest_invocation(line: str) -> bool:
    """True when --ignore= appears in what looks like a pytest call.

    A real pytest invocation has ``pytest`` (or ``python -m pytest`` or
    ``py.test``) on the same line as the ``--ignore=``. String literals in
    Python source or shell comments that happen to contain ``--ignore=``
    (e.g., this script's own help text, precommit.sh comments describing
    the check) lack that surrounding command shape and should NOT be
    flagged.

    Heuristic chain:
      1. ``--ignore=`` AND ``pytest`` (or ``py.test``) on the same line
      2. Line is not a comment (doesn't start with ``#`` after whitespace)
      3. Line doesn't begin with ``"`` or ``'`` (string-literal prose)

    Other tools that use --ignore (grep, rsync) don't fit (1) and so are
    correctly excluded.
    """
    if "--ignore=" not in line:
        return False
    if "pytest" not in line and "py.test" not in line:
        return False
    stripped = line.lstrip()
    if stripped.startswith("#"):
        return False
    if stripped.startswith(('"', "'")):
        return False
    return True


def _check_file(path: Path) -> list[tuple[int, str]]:
    """Return list of (line_number, offending_line) for bypasses lacking REASON.

    The REASON token must appear in a comment within ``_LOOKBACK_LINES``
    lines above the ``--ignore=`` usage. We accept any line that contains
    the literal ``REASON:`` token — case-sensitive, so accidental
    occurrences in prose don't satisfy the check.

    Each REASON binds to exactly one --ignore invocation. If the lookback
    window encounters an earlier --ignore invocation before finding the
    REASON, the lookback stops — the REASON was for that earlier
    invocation, not this one. Otherwise, ONE REASON comment near the top
    of a file would justify every --ignore in the file.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    lines = text.splitlines()
    violations: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if not _looks_like_pytest_invocation(line):
            continue
        # Walk back up to _LOOKBACK_LINES looking for REASON, but stop
        # at any other --ignore invocation (its REASON, not this one's).
        has_reason = False
        for back in range(1, _LOOKBACK_LINES + 1):
            j = i - back
            if j < 0:
                break
            prev = lines[j]
            if _looks_like_pytest_invocation(prev):
                break  # REASON beyond this point binds to a different invocation
            if "REASON:" in prev:
                has_reason = True
                break
        if not has_reason:
            violations.append((i + 1, line.strip()))
    return violations


def main(argv: list[str]) -> int:
    args = argv[1:]
    repo_root = Path(__file__).resolve().parent.parent

    if args:
        paths = [Path(a).resolve() for a in args]
    else:
        paths = _gather_files(repo_root)

    if not paths:
        print("[ignore-has-reason] no files to scan", file=sys.stderr)
        return 0

    violations: list[tuple[Path, int, str]] = []
    for p in paths:
        if not p.exists() or not p.is_file():
            continue
        for line_num, line in _check_file(p):
            violations.append((p, line_num, line))

    if not violations:
        return 0

    print(
        "[ignore-has-reason] BLOCKED — --ignore= usages without REASON comments:",
        file=sys.stderr,
    )
    for p, line_num, line in violations:
        try:
            rel = p.relative_to(repo_root)
        except ValueError:
            rel = p
        print(f"  {rel}:{line_num}: {line[:120]}", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "Each --ignore= invocation must carry a # REASON: comment within "
        f"{_LOOKBACK_LINES} lines above naming what's masked and why.",
        file=sys.stderr,
    )
    print("Example:", file=sys.stderr)
    print("", file=sys.stderr)
    print(
        "    # REASON: test_check_broad_exceptions has 21 pre-existing",
        file=sys.stderr,
    )
    print(
        "    #         violations on unrelated files (claim b28b9a27);",
        file=sys.stderr,
    )
    print(
        "    #         masking here so this gate's local pre-flight matches CI.",
        file=sys.stderr,
    )
    print(
        "    pytest --ignore=tests/test_check_broad_exceptions.py",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print(
        "Aletheia Finding 74 (2026-05-17): bypass-too-broad catches less "
        "than intended. The REASON: comment is the substrate-level fix.",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
