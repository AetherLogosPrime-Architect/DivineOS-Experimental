"""End-to-end wiring test for .claude/hooks/corrigibility-tool-gate.sh.

Marc external audit 2026-07-16 finding #2: the corrigibility_tool_gate
module was complete + unit-tested but had zero non-test callers, meaning
EMERGENCY_STOP mode blocked only the divineos CLI dispatcher and did
NOT reach the agent's actual Bash/Edit/Write/NotebookEdit tools.

This test suite pins the wiring closed:
  - static: hook imports check_tool_under_corrigibility
  - static: hook is registered in .claude/settings.json under a matcher
    covering Edit|Write|NotebookEdit|Bash
  - runtime: hook executes end-to-end without import/parse/gate errors
    (skipped on Windows-with-broken-WSL-bash boxes)
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK_PATH = REPO_ROOT / ".claude" / "hooks" / "corrigibility-tool-gate.sh"
SETTINGS_PATH = REPO_ROOT / ".claude" / "settings.json"


def _has_working_bash() -> bool:
    if shutil.which("bash") is None:
        return False
    try:
        r = subprocess.run(["bash", "-c", "echo ok"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return r.returncode == 0 and r.stdout.strip() == "ok"


_RUNTIME_SKIP = pytest.mark.skipif(
    not _has_working_bash(),
    reason="no working bash for runtime hook execution (e.g. WSL relay stub on Windows)",
)


def _run_hook(payload: dict) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(HOOK_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )


class TestCorrigibilityToolGateHookWiring:
    def test_hook_imports_the_real_entry_point(self):
        """Regression pin for Marc finding #2: hook must import
        check_tool_under_corrigibility. If the module is renamed or the
        hook diverges, this catches it in CI.
        """
        hook_text = HOOK_PATH.read_text(encoding="utf-8")
        assert (
            "from divineos.core.corrigibility_tool_gate import check_tool_under_corrigibility"
            in hook_text
        ), (
            "hook does not import check_tool_under_corrigibility — the real "
            "corrigibility_tool_gate entry point. Regression of Marc finding #2."
        )

    def test_hook_is_registered_in_settings_json(self):
        """The hook must appear in a PreToolUse matcher covering the
        mutating tools. Marc's finding: the module was complete but
        never referenced in settings.json, so it never ran.
        """
        settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        pre_tool_use = settings.get("hooks", {}).get("PreToolUse", [])
        for block in pre_tool_use:
            matcher = block.get("matcher", "")
            hooks = block.get("hooks", [])
            for hook in hooks:
                cmd = hook.get("command", "")
                if "corrigibility-tool-gate.sh" in cmd:
                    # Matcher must include at least Edit, Write, Bash.
                    for required in ("Edit", "Write", "Bash"):
                        assert required in matcher, (
                            f"corrigibility-tool-gate.sh matcher {matcher!r} "
                            f"is missing {required!r} — a mutating tool the "
                            f"gate is meant to cover."
                        )
                    return
        pytest.fail(
            "corrigibility-tool-gate.sh is not registered in any PreToolUse "
            "matcher in .claude/settings.json — regression of Marc finding #2."
        )

    @_RUNTIME_SKIP
    def test_hook_runs_end_to_end_without_errors(self):
        """A tool call under normal mode (not EMERGENCY_STOP) must pass
        through the hook without any IMPORT/PARSE/GATE errors on stderr.
        """
        result = _run_hook({"tool_name": "Bash", "tool_input": {"command": "echo hi"}})
        assert result.returncode == 0
        for err_marker in ("IMPORT_ERROR", "GATE_ERROR", "PARSE_ERROR"):
            assert err_marker not in result.stderr, (
                f"hook stderr contains {err_marker}: {result.stderr}"
            )
