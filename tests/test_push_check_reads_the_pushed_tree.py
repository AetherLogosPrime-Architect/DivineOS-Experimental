"""The push check measures the tree the push runs in, not the session's.

2026-09-30: a branch 0 behind main was refused three times as "20 behind",
because the check only honoured a 'cd' at the very start of the command, and
the pipeline gate requires 'set -o pipefail;' before every mutating pipe. Two
correct gates, composed, made every worktree push measure the wrong tree, and
the only exit left was a bypass. These run the hook's own extraction code, cut
from the hook file itself, so the test cannot drift from what actually fires.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "check-branch-on-push.sh"
PUSH = "git " + "push"


def _extractor() -> str:
    text = HOOK.read_text(encoding="utf-8")
    m = re.search(r'PUSH_CWD=\$\(printf .*?-c "\n(.*?)\n" 2>/dev/null\)', text, re.S)
    assert m, "could not find the push-folder extraction in the hook"
    return m.group(1).replace('\\"', '"')


def _run(command: str) -> str:
    payload = json.dumps({"tool_input": {"command": command}})
    out = subprocess.run(
        [sys.executable, "-c", _extractor()],
        input=payload,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return out.stdout.strip()


@pytest.fixture
def tree(tmp_path) -> Path:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    return tmp_path


def test_the_command_that_failed_tonight(tree) -> None:
    got = _run(
        f"set -o pipefail; cd {tree.as_posix()} && git add x && {PUSH} -u origin b 2>&1 | tail -8"
    )
    assert Path(got) == tree


def test_a_plain_leading_cd_still_works(tree) -> None:
    assert Path(_run(f"cd {tree.as_posix()} && {PUSH}")) == tree


def test_the_last_cd_before_the_push_wins(tree, tmp_path_factory) -> None:
    other = tmp_path_factory.mktemp("other")
    got = _run(f"cd {other.as_posix()} && ls; cd {tree.as_posix()} && {PUSH}")
    assert Path(got) == tree


def test_a_cd_after_the_push_is_not_the_pushed_tree(tree) -> None:
    assert _run(f"{PUSH}; cd {tree.as_posix()}") == ""


def test_a_word_containing_cd_is_not_a_cd(tree) -> None:
    assert _run(f"echo abcd {tree.as_posix()} && {PUSH}") == ""
