"""The merge check tests what THIS branch changed, not everything main changed.

2026-10-27, Dad: "every push fails three times and takes 30 mins per push." Measured on a real
merge: 282 files differed between the two tips (nearly the whole suite, 13,500 tests, 28 minutes),
while this side had changed 17. The check had also been handing its test list to pytest in hash
order, so a test that reloads the ledger ran before the test holding the old Ledger class.

These tests build a real repository with a real merge in progress and run the real script.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

# a bash proven to run a script, not the WSL relay that shutil.which can return
from tests.test_a_merge_cannot_commit_past_its_own_tests import BASH

REAL = Path(__file__).resolve().parents[1]
SCRIPT = REAL / "scripts" / "check_merge_resolution_tested.sh"
SELECTOR = REAL / "scripts" / "draft_test_selection.py"

pytestmark = pytest.mark.skipif(BASH is None, reason="needs bash to run the check script")

PASSING = "def test_it():\n    assert True\n"
FAILING = "def test_it():\n    assert False\n"
GIT_STATE = ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR")


def _clean_env(**extra):
    env = {**os.environ, **extra}
    for k in GIT_STATE:
        env.pop(k, None)
    return env


def _git(repo, *args):
    env = _clean_env(
        GIT_AUTHOR_NAME="t",
        GIT_AUTHOR_EMAIL="t@t",
        GIT_COMMITTER_NAME="t",
        GIT_COMMITTER_EMAIL="t@t",
    )
    return subprocess.run(
        ["git", *args], cwd=repo, env=env, capture_output=True, text=True, check=False
    )


def _write(repo, rel, text):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def _test_naming(name, body=PASSING):
    # Names the module so the selector finds it, without importing it: the temp repo's
    # modules are not on any path, and the real divineos has no mod_a.
    return f'NAMES = "divineos.core.mod_{name}"\n\n{body}'


def _repo_with_merge(tmp_path, mine, theirs):
    """base has modules a, b, c each with a test naming it; `mine` and `theirs` are
    {path: text} edits made on each side. Leaves the merge open (--no-commit)."""
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    (repo / "scripts").mkdir()
    shutil.copy(SELECTOR, repo / "scripts" / "draft_test_selection.py")
    shutil.copy(SCRIPT, repo / "scripts" / "check_merge_resolution_tested.sh")
    for name in ("a", "b", "c"):
        _write(repo, f"src/divineos/core/mod_{name}.py", "VALUE = 1\n")
        _write(repo, f"tests/test_{name}.py", _test_naming(name))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "base")
    _git(repo, "checkout", "-q", "-b", "theirs")
    for rel, text in theirs.items():
        _write(repo, rel, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "theirs")
    _git(repo, "checkout", "-q", "main")
    for rel, text in mine.items():
        _write(repo, rel, text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "mine")
    merged = _git(repo, "merge", "--no-commit", "--no-ff", "theirs")
    assert merged.returncode == 0, merged.stdout + merged.stderr
    return repo


def _run_check(repo):
    env = _clean_env(PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ["PATH"])
    return subprocess.run(
        [BASH, "scripts/check_merge_resolution_tested.sh"],
        cwd=repo,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_it_runs_the_tests_for_what_my_side_changed_and_not_for_what_only_main_changed(tmp_path):
    repo = _repo_with_merge(
        tmp_path,
        mine={"src/divineos/core/mod_a.py": "VALUE = 2\n"},
        theirs={"src/divineos/core/mod_c.py": "VALUE = 3\n"},
    )
    out = _run_check(repo)
    text = out.stdout + out.stderr
    assert out.returncode == 0, text
    assert "running 1 test file(s)" in text, text
    assert "1 file(s) this branch changed since the merge base" in text, text
    assert "NOT a whole-tree pass" in text, text


def test_a_test_that_fails_for_my_side_still_refuses_the_merge(tmp_path):
    """Narrowing must not turn the check into one that cannot fail."""
    repo = _repo_with_merge(
        tmp_path,
        mine={
            "src/divineos/core/mod_a.py": "VALUE = 2\n",
            "tests/test_a.py": _test_naming("a", FAILING),
        },
        theirs={"src/divineos/core/mod_c.py": "VALUE = 3\n"},
    )
    out = _run_check(repo)
    assert out.returncode == 1, out.stdout + out.stderr
    assert "REFUSED" in out.stderr


def test_a_failure_in_a_file_only_main_changed_does_not_refuse_my_merge(tmp_path):
    """The case that cost 28 minutes: a test unrelated to anything I changed."""
    repo = _repo_with_merge(
        tmp_path,
        mine={"src/divineos/core/mod_a.py": "VALUE = 2\n"},
        theirs={
            "src/divineos/core/mod_c.py": "VALUE = 3\n",
            "tests/test_c.py": _test_naming("c", FAILING),
        },
    )
    out = _run_check(repo)
    assert out.returncode == 0, out.stdout + out.stderr


def test_when_it_cannot_narrow_it_falls_back_to_the_wide_set_and_says_so(tmp_path):
    """A changed conftest changes what every test sees, so the selector refuses to narrow
    and the check goes wide: a failure of the narrowing is wide, never a silent pass."""
    repo = _repo_with_merge(
        tmp_path,
        mine={"tests/conftest.py": "# shared setup\n"},
        theirs={"src/divineos/core/mod_c.py": "VALUE = 3\n"},
    )
    out = _run_check(repo)
    text = out.stdout + out.stderr
    assert "the narrow set was unavailable" in text, text


def test_the_tests_are_handed_to_pytest_in_sorted_order():
    """An associative array gives its keys back in hash order; the file list must be sorted."""
    body = SCRIPT.read_text(encoding="utf-8")
    assert "printf '%s\\n' \"${!TESTS[@]}\" | sort" in body
