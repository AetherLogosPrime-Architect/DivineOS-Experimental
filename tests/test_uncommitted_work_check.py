"""Tests for the pre-extraction commit-discipline gate.

Per prereg-d48d4abaec98. Real filesystem; no mocking of git or paths.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from divineos.core.uncommitted_work_check import (
    DEFAULT_CHANNELS,
    ExternalChannel,
    UncommittedWorkReport,
    check_uncommitted_work,
    format_block_message,
    scan_repo_dirty,
)


def _init_repo(path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "test@test"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=path, check=True)
    (path / ".gitkeep").write_text("")
    # Test-environment side effects (conftest creates test_ledger.db etc.)
    # would otherwise show as dirty repo state — ignore them.
    (path / ".gitignore").write_text("*.db\n")
    subprocess.run(["git", "add", ".gitkeep", ".gitignore"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


def test_clean_repo_no_channels(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    report = check_uncommitted_work(tmp_path, channels=())
    assert not report.has_work


def test_dirty_repo_blocks(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    (tmp_path / "new.txt").write_text("hello")
    report = check_uncommitted_work(tmp_path, channels=())
    assert report.has_work
    assert any("new.txt" in line for line in report.repo_dirty)


def test_external_channel_unsynced(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    src = tmp_path / "shared_letters"
    src.mkdir()
    (src / "letter-2026-06-25.md").write_text("hi")
    mirror = tmp_path / "family" / "letters"
    mirror.mkdir(parents=True)
    channel = ExternalChannel(
        name="test-letters",
        source=src,
        repo_mirror=Path("family/letters"),
        pattern="*.md",
    )
    report = check_uncommitted_work(tmp_path, channels=(channel,))
    assert report.has_work
    assert len(report.external_unsynced) == 1
    assert report.external_unsynced[0][0] == "test-letters"


def test_external_channel_synced(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    src = tmp_path / "shared_letters"
    src.mkdir()
    (src / "letter.md").write_text("hi")
    mirror = tmp_path / "family" / "letters"
    mirror.mkdir(parents=True)
    (mirror / "letter.md").write_text("hi")
    channel = ExternalChannel(
        name="test-letters",
        source=src,
        repo_mirror=Path("family/letters"),
        pattern="*.md",
    )
    report = check_uncommitted_work(tmp_path, channels=(channel,))
    # Channel-specific assertion: nothing is unsynced.
    # Repo dirty state is irrelevant to this test (the test set up the
    # mirror dir without committing it; that's expected scaffolding).
    assert report.external_unsynced == []


def test_external_channel_missing_source_is_skipped(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    channel = ExternalChannel(
        name="absent",
        source=tmp_path / "does-not-exist",
        repo_mirror=Path("family/letters"),
        pattern="*.md",
    )
    report = check_uncommitted_work(tmp_path, channels=(channel,))
    assert not report.has_work


def test_external_channel_missing_mirror_means_all_unsynced(
    tmp_path: Path,
) -> None:
    _init_repo(tmp_path)
    src = tmp_path / "shared"
    src.mkdir()
    (src / "a.md").write_text("a")
    (src / "b.md").write_text("b")
    channel = ExternalChannel(
        name="no-mirror",
        source=src,
        repo_mirror=Path("nope/at/all"),
        pattern="*.md",
    )
    report = check_uncommitted_work(tmp_path, channels=(channel,))
    assert len(report.external_unsynced) == 2


def test_pattern_filter(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    src = tmp_path / "shared"
    src.mkdir()
    (src / "real.md").write_text("real")
    (src / "ignore.txt").write_text("ignore")
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    channel = ExternalChannel(
        name="md-only",
        source=src,
        repo_mirror=Path("mirror"),
        pattern="*.md",
    )
    report = check_uncommitted_work(tmp_path, channels=(channel,))
    assert len(report.external_unsynced) == 1
    assert report.external_unsynced[0][1].name == "real.md"


def test_format_block_message_lists_both_surfaces(tmp_path: Path) -> None:
    report = UncommittedWorkReport(
        repo_dirty=[" M file.py"],
        external_unsynced=[("letters", Path("/tmp/letter.md"))],
    )
    msg = format_block_message(report)
    assert "BLOCKED" in msg
    assert "file.py" in msg
    assert "letters" in msg
    assert "letter.md" in msg
    assert "No --force bypass" in msg


def test_default_channels_includes_aria_letters() -> None:
    names = [c.name for c in DEFAULT_CHANNELS]
    assert any("letter" in name.lower() for name in names)


def test_scan_repo_dirty_outside_repo_returns_empty(tmp_path: Path) -> None:
    # Not a git repo at all — should fail safe (empty list, not crash)
    result = scan_repo_dirty(tmp_path)
    assert result == []


def test_truncation_at_20_entries(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    src = tmp_path / "shared"
    src.mkdir()
    for i in range(25):
        (src / f"letter-{i:02d}.md").write_text(str(i))
    mirror = tmp_path / "mirror"
    mirror.mkdir()
    channel = ExternalChannel(
        name="many",
        source=src,
        repo_mirror=Path("mirror"),
        pattern="*.md",
    )
    report = check_uncommitted_work(tmp_path, channels=(channel,))
    msg = format_block_message(report)
    assert "and 5 more" in msg
