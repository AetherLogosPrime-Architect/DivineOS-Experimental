"""Tests for scripts/ci_check_guardrail_trailer.sh.

Closes the test-coverage gap on the server-side multi-party-review
gate that this session (2026-06-13) made visible. Per knowledge
a7193bf6-1e9d-4f04-ad37-706860b80b20 — the prior will-shape
correction about where to put the External-Review trailer needed
structural backing (a test, not just procedural memory).

The script under test is the server-side guardrail-trailer gate.
These tests build synthetic git repos with various commit+guardrail
configurations and assert the script's pass/fail behavior.

What the gate currently catches and what it does NOT — both are
tested explicitly so the gap stays visible as the gate is extended
in follow-up work.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from _git_test_helpers import safe_git_init

REPO_ROOT = Path(__file__).parent.parent
SCRIPT = REPO_ROOT / "scripts" / "ci_check_guardrail_trailer.sh"


def _find_bash() -> str | None:
    """Locate a usable bash on this platform. On Windows-from-WSL
    invocation `bash` may resolve to WSL bash that can't see the
    script path, so we try the git-for-windows bash explicitly."""
    candidates = [
        "/usr/bin/bash",
        "/c/Program Files/Git/bin/bash.exe",
        r"C:\Program Files\Git\bin\bash.exe",
        shutil.which("bash") or "",
    ]
    for c in candidates:
        if c and Path(c).exists():
            return c
    return None


_BASH = _find_bash()

pytestmark = pytest.mark.skipif(
    _BASH is None, reason="no usable bash interpreter found on this platform"
)


def _run_script(repo: Path, base: str, head: str) -> subprocess.CompletedProcess:
    assert _BASH is not None
    return subprocess.run(
        [_BASH, str(SCRIPT), base, head],
        cwd=str(repo),
        capture_output=True,
        text=True,
    )


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args],
        cwd=str(repo),
        check=True,
        capture_output=True,
        text=True,
    )


def _commit(repo: Path, message: str, files: dict[str, str]) -> str:
    for path, contents in files.items():
        full = repo / path
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(contents, encoding="utf-8")
        _git(repo, "add", path)
    # Use stdin for message to preserve newlines (trailer format).
    subprocess.run(
        ["git", "commit", "-F", "-"],
        cwd=str(repo),
        input=message,
        text=True,
        check=True,
        capture_output=True,
    )
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    return sha


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    safe_git_init(tmp_path, "--initial-branch=main")
    _git(tmp_path, "config", "user.email", "test@test")
    _git(tmp_path, "config", "user.name", "test")
    return tmp_path


def test_no_guardrail_files_means_no_check_fires(repo):
    """Empty guardrail list -> no commits get blocked even without trailer."""
    base = _commit(repo, "initial", {"scripts/guardrail_files.txt": "# empty\n"})
    head = _commit(
        repo,
        "feat: change anything",
        {"src/foo.py": "x"},
    )
    result = _run_script(repo, base, head)
    assert result.returncode == 0, result.stdout + result.stderr


def test_guardrail_touch_without_trailer_blocks(repo):
    """A commit modifying a guardrail file with no External-Review trailer fails."""
    base = _commit(
        repo,
        "initial; add guardrail entry",
        {
            "scripts/guardrail_files.txt": "src/foo.py\n",
            "src/foo.py": "v1",
        },
    )
    head = _commit(repo, "feat: modify the guardrailed file", {"src/foo.py": "v2"})
    result = _run_script(repo, base, head)
    assert result.returncode == 1
    assert "BLOCKED" in result.stdout


def test_guardrail_touch_with_trailer_passes(repo):
    """A commit modifying a guardrail file with a trailer passes (presence-only)."""
    base = _commit(
        repo,
        "initial; add guardrail entry",
        {
            "scripts/guardrail_files.txt": "src/foo.py\n",
            "src/foo.py": "v1",
        },
    )
    head = _commit(
        repo,
        "feat: modify the guardrailed file\n\nExternal-Review: round-abcdef123\n",
        {"src/foo.py": "v2"},
    )
    result = _run_script(repo, base, head)
    assert result.returncode == 0, result.stdout + result.stderr


def test_non_guardrail_commit_skipped_even_without_trailer(repo):
    """A commit that doesn't touch any guardrail file doesn't need a trailer."""
    base = _commit(
        repo,
        "initial; add guardrail entry",
        {
            "scripts/guardrail_files.txt": "src/special.py\n",
            "src/special.py": "v1",
            "src/normal.py": "v1",
        },
    )
    head = _commit(repo, "feat: change normal", {"src/normal.py": "v2"})
    result = _run_script(repo, base, head)
    assert result.returncode == 0


def test_self_disclosure_block_always_emitted(repo):
    """The gate must always print what it checked AND what it did NOT check.
    This is the meta-self-disclosure piece (Aletheia 2026-06-13)."""
    base = _commit(repo, "initial", {"scripts/guardrail_files.txt": "# empty\n"})
    head = _commit(repo, "feat: nothing important", {"src/foo.py": "x"})
    result = _run_script(repo, base, head)
    assert "Multi-Party-Review Gate: scope of this check" in result.stdout
    assert "Checked:" in result.stdout
    assert "Did NOT check" in result.stdout
    assert "hash-binding" in result.stdout
    assert "temporal precedence" in result.stdout


def test_self_disclosure_present_on_block_too(repo):
    """The self-disclosure must print on the BLOCKED path too, not just pass."""
    base = _commit(
        repo,
        "initial; add guardrail entry",
        {
            "scripts/guardrail_files.txt": "src/foo.py\n",
            "src/foo.py": "v1",
        },
    )
    head = _commit(repo, "feat: bypass attempt", {"src/foo.py": "v2"})
    result = _run_script(repo, base, head)
    assert result.returncode == 1
    assert "Did NOT check" in result.stdout


def test_known_gap_substance_binding_not_checked(repo):
    """DOCUMENTS THE GAP: the current gate accepts any trailer text — it
    does NOT verify the round substantively covers the work. This test
    encodes the exploit the 2026-06-13 session lived through. When the
    substance-binding follow-up lands, this test should change to assert
    the bypass is now caught."""
    base = _commit(
        repo,
        "initial; add guardrail entry",
        {
            "scripts/guardrail_files.txt": "src/foo.py\n",
            "src/foo.py": "v1",
        },
    )
    # Stamp with a totally unrelated/fictional round-id. The current
    # gate has no way to know — and that's exactly what's not checked.
    head = _commit(
        repo,
        "feat: stale-round bypass demo\n\nExternal-Review: round-totally-stale-and-fake\n",
        {"src/foo.py": "v2"},
    )
    result = _run_script(repo, base, head)
    # Currently passes — this is the gap. The follow-up will close it.
    assert result.returncode == 0


def test_root_commit_does_not_explode(repo):
    """An initial commit (no parent) must not crash the script."""
    # The fixture creates an empty repo; make the very first commit.
    first = _commit(repo, "initial", {"src/foo.py": "v1"})
    # Range = first..first is empty — the script should pass cleanly.
    result = _run_script(repo, first, first)
    assert result.returncode == 0
