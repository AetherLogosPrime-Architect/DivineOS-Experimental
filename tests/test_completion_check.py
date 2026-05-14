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

from divineos.core.completion_check import (
    Unfinished,
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


def test_unfinished_mechanisms_returns_list() -> None:
    """Smoke: the live probe runs against the real repo without error.
    Result shape is list[Unfinished] — content depends on git state."""
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
