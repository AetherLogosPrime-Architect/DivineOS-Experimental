"""A refspec names two things and the wrapper has to ask about the right one.

The left half is what is being sent and is resolved locally. The right half is
where it lands and is what the remote is asked for. With no colon they are the
same string, which is the ordinary case and the reason one variable held both
for months without anyone noticing. Pushing `HEAD:some-branch` made the local
lookup ask for a path inside a commit and the remote lookup ask for a ref with
a colon in its name. Both found nothing, and a tool whose whole job is a
truthful verdict called a landed push a failure.

That defect was found by hand and fixed by hand, and a hand check cannot be
re-run by anyone but the session that ran it. This is the form of that evidence
which survives the session.

WHY THIS FILE EXISTS BESIDE THE SHELL TESTS THAT ALREADY COVER THE WRAPPER.
`tests/test_divineos_push_wrapper.sh` exercises the same script against real
repositories and is the better harness, which is why the fixture here is
borrowed from it rather than replaced. It is a shell script, so the suite never
collects it and it runs only when someone remembers. The refspec case is the
one that was wrong in production, so it belongs where the collector can see it.

THE CONTROL RUNS IN THE SUITE RATHER THAN IN MY HEAD. `test_the_pre_split_
wrapper_fails_this_same_case` rebuilds the wrapper as it was before the halves
were separated and asserts it does NOT reach a verified verdict. Without it, a
test exercising only the current code proves the parser agrees with itself. If
the rebuild cannot be performed the test FAILS rather than skips — a control
that cannot be built is not a control, and a skip would read as a pass.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = REPO_ROOT / "scripts" / "divineos_push.sh"

DEST_REF = "landing-branch"


def _working_bash() -> str | None:
    """A bash proven able to run a script, not merely resolved by name.

    Asking for bash by name on this box can return the WSL relay, which exists,
    runs, and cannot execute a Windows-path script.
    """
    candidates = []
    git = shutil.which("git")
    if git:
        candidates.append(str(Path(git).with_name("bash.exe")))
        candidates.append(str(Path(git).parents[1] / "bin" / "bash.exe"))
    found = shutil.which("bash")
    if found:
        candidates.append(found)
    for candidate in candidates:
        if not os.path.exists(candidate):
            continue
        try:
            probe = subprocess.run(
                [candidate, "-c", "echo ok"], capture_output=True, text=True, timeout=20
            )
        except (OSError, subprocess.SubprocessError):
            continue
        if probe.returncode == 0 and probe.stdout.strip() == "ok":
            return candidate
    return None


BASH = _working_bash()

pytestmark = [
    pytest.mark.skipif(not WRAPPER.exists(), reason="wrapper absent from this checkout"),
    pytest.mark.skipif(BASH is None, reason="no working bash on this platform"),
    pytest.mark.skipif(shutil.which("git") is None, reason="no git on this platform"),
]


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, timeout=120)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    """A local repo with a bare remote, so the real push path runs."""
    remote = tmp_path / "remote.git"
    local = tmp_path / "local"
    subprocess.run(
        ["git", "init", "--bare", "--initial-branch=main", str(remote)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    subprocess.run(
        ["git", "init", "--initial-branch=main", str(local)],
        check=True,
        capture_output=True,
        timeout=120,
    )
    _git("config", "user.email", "test@test", cwd=local)
    _git("config", "user.name", "test", cwd=local)
    (local / "README.md").write_text("hello\n", encoding="utf-8")
    _git("add", "README.md", cwd=local)
    _git("commit", "-m", "initial", cwd=local)
    _git("remote", "add", "origin", str(remote), cwd=local)
    return local


def _run(repo: Path, args: list[str], script_text: str | None = None):
    assert BASH is not None
    script = WRAPPER
    if script_text is not None:
        script = repo.parent / "pre_split_wrapper.sh"
        script.write_text(script_text, encoding="utf-8", newline="\n")
    env = dict(os.environ)
    env["DIVINEOS_HOME"] = str(repo.parent / "home")
    return subprocess.run(
        [BASH, str(script), *args],
        capture_output=True,
        text=True,
        env=env,
        cwd=str(repo),
        timeout=300,
    )


def _pre_split_wrapper_text() -> str:
    """The wrapper as it was before the two halves were separated.

    Deletes the case block that performs the split, leaving the single
    assignment that made the destination stand in for the source as well.
    """
    text = WRAPPER.read_text(encoding="utf-8")
    pattern = re.compile(r'case "\$TARGET_BRANCH" in\n\s*\*:\*\).*?\n\s*;;\nesac\n', re.DOTALL)
    reverted, count = pattern.subn("", text)
    assert count == 1, (
        "could not rebuild the pre-fix wrapper: the split block did not match. "
        "The control cannot be built, so these tests prove nothing about the "
        "defect, and this failure is the honest report of that."
    )
    return reverted


def test_a_colon_refspec_resolves_the_left_half_and_asks_for_the_right(repo: Path):
    result = _run(repo, ["origin", f"HEAD:{DEST_REF}"])
    assert "PUSHED+VERIFIED" in result.stdout, result.stdout + result.stderr
    assert result.returncode == 0


def test_the_pre_split_wrapper_fails_this_same_case(repo: Path):
    """The control. Without this, the case above proves only self-agreement."""
    result = _run(repo, ["origin", f"HEAD:{DEST_REF}"], _pre_split_wrapper_text())
    # The production symptom exactly: the branch lands on the remote and the
    # wrapper calls the push a silent failure. Asserting the verdict rather
    # than merely the absence of a good one, because an absence would also be
    # satisfied by the script erroring out before it ever reached a decision.
    assert "new branch" in result.stdout + result.stderr, (
        "the push did not actually land, so whatever this measured, it was not "
        "a correct push being reported as a failure"
    )
    assert "PUSH_FAILED_silently" in result.stdout, result.stdout + result.stderr
    assert result.returncode == 22


def test_a_bare_branch_name_is_unchanged_by_the_split(repo: Path):
    """With no colon both halves are the same string, the ordinary case."""
    result = _run(repo, ["origin", "main"])
    assert "PUSHED+VERIFIED" in result.stdout, result.stdout + result.stderr
    assert result.returncode == 0


def test_flags_are_not_mistaken_for_the_refspec(repo: Path):
    result = _run(repo, ["--force-with-lease", "origin", f"HEAD:{DEST_REF}"])
    assert "PUSHED+VERIFIED" in result.stdout, result.stdout + result.stderr
    assert result.returncode == 0
