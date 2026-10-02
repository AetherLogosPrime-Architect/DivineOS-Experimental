"""The SessionStart hook ends every earlier goal, driven through the live hook.

Aria's station-3 objection to goal freshness by last use: without a boundary a
goal outlives the work it named. The hook is the boundary, and it has to fire
on compaction, which session-init-once never re-runs (council-7666a3816f92).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "goal-boundary-at-session-start.sh"
BASH = bash_executable()

needs_hook = pytest.mark.skipif(
    not HOOK.exists() or BASH is None,
    reason="hook or a POSIX bash absent here -- could-not-look, which is not a pass",
)


def _run(home: Path) -> subprocess.CompletedProcess:
    # DIVINEOS_HOME, not HOME: divineos_home() follows the checkout marker, so
    # setting HOME alone writes into the live seat (Aria, 2026-10-01).
    env = {**os.environ, "DIVINEOS_HOME": str(home), "PYTHONPATH": str(REPO / "src")}
    payload = json.dumps({"hook_event_name": "SessionStart", "source": "compact"})
    return subprocess.run(
        [BASH, str(HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        env=env,
        cwd=REPO,
        timeout=60,
    )


@needs_hook
def test_the_hook_writes_a_boundary_and_says_so(tmp_path):
    before = time.time()
    result = _run(tmp_path)
    assert result.returncode == 0
    assert "new stretch" in result.stdout
    # The hud dir's layout under the home differs between the test runner and
    # a live shell, so find the marker rather than assume its depth.
    markers = list(tmp_path.rglob("goal_boundary.json"))
    assert len(markers) == 1, markers
    assert json.loads(markers[0].read_text(encoding="utf-8"))["boundary_at"] >= before - 1


def _py(home: Path, code: str) -> str:
    env = {**os.environ, "DIVINEOS_HOME": str(home), "PYTHONPATH": str(REPO / "src")}
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, env=env, cwd=REPO, timeout=60
    )
    assert out.returncode == 0, out.stderr
    return out.stdout.strip()


@needs_hook
def test_after_the_hook_a_goal_in_steady_use_no_longer_counts(tmp_path):
    # Ask the code where its hud dir is: a goal written anywhere else would
    # read as "no goal" and pass this test without the hook doing anything.
    hud = Path(
        _py(tmp_path, "from divineos.core._hud_io import _ensure_hud_dir; print(_ensure_hud_dir())")
    )
    now = time.time()
    (hud / "active_goals.json").write_text(
        json.dumps(
            [{"text": "x", "status": "active", "added_at": now - 600, "last_used_at": now - 30}]
        ),
        encoding="utf-8",
    )
    ask = "from divineos.core.hud_state import has_session_fresh_goal as f; print(f())"
    assert _py(tmp_path, ask) == "True"  # the control is live before the hook
    assert _run(tmp_path).returncode == 0
    assert _py(tmp_path, ask) == "False"
