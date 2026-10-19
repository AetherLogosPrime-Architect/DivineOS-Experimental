"""link_worktree_venv.sh repairs a dangling junction, refuses to wipe a real folder, and will not
say "linked" unless Python resolves through the link.

2026-10-12: two work copies were given a .venv junction typed by hand with a doubled drive
(C:\\C:\\...). A dangling junction reads as an empty directory, so the merge's test step failed with
"tests could not be run" and looked like a test problem. The script's last check is the point: a link
nobody has resolved is not yet a link. Each case runs against a throwaway repo and worktree, never
the live ones, and the script is Windows-junction work, so it is skipped elsewhere and where no
working bash exists (a skip that says why is an absence announcing itself, not a pass).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "link_worktree_venv.sh"
BASH = bash_executable()

pytestmark = [
    pytest.mark.skipif(os.name != "nt", reason="the script makes Windows junctions"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this machine"),
]


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
    )


@pytest.fixture
def repo_and_worktree(tmp_path):
    """A throwaway main checkout holding a .venv with a python in it, and one worktree of it."""
    main = tmp_path / "main"
    main.mkdir()
    _git(main, "init", "-q", "-b", "main")
    _git(main, "commit", "-q", "--allow-empty", "-m", "x")
    py = main / ".venv" / "Scripts" / "python.exe"
    py.parent.mkdir(parents=True)
    py.write_text("", encoding="utf-8")
    wt = tmp_path / "wt"
    _git(main, "worktree", "add", "-q", str(wt))
    return main, wt


def _run(wt: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [BASH, SCRIPT.as_posix(), wt.as_posix()], capture_output=True, text=True, timeout=60
    )


def test_it_creates_the_link_and_python_resolves_through_it(repo_and_worktree):
    _, wt = repo_and_worktree
    result = _run(wt)
    assert result.returncode == 0, result.stderr
    assert (wt / ".venv" / "Scripts" / "python.exe").exists()
    assert "Python resolves" in result.stdout


def test_it_repairs_a_dangling_junction(repo_and_worktree, tmp_path):
    # The real failure: a junction that points nowhere reads as an empty directory.
    _, wt = repo_and_worktree
    (tmp_path / "gone").mkdir()
    # The target is spelled from tmp_path in the call itself, so the link can never reach out of
    # the sandbox: pytest's temp cleanup walks a junction, and this repo lost a virtualenv to that.
    subprocess.run(
        ["cmd", "/c", "mklink", "/J", str(wt / ".venv"), str(tmp_path / "gone")],
        check=True,
        capture_output=True,
    )
    (tmp_path / "gone").rmdir()  # the link now dangles
    assert not (wt / ".venv" / "Scripts" / "python.exe").exists()

    result = _run(wt)

    assert result.returncode == 0, result.stderr
    assert (wt / ".venv" / "Scripts" / "python.exe").exists()


def test_it_never_wipes_a_real_folder_with_things_in_it(repo_and_worktree):
    _, wt = repo_and_worktree
    real = wt / ".venv"
    real.mkdir()
    (real / "keep.txt").write_text("mine", encoding="utf-8")

    result = _run(wt)

    assert result.returncode == 4, (result.returncode, result.stderr)
    assert (real / "keep.txt").read_text(encoding="utf-8") == "mine"


def test_it_will_not_link_to_a_main_checkout_with_no_usable_python(repo_and_worktree):
    main, wt = repo_and_worktree
    (main / ".venv" / "Scripts" / "python.exe").unlink()

    result = _run(wt)

    assert result.returncode == 3
    assert not (wt / ".venv").exists()


def test_an_already_good_link_is_left_alone(repo_and_worktree):
    _, wt = repo_and_worktree
    assert _run(wt).returncode == 0
    again = _run(wt)
    assert again.returncode == 0
    assert "already linked" in again.stdout
