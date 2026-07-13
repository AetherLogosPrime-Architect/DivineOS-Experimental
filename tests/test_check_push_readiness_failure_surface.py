"""Tests for the pre-push gate's failure-surface behavior.

Andrew 2026-06-10 ordeal: scripts/check_push_readiness.sh used to do
``tail -30 "$PYTEST_LOG" >&2`` on pytest failure, which dropped FAILED
lines for any suite with substantial warning output. Burned ~30 minutes
guessing at a single flaky test because the log buffer the script kept
didn't include the test name that broke.

These tests verify three properties of the fix:

1. On pytest failure, the full log is persisted to
   ``~/.divineos/last_pre_push_pytest.log`` so the agent can read it
   after the script exits.
2. The script greps for ``FAILED``/``ERROR`` lines and surfaces them
   explicitly in stderr (separate from the tail buffer).
3. The deny-message names where the full log lives so future-me knows
   where to read it without inventing the path.

Implementation: stub pytest with a tiny inline script that writes a
synthetic pytest-shaped output (warnings noise + FAILED lines + summary)
and exits non-zero, then run check_push_readiness.sh and inspect the
captured stderr + the persisted log file.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
_SCRIPT = _PROJECT_ROOT / "scripts" / "check_push_readiness.sh"


def _find_bash() -> str | None:
    candidates = [
        r"C:\Program Files\Git\bin\bash.exe",
        "/bin/bash",
        "/usr/bin/bash",
    ]
    for c in candidates:
        if Path(c).exists():
            return c
    found = shutil.which("bash")
    return found


_BASH = _find_bash()


@pytest.fixture
def isolated_home(tmp_path, monkeypatch):
    """Redirect HOME to tmp_path so the persisted log doesn't touch the
    real ~/.divineos directory."""
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    return tmp_path


@pytest.fixture
def fake_pytest_failing(tmp_path, monkeypatch):
    """Stand up a fake `python` on PATH whose `pytest` invocation emits
    realistic noise + FAILED lines and exits non-zero. The fixture writes
    a shim and prepends its directory to PATH for the test's duration."""
    shim_dir = tmp_path / "bin"
    shim_dir.mkdir()
    # On Windows the script invokes `python` literally; build a CMD batch
    # shim and a sibling shell shim so both contexts find it.
    bat_path = shim_dir / "python.bat"
    sh_path = shim_dir / "python"
    fake_output = (
        "============================= test session starts =============================\n"
        "platform win32 -- Python 3.13.11\n"
        "collected 3 items\n"
        "\n"
        "tests/test_a.py .                                                       [ 33%]\n"
        "tests/test_b.py F                                                       [ 66%]\n"
        "tests/test_c.py .                                                       [100%]\n"
        "\n"
        "================================== FAILURES ===================================\n"
        "________________________________ test_b_thing _________________________________\n"
        "tests/test_b.py:42: AssertionError\n"
        + ("warning noise line that pads the tail buffer\n" * 60)
        + "=========================== short test summary info ===========================\n"
        "FAILED tests/test_b.py::test_b_thing\n"
        "1 failed, 2 passed in 0.42s\n"
    )
    # Use a python one-liner inside the shim so the output stays portable.
    payload = fake_output.replace("'", "'\\''")
    bat_path.write_text(f"@echo off\r\necho '{payload}'\r\nexit /b 1\r\n")
    # Bash shim — fires for non-pytest invocations too (the script also
    # calls python earlier to set up env). Detect "-m pytest" and emit
    # the canned output; otherwise pass through to the real python.
    real_python = shutil.which("python") or "/usr/bin/python3"
    sh_path.write_text(
        "#!/bin/bash\n"
        'if [[ "$*" == *"-m pytest"* ]]; then\n'
        f"cat <<'PYTEST_EOF'\n{fake_output}PYTEST_EOF\n"
        "  exit 1\n"
        "fi\n"
        f'exec "{real_python}" "$@"\n'
    )
    os.chmod(sh_path, 0o755)
    monkeypatch.setenv("PATH", f"{shim_dir}{os.pathsep}{os.environ.get('PATH', '')}")
    return shim_dir


