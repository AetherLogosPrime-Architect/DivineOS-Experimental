"""The pipe checker rewrites a command; no other hook may, and it must say what it costs.

2026-10-13: the pipe checker stopped warning and refusing and now adds ``set -o pipefail;``
itself, through the harness's ``updatedInput``. Two hooks that both rewrite the same Bash
input would fight over the whole input object, and the docs say nothing about which wins
(Aria, cold read of #644). So a second rewriter fails here until someone decides how two
should combine.

It also pins what the rewrite says about the one surprise it can cause: a reader that
stops early (``head``) makes the writer exit 141, and the note must say that is the pipe.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests._bash_resolver import bash_executable

REPO = Path(__file__).resolve().parents[1]
HOOKS = REPO / ".claude" / "hooks"
THE_REWRITER = "pipeline-exit-ambiguity.sh"
BASH = bash_executable()


def _hooks_that_name_updated_input() -> set[str]:
    return {
        p.name
        for p in HOOKS.iterdir()
        if p.is_file()
        and p.suffix in {".sh", ".py"}
        and "updatedInput" in p.read_text(encoding="utf-8", errors="replace")
    }


def test_only_the_pipe_checker_rewrites_input():
    assert _hooks_that_name_updated_input() == {THE_REWRITER}


def test_control_the_scan_can_find_a_rewriter():
    # Without this, the test above would pass if the scan could only ever say "none".
    assert THE_REWRITER in _hooks_that_name_updated_input()


def _note_for(command: str, home: Path) -> str:
    if BASH is None:
        pytest.skip("no working bash is available, so the shell hook cannot be run")
    env = dict(
        os.environ,
        HOME=str(home),
        USERPROFILE=str(home),
        HOMEDRIVE=home.drive,
        HOMEPATH=str(home)[len(home.drive) :],
    )
    done = subprocess.run(
        [BASH, str(HOOKS / THE_REWRITER)],
        input=json.dumps({"tool_input": {"command": command}}),
        capture_output=True,
        text=True,
        cwd=REPO,
        env=env,
        timeout=120,
        check=False,
    )
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip(), "the hook said nothing for a pipeline it should rewrite"
    return json.loads(done.stdout)["hookSpecificOutput"]["additionalContext"]


def test_a_head_pipe_warns_about_exit_141_with_the_rewrite(tmp_path):
    assert "141" in _note_for("git log | head -3", tmp_path)


def test_a_tail_pipe_does_not_mention_141(tmp_path):
    # tail reads everything, so the surprise cannot happen; a warning about it would be noise.
    assert "141" not in _note_for("git log | tail -3", tmp_path)
