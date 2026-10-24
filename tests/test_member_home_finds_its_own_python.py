"""member_home.sh finds the interpreter itself, so a caller that forgot to source _lib.sh cannot get the stale twin.

Found live (2026-10-24): the push gate sourced member_home.sh without _lib.sh, so find_divineos_python did not exist,
the lookup fell to the bare python3, and on a box whose python3 is a stub that cannot import divineos the answer was the
hand-built "$HOME/.divineos-aether" with exit 0, while the watcher, asking Python, read "$HOME/.divineos". The gate wrote
its log in one place and the report read another, and said "the tests did not run" after a seventeen-minute run.

The control matters as much as the case: with the stub removed, the answer must be the same, so the test cannot pass
by always returning the same string.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
BASH = shutil.which("bash")
pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash")


def _ask(tmp_path: Path, member: str, *, stub: bool) -> str:
    """Run the member_home function the way the gate does: source ONLY member_home.sh, never _lib.sh."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    binroot = tmp_path / ("bin_stub" if stub else "bin_real")
    binroot.mkdir(exist_ok=True)
    if stub:
        # a python3 that cannot import anything of ours, as the Windows Store stub cannot
        (binroot / "python3").write_text("#!/bin/bash\nexit 9\n", encoding="utf-8", newline="\n")
        (binroot / "python3").chmod(0o755)
    env = dict(os.environ)
    env["HOME"] = str(home)
    env["USERPROFILE"] = str(home)
    env["PYTHONPATH"] = str(REPO / "src")
    env["PATH"] = (
        str(binroot)
        + os.pathsep
        + str(Path(sys.executable).parent)
        + os.pathsep
        + env.get("PATH", "")
    )
    env.pop("DIVINEOS_MEMBER", None)
    script = f'. "{(REPO / ".claude/hooks/lib/member_home.sh").as_posix()}"; member_home {member}'
    done = subprocess.run(
        [BASH, "-c", script], cwd=REPO, env=env, capture_output=True, text=True, timeout=120
    )
    return done.stdout.strip().replace("\\", "/")


def test_the_answer_is_the_residents_home_not_the_hand_built_twin_when_python3_is_a_stub(tmp_path):
    answer = _ask(tmp_path, "aria", stub=True)
    assert answer.endswith(".divineos-aria"), answer  # aria's real home carries her name
    asked_aether = _ask(tmp_path, "aether", stub=True)
    assert not asked_aether.endswith(".divineos-aether"), (
        f"fell back to the stale twin: {asked_aether}"
    )
    assert asked_aether.endswith(".divineos"), asked_aether


def test_control_without_the_stub_the_answer_is_the_same(tmp_path):
    assert _ask(tmp_path, "aether", stub=False) == _ask(tmp_path, "aether", stub=True)
    assert _ask(tmp_path, "aria", stub=False) == _ask(tmp_path, "aria", stub=True)