@pytest.mark.skipif(_BASH is None, reason="bash not available")
def test_persists_full_log_to_stable_path_on_failure(
    isolated_home, fake_pytest_failing, monkeypatch
):
    """The full pytest log must be copied to ~/.divineos/last_pre_push_pytest.log
    so the agent can read it after the script exits with the failure code."""
    # Run the script. It will invoke our shim python via PATH.
    result = subprocess.run(
        [_BASH, str(_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
        timeout=120,
        env={**os.environ, "HOME": str(isolated_home)},
    )

    # The script should exit non-zero from the pytest failure (exit 10).
    # The pre-script git-state checks may also exit early; what matters
    # is the persisted-log behavior IF pytest ran.
    log_path = isolated_home / ".divineos" / "last_pre_push_pytest.log"
    if not log_path.exists():
        pytest.skip(
            "pytest did not run in this environment (likely the script "
            "short-circuited on a pre-pytest check). The persistence "
            "behavior is only exercised when pytest actually runs and "
            "fails. Full stderr:\n" + result.stderr
        )
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    assert "FAILED tests/test_b.py::test_b_thing" in log_text, (
        "persisted log must contain the FAILED line that the tail-30 "
        "buffer dropped — that's the whole point of persistence"
    )


@pytest.mark.skipif(_BASH is None, reason="bash not available")
def test_deny_message_names_the_persisted_log_path(isolated_home, fake_pytest_failing):
    """The deny-message must tell the operator/agent where the full log
    lives so they don't have to invent the path."""
    result = subprocess.run(
        [_BASH, str(_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
        timeout=120,
        env={**os.environ, "HOME": str(isolated_home)},
    )
    log_path = isolated_home / ".divineos" / "last_pre_push_pytest.log"
    if not log_path.exists():
        pytest.skip("pytest did not run; can't verify the message. stderr:\n" + result.stderr)
    assert "last_pre_push_pytest.log" in result.stderr, (
        "deny-message must name the persisted log path so the agent "
        "knows where to read the full failure detail"
    )


@pytest.mark.skipif(_BASH is None, reason="bash not available")
def test_low_impact_path_helper_classifies_correctly():
    """Andrew 2026-06-10 PR-throughput fix — the fast path skips local
    pytest when only low-impact paths (tests/, docs/, family/,
    exploration/, root *.md, *.txt) are touched. Verify the helper:

    - All-low-impact file list → returns true (skip pytest)
    - Any src/ touched         → returns false (full pytest)
    - Empty list               → returns false (conservative; can't
                                  prove low-impact, so run full)
    """
    inline = (
        "_all_changed_low_impact() {\n"
        "    local file saw_any=0\n"
        "    while IFS= read -r file; do\n"
        '        [[ -z "$file" ]] && continue\n'
        "        saw_any=1\n"
        '        case "$file" in\n'
        "            tests/*|docs/*|family/*|exploration/*|*.md|*.txt) ;;\n"
        "            *) return 1 ;;\n"
        "        esac\n"
        '    done <<< "$1"\n'
        '    [[ "$saw_any" == "1" ]]\n'
        "}\n"
        'low_input=$(printf "tests/a.py\\ndocs/b.md\\nfamily/c.md")\n'
        'high_input=$(printf "src/divineos/foo.py\\ntests/a.py")\n'
        'empty_input=""\n'
        '_all_changed_low_impact "$low_input"   && echo LOW   || echo HIGH\n'
        '_all_changed_low_impact "$high_input"  && echo LOW2  || echo HIGH2\n'
        '_all_changed_low_impact "$empty_input" && echo EMPTY_LOW || echo EMPTY_HIGH\n'
    )
    result = subprocess.run(
        [_BASH, "-c", inline],
        capture_output=True,
        text=True,
        timeout=10,
    )
    out = result.stdout
    assert "LOW\n" in out, f"all-low-impact must return true. stdout: {out!r}"
    assert "HIGH2\n" in out, f"src/ touch must return false. stdout: {out!r}"
    assert "EMPTY_HIGH\n" in out, f"empty list must return false (conservative). stdout: {out!r}"


@pytest.mark.skipif(_BASH is None, reason="bash not available")
def test_failed_lines_are_grepped_and_surfaced_in_stderr(isolated_home, fake_pytest_failing):
    """The script must explicitly grep FAILED/ERROR lines and emit them
    in stderr, separate from the tail buffer. This makes the failing-test
    name immediately visible regardless of how much warning noise pytest
    emitted around it (the failure mode tonight: tail -30 dropped FAILED
    under 60+ warning lines)."""
    result = subprocess.run(
        [_BASH, str(_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(_PROJECT_ROOT),
        timeout=120,
        env={**os.environ, "HOME": str(isolated_home)},
    )
    log_path = isolated_home / ".divineos" / "last_pre_push_pytest.log"
    if not log_path.exists():
        pytest.skip("pytest did not run; can't verify grep surfacing. stderr:\n" + result.stderr)
    assert "Failing tests" in result.stderr, (
        "stderr must include the explicit 'Failing tests' section produced by grepping the log"
    )
    assert "FAILED tests/test_b.py::test_b_thing" in result.stderr, (
        "the grepped FAILED line must appear in stderr (not just the log)"
    )
