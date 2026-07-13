"""Regression-pin for the vulture (dead-code) configuration.

Task #117 (Andrew 2026-06-09): Click-decorated CLI commands, pytest
fixtures, Protocol parameter names, and other dynamically-referenced
symbols look statically unused. Without proper vulture config, an AI
cleanup pass would delete them.

This test runs vulture with the project's pyproject.toml config + the
load-bearing whitelist and pins:
  - Zero high-confidence hits in src/divineos/.
  - The whitelist file is wired into the paths.
  - The decorator-ignore list catches Click + pytest patterns.

If vulture surfaces a new hit, treat it as a real signal:
  1. If genuinely dead → delete the symbol.
  2. If load-bearing but undetectable statically → add an entry to
     scripts/vulture_whitelist.py with a one-line REASON comment.

A failing run here means the rule got crossed; the test names exactly
which symbol so the resolution is unambiguous.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.skipif(
    shutil.which("vulture") is None,
    reason="vulture not installed in this environment",
)
def test_vulture_clean_on_default_config():
    """Run vulture with no args — pyproject config applies. Expect
    exit code 0 (no high-confidence dead code under current config)."""
    result = subprocess.run(
        [sys.executable, "-m", "vulture"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=60,
    )
    # vulture exits 0 if no dead code found, 3 if dead code found.
    assert result.returncode == 0, (
        "Vulture flagged new candidates — either delete the symbol or add it to "
        "scripts/vulture_whitelist.py with a reason comment.\n\n"
        f"Output:\n{result.stdout}"
    )


def test_whitelist_file_exists():
    """The whitelist file must exist; pyproject's [tool.vulture] paths
    references it. A missing file would silently make all Protocol
    param hits reappear."""
    whitelist = REPO_ROOT / "scripts" / "vulture_whitelist.py"
    assert whitelist.exists(), (
        "scripts/vulture_whitelist.py is referenced by pyproject "
        "[tool.vulture].paths and must exist."
    )


def test_pyproject_has_vulture_config():
    """The pyproject [tool.vulture] block carries the decorator-ignore
    list. Without it, hundreds of Click/pytest false positives reappear."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[tool.vulture]" in pyproject
    assert "ignore_decorators" in pyproject
    assert "@*.command" in pyproject  # Click pattern
    assert "@pytest.fixture" in pyproject  # pytest pattern
