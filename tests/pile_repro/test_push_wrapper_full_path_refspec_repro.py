"""Reproduction: the push helper calls a landed push a failure when the branch is named by its full path.

Rows: psf-cb3017c7, psf-8caccd2a, psf-e54da291
Note (psf-cb3017c7): "scripts/divineos_push.sh misreports a refspec push (origin HEAD:refs/heads/<b>) as PUSH_FAILED_silently: TARGET_BRANCH takes the whole refspec and rev-parse/ls-remote look up a ref that does not exist"
Note (psf-8caccd2a): "the wrapper should accept a full branch path without doubling it."

The short form `HEAD:branch` is handled and tested in
tests/test_the_push_wrapper_reads_both_halves_of_a_refspec.py. The long form
`HEAD:refs/heads/branch` is not: the wrapper keeps `refs/heads/branch` as the
branch name and then asks the remote for `refs/heads/refs/heads/branch`.

Marked ``xfail(strict=True)``: it passes quietly as an expected failure today and
turns into a real failure the day the helper is repaired, which forces the marker
out. Nothing here changes the helper.

What would make the reproduction test wrong: it runs the real wrapper against a
local bare repository, so it proves nothing about a network remote or a
different git version. It asserts the wrapper's own words (``PUSHED+VERIFIED``,
exit 0). A repair that reports success with a different wording would fail it
for a reason that is not the problem, and the wording should then be
updated, not the repair bent to fit.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

REPO_ROOT = Path(__file__).resolve().parents[2]
WRAPPER = REPO_ROOT / "scripts" / "divineos_push.sh"
BASH = bash_executable()
DEST = "landing-branch"

pytestmark = [
    pytest.mark.skipif(not WRAPPER.exists(), reason="wrapper absent from this checkout"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this platform"),
    pytest.mark.skipif(shutil.which("git") is None, reason="no git on this platform"),
]


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, timeout=120)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A local repository with a bare remote, so the real push path runs."""
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    for path, bare in ((remote, True), (local, False)):
        cmd = ["git", "init", "--initial-branch=main"] + (["--bare"] if bare else []) + [str(path)]
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    _git("config", "user.email", "test@test", cwd=local)
    _git("config", "user.name", "test", cwd=local)
    (local / "README.md").write_text("hello\n", encoding="utf-8")
    _git("add", "README.md", cwd=local)
    _git("commit", "-m", "initial", cwd=local)
    _git("remote", "add", "origin", str(remote), cwd=local)
    return local


def _wrapper(repo: Path, refspec: str) -> subprocess.CompletedProcess[str]:
    assert BASH is not None
    env = dict(os.environ, DIVINEOS_HOME=str(repo.parent / "home"))
    return subprocess.run(
        [BASH, str(WRAPPER), "origin", refspec],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo),
        timeout=300,
        check=False,
    )


def _remote_has(repo: Path, ref: str) -> bool:
    out = subprocess.run(
        ["git", "ls-remote", "origin", ref],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
        check=True,
    ).stdout
    return bool(out.strip())


@pytest.mark.xfail(
    strict=True,
    reason="reproduces: a push named by its full path lands, and the helper reports it as PUSH_FAILED_silently (exit 22)",
)
def test_a_full_path_refspec_that_landed_is_reported_as_landed(repo: Path):
    result = _wrapper(repo, f"HEAD:refs/heads/{DEST}")
    assert _remote_has(repo, f"refs/heads/{DEST}"), (
        "the push did not land, so whatever this measured it was not a good push "
        "being called a failure: " + result.stdout + result.stderr
    )
    assert "PUSHED+VERIFIED" in result.stdout, (
        "a push that landed was not reported as landed:\n" + result.stdout + result.stderr
    )
    assert result.returncode == 0, f"exit {result.returncode}"


def test_control_the_short_form_is_reported_as_landed(repo: Path):
    """Control: the same wrapper and fixture, the form that is handled today."""
    result = _wrapper(repo, f"HEAD:{DEST}")
    assert _remote_has(repo, f"refs/heads/{DEST}"), result.stdout + result.stderr
    assert "PUSHED+VERIFIED" in result.stdout, result.stdout + result.stderr
    assert result.returncode == 0


def test_control_the_full_path_push_really_lands_on_the_remote(repo: Path):
    """Control: whatever the wrapper says, the long-form push itself lands.

    This is what makes the reproduction a false failure and not a failed push.
    It asserts the remote's state only, and deliberately says nothing about the
    wrapper's verdict, so it passes both before and after a repair.
    """
    _wrapper(repo, f"HEAD:refs/heads/{DEST}")
    assert _remote_has(repo, f"refs/heads/{DEST}")
