"""The push verifier asks the remote about the ref the push WROTE TO.

2026-10-07, claim run, real bare remote. verify-push-landed.sh exists so a push
is never reported as landed before it landed. It kept only the LOCAL side of a
`local:remote` refspec and asked the remote whether that name sat at the same
tip, so `git push origin main:other` printed a green "verified" when main was
already on the remote and `other` never landed: a success report about a
different thing from the one claimed. A flag that takes its own value
(`-o ci.skip`) was also read as the remote.

Real git, real bare remote, the real hook. A missing marker is could-not-look and
fails the assertion; it is never read as a pass.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
HOOK = REPO / ".claude" / "hooks" / "verify-push-landed.sh"


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
    not HOOK.exists() or BASH is None,
    reason="hook or a POSIX bash absent here -- could-not-look, which is not a pass",
)


def _git(cwd: Path, *args: str) -> None:
    done = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    assert done.returncode == 0, (args, done.stderr)


@pytest.fixture
def pushed_main_only(tmp_path: Path):
    """A work repo whose `main` is on the remote and whose `feature` is not."""
    remote = tmp_path / "remote.git"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    work = tmp_path / "work"
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "t@t")
    _git(work, "config", "user.name", "t")
    (work / "a").write_text("a", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "one")
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "-q", "origin", "main")
    _git(work, "checkout", "-q", "-b", "feature")
    (work / "b").write_text("b", encoding="utf-8")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "two")
    home = tmp_path / "home"
    home.mkdir()
    return work, home


def _verdict(work: Path, home: Path, command: str) -> str | None:
    env = dict(os.environ, HOME=str(home), PUSH_VERIFY_SLEEP="0", PUSH_VERIFY_MAX_RETRIES="1")
    subprocess.run(
        [BASH, str(HOOK)],
        input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        cwd=str(work),
        env=env,
        timeout=120,
    )
    marker = home / ".divineos-aether" / "last_push_verified.json"
    return json.loads(marker.read_text(encoding="utf-8"))["status"] if marker.exists() else None


def test_control_a_branch_on_the_remote_is_verified(pushed_main_only) -> None:
    work, home = pushed_main_only
    assert _verdict(work, home, "git push origin main") == "verified"


def test_control_a_branch_not_on_the_remote_is_unverified(pushed_main_only) -> None:
    work, home = pushed_main_only
    assert _verdict(work, home, "git push origin feature") == "unverified"


def test_a_push_to_a_different_remote_name_is_checked_under_that_name(pushed_main_only) -> None:
    work, home = pushed_main_only
    # main is on the remote at the same tip, but `other` never landed.
    assert _verdict(work, home, "git push origin main:other") == "unverified"


def test_the_full_ref_form_of_the_remote_side_is_read_the_same(pushed_main_only) -> None:
    work, home = pushed_main_only
    assert _verdict(work, home, "git push origin main:refs/heads/other") == "unverified"
    assert _verdict(work, home, "git push origin main:refs/heads/main") == "verified"


def test_a_push_option_with_its_own_value_is_not_read_as_the_remote(pushed_main_only) -> None:
    work, home = pushed_main_only
    assert _verdict(work, home, "git push -o ci.skip origin main") == "verified"
