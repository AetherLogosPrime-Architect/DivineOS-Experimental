"""Tests for .claude/hooks/check-cleanup-period.sh.

The hook surfaces a warning if Claude Code's cleanupPeriodDays setting
is dangerously low (< 90 days) or missing entirely (default 30 applies).
At 7 days (Andrew's prior state), session transcripts were getting
silently purged before DivineOS extraction could parse them.

These tests subprocess-invoke the hook with a fake HOME pointing at a
controlled settings.json fixture and verify the warning behavior.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


HOOK_PATH = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "check-cleanup-period.sh"


def _find_bash() -> str | None:
    """Same shape as the require-monitors-armed test — Windows finds
    Git Bash explicitly; Linux/macOS use whichever bash is on PATH."""
    if sys.platform.startswith("win"):
        candidates = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ]
        for c in candidates:
            if Path(c).exists():
                return c
        return None
    return shutil.which("bash")


_BASH = _find_bash()
pytestmark = pytest.mark.skipif(_BASH is None, reason="no usable bash found for hook invocation")


def _write_settings(home: Path, contents: dict | None) -> None:
    """Lay down a fake ~/.claude/settings.json under the given home."""
    settings_dir = home / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    if contents is not None:
        (settings_dir / "settings.json").write_text(
            json.dumps(contents, indent=2), encoding="utf-8"
        )


def _run_hook(home: Path) -> tuple[int, str]:
    """Invoke the hook with HOME pointed at the fixture dir.

    Returns (returncode, stdout).
    """
    env = os.environ.copy()
    # On Windows, both HOME and USERPROFILE matter — Python's Path.home()
    # uses USERPROFILE on Windows. We override both so the hook's
    # `$HOME` expansion AND the embedded python's `Path.home()` see
    # the fixture.
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    result = subprocess.run(
        [_BASH, str(HOOK_PATH)],
        input="",
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return result.returncode, result.stdout


class TestUnsafeValues:
    """Values that should trigger the warning."""

    def test_warns_when_missing(self, tmp_path):
        """No cleanupPeriodDays key → default 30 days applies, warn."""
        _write_settings(tmp_path, {"otherKey": "value"})
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0  # fail-open / informational
        assert "CLEANUPPERIODDAYS WARNING" in stdout
        assert "missing" in stdout.lower()

    def test_warns_when_7(self, tmp_path):
        """Andrew's prior state — 7 days, transcripts silently purged."""
        _write_settings(tmp_path, {"cleanupPeriodDays": 7})
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0
        assert "CLEANUPPERIODDAYS WARNING" in stdout
        assert "7 days" in stdout

    def test_warns_at_claude_code_default(self, tmp_path):
        """Claude Code's default of 30 is also below the 90-day safety
        minimum and should warn."""
        _write_settings(tmp_path, {"cleanupPeriodDays": 30})
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0
        assert "CLEANUPPERIODDAYS WARNING" in stdout
        assert "30 days" in stdout


class TestSafeValues:
    """Values that should keep the hook silent."""

    def test_silent_at_safety_threshold(self, tmp_path):
        """Exactly 90 is the safety minimum — silent."""
        _write_settings(tmp_path, {"cleanupPeriodDays": 90})
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0
        assert stdout == "" or "WARNING" not in stdout

    def test_silent_at_recommended(self, tmp_path):
        """99999 is the recommended value — silent."""
        _write_settings(tmp_path, {"cleanupPeriodDays": 99999})
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0
        assert stdout == "" or "WARNING" not in stdout

    def test_silent_at_365(self, tmp_path):
        """A reasonable year-long retention — silent."""
        _write_settings(tmp_path, {"cleanupPeriodDays": 365})
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0
        assert stdout == "" or "WARNING" not in stdout


class TestFailOpen:
    """Edge cases that must not block work."""

    def test_no_settings_file_silent(self, tmp_path):
        """If ~/.claude/settings.json doesn't exist (fresh Claude Code
        install pre-config), the hook stays silent — nothing to warn about
        yet."""
        # Don't write a settings file at all.
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0
        assert stdout == ""

    def test_malformed_json_silent(self, tmp_path):
        """Broken settings.json shouldn't crash the hook — fail-open."""
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir(parents=True)
        (settings_dir / "settings.json").write_text("not valid json {{", encoding="utf-8")
        rc, stdout = _run_hook(tmp_path)
        assert rc == 0
        # The hook can't parse the value, so it stays silent (rather
        # than warn falsely about a parse error).
        assert "WARNING" not in stdout
