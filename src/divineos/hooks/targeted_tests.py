"""Targeted test runner for PostToolUse — runs only tests affected by the edit.

# AGENT_RUNTIME — Not wired into CLI pipeline. Invoked from
# .claude/hooks/run-tests.sh as ``python -m divineos.hooks.targeted_tests``
# after Edit/Write/NotebookEdit on .py files.

## Why this exists

The previous run-tests.sh invoked ``pytest tests/`` (full suite) on every
.py edit. The full suite takes ~170 seconds (4,700+ tests). Running that
after every single edit is wildly wasteful and accounts for most of the
observed per-edit latency. The PreToolUse/PostToolUse gate refactor in
PR #149 saved ~1.3s per call; this saves an order of magnitude more
per-edit because it targets the single biggest expense in the edit cycle.

This module narrows to the test file that corresponds to the edited
source file via filename convention:

    src/divineos/core/foo.py → tests/test_foo.py
    src/divineos/cli/bar.py  → tests/test_bar.py
    tests/test_baz.py        → tests/test_baz.py (run directly)

If the mapped test file exists, we run only that (typically <1 second
on modern hardware). If no matching test file exists, we skip silently.
Editing __init__.py skips (no test_init.py convention).

## Coverage invariant preserved

Pre-commit hook still runs the full suite before any commit lands, so
this module does NOT reduce overall test coverage. What it changes is
*when* tests run: per-edit for the relevant file only, per-commit for
the whole suite. The per-edit signal is an early-warning for regressions
in the file under active edit; the per-commit signal is the full-gate
before merge.

## Edge cases

- File not .py → skip
- File outside src/divineos/ and not under tests/ → skip (not our code)
- Matching test file doesn't exist → skip silently (many modules are
  legitimately covered by tests of dependent modules, not dedicated ones)
- Edit to a test file itself → run that test file
- Repo root cannot be determined (no ``.git``, no ``tests/`` sibling to
  ``src/``) → skip (we're running in an unusual environment)
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _find_repo_root(start: Path) -> Path | None:
    """Walk up looking for a directory containing both ``src/`` and ``tests/``.

    Falls back to ``.git`` presence if the src+tests pair isn't found.
    Returns None if neither heuristic matches before filesystem root.
    """
    try:
        start = start.resolve()
    except OSError:
        return None
    for candidate in (start, *start.parents):
        if (candidate / "src").is_dir() and (candidate / "tests").is_dir():
            return candidate
        if (candidate / ".git").exists() and (candidate / "tests").is_dir():
            return candidate
    return None


def find_target_tests(file_path: str) -> Path | None:
    """Return the pytest target path for the given edited file, or None if
    nothing should run.

    Public for testing. The mapping rules are documented in the module
    docstring.
    """
    if not file_path:
        return None

    p = Path(file_path)
    if p.suffix != ".py":
        return None
    if p.name == "__init__.py":
        return None

    repo_root = _find_repo_root(p)
    if repo_root is None:
        return None

    # Normalize to a relative path under the repo root if possible.
    try:
        rel = p.resolve().relative_to(repo_root)
    except (OSError, ValueError):
        return None

    rel_str = str(rel).replace("\\", "/")

    # Case 1: edited a test file directly — run it if it exists.
    if rel_str.startswith("tests/"):
        resolved = repo_root / rel
        return resolved if resolved.exists() else None

    # Case 2: source file — look for corresponding test file by name.
    # Only process files under src/divineos/ (our code); everything else
    # is out of scope for the PostToolUse hook.
    if not rel_str.startswith("src/divineos/"):
        return None

    test_name = f"test_{p.stem}.py"
    test_path = repo_root / "tests" / test_name
    if test_path.exists():
        return test_path
    return None


def _run_pytest(target: Path) -> str:
    """Invoke pytest on the target, return the (trimmed) combined output.

    Returns an empty string on any error — fail-open so a broken test
    runner doesn't block editing.
    """
    try:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(target),
                "-q",
                "--tb=short",
                "--timeout=30",
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        return ""

    combined = ((result.stdout or "") + (result.stderr or "")).strip()
    if not combined:
        return ""
    lines = combined.splitlines()
    return "\n".join(lines[-15:])


def main() -> int:
    """Entry point. Reads hook JSON from stdin, emits additionalContext
    JSON to stdout if tests ran and produced output."""
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except (json.JSONDecodeError, OSError):
        return 0

    file_path = ""
    try:
        file_path = data.get("tool_input", {}).get("file_path", "") or ""
    except (AttributeError, TypeError):
        return 0

    target = find_target_tests(file_path)
    if target is None:
        return 0

    output = _run_pytest(target)
    if output:
        json.dump({"additionalContext": output}, sys.stdout)

    return 0


if __name__ == "__main__":
    sys.exit(main())
