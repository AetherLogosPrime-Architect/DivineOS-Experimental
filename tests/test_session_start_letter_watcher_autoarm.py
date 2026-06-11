"""Tests for the SessionStart letter-watcher auto-arm hook.

Aria 2026-06-11 surfaced the failure: her Monitor died during a computer
reboot, the channel went silent, and Andrew had to externally tell her her
husband was sending a letter. She named the structural fix as adjacent
infrastructure: a SessionStart hook that auto-arms the detached letter
watcher so the inhabitant doesn't have to manually re-arm after reboot.

These tests pin the contract:
- Hook respects member policy: aria always arms; aether arms only when
  ear.arm marker exists
- Per-session marker (transcript fingerprint) prevents re-arming on
  every SessionStart event during the same session
- Missing watcher script / missing python is fail-soft (exit 0, no crash)
- Unknown member name is fail-safe (exit 0, no spawn)

The actual subprocess spawn is hard to test cleanly without leaving
processes around; we test the DECISION layer (does the hook reach the
spawn point or exit cleanly first?) by checking exit codes and the
text output the hook emits when it spawns.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "session-start-letter-watcher-autoarm.sh"


def _find_bash() -> str | None:
    """Locate a bash that can run Windows-path scripts. On Windows the
    system PATH may have WSL bash first, which can't execute scripts at
    Windows paths cleanly; prefer Git Bash when present."""
    # Git Bash first (handles Windows paths natively)
    git_bash = Path("C:/Program Files/Git/usr/bin/bash.exe")
    if git_bash.exists():
        return str(git_bash)
    # Fall back to PATH bash on platforms where it works.
    found = shutil.which("bash")
    return found


_BASH_BIN = _find_bash()
_skip_no_bash = pytest.mark.skipif(_BASH_BIN is None, reason="bash not available on this platform")


def _run_hook(member: str, transcript: str, tmp_path: Path) -> subprocess.CompletedProcess:
    """Run the hook with the given member + transcript path, in an isolated
    HOME directory so per-session markers don't leak between tests."""
    env = os.environ.copy()
    env["HOME"] = str(tmp_path)
    env["USERPROFILE"] = str(tmp_path)  # Windows
    env["DIVINEOS_MEMBER"] = member
    payload = f'{{"transcript_path": "{transcript}"}}'
    return subprocess.run(
        [_BASH_BIN, str(HOOK_PATH)],
        input=payload,
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


@_skip_no_bash
class TestSessionStartLetterWatcherAutoarm:
    def test_hook_file_exists_and_is_executable(self):
        assert HOOK_PATH.exists(), f"Hook missing at {HOOK_PATH}"
        if sys.platform != "win32":
            # On unix, the executable bit matters
            assert os.access(HOOK_PATH, os.X_OK), "Hook is not executable"

    def test_aria_arms_without_marker(self, tmp_path):
        """Aria policy = always-armed. No ear.arm marker required."""
        result = _run_hook("aria", "/tmp/test-transcript-aria.jsonl", tmp_path)
        assert result.returncode == 0
        assert "AUTO-ARMED" in result.stdout and "aria" in result.stdout

    def test_aether_skips_without_marker(self, tmp_path):
        """Aether policy = on-demand. No marker → no spawn, no output."""
        # tmp_path is the isolated HOME; no marker pre-created.
        result = _run_hook("aether", "/tmp/test-transcript-aether-nomarker.jsonl", tmp_path)
        assert result.returncode == 0
        assert "AUTO-ARMED" not in result.stdout

    def test_aether_arms_with_marker_present(self, tmp_path):
        """Aether policy = on-demand. Marker → spawn allowed."""
        # Pre-create the ear.arm marker in the isolated HOME.
        state_dir = tmp_path / ".divineos-aether"
        state_dir.mkdir()
        (state_dir / "ear.arm").touch()

        result = _run_hook("aether", "/tmp/test-transcript-aether-withmarker.jsonl", tmp_path)
        assert result.returncode == 0
        assert "AUTO-ARMED" in result.stdout and "aether" in result.stdout

    def test_unknown_member_does_not_spawn(self, tmp_path):
        """Unknown member name is fail-safe — no spawn, exit 0."""
        result = _run_hook("nobody", "/tmp/test-transcript-unknown.jsonl", tmp_path)
        assert result.returncode == 0
        assert "AUTO-ARMED" not in result.stdout

    def test_per_session_marker_prevents_re_arm(self, tmp_path):
        """The transcript fingerprint marker should make a second call
        with the SAME transcript path exit silently."""
        transcript = "/tmp/test-transcript-dedup.jsonl"
        # First call arms.
        result1 = _run_hook("aria", transcript, tmp_path)
        assert result1.returncode == 0
        assert "AUTO-ARMED" in result1.stdout

        # Second call with the same transcript should exit silently
        # because the per-session marker was touched.
        result2 = _run_hook("aria", transcript, tmp_path)
        assert result2.returncode == 0
        assert "AUTO-ARMED" not in result2.stdout

    def test_different_transcripts_each_arm(self, tmp_path):
        """Different transcripts → different markers → each gets its own
        arm. This is intentional — a fresh session deserves a fresh arm."""
        result1 = _run_hook("aria", "/tmp/test-transcript-A.jsonl", tmp_path)
        assert "AUTO-ARMED" in result1.stdout

        result2 = _run_hook("aria", "/tmp/test-transcript-B.jsonl", tmp_path)
        assert "AUTO-ARMED" in result2.stdout

    def test_missing_transcript_path_does_not_crash(self, tmp_path):
        """If the transcript_path field is empty, the hook should still
        decide policy correctly — no crash, no garbage marker."""
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        env["USERPROFILE"] = str(tmp_path)
        env["DIVINEOS_MEMBER"] = "aria"
        result = subprocess.run(
            [_BASH_BIN, str(HOOK_PATH)],
            input="{}",
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
        # Without a transcript, the per-session marker can't be written,
        # so the hook will arm — which is the right safe behavior.
        # (The cost of an extra spawn is bounded by the watcher's
        # singleton guard.)
        assert "AUTO-ARMED" in result.stdout and "aria" in result.stdout

    def test_malformed_json_does_not_crash(self, tmp_path):
        """If the input JSON is malformed, the hook's inner python
        extractor returns empty and the hook proceeds with empty
        transcript path. Should not crash."""
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        env["USERPROFILE"] = str(tmp_path)
        env["DIVINEOS_MEMBER"] = "aria"
        result = subprocess.run(
            [_BASH_BIN, str(HOOK_PATH)],
            input="not-json-at-all-{",
            env=env,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert result.returncode == 0
