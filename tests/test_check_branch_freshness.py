"""Tests for scripts/check_branch_freshness.sh.

Builds a temp upstream + clone, then exercises the script against
synthesized branch states (fresh, behind, ahead, on-base, detached).
No mocking of subprocess — the whole point of the script is to actually
call git.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "check_branch_freshness.sh"


def _resolve_bash() -> str | None:
    """Find a real bash on the system.

    On Windows, ``shutil.which('bash')`` may return either the WSL
    stub at ``C:\\Windows\\System32\\bash.exe`` (which only works if a
    Linux distro is installed) or Git Bash. The WSL stub emits UTF-16
    error output and exit 1 when no distro exists — we want Git Bash.
    Prefer Git Bash explicitly on Windows; fall back to ``which``.
    """
    if sys.platform == "win32":
        for candidate in (
            r"C:\Program Files\Git\usr\bin\bash.EXE",
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\usr\bin\bash.EXE",
        ):
            if Path(candidate).is_file():
                return candidate
    return shutil.which("bash")


_BASH = _resolve_bash()
_pytestmark_bash = pytest.mark.skipif(_BASH is None, reason="no usable bash interpreter found")


def _git(repo: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=check,
        encoding="utf-8",
        errors="replace",
    )


def _commit(repo: Path, message: str) -> None:
    """Make a commit so each branch has distinct content."""
    name_safe = "".join(c if c.isalnum() else "_" for c in message)[:30] or "f"
    fname = repo / f"f-{name_safe}-{abs(hash(message)) % 10**8}.txt"
    fname.write_text(message, encoding="utf-8")
    _git(repo, "add", str(fname.name))
    _git(repo, "commit", "-m", message)


@pytest.fixture
def repo() -> Path:
    """Build a tmp upstream-bare + clone with main branched off."""
    base_tmp = Path(tempfile.mkdtemp())
    upstream = base_tmp / "upstream.git"
    upstream.mkdir()
    _git(upstream, "init", "--bare", "--initial-branch=main")

    work = base_tmp / "work"
    work.mkdir()
    _git(work, "init", "--initial-branch=main")
    _git(work, "config", "user.email", "test@example.com")
    _git(work, "config", "user.name", "test")
    _git(work, "remote", "add", "origin", str(upstream))
    _commit(work, "initial main")
    _git(work, "push", "-u", "origin", "main")

    yield work

    # Best-effort cleanup. Windows may hold file locks briefly.
    shutil.rmtree(base_tmp, ignore_errors=True)


def _run_script(repo: Path) -> subprocess.CompletedProcess:
    """Invoke the freshness-check script in `repo`. Returns the process."""
    cmd = [_BASH, str(SCRIPT), "origin", "main"]
    return subprocess.run(
        cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def test_fresh_branch_passes(repo: Path):
    """Branch off current main, no upstream advance — exit 0."""
    _git(repo, "checkout", "-b", "claude/fresh")
    _commit(repo, "feature work")
    result = _run_script(repo)
    assert result.returncode == 0, result.stderr


def test_stale_branch_blocked(repo: Path):
    """Simulate the silent-revert precondition: main advances after branch is cut."""
    # Cut a feature branch first.
    _git(repo, "checkout", "-b", "claude/stale-feature")
    _commit(repo, "branch-side commit")

    # Meanwhile, main advances on the upstream side.
    _git(repo, "checkout", "main")
    _commit(repo, "main moved forward")
    _git(repo, "push", "origin", "main")

    # Switch back to the stale branch — it doesn't have main's new commit.
    _git(repo, "checkout", "claude/stale-feature")
    result = _run_script(repo)
    assert result.returncode == 1, (
        f"expected stale branch to be blocked\nstdout={result.stdout}\nstderr={result.stderr}"
    )
    # Error message must explain the situation.
    assert "stale" in result.stderr.lower() or "behind" in result.stderr.lower()
    assert "rebase" in result.stderr.lower()


def test_branch_at_main_parity_passes(repo: Path):
    """Branch with main as ancestor, zero commits ahead — still fine."""
    _git(repo, "checkout", "-b", "claude/parity")
    # No commits — branch tip == origin/main tip; ancestor relation holds.
    result = _run_script(repo)
    assert result.returncode == 0, result.stderr


def test_main_branch_skipped(repo: Path):
    """Pushing main itself is not a stale-branch case — exit 0."""
    _git(repo, "checkout", "main")
    result = _run_script(repo)
    assert result.returncode == 0, result.stderr


def test_skip_env_var_bypasses_check(repo: Path):
    """DIVINEOS_SKIP_FRESHNESS_CHECK=1 escape hatch."""
    _git(repo, "checkout", "-b", "claude/stale-feature")
    _git(repo, "checkout", "main")
    _commit(repo, "main moved")
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "claude/stale-feature")

    env = os.environ.copy()
    env["DIVINEOS_SKIP_FRESHNESS_CHECK"] = "1"
    cmd = [_BASH, str(SCRIPT), "origin", "main"]
    result = subprocess.run(
        cmd,
        cwd=repo,
        capture_output=True,
        text=True,
        env=env,
        encoding="utf-8",
        errors="replace",
    )
    assert result.returncode == 0, result.stderr
    assert "skipping" in result.stdout.lower()


def test_no_remote_returns_infra_error(repo: Path):
    """Missing remote → exit 2 (infra error, hook fails open)."""
    _git(repo, "checkout", "-b", "claude/feature")
    _git(repo, "remote", "remove", "origin")
    result = _run_script(repo)
    assert result.returncode == 2, result.stderr


def test_message_mentions_claim_for_traceability(repo: Path):
    """The error explains WHY (silent-revert pattern, claim d3baec5a)."""
    _git(repo, "checkout", "-b", "claude/stale")
    _git(repo, "checkout", "main")
    _commit(repo, "main moved")
    _git(repo, "push", "origin", "main")
    _git(repo, "checkout", "claude/stale")
    result = _run_script(repo)
    assert result.returncode == 1
    # The forensic pointer matters — readers debugging the hook later
    # need a thread to pull on, not just "BLOCKED."
    assert "d3baec5a" in result.stderr or "silent-revert" in result.stderr
