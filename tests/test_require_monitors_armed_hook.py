"""Tests for .claude/hooks/require-monitors-armed.sh.

The hook itself is bash; these tests subprocess-invoke it with crafted
PreToolUse JSON inputs and check the exit code / stderr behavior.

Deterministic paths covered here:
- Bypass list (`divineos ask`, etc.) → exit 0
- Emergency env var (`DIVINEOS_REQUIRE_MONITORS_BYPASS=1`) → exit 0
- Empty command → exit 0 (fail-open)
- Malformed JSON → exit 0 (fail-open)

The deny path (Monitor not alive → exit 2) depends on the OS process
list at test time and is verified by empirical smoke-test during PR
review rather than CI, because CI runs in environments where no
Monitors are alive — every test would fail unless we mocked the
process check, and mocking a shell-level powershell call inside a
bash script crosses too many layers to be useful.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


HOOK_PATH = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "require-monitors-armed.sh"


def _find_bash() -> str | None:
    """Locate a usable bash binary for invoking the hook in subprocess.

    On Windows the bare 'bash' on PATH resolves to WSL bash which can't
    see Windows files at Linux paths. The hooks are designed for Git Bash
    (`C:\\Program Files\\Git\\bin\\bash.exe`). On Linux/macOS, '/bin/bash'
    is the right binary.

    Returns the path string, or None if no suitable bash is found.
    """
    if sys.platform.startswith("win"):
        candidates = [
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ]
        for c in candidates:
            if Path(c).exists():
                return c
        return None
    found = shutil.which("bash")
    return found


_BASH = _find_bash()
pytestmark = pytest.mark.skipif(_BASH is None, reason="no usable bash found for hook invocation")


def _run_hook(command: str, extra_env: dict[str, str] | None = None) -> tuple[int, str, str]:
    """Invoke the hook with the given bash command as PreToolUse stdin.

    Returns (returncode, stdout, stderr).
    """
    payload = json.dumps(
        {
            "tool_name": "Bash",
            "tool_input": {"command": command},
        }
    )
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    result = subprocess.run(
        [_BASH, str(HOOK_PATH)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    return result.returncode, result.stdout, result.stderr


class TestEmergencyBypass:
    """The DIVINEOS_REQUIRE_MONITORS_BYPASS env var is the operator-level
    escape. Set on the specific invocation, not exported globally — that's
    Andrew 2026-05-31 design-constraint #3 (bypass must cost more than
    tool use)."""

    def test_emergency_bypass_passes(self):
        """With DIVINEOS_REQUIRE_MONITORS_BYPASS=1, ANY command exits 0
        even if Monitors are not alive — the operator has chosen to
        override."""
        rc, _, _ = _run_hook(
            "echo hello world",
            extra_env={"DIVINEOS_REQUIRE_MONITORS_BYPASS": "1"},
        )
        assert rc == 0


class TestBypassList:
    """Substrate-consult commands must always pass through — these are
    the gate-system's own prescribed remedies. Blocking them would
    create a chicken-and-egg trap (gate's recovery command blocked by
    the same gate). Pattern lifted from PR #112's shared bypass-list."""

    @pytest.mark.parametrize(
        "command",
        [
            "divineos briefing",
            "divineos ask 'topic'",
            "divineos recall",
            "divineos context",
            "divineos decide 'thing' --why 'reason'",
            "divineos directives",
            "divineos active",
            "divineos goal add 'new goal'",
            "divineos verify",
            "divineos learn 'lesson'",
            "divineos compass",
            "divineos compass-ops observe spectrum -p 0.5 -e 'evidence'",
            "divineos andrew-correction list",
        ],
    )
    def test_substrate_consult_passes(self, command):
        """Every documented substrate-consult command must pass through,
        because those ARE the commands the gate-system would tell the
        agent to run as recovery from any block."""
        rc, _, _ = _run_hook(command)
        assert rc == 0, f"command {command!r} should bypass but exited {rc}"

    def test_compound_with_bypass_first_passes(self):
        """A compound command starting with a bypass prefix passes
        (the bypass segment is the gate-recovery path)."""
        rc, _, _ = _run_hook("divineos ask 'topic' && echo done")
        assert rc == 0

    def test_partial_prefix_match_does_not_bypass(self):
        """`divineos askill` should NOT match `divineos ask` — the
        prefix check must require either exact-match or prefix+space.
        This catches the loose-prefix hole."""
        # We can't easily test the deny path here (depends on monitor
        # state), but we CAN test the BYPASS path: this command must
        # NOT be classified as a bypass. If it were, exit would be 0
        # regardless of monitor state. We force monitors-absent via
        # a side-channel: assume the hook either denies (rc=2) or
        # passes-because-monitors-alive (rc=0). To isolate just the
        # bypass logic, check that the hook's behavior on this string
        # is the SAME as its behavior on a clearly-not-bypass string
        # like "rm -rf /tmp/foo" — both should follow the same path.
        rc_a, _, _ = _run_hook("divineos askill")  # not a real divineos subcommand
        rc_b, _, _ = _run_hook("echo definitely-not-bypass")
        # The two non-bypass commands should reach the same verdict.
        assert rc_a == rc_b, (
            f"non-bypass 'divineos askill' (rc={rc_a}) should behave the "
            f"same as non-bypass 'echo definitely-not-bypass' (rc={rc_b}); "
            "if they diverge, the prefix-match is leaking 'askill' through "
            "as if it matched 'ask'"
        )


class TestFailOpen:
    """The hook is fail-open by design — any internal error MUST result
    in exit 0 rather than break the agent's turn. The deny path is
    intentional; the never-pass path would be catastrophic."""

    def test_empty_command_passes(self):
        rc, _, _ = _run_hook("")
        assert rc == 0

    def test_whitespace_only_command_passes(self):
        rc, _, _ = _run_hook("   ")
        assert rc == 0

    def test_malformed_json_input_passes(self):
        """If the JSON parser fails, the hook should silently exit 0
        rather than block the agent on a bad input."""
        result = subprocess.run(
            [_BASH, str(HOOK_PATH)],
            input="not valid json {{",
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
