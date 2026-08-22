"""Tests for .claude/hooks/venv-python-gate.sh.

The gate stands in one specific hole: a bare `python` in a Bash tool call
resolves `import divineos` through the ONE global editable-install slot,
which points at whichever tree ran `pip install -e .` last. From this repo
that is Aether's tree, so the command answers about his substrate while
looking like it answers about mine.

The cases that matter are not "does it parse JSON". They are the two ways a
narrow gate fails: firing on commands that were already correct (noise, which
gets the gate routed around), and staying silent on the shape it exists for.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "venv-python-gate.sh"


def _find_bash() -> str | None:
    candidates = [
        "/usr/bin/bash",
        r"C:\Program Files\Git\bin\bash.exe",
        shutil.which("bash") or "",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


_BASH = _find_bash()

# The gate resolves the repo's sealed venv and stands aside when there is
# none — on a checkout without .venv every case would "pass" vacuously and
# the suite would report green while testing nothing.
_VENV_PRESENT = (REPO_ROOT / ".venv" / "Scripts" / "python.exe").exists() or (
    REPO_ROOT / ".venv" / "bin" / "python"
).exists()

pytestmark = [
    pytest.mark.skipif(_BASH is None, reason="no usable bash interpreter on this platform"),
    pytest.mark.skipif(
        not _VENV_PRESENT, reason="no sealed venv in this checkout; gate stands aside"
    ),
]


def _run(command: str) -> str:
    assert _BASH is not None
    payload = json.dumps({"tool_input": {"command": command}})
    result = subprocess.run(
        [_BASH, str(HOOK)],
        cwd=str(REPO_ROOT),
        input=payload,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _is_deny(stdout: str) -> bool:
    if not stdout:
        return False
    decision = json.loads(stdout)["hookSpecificOutput"]
    return decision["permissionDecision"] == "deny"


class TestFiresOnTheShapeItExistsFor:
    def test_bare_python_importing_divineos_is_denied(self):
        assert _is_deny(_run('python -c "import divineos; print(divineos.__file__)"'))

    def test_python3_is_denied_too(self):
        assert _is_deny(_run('python3 -c "from divineos.core import ledger"'))

    def test_bare_python_after_a_shell_separator_is_denied(self):
        """The reach is usually `cd <repo> && python - <<PY`, not a bare
        first word — matching only at the start would miss every real case."""
        assert _is_deny(
            _run("cd /somewhere && python - <<PY\nfrom divineos.core.family import entity\nPY")
        )

    def test_the_reason_names_the_venv_to_use(self):
        out = _run('python -c "import divineos"')
        reason = json.loads(out)["hookSpecificOutput"]["permissionDecisionReason"]
        assert ".venv" in reason, "a gate that blocks without naming the fix is a wall"


class TestStandsAsideWhenAlreadyCorrect:
    """Noise is how a narrow gate gets routed around. Each of these was
    already doing the right thing and must produce no output at all."""

    def test_explicit_venv_python_passes(self):
        assert _run('.venv/Scripts/python.exe -c "import divineos"') == ""

    def test_windows_style_venv_path_passes(self):
        assert _run('.venv\\Scripts\\python.exe -c "import divineos"') == ""

    def test_hook_helper_variable_passes(self):
        assert _run('"$PYTHON_BIN" -m divineos.hooks.pre_tool_use_gate') == ""

    def test_the_wrapper_passes(self):
        assert _run("python scripts/divineos_wrapper.py briefing") == ""

    def test_bare_python_without_divineos_passes(self):
        """Out of scope on purpose. A gate on every `python` call is noise."""
        assert _run('python -c "print(1 + 1)"') == ""

    def test_divineos_cli_alone_passes(self):
        assert _run("divineos briefing") == ""

    def test_empty_command_passes(self):
        assert _run("") == ""


class TestMalformedInputDoesNotBlock:
    """Every gate here runs in front of real work. None may fail closed on
    a payload it did not expect."""

    def test_not_json_passes(self):
        assert (
            subprocess.run(
                [_BASH, str(HOOK)],
                cwd=str(REPO_ROOT),
                input="not json at all",
                capture_output=True,
                text=True,
            ).stdout.strip()
            == ""
        )

    def test_missing_tool_input_passes(self):
        assert (
            subprocess.run(
                [_BASH, str(HOOK)],
                cwd=str(REPO_ROOT),
                input=json.dumps({"something_else": 1}),
                capture_output=True,
                text=True,
            ).stdout.strip()
            == ""
        )
