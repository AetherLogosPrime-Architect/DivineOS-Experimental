"""When the state block is unchanged the second showing must say so, and the two
pointers a reader needs (the whole-text path and the full corrections list) must
still stand, and a block with no dash lines must not collapse to nothing.

The first quiet version kept only the dash lines, which dropped the "unchanged
since last shown" pointer the dedup returns and both pointer lines.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
HOOK = REPO_ROOT / ".claude" / "hooks" / "state-gravity-surface.sh"
BASH = shutil.which("bash")

pytestmark = [
    pytest.mark.skipif(not HOOK.exists(), reason="hook absent from this checkout"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this platform"),
]

PAYLOAD = json.dumps(
    {
        "tool_name": "Edit",
        "tool_input": {"file_path": (REPO_ROOT / "src" / "divineos" / "core" / "x.py").as_posix()},
    }
)


@pytest.fixture(autouse=True)
def _one_block_to_show():
    from divineos.core.bypass_telemetry import record_bypass

    record_bypass("test-gate", "DIVINEOS_TEST_STATE_BLOCK", reason="seed for the pointer test")


def _run(dedup_dir: str, glance_dir: str) -> str:
    env = dict(os.environ)
    env["DIVINEOS_CONTEXT_DEDUP_DIR"] = dedup_dir
    # His newest correction rides for three showings, counted in this dir; a private one keeps the
    # test from depending on what he filed today.
    env["DIVINEOS_STATE_GLANCE_DIR"] = glance_dir
    done = subprocess.run(
        [BASH, str(HOOK)],
        input=PAYLOAD,
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=180,
        env=env,
    )
    out = done.stdout.strip()
    return json.loads(out)["hookSpecificOutput"]["additionalContext"] if out else ""


def _warm_up(glance_dir: str) -> None:
    # Four runs: the newest-correction line needs three showings to be spent, and each hook run counts one.
    with tempfile.TemporaryDirectory(prefix="dedup-warm-") as w:
        for _ in range(4):
            _run(w, glance_dir)


def test_the_quiet_showing_says_unchanged_and_keeps_both_pointers():
    with tempfile.TemporaryDirectory(prefix="glance-") as g:
        _warm_up(g)
        _check(g)


def _check(g: str) -> None:
    with tempfile.TemporaryDirectory(prefix="dedup-") as d:
        first = _run(d, g)
        if not first:
            pytest.skip("no state blocks to show on this checkout")
        second = _run(d, g)
        assert "unchanged" in second, "the quiet showing does not say it is unchanged"
        assert "all of them: divineos andrew-correction list" in second, (
            "the pointer to the full corrections list was dropped"
        )
        assert "Whole text" in second, "the pointer to the whole text was dropped"
