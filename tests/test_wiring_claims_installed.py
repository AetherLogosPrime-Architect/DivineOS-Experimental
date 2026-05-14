"""Regression-pin test for the check_wiring_claims commit-msg gate
installation (Aletheia round-3b2ec087c17a Finding 1, wire-decision
for scripts/check_wiring_claims.py).

The bug-shape: check_wiring_claims.py existed and worked, but
setup/setup-hooks.sh never wired it into the .git/hooks/commit-msg
installer — so operators running setup got every commit-msg check
except this one. Same wiring-gap class as Finding 29.

Fix: setup-hooks.sh commit-msg installer now invokes check_wiring_
claims.py after the root-cause-audit gate. Soft warning; never
blocks.

If this test fails, the installer no longer references the script
and the gate has reverted to unwired.
"""

from __future__ import annotations

from pathlib import Path


def test_setup_hooks_sh_references_check_wiring_claims() -> None:
    """LOAD-BEARING: setup/setup-hooks.sh must include a call to
    check_wiring_claims.py inside the commit-msg installer block."""
    repo_root = Path(__file__).resolve().parents[1]
    setup = (repo_root / "setup" / "setup-hooks.sh").read_text(encoding="utf-8", errors="replace")
    assert "check_wiring_claims.py" in setup, (
        "setup-hooks.sh no longer installs the wiring-claims commit-msg "
        "gate. Finding 1 wire-decision for this script has regressed."
    )


def test_check_wiring_claims_script_exists() -> None:
    """The script itself must still exist (not accidentally deleted
    while we cleaned up the other 3 unwired scripts under Finding 1)."""
    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "check_wiring_claims.py"
    assert script.exists(), (
        "scripts/check_wiring_claims.py is missing. The setup-hooks.sh "
        "installer would silently no-op without the script."
    )


def test_check_wiring_claims_self_test_passes() -> None:
    """The script's built-in --self-test should pass. Pins the regex
    set against accidental breakage."""
    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    script = repo_root / "scripts" / "check_wiring_claims.py"
    result = subprocess.run(
        [sys.executable, str(script), "--self-test"],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, (
        f"check_wiring_claims --self-test failed: {result.stdout}\n{result.stderr}"
    )
    assert "OK" in result.stdout
