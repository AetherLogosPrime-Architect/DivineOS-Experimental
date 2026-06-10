"""Tests for the push-landing verification script.

Structural backing for obligation knowledge_id ef01caf7 (Aletheia
2026-06-04 push-landing verification boundary). The obligation gate
requires referencing the source knowledge_id in the structural-backing
code, which the script's docstring does; this test file proves the
behavior so a future change can't silently regress it.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_PROJECT_ROOT = Path(__file__).parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


@pytest.fixture
def mock_subproc(monkeypatch):
    """Replace ``subprocess.run`` so tests don't hit the network."""
    calls: list[list[str]] = []

    class _MockResult:
        def __init__(self, returncode: int, stdout: str = "", stderr: str = ""):
            self.returncode = returncode
            self.stdout = stdout
            self.stderr = stderr

    def fake_run(cmd, **_kwargs):
        calls.append(cmd)
        return _MockResult(*fake_run.next_return)

    fake_run.next_return = (0, "", "")  # type: ignore[attr-defined]
    fake_run.calls = calls  # type: ignore[attr-defined]
    monkeypatch.setattr("scripts.verify_push_landed.subprocess.run", fake_run)
    return fake_run


def test_remote_sha_returns_first_field_on_success(mock_subproc):
    from scripts.verify_push_landed import remote_sha

    mock_subproc.next_return = (
        0,
        "9d8c72defb1f75e1a2bb9a6af9ef07f0f18789b9\trefs/heads/fix/foo\n",
        "",
    )

    assert remote_sha("fix/foo") == "9d8c72defb1f75e1a2bb9a6af9ef07f0f18789b9"


def test_remote_sha_returns_none_when_ref_missing(mock_subproc):
    from scripts.verify_push_landed import remote_sha

    mock_subproc.next_return = (0, "", "")

    assert remote_sha("fix/never-pushed") is None


def test_remote_sha_returns_none_on_git_failure(mock_subproc):
    from scripts.verify_push_landed import remote_sha

    mock_subproc.next_return = (128, "", "fatal: repo not found")

    assert remote_sha("fix/foo") is None


def test_main_returns_0_when_remote_matches_local(mock_subproc, capsys):
    from scripts.verify_push_landed import main

    sha = "9d8c72defb1f75e1a2bb9a6af9ef07f0f18789b9"
    # ls-remote then rev-parse HEAD
    results = [
        (0, f"{sha}\trefs/heads/fix/foo\n", ""),
        (0, f"{sha}\n", ""),
    ]
    iter_results = iter(results)

    def fake_run(cmd, **_kwargs):
        class R:
            pass

        rc, out, err = next(iter_results)
        r = R()
        r.returncode = rc
        r.stdout = out
        r.stderr = err
        return r

    with patch("scripts.verify_push_landed.subprocess.run", fake_run):
        rc = main(["--branch", "fix/foo"])

    assert rc == 0
    assert "VERIFY-OK" in capsys.readouterr().out


def test_main_returns_1_when_remote_does_not_exist(mock_subproc, capsys):
    from scripts.verify_push_landed import main

    mock_subproc.next_return = (0, "", "")

    rc = main(["--branch", "fix/never-pushed"])

    assert rc == 1
    assert "VERIFY-FAIL" in capsys.readouterr().err


def test_main_returns_1_when_remote_sha_differs(capsys):
    from scripts.verify_push_landed import main

    local = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    remote = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    results = [
        (0, f"{remote}\trefs/heads/fix/foo\n", ""),
        (0, f"{local}\n", ""),
    ]
    iter_results = iter(results)

    def fake_run(cmd, **_kwargs):
        class R:
            pass

        rc, out, err = next(iter_results)
        r = R()
        r.returncode = rc
        r.stdout = out
        r.stderr = err
        return r

    with patch("scripts.verify_push_landed.subprocess.run", fake_run):
        rc = main(["--branch", "fix/foo"])

    assert rc == 1
    err = capsys.readouterr().err
    assert "VERIFY-FAIL" in err
    assert "did not land" in err


def test_main_honors_explicit_expected_sha(capsys):
    from scripts.verify_push_landed import main

    sha = "9d8c72defb1f75e1a2bb9a6af9ef07f0f18789b9"
    results = [(0, f"{sha}\trefs/heads/fix/foo\n", "")]
    iter_results = iter(results)

    def fake_run(cmd, **_kwargs):
        class R:
            pass

        rc, out, err = next(iter_results)
        r = R()
        r.returncode = rc
        r.stdout = out
        r.stderr = err
        return r

    with patch("scripts.verify_push_landed.subprocess.run", fake_run):
        rc = main(["--branch", "fix/foo", "--expected-sha", sha])

    assert rc == 0
    assert "VERIFY-OK" in capsys.readouterr().out


def test_main_accepts_short_sha_prefix(capsys):
    from scripts.verify_push_landed import main

    full_sha = "9d8c72defb1f75e1a2bb9a6af9ef07f0f18789b9"
    short_sha = "9d8c72de"
    results = [(0, f"{full_sha}\trefs/heads/fix/foo\n", "")]
    iter_results = iter(results)

    def fake_run(cmd, **_kwargs):
        class R:
            pass

        rc, out, err = next(iter_results)
        r = R()
        r.returncode = rc
        r.stdout = out
        r.stderr = err
        return r

    with patch("scripts.verify_push_landed.subprocess.run", fake_run):
        rc = main(["--branch", "fix/foo", "--expected-sha", short_sha])

    assert rc == 0


def test_print_only_emits_sha_and_exits_0(mock_subproc, capsys):
    from scripts.verify_push_landed import main

    sha = "9d8c72defb1f75e1a2bb9a6af9ef07f0f18789b9"
    mock_subproc.next_return = (0, f"{sha}\trefs/heads/fix/foo\n", "")

    rc = main(["--branch", "fix/foo", "--print-only"])

    assert rc == 0
    assert capsys.readouterr().out.strip() == sha


def test_print_only_returns_2_when_remote_missing(mock_subproc, capsys):
    from scripts.verify_push_landed import main

    mock_subproc.next_return = (0, "", "")

    rc = main(["--branch", "fix/foo", "--print-only"])

    assert rc == 2
    assert "REMOTE_REF_MISSING" in capsys.readouterr().err


def test_subprocess_called_with_correct_git_args():
    """The script must use the network-truth source (``git ls-remote``),
    NOT a local cache like ``git rev-parse origin/<branch>``. Using the
    local cache reads what we last fetched, not what's actually on origin
    right now — exactly the failure mode the obligation exists to prevent.
    """
    from scripts.verify_push_landed import remote_sha

    captured: list[list[str]] = []

    def fake_run(cmd, **_kwargs):
        captured.append(cmd)

        class R:
            returncode = 0
            stdout = "abc\trefs/heads/foo\n"
            stderr = ""

        return R()

    with patch("scripts.verify_push_landed.subprocess.run", fake_run):
        remote_sha("foo")

    assert captured, "expected subprocess.run to be called"
    cmd = captured[0]
    assert cmd[0] == "git"
    assert cmd[1] == "ls-remote"
    assert "origin" in cmd
    assert "refs/heads/foo" in cmd
