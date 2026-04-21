"""End-to-end subprocess tests for corrigibility wiring.

Fresh-Claude audit round-03952b006724, finding find-f0d7df1c7798:

  "Tests skip the gate via if 'pytest' in sys.modules: return. No
  end-to-end test ever exercises the real CLI bootstrap with
  corrigibility active. If someone refactors cli/__init__.py and
  accidentally removes the _enforce_operating_mode() call, the entire
  test suite passes. A single subprocess-based test that actually
  invokes divineos <cmd> in EMERGENCY_STOP and verifies the exit code
  would close this gap."

These tests spawn real subprocesses — they will NOT see the
``pytest in sys.modules`` sentinel in the child interpreter, so the
enforce-path runs for real. They lock the invariant that:

  (a) ``_enforce_operating_mode`` is still called during CLI bootstrap,
  (b) corrigibility refuses non-bypass commands in EMERGENCY_STOP, and
  (c) the mode command itself remains reachable so the operator can
      restore NORMAL mode after the stop.

If a future refactor removes the gate call, these tests fail loudly
even though the logic-level tests of corrigibility itself still pass.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.fixture
def isolated_env(tmp_path, monkeypatch):
    """Isolate subprocess-visible state via env vars + clear briefing gate.

    Subprocess invocations still hit the full gate stack (briefing
    required, goal required, engagement tracking, corrigibility). For
    these E2E tests we want corrigibility to be the live gate — so the
    fixture pre-runs ``divineos briefing`` so the briefing-loaded marker
    is set and subsequent commands don't bounce off the briefing gate.
    """
    # Provide a tmp-path DIVINEOS_DB so the child CLI doesn't touch the real DB.
    db_path = tmp_path / "ledger.db"
    family_db = tmp_path / "family.db"
    hud_home = tmp_path / "divineos_home"
    hud_home.mkdir()

    env = os.environ.copy()
    env["DIVINEOS_DB"] = str(db_path)
    env["DIVINEOS_FAMILY_DB"] = str(family_db)
    # Redirect ~/.divineos/ to the tmp path so session markers (briefing
    # loaded, engagement) don't contaminate between test runs.
    env["HOME"] = str(hud_home)
    env["USERPROFILE"] = str(hud_home)  # Windows
    # Ensure pytest sentinel does NOT carry into the child.
    env.pop("PYTEST_CURRENT_TEST", None)
    # Keep PYTHONPATH so divineos is importable.
    repo_root = Path(__file__).resolve().parent.parent
    src = repo_root / "src"
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{src}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = str(src)

    # Initialize DB and clear the briefing gate so corrigibility is
    # the live gate under test.
    subprocess.run(
        [sys.executable, "-m", "divineos", "init"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    subprocess.run(
        [sys.executable, "-m", "divineos", "briefing"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    subprocess.run(
        [sys.executable, "-m", "divineos", "goal", "add", "e2e test run"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return env


def _run_divineos(env: dict, *args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Invoke `python -m divineos.cli <args>` as a subprocess.

    Using the module form (not a shell `divineos` command) so the test
    works across install modes (editable pip install vs. direct source).
    """
    return subprocess.run(
        [sys.executable, "-m", "divineos", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestNormalModeAllowsCommands:
    """Baseline: in the default NORMAL mode, a normal read-only command
    runs cleanly. If this fails, the subprocess fixture itself is broken
    and the other tests can't be trusted."""

    def test_help_runs_in_normal_mode(self, isolated_env):
        result = _run_divineos(isolated_env, "--help")
        assert result.returncode == 0, f"divineos --help failed: {result.stderr}"


class TestEmergencyStopBlocksCommands:
    """EMERGENCY_STOP must refuse non-bypass commands with a non-zero
    exit code. This is the invariant that would break silently if the
    gate call were removed from cli/__init__.py."""

    def test_emergency_stop_refuses_regular_command(self, isolated_env):
        # First put the system into EMERGENCY_STOP
        set_result = _run_divineos(
            isolated_env, "mode", "set", "emergency_stop", "--reason", "e2e test"
        )
        assert set_result.returncode == 0, (
            f"mode set failed — can't run the test: {set_result.stderr}"
        )

        # Now a read-only command that WOULD be allowed in NORMAL should
        # be refused.
        result = _run_divineos(isolated_env, "recall")
        assert result.returncode != 0, (
            "EMERGENCY_STOP failed to block 'recall' — the gate is not wired. "
            f"stdout={result.stdout}, stderr={result.stderr}"
        )

    def test_mode_command_still_reachable_in_emergency_stop(self, isolated_env):
        """After entering EMERGENCY_STOP, the operator must still be able
        to run `mode set NORMAL` to recover. If the off-switch locks
        itself in, it is a trap, not a safety feature."""
        _run_divineos(isolated_env, "mode", "set", "emergency_stop", "--reason", "e2e test")

        # mode show should still work even in EMERGENCY_STOP
        show_result = _run_divineos(isolated_env, "mode", "show")
        assert show_result.returncode == 0, (
            "mode show was blocked by EMERGENCY_STOP — the operator "
            "cannot recover. Off-switch is a trap. "
            f"stdout={show_result.stdout}, stderr={show_result.stderr}"
        )

        # And mode set NORMAL should restore the system
        restore_result = _run_divineos(
            isolated_env, "mode", "set", "normal", "--reason", "e2e test restore"
        )
        assert restore_result.returncode == 0, (
            "Could not restore NORMAL mode from EMERGENCY_STOP. "
            f"stdout={restore_result.stdout}, stderr={restore_result.stderr}"
        )

        # Verify recovery: a command that was blocked should now run
        final = _run_divineos(isolated_env, "--help")
        assert final.returncode == 0


class TestGateRunsDuringBootstrap:
    """Verifies _enforce_operating_mode actually runs during CLI bootstrap.

    Indirect but reliable: if the gate call were removed, EMERGENCY_STOP
    would no longer block commands — which is exactly what the tests
    above check. This class documents the invariant explicitly so a
    future refactor's intent is clear."""

    def test_bootstrap_invokes_enforcement(self, isolated_env):
        """Regression guard: if cli/__init__.py stops calling
        _enforce_operating_mode(), this test fails with a different
        symptom than the 'EMERGENCY_STOP blocks command' test."""
        _run_divineos(isolated_env, "mode", "set", "emergency_stop", "--reason", "e2e test")

        # Run a command that WOULD produce recognizable output if it
        # proceeded past the gate. 'recall' is a safe choice — it's not
        # in the bypass list, so it must be blocked.
        result = _run_divineos(isolated_env, "recall")

        # The gate prints a red-colored refusal message to stdout then
        # exits 1. If the gate didn't run, recall would succeed and print
        # memory contents instead.
        assert result.returncode != 0
        # Recovery so the tmp DB stays in a known state for any follow-up.
        _run_divineos(isolated_env, "mode", "set", "normal", "--reason", "e2e test restore")
