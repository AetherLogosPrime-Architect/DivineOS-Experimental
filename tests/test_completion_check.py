"""Tests for completion_check — the initiative-spectrum signal source.

The probe must:
1. Surface mechanisms missing wiring or test (not just pace)
2. NOT flood the signal — only files in mechanism dirs, .py/.sh only
3. Be safe in non-git checkouts / empty repos (return [])
4. Format evidence as descriptive questions, not a single number
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import pytest

from divineos.core.completion_check import (
    Unfinished,
    _batch_has_test_for,
    _batch_has_wiring_for,
    _has_test_for,
    _questions_for,
    _recently_added_files,
    format_for_compass,
    unfinished_mechanisms,
)


def _make_repo(tmp: Path) -> Path:
    """Initialize a tiny git repo for probe testing."""
    subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=tmp, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=tmp, check=True)
    return tmp


def test_recently_added_files_empty_on_non_git() -> None:
    """LOAD-BEARING: probe is safe on non-git paths — returns []
    rather than raising, so the compass observation step never breaks."""
    with tempfile.TemporaryDirectory() as tmp:
        out = _recently_added_files(7, Path(tmp))
        assert out == []


def test_batch_probe_scales_with_single_subprocess_call() -> None:
    """Regression guard against Andrew catch 2026-07-07: the per-file
    loop shelled out N times to git grep, and CI runners under load
    exceeded the test's own 30s cap when N grew (~20+ new mechanisms
    in a day). The batched helpers collapse the N calls to at most 3
    git greps total (one for tests, one for .py wiring, one for .sh
    wiring). This test hits the batched code path with a synthetic N=50
    and asserts it completes fast — if a future refactor silently reverts
    to the per-file shell-out loop, this test fails loud."""
    import time as _time

    with tempfile.TemporaryDirectory() as tmp:
        root = _make_repo(Path(tmp))
        (root / "src" / "divineos" / "core").mkdir(parents=True)
        (root / "tests").mkdir()
        paths: list[str] = []
        for i in range(50):
            (root / "src" / "divineos" / "core" / f"m_{i}.py").write_text("# x\n")
            paths.append(f"src/divineos/core/m_{i}.py")
        subprocess.run(["git", "add", "-A"], cwd=root, check=True)
        subprocess.run(
            ["git", "commit", "-q", "-m", "seed", "--no-verify"],
            cwd=root,
            check=True,
        )
        t0 = _time.time()
        test_map = _batch_has_test_for(paths, root)
        wiring_map = _batch_has_wiring_for(paths, root)
        elapsed = _time.time() - t0
        assert len(test_map) == 50
        assert len(wiring_map) == 50
        # 50 paths must complete well under CI's 30s cap. Generous
        # 10s ceiling gives headroom for slow CI runners while still
        # catching the per-file-loop regression (which would linear-scale
        # to well over 30s).
        assert elapsed < 10.0, (
            f"Batched probe took {elapsed:.1f}s on N=50 — likely reverted "
            "to per-file subprocess loop. See Andrew 2026-07-07 catch."
        )


def test_questions_for_includes_usefulness_always() -> None:
    """The usefulness question rides along even when test+wiring exist,
    because the probe can't auto-answer it."""
    qs = _questions_for("src/divineos/core/foo.py", has_test=True, has_wiring=True)
    assert any("help" in q.lower() or "caught" in q.lower() for q in qs)


def test_questions_for_flags_missing_test() -> None:
    qs = _questions_for("src/divineos/core/foo.py", has_test=False, has_wiring=True)
    assert any("test" in q.lower() for q in qs)


def test_questions_for_flags_missing_wiring() -> None:
    qs = _questions_for("src/divineos/core/foo.py", has_test=True, has_wiring=False)
    assert any("wired" in q.lower() or "wiring" in q.lower() for q in qs)


def test_format_for_compass_no_unfinished() -> None:
    """When nothing's unfinished, the evidence string says so plainly."""
    msg = format_for_compass([])
    assert "no recently-built" in msg


def test_format_for_compass_caps_at_five() -> None:
    """Evidence string truncates to keep observation rows bounded."""
    items = [
        Unfinished(
            path=f"src/divineos/core/mech_{i}.py",
            has_test=False,
            has_wiring=False,
            questions=["?"],
        )
        for i in range(8)
    ]
    msg = format_for_compass(items)
    assert "+3 more" in msg


def test_format_for_compass_names_flags() -> None:
    """Each entry tells you what's missing — unwired, untested, or both."""
    items = [
        Unfinished(
            path="src/divineos/core/lonely.py",
            has_test=False,
            has_wiring=False,
            questions=["?"],
        ),
    ]
    msg = format_for_compass(items)
    assert "unwired" in msg
    assert "untested" in msg


@pytest.mark.slow
@pytest.mark.timeout(30)
def test_unfinished_mechanisms_returns_list() -> None:
    """Smoke: the live probe runs against the real repo without error.
    Result shape is list[Unfinished] — content depends on git state.

    Marked `slow` per 2026-07-02 Fable audit finding #8: this test
    shells out to real git and its runtime scales with recently-added
    file count in the actual repo. Under -n auto in the pre-push hook
    it was observed hanging parallel workers when git state was noisy.
    Also given an explicit 30s timeout as a hard cap: if the subprocess
    calls inside _has_wiring_for / _has_test_for get slow for any reason
    (network-mounted repo, hot git cache miss, etc.), the test fails
    loud rather than hanging the suite.

    Skipped from the default -m "not slow" runs; re-enable with
    `pytest -m slow` for full-coverage runs (e.g. nightly CI)."""
    out = unfinished_mechanisms(days=1)
    assert isinstance(out, list)
    for u in out:
        assert isinstance(u, Unfinished)
        assert u.path.endswith((".py", ".sh"))


def test_has_test_for_finds_existing_test() -> None:
    """If tests/test_<stem>.py exists, has_test=True."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "tests").mkdir()
        (root / "tests" / "test_foo.py").write_text("# x")
        assert _has_test_for("src/divineos/core/foo.py", root) is True
        assert _has_test_for("src/divineos/core/bar.py", root) is False
