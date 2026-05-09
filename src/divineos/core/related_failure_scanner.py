"""Related-failure scanner — catches "fixed one but missed related failures."

Lesson x8 (second most repeated): "I fixed one problem but missed
related failures. Check all affected areas after a fix."

## Architecture

After an Edit tool succeeds, this module checks whether the old_string
pattern appears in other files in the same codebase. If it does, the
PostToolUse hook surfaces an advisory: "You fixed this in file X —
but the same pattern exists in files Y and Z."

This is advisory (soft-advise), not blocking. The agent gets the
information and decides whether the other occurrences need fixing.
Blocking would be too aggressive — sometimes the "same pattern" in
other files is intentionally different.

## How it works

1. PostToolUse hook calls ``scan_for_related()`` after a successful Edit.
2. The scanner greps for the old_string (or a simplified version of it)
   across ``src/`` and ``tests/``.
3. If matches are found in OTHER files, it returns an advisory message.
4. The hook surfaces the advisory via ``_make_soft_advise()``.

## Performance

Only runs on Edit (not Write, not Bash). Only greps if the old_string
is >= 10 chars (short strings produce too many false matches). Limits
results to 5 files to keep the message readable.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

# Don't scan for patterns shorter than this — too many false matches.
MIN_PATTERN_LENGTH = 10

# Maximum files to report in the advisory.
MAX_REPORTED_FILES = 5


def scan_for_related(
    file_path: str,
    old_string: str,
    repo_root: str | None = None,
) -> str | None:
    """Check if old_string appears in other files.

    Returns an advisory message if matches found, None otherwise.
    """
    if not old_string or len(old_string.strip()) < MIN_PATTERN_LENGTH:
        return None

    # Use the first meaningful line of the old_string as search pattern.
    # Full multi-line patterns are too specific to match elsewhere.
    lines = [ln.strip() for ln in old_string.strip().splitlines() if ln.strip()]
    if not lines:
        return None

    # Pick the most distinctive line (longest, avoiding common boilerplate)
    search_line = max(lines, key=len)
    if len(search_line) < MIN_PATTERN_LENGTH:
        return None

    # Determine repo root
    if repo_root is None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            repo_root = result.stdout.strip() if result.returncode == 0 else "."
        except (subprocess.TimeoutExpired, OSError):
            repo_root = "."

    # Escape regex special chars for literal grep
    import re

    escaped = re.escape(search_line[:80])

    # Run ripgrep or grep for the pattern
    try:
        result = subprocess.run(
            [
                "rg",
                "--files-with-matches",
                "--fixed-strings",
                "--glob",
                "*.py",
                "--max-count",
                "1",
                search_line[:80],
            ],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=repo_root,
        )
        if result.returncode != 0:
            return None
        matched_files = result.stdout.strip().splitlines()
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # Fallback to grep if rg not available
        try:
            result = subprocess.run(
                ["grep", "-rl", "--include=*.py", search_line[:60], "src/", "tests/"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=repo_root,
            )
            if result.returncode != 0:
                return None
            matched_files = result.stdout.strip().splitlines()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None

    # Normalize and exclude the file we just edited
    norm_edited = Path(file_path).resolve()
    other_files = []
    for f in matched_files:
        norm_f = (Path(repo_root) / f).resolve()
        if norm_f != norm_edited:
            other_files.append(f)

    if not other_files:
        return None

    shown = other_files[:MAX_REPORTED_FILES]
    extra = len(other_files) - len(shown)
    file_list = ", ".join(shown)
    extra_note = f" (+{extra} more)" if extra else ""

    return (
        f"RELATED-PATTERN CHECK: The pattern you just changed in "
        f"{Path(file_path).name} also appears in: {file_list}{extra_note}. "
        f"Check whether those files need the same fix. "
        f"(Lesson x8: 'fixed one but missed related failures.')"
    )
