"""A push for a draft, or for a new branch with no PR yet, does not run the full suite.

Dad, 2026-10-21, the fourth time he said it (09-09, 09-23, 09-30): "why is a draft
running the full suite? only a push before merge should be running the full suite..
that is the whole point of the draft." Asked whether a brand-new branch with no
draft yet counts: "yes it counts." Every code-touching push had run the whole
suite regardless of PR state, which is weeks of waiting and his PC.

The cases are what GitHub can say about the branch: nothing (a new branch), only
drafts, a ready PR, a mix, or nothing at all because the question could not be
asked. The last one must RUN the suite: not knowing a PR is a draft must never
pass as knowing it is one.

SYNTHETIC REPOS and a FAKE gh on PATH, never this repository and never GitHub, for
the reason its sibling test_push_gate_tag_only.py gives: a gate test whose answer
depends on where it stands is not a measurement.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
_SCRIPT = _PROJECT_ROOT / "scripts" / "check_push_readiness.sh"
_SCOPE = _PROJECT_ROOT / "scripts" / "check_branch_scope.py"
_SELECT = _PROJECT_ROOT / "scripts" / "draft_test_selection.py"

_ZERO = "0" * 40


def _find_bash() -> str | None:
    for candidate in (r"C:\Program Files\Git\bin\bash.exe", "/bin/bash", "/usr/bin/bash"):
        if Path(candidate).exists():
            return candidate
    return shutil.which("bash")


_BASH = _find_bash()

# Each test runs the real push gate in a throwaway repo, so each is slow, and the suite's 30s default ends the whole
# worker when it trips ("node down: Not properly terminated"); the gate's own log named these as repeat crashers.
# Same mechanism and same remedy as test_mutate_copy.py (2026-10-22). A real hang still fails, at 600s.
pytestmark = [
    pytest.mark.timeout(600),
    pytest.mark.skipif(_BASH is None, reason="bash not available"),
]

_HARNESS_OWNED = frozenset(
    {
        "DIVINEOS_DB",
        "DIVINEOS_HOME",
        "DIVINEOS_SESSION_ID",
        "DIVINEOS_DISABLE_AUTO_REMEDIATE",
    }
)

_DRAFT_LINE = "Draft path:"


def _clean_env(fake_bin: Path, out: str, rc: int) -> dict[str, str]:
    env = {
        k: v for k, v in os.environ.items() if not k.startswith("DIVINEOS_") or k in _HARNESS_OWNED
    }
    env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
    env["FAKE_GH_OUT"] = out
    env["FAKE_GH_RC"] = str(rc)
    return env


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=str(repo), capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def fake_bin(tmp_path: Path) -> Path:
    """A gh that answers whatever the test put in FAKE_GH_OUT and exits FAKE_GH_RC."""
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    gh = bin_dir / "gh"
    gh.write_text('#!/bin/bash\nprintf "%b" "$FAKE_GH_OUT"\nexit "${FAKE_GH_RC:-0}"\n', "utf-8")
    gh.chmod(0o755)
    return bin_dir


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "test")
    (root / "scripts").mkdir()
    for script in (_SCRIPT, _SCOPE, _SELECT):
        shutil.copy2(script, root / "scripts" / script.name)
    (root / "src").mkdir()
    (root / "src" / "thing.py").write_text("value = 1\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "base")
    _git(root, "update-ref", "refs/remotes/origin/main", _git(root, "rev-parse", "HEAD"))
    return root


def _run_gate(
    repo: Path, fake_bin: Path, refs: list[str], out: str = "", rc: int = 0
) -> subprocess.CompletedProcess[str]:
    # A REAL commit, not a made-up id (Aria 2026-10-22): the draft path now reads the pushed commit to choose
    # which tests to run, and a commit that does not exist is, rightly, "cannot read, run everything". It is also
    # one commit AHEAD of main, because a branch with nothing ahead is stopped as an empty push before any of this.
    if _git(repo, "rev-parse", "HEAD") == _git(repo, "rev-parse", "refs/remotes/origin/main"):
        (repo / "src" / "thing.py").write_text("value = 2\n", encoding="utf-8")
        _git(repo, "add", "-A")
        _git(repo, "-c", "core.hooksPath=/dev/null", "commit", "-q", "-m", "a change on the branch")
    sha = _git(repo, "rev-parse", "HEAD")
    stdin = "".join(f"{ref} {sha} {ref} {_ZERO}\n" for ref in refs)
    return subprocess.run(
        [_BASH, str(_SCRIPT)],
        input=stdin,
        capture_output=True,
        text=True,
        timeout=300,
        cwd=str(repo),
        env=_clean_env(fake_bin, out, rc),
    )


def test_a_new_branch_with_no_pr_takes_the_draft_path(repo, fake_bin):
    """THE CASE HE NAMED: no draft exists yet, and the first push is the light one."""
    result = _run_gate(repo, fake_bin, ["refs/heads/work"], out="")
    assert _DRAFT_LINE in result.stdout, result.stdout[-2000:]


def test_a_branch_with_only_a_draft_takes_the_draft_path(repo, fake_bin):
    result = _run_gate(repo, fake_bin, ["refs/heads/work"], out="true\\n")
    assert _DRAFT_LINE in result.stdout, result.stdout[-2000:]


def test_a_branch_with_a_ready_pr_runs_the_suite(repo, fake_bin):
    """THE MERGE-BOUND PUSH: guard the guard, a leak here silently disables the
    one run that is supposed to happen."""
    result = _run_gate(repo, fake_bin, ["refs/heads/work"], out="false\\n")
    assert _DRAFT_LINE not in result.stdout, result.stdout[-2000:]


def test_one_ready_pr_among_drafts_still_runs_the_suite(repo, fake_bin):
    result = _run_gate(repo, fake_bin, ["refs/heads/work"], out="true\\nfalse\\n")
    assert _DRAFT_LINE not in result.stdout, result.stdout[-2000:]


def test_a_push_to_main_runs_the_suite_without_asking_github(repo, fake_bin):
    """Even when GitHub would say nothing at all, main is the merge itself."""
    result = _run_gate(repo, fake_bin, ["refs/heads/main"], out="")
    assert _DRAFT_LINE not in result.stdout, result.stdout[-2000:]


def test_a_failed_question_runs_the_suite_and_says_why(repo, fake_bin):
    """COULD-NOT-LOOK must not pass as nothing: an unreachable GitHub is not a draft."""
    result = _run_gate(repo, fake_bin, ["refs/heads/work"], out="", rc=1)
    assert _DRAFT_LINE not in result.stdout, result.stdout[-2000:]
    assert "could not ask GitHub" in result.stderr, result.stderr[-2000:]


def test_two_branches_where_one_is_ready_runs_the_suite(repo, fake_bin):
    """The fake answers the same for every branch, so a ready answer covers both,
    and a single ready branch anywhere in the push makes it merge-bound."""
    result = _run_gate(repo, fake_bin, ["refs/heads/a", "refs/heads/b"], out="false\\n")
    assert _DRAFT_LINE not in result.stdout, result.stdout[-2000:]


def test_the_draft_path_is_named_in_the_script_so_a_rename_breaks_this_file():
    """The assertions above look for the printed line; pin that the script still prints it."""
    assert _DRAFT_LINE in _SCRIPT.read_text(encoding="utf-8")
