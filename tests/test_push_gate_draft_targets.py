"""A draft push runs the tests that touch the change, and only those; the merge-bound push still runs everything.

Dad, 2026-10-21: "we just test that code and anything directly touching it. we dont run the full suite until its being
merged to main." Aether's draft path (test_push_gate_draft_path.py) skips the suite for a draft; this is the layer that
keeps the August 2026 promise, that a test change on a draft is never verified by nobody.

REAL COMMITS in a throwaway repository, the REAL gate, and a FAKE gh, never this repository and never GitHub. The base
holds a test that always fails (`test_unrelated_fails.py`). It is the instrument: a draft push that touches something
else must NOT trip over it (proving the suite was not run), and a push bound for merge MUST (proving the suite still is).
A selector that ran nothing would pass the first and fail the rest; one that ran everything would pass the rest and fail
the first.

WHAT THIS DOES NOT COVER, said so silence is not read as coverage: what the selector can and cannot find is
test_draft_test_selection.py's job. This file reads only what the gate does with the answer.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
_SCRIPTS = (
    "check_push_readiness.sh",
    "check_branch_scope.py",
    "draft_test_selection.py",
    "recover_crashed_workers.py",
)
_ZERO = "0" * 40


def _find_bash() -> str | None:
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", "/bin/bash", "/usr/bin/bash"):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


_BASH = _find_bash()

# Each test runs the real gate, which runs a real test run inside it, so each is slow; the suite's default limit of
# 30s would end the whole worker (found 2026-10-21), so the limit is raised here, as in test_mutate_copy.py.
pytestmark = [
    pytest.mark.timeout(600),
    pytest.mark.skipif(_BASH is None, reason="bash not available"),
    pytest.mark.skipif(
        not all((_PROJECT_ROOT / "scripts" / s).exists() for s in _SCRIPTS),
        reason="a gate script is absent here",
    ),
]


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    )
    return done.stdout.strip()


def _write(repo: Path, rel: str, body: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.invalid")
    _git(root, "config", "user.name", "t")
    (root / "scripts").mkdir()
    for name in _SCRIPTS:
        shutil.copy2(_PROJECT_ROOT / "scripts" / name, root / "scripts" / name)
    _write(root, "src/pkg/__init__.py", "")
    _write(root, "src/pkg/mod.py", "def value():\n    return 1\n")
    _write(root, "src/pkg/lonely.py", "NOBODY_TESTS_ME = 1\n")
    _write(
        root,
        "tests/test_mod.py",
        "from pkg.mod import value\n\n\ndef test_value():\n    assert value() == 1\n",
    )
    _write(root, "tests/test_unrelated_fails.py", "def test_unrelated_fails():\n    assert False\n")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))
    _git(root, "switch", "-q", "-c", "work")
    return root


@pytest.fixture
def fake_bin(tmp_path: Path) -> Path:
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text('#!/bin/bash\nprintf "%b" "$FAKE_GH_OUT"\nexit 0\n', "utf-8")
    gh.chmod(0o755)
    return bin_dir


def _push(repo: Path, fake_bin: Path, *, pr: str = "true\\n") -> subprocess.CompletedProcess[str]:
    """Run the real gate for `refs/heads/work` at the repo's current commit. `pr` is what the fake gh says."""
    sha = _git(repo, "rev-parse", "HEAD")
    env = {k: v for k, v in os.environ.items() if not k.startswith(("DIVINEOS_", "GIT_"))}
    env["PATH"] = os.pathsep.join(
        [str(fake_bin), str(Path(sys.executable).parent), env.get("PATH", "")]
    )
    env["FAKE_GH_OUT"] = pr
    env["DIVINEOS_SKIP_LOAD_CHECK"] = "1"  # these are two-line toy tests, not a memory question
    env["DIVINEOS_PUSH_GATE_NO_PARALLEL"] = "1"
    env["DIVINEOS_ALLOW_EMPTY_PUSH"] = "1"
    return subprocess.run(
        [_BASH, str(repo / "scripts" / "check_push_readiness.sh")],
        input=f"refs/heads/work {sha} refs/heads/work {_ZERO}\n",
        capture_output=True,
        text=True,
        timeout=280,
        cwd=str(repo),
        env=env,
    )


def _commit(repo: Path, rel: str, body: str) -> None:
    _write(repo, rel, body)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", f"change {rel}")


def _said(result: subprocess.CompletedProcess[str]) -> str:
    return result.stdout + result.stderr


def test_a_draft_touching_a_module_runs_that_modules_tests_and_not_the_rest(repo, fake_bin):
    _commit(repo, "src/pkg/mod.py", "def value():\n    return 1  # reworded\n")
    said = _said(_push(repo, fake_bin))
    assert "only the tests that touch the change run" in said, said[-2500:]
    assert "tests/test_mod.py" in said
    assert "tests failing" not in said, said[-2500:]  # the always-failing test was NOT run


def test_a_draft_that_breaks_a_module_is_caught_by_the_tests_that_touch_it(repo, fake_bin):
    """The August property, kept: nothing breaks on a draft unseen."""
    _commit(repo, "src/pkg/mod.py", "def value():\n    return 99\n")
    result = _push(repo, fake_bin)
    assert result.returncode == 10, _said(result)[-2500:]
    assert "tests failing" in _said(result)


def test_a_test_file_changed_on_a_draft_is_run(repo, fake_bin):
    """The exact gap of 2026-08-22: a changed test, on a draft, verified by nobody."""
    _commit(repo, "tests/test_mod.py", "def test_value():\n    assert False\n")
    result = _push(repo, fake_bin)
    assert result.returncode == 10, _said(result)[-2500:]


def test_a_change_no_test_names_is_skipped_and_said_out_loud(repo, fake_bin):
    _commit(repo, "src/pkg/lonely.py", "NOBODY_TESTS_ME = 2\n")
    said = _said(_push(repo, fake_bin))
    assert "Draft path:" in said
    assert "NO TEST NAMES src/pkg/lonely.py" in said
    assert "tests failing" not in said


def test_a_shared_setup_file_runs_the_whole_suite_even_on_a_draft(repo, fake_bin):
    """Cannot be narrowed, so it is not: the always-failing test is reached and the push is stopped."""
    _commit(repo, "tests/conftest.py", "# shared setup\n")
    result = _push(repo, fake_bin)
    assert result.returncode == 10, _said(result)[-2500:]
    assert "cannot narrow" in _said(result)


def test_a_missing_selector_runs_the_whole_suite_and_says_why(repo, fake_bin):
    """Not being able to choose is not the same as nothing to choose: it must fall back to everything."""
    (repo / "scripts" / "draft_test_selection.py").unlink()
    _commit(repo, "src/pkg/mod.py", "def value():\n    return 1  # reworded\n")
    result = _push(repo, fake_bin)
    assert result.returncode == 10, _said(result)[-2500:]
    assert "cannot narrow the tests" in _said(result)


def test_a_push_bound_for_merge_still_runs_everything(repo, fake_bin):
    """The control for all of the above: a ready pull request is the merge-bound push, and it runs the whole suite."""
    _commit(repo, "src/pkg/mod.py", "def value():\n    return 1  # reworded\n")
    result = _push(repo, fake_bin, pr="false\\n")
    assert result.returncode == 10, _said(result)[-2500:]
    assert "only the tests that touch the change run" not in _said(result)
