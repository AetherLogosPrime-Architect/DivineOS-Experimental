"""A tag push is a snapshot, and the branch check refused it for being one.

Aria 2026-09-24: her reader fix lived only on her machine. She tried to push an
archive tag of it, and check-branch-on-push refused the tag as "twelve behind
main" -- a branch question asked of something that never merges. The fix stayed
on one disk.

The half that matters more is the other direction: a push that LOOKS tag-only
but sends a branch must still be checked. Most of this file is those cases.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from divineos.core.push_detection import pushes_only_tags

_HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "check-branch-on-push.sh"


@pytest.mark.parametrize(
    "command",
    [
        "git push origin refs/tags/archive/fix/x",
        "git push -q origin refs/tags/archive/a refs/tags/archive/b",
        "git push origin --tags",
        "git push --tags",
        "git push origin tag v1.0",
        "git push origin :refs/tags/old",
        "git push origin --delete refs/tags/old",
        "git push -o ci.skip origin refs/tags/x",
        'cd "C:/w507" && git push origin refs/tags/archive/salvage',
        "git push origin +refs/tags/x",
    ],
)
def test_tag_only_pushes_are_recognised(command: str) -> None:
    assert pushes_only_tags(command)


@pytest.mark.parametrize(
    "command",
    [
        # a branch riding along with a tag
        "git push origin refs/tags/x main",
        "git push origin main --tags",
        # a tag SOURCE landing on a branch DESTINATION -- the smuggle
        "git push origin refs/tags/x:refs/heads/main",
        # options that send branches whatever else is named
        "git push --all origin",
        "git push --mirror origin",
        "git push --tags --all origin",
        # a bare name git may resolve to a branch
        "git push origin archive/fix/x",
        # the current branch, implicitly
        "git push",
        "git push origin",
        "git push -u origin HEAD",
        # a second push in the chain sends a branch
        "git push origin refs/tags/x && git push origin main",
        # could not parse: the check runs
        "git push origin 'refs/tags/x",
        # not a push at all
        "git status",
        "",
    ],
)
def test_anything_that_could_send_a_branch_is_not(command: str) -> None:
    assert not pushes_only_tags(command)


def _bash() -> str:
    """A bash proven to run a script -- a bare "bash" on Windows can resolve to
    the WSL stub, which cannot run a Windows-path hook (same guard as
    test_a_door_still_refuses_without_its_library)."""
    found = shutil.which("bash")
    assert found, "no bash on PATH; this suite cannot exercise shell hooks"
    probe = subprocess.run([found, "-c", "exit 7"], capture_output=True)
    assert probe.returncode == 7, f"{found} cannot run a trivial script"
    return found


def _run_hook(command: str, home: Path | None = None) -> subprocess.CompletedProcess[str]:
    payload = json.dumps({"tool_name": "Bash", "tool_input": {"command": command}})
    env = dict(os.environ)
    env["PYTHONPATH"] = str(_HOOK.parents[2] / "src") + os.pathsep + env.get("PYTHONPATH", "")
    if home is not None:
        env["DIVINEOS_HOME"] = str(home)
    return subprocess.run(
        [_bash(), str(_HOOK)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
        cwd=str(_HOOK.parents[2]),
    )


def test_the_hook_lets_a_tag_push_through_without_running_the_branch_check(tmp_path: Path) -> None:
    """A healthy branch passes the check either way, so a bare pass proves
    nothing. A reasonless kill-switch marker in a throwaway home refuses EVERY
    push that reaches the check -- so the branch push must be refused (the
    control) and the tag push must not, because it never gets there."""
    (tmp_path / "check-branch.disabled").write_text("", encoding="utf-8")

    branch = _run_hook("git push origin archive/some/branch", home=tmp_path)
    assert branch.returncode == 2, branch.stderr
    assert "NO REASON" in branch.stderr

    tag = _run_hook("git push origin refs/tags/archive/some/branch", home=tmp_path)
    assert tag.returncode == 0, tag.stderr
    assert (tmp_path / "check-branch.disabled").exists(), "a tag push must not consume the switch"
