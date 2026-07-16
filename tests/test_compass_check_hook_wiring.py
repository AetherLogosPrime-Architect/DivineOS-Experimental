"""End-to-end wiring test for .claude/hooks/compass-check.sh.

Marc external audit 2026-07-16 finding #1: the hook imported a
``main`` function from ``compass_rudder`` that does not exist. The
ImportError was swallowed by ``except: pass``, making the moral
compass rudder a permanent silent no-op. This was never caught in CI
because the existing compass-check tests only do static text/lexical
checks on the shell script — they never invoke it end-to-end against
the real Python module.

This test executes the hook the same way Claude Code does: pipes a
JSON tool-use payload into stdin, reads the stdout for the deny-
decision JSON. If the import is broken again, this test fails.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "compass-check.sh"


def _has_working_bash() -> bool:
    """Detect a bash that can actually execute — not just resolve on PATH.

    On Windows, ``shutil.which("bash")`` may find a WSL relay stub that
    fails to spawn ``/bin/bash`` in this repo's working directory. Probe
    with a trivial command; if it doesn't return cleanly, the runtime
    hook tests can't run here.
    """
    if shutil.which("bash") is None:
        return False
    try:
        r = subprocess.run(["bash", "-c", "echo ok"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and r.stdout.strip() == "ok"


_RUNTIME_SKIP = pytest.mark.skipif(
    not _has_working_bash(),
    reason="no working bash for runtime hook execution (e.g. WSL relay stub on this Windows box)",
)


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    """Invoke the hook the same way Claude Code does."""
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )


class TestCompassCheckHookWiring:
    def test_hook_imports_the_real_entry_point(self):
        """The hook must import a function that actually exists.

        Marc's finding: hook imported ``main`` which never existed.
        Real entry is ``check_tool_use``. This test greps the hook
        source for the correct import; a regression rename here fails
        the test loudly instead of silently at runtime.
        """
        hook_text = HOOK_PATH.read_text(encoding="utf-8")
        assert "from divineos.core.compass_rudder import check_tool_use" in hook_text, (
            "hook does not import check_tool_use — the real compass_rudder "
            "entry point. If this fails, Marc audit finding #1 has regressed."
        )
        # Belt-and-suspenders: the broken import must NOT be present.
        assert "from divineos.core.compass_rudder import main" not in hook_text, (
            "hook still imports the nonexistent 'main' function — regression "
            "of Marc audit finding #1."
        )

    @_RUNTIME_SKIP
    def test_hook_runs_end_to_end_on_non_gated_tool(self):
        """A non-gated tool (Bash, Read, etc.) must pass through
        without error. Proves the hook actually executes — if the
        import were broken, we'd see the exception in stderr and no
        stdout."""
        result = _run_hook({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
        assert result.returncode == 0
        # Non-gated tool: allow, so no deny JSON on stdout.
        assert result.stdout.strip() == ""
        # And crucially: no GATE_ERROR / IMPORT_ERROR / PARSE_ERROR should have
        # been printed to stderr. If any of those appear, the wiring is broken.
        for err_marker in ("IMPORT_ERROR", "GATE_ERROR", "PARSE_ERROR"):
            assert err_marker not in result.stderr, (
                f"hook stderr contains {err_marker}: {result.stderr}"
            )

    @_RUNTIME_SKIP
    def test_hook_reaches_check_tool_use_for_gated_tool(self):
        """A gated tool (Task/Agent) must reach check_tool_use.
        Whether it blocks or allows depends on live compass state, but
        the hook must complete without import/parse/gate errors.
        """
        result = _run_hook(
            {
                "tool_name": "Task",
                "tool_input": {"subagent_type": "general-purpose", "prompt": "test"},
            }
        )
        assert result.returncode == 0
        for err_marker in ("IMPORT_ERROR", "GATE_ERROR", "PARSE_ERROR"):
            assert err_marker not in result.stderr, (
                f"hook stderr contains {err_marker}: {result.stderr}"
            )
        # If stdout has content, it must be valid JSON with the
        # PreToolUse deny shape. If empty, that means allow (no drift
        # above threshold, or no missing justification).
        if result.stdout.strip():
            parsed = json.loads(result.stdout)
            hso = parsed.get("hookSpecificOutput", {})
            assert hso.get("hookEventName") == "PreToolUse"
            assert hso.get("permissionDecision") in ("deny", "allow")
