"""Removing a work copy must never delete what a junction inside it points at.

2026-10-20, Aria: cleaning the C root, `git worktree remove --force` on work copies whose `.venv` was
a junction to the main checkout's real `.venv` emptied that real venv. Nothing in the removal said it
would; git walks the link. The repo's own link script says only `rmdir` removes a junction without
touching its target, and this house had already lost a virtualenv to a test cleanup once.

`scripts/remove_work_copy.sh` unlinks first, refuses a work copy that holds work nowhere else, and only
then lets git remove the folder. The first test below is the control: it reproduces the incident with
raw git, so the second test cannot pass because the hazard no longer exists on this machine.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "remove_work_copy.sh"


def _bash() -> str | None:
    for candidate in (
        r"C:\Program Files\Git\bin\bash.exe",
        "/usr/bin/bash",
        shutil.which("bash") or "",
    ):
        if candidate and Path(candidate).exists() and "System32" not in candidate:
            return candidate
    return None


BASH = _bash()
pytestmark = pytest.mark.skipif(
    os.name != "nt" or BASH is None,
    reason="needs Windows junctions and a POSIX bash -- could-not-look, which is not a pass",
)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def _repo_with_copy(tmp_path: Path, name: str):
    """A throwaway repo, a work copy of it, and an outside folder holding a canary the copy links to."""
    main = tmp_path / f"main_{name}"
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _git(main, "config", "user.email", "t@example.invalid")
    _git(main, "config", "user.name", "t")
    (main / "a.txt").write_text("a\n", encoding="utf-8")
    _git(main, "add", "a.txt")
    _git(main, "commit", "-q", "-m", "first")
    _git(main, "branch", f"b_{name}")
    wt = tmp_path / f"copy_{name}"
    assert _git(main, "worktree", "add", "-q", str(wt), f"b_{name}").returncode == 0
    (tmp_path / f"outside_{name}").mkdir()
    canary = tmp_path / f"outside_{name}" / "canary.txt"
    canary.write_text("must survive\n", encoding="utf-8")
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(wt / ".venv"), str(tmp_path / f"outside_{name}")],
        check=True,
        capture_output=True,
    )
    return main, wt, canary


def _remove(main: Path, wt: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, str(SCRIPT), str(wt), *extra], cwd=main, capture_output=True, text=True, timeout=120
    )


def test_control_raw_git_removal_follows_the_link_and_deletes_the_target(tmp_path):
    main, wt, canary = _repo_with_copy(tmp_path, "control")
    assert canary.exists()
    _git(main, "worktree", "remove", "--force", str(wt))
    assert not canary.exists(), (
        "git did not follow the link on this machine; the hazard is not reproduced"
    )


def test_the_script_removes_the_copy_and_the_link_target_survives(tmp_path):
    main, wt, canary = _repo_with_copy(tmp_path, "safe")
    done = _remove(main, wt)
    assert done.returncode == 0, done.stdout + done.stderr
    assert not wt.exists()
    assert canary.exists() and canary.read_text(encoding="utf-8") == "must survive\n"


def test_a_copy_holding_uncommitted_work_is_refused_and_left_alone(tmp_path):
    main, wt, canary = _repo_with_copy(tmp_path, "dirty")
    (wt / "unsaved.md").write_text("only here\n", encoding="utf-8")
    done = _remove(main, wt)
    assert done.returncode != 0
    assert "unsaved.md" in done.stdout + done.stderr or "uncommitted" in (done.stdout + done.stderr)
    assert (wt / "unsaved.md").exists() and canary.exists()


def test_snapshot_keeps_the_unsaved_work_in_a_rescue_ref_then_removes(tmp_path):
    main, wt, canary = _repo_with_copy(tmp_path, "snap")
    (wt / "unsaved.md").write_text("only here\n", encoding="utf-8")
    done = _remove(main, wt, "--snapshot")
    assert done.returncode == 0, done.stdout + done.stderr
    assert not wt.exists() and canary.exists()
    shown = _git(main, "show", "refs/rescue/copy_snap:unsaved.md")
    assert shown.returncode == 0 and shown.stdout == "only here\n"


def test_an_inherited_windows_style_pythonpath_does_not_hide_the_modules_own_source(tmp_path):
    """The push gate sets PYTHONPATH to a Windows-style path. The wrapper once built a mixed list that the
    shell's conversion mangled, so Python imported the OLD package from the main checkout and the module
    was 'not found' (found 2026-10-20 when the gate failed these tests and a plain run passed them)."""
    main, wt, canary = _repo_with_copy(tmp_path, "pypath")
    env = {**os.environ, "PYTHONPATH": str(tmp_path / "somewhere_else")}
    done = subprocess.run(
        [BASH, str(SCRIPT), str(wt)], cwd=main, capture_output=True, text=True, timeout=120, env=env
    )
    assert done.returncode == 0, done.stdout + done.stderr
    assert not wt.exists() and canary.exists()


def test_the_main_checkout_is_never_removed(tmp_path):
    main, wt, canary = _repo_with_copy(tmp_path, "main")
    done = _remove(wt, main)
    assert done.returncode == 3, done.stdout + done.stderr
    assert "main checkout" in done.stderr
    assert main.exists() and (main / "a.txt").exists()
