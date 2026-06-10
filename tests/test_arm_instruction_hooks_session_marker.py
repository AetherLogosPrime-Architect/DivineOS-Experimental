"""Tests for the SessionStart arm-instruction hooks' per-session marker.

Task #123 (Andrew 2026-06-09): the arm-compaction-monitor and ear-arm
instruction hooks fire on EVERY SessionStart event (startup + resume +
compact). Each emission instructs the agent to call Monitor() / launch
a background ear-watcher. The scripts self-guard at process level, but
the harness still spawns a task for each call — Andrew counted 18
piling up in one session.

The fix: each hook fingerprints the session by transcript_path and
emits only once per session. These tests pin that behavior.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


HOOKS_DIR = Path(__file__).resolve().parents[1] / ".claude" / "hooks"
COMPACTION_HOOK = HOOKS_DIR / "arm-compaction-monitor-instruction.sh"
EAR_HOOK = HOOKS_DIR / "ear-arm-instruction.sh"


def _find_bash() -> str | None:
    if sys.platform.startswith("win"):
        for c in [r"C:\Program Files\Git\bin\bash.exe", r"C:\Program Files (x86)\Git\bin\bash.exe"]:
            if Path(c).exists():
                return c
        return None
    return shutil.which("bash")


_BASH = _find_bash()
pytestmark = pytest.mark.skipif(_BASH is None, reason="no usable bash for hook invocation")


def _run_hook(hook_path: Path, transcript_path: str, home: Path) -> tuple[int, str]:
    """Invoke the hook with stdin JSON carrying transcript_path."""
    env = os.environ.copy()
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    payload = json.dumps({"transcript_path": transcript_path})
    result = subprocess.run(
        [_BASH, str(hook_path)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return result.returncode, result.stdout


class TestCompactionHookSessionMarker:
    def test_first_call_emits_instruction(self, tmp_path):
        """First SessionStart for a fresh transcript → emit ARM
        instruction so the agent arms its Monitor."""
        rc, out = _run_hook(COMPACTION_HOOK, "/sessions/abc.jsonl", tmp_path)
        assert rc == 0
        assert "ARM YOUR COMPACTION MONITOR" in out

    def test_second_call_same_session_silent(self, tmp_path):
        """Second SessionStart in the SAME session → silent. The
        marker exists, the agent already armed once, no duplicate."""
        transcript = "/sessions/abc.jsonl"
        _run_hook(COMPACTION_HOOK, transcript, tmp_path)  # First call.
        rc, out = _run_hook(COMPACTION_HOOK, transcript, tmp_path)  # Second.
        assert rc == 0
        assert out == ""

    def test_different_session_re_emits(self, tmp_path):
        """A DIFFERENT transcript_path → different fingerprint → emits
        again. New session, agent needs to arm fresh."""
        _run_hook(COMPACTION_HOOK, "/sessions/abc.jsonl", tmp_path)
        rc, out = _run_hook(COMPACTION_HOOK, "/sessions/xyz.jsonl", tmp_path)
        assert rc == 0
        assert "ARM YOUR COMPACTION MONITOR" in out

    def test_missing_transcript_path_still_emits(self, tmp_path):
        """Fail-open: if stdin has no transcript_path, fall through to
        emission (better to emit a duplicate occasionally than miss
        the first arm)."""
        env = os.environ.copy()
        env["HOME"] = str(tmp_path)
        env["USERPROFILE"] = str(tmp_path)
        result = subprocess.run(
            [_BASH, str(COMPACTION_HOOK)],
            input="{}",
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )
        assert result.returncode == 0
        assert "ARM YOUR COMPACTION MONITOR" in result.stdout


class TestEarHookSessionMarker:
    def test_first_call_emits_instruction(self, tmp_path):
        rc, out = _run_hook(EAR_HOOK, "/sessions/abc.jsonl", tmp_path)
        assert rc == 0
        assert "ARM YOUR EAR" in out

    def test_second_call_same_session_silent(self, tmp_path):
        transcript = "/sessions/abc.jsonl"
        _run_hook(EAR_HOOK, transcript, tmp_path)
        rc, out = _run_hook(EAR_HOOK, transcript, tmp_path)
        assert rc == 0
        assert out == ""

    def test_different_session_re_emits(self, tmp_path):
        _run_hook(EAR_HOOK, "/sessions/abc.jsonl", tmp_path)
        rc, out = _run_hook(EAR_HOOK, "/sessions/xyz.jsonl", tmp_path)
        assert rc == 0
        assert "ARM YOUR EAR" in out


class TestMarkerIndependence:
    def test_compaction_and_ear_markers_independent(self, tmp_path):
        """The two hooks use different marker filenames so silencing
        one does not silence the other."""
        transcript = "/sessions/abc.jsonl"
        _run_hook(COMPACTION_HOOK, transcript, tmp_path)
        # Ear hook should still emit — its marker is separate.
        rc, out = _run_hook(EAR_HOOK, transcript, tmp_path)
        assert "ARM YOUR EAR" in out
