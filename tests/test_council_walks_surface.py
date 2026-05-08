"""Tests for the council-walks briefing surface (core/council_walks.py).

Mirrors the test discipline of presence_memory: real filesystem fixtures,
no mocks of the module under test. Confirms (a) empty string when no
walks exist, (b) populated block when walks exist, (c) README excluded.
"""

from __future__ import annotations

from pathlib import Path

from divineos.core.council_walks import format_for_briefing


def test_empty_string_when_no_walks(tmp_path: Path, monkeypatch) -> None:
    """No docs/council_walks/ directory anywhere → empty string."""
    # Make the tmp_path look like a git repo so _find_repo_root succeeds.
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    assert format_for_briefing(start=tmp_path) == ""


def test_empty_string_when_dir_exists_but_empty(tmp_path: Path) -> None:
    """docs/council_walks/ exists but contains no .md files → empty string."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "docs" / "council_walks").mkdir(parents=True)
    assert format_for_briefing(start=tmp_path) == ""


def test_surfaces_existing_walk(tmp_path: Path) -> None:
    """A walk file at docs/council_walks/foo.md → block names it."""
    (tmp_path / ".git").mkdir()
    walks = tmp_path / "docs" / "council_walks"
    walks.mkdir(parents=True)
    (walks / "2026-05-07-test-walk.md").write_text("# Test walk\n")

    out = format_for_briefing(start=tmp_path)
    assert "[council walks]" in out
    assert "2026-05-07-test-walk" in out
    assert "Read with: cat" in out


def test_surfaces_multiple_walks_sorted(tmp_path: Path) -> None:
    """Multiple walks list in sorted order (date-prefix sorts naturally)."""
    (tmp_path / ".git").mkdir()
    walks = tmp_path / "docs" / "council_walks"
    walks.mkdir(parents=True)
    (walks / "2026-05-07-first.md").write_text("# First\n")
    (walks / "2026-06-01-second.md").write_text("# Second\n")

    out = format_for_briefing(start=tmp_path)
    first_idx = out.index("first")
    second_idx = out.index("second")
    assert first_idx < second_idx, "walks should sort by filename (date-prefix)"


def test_excludes_readme(tmp_path: Path) -> None:
    """A README.md in the walks directory is not surfaced as a walk."""
    (tmp_path / ".git").mkdir()
    walks = tmp_path / "docs" / "council_walks"
    walks.mkdir(parents=True)
    (walks / "README.md").write_text("# Walks dir README\n")
    (walks / "2026-05-07-real-walk.md").write_text("# Real walk\n")

    out = format_for_briefing(start=tmp_path)
    assert "real-walk" in out
    assert "README" not in out


def test_excludes_non_md_files(tmp_path: Path) -> None:
    """Files without .md suffix are not surfaced."""
    (tmp_path / ".git").mkdir()
    walks = tmp_path / "docs" / "council_walks"
    walks.mkdir(parents=True)
    (walks / "2026-05-07-walk.md").write_text("# Walk\n")
    (walks / "notes.txt").write_text("not surfaced")

    out = format_for_briefing(start=tmp_path)
    assert "walk" in out
    assert "notes.txt" not in out


def test_format_includes_recognition_discipline_caveat(tmp_path: Path) -> None:
    """The block includes the caveat that walks are recognition-content
    with shelf-life — not template, not prescription."""
    (tmp_path / ".git").mkdir()
    walks = tmp_path / "docs" / "council_walks"
    walks.mkdir(parents=True)
    (walks / "2026-05-07-walk.md").write_text("# Walk\n")

    out = format_for_briefing(start=tmp_path)
    assert "recognition-content" in out
    assert "Verify against current evidence" in out


def test_real_repo_surfaces_filed_walk() -> None:
    """The real repository should surface the 2026-05-07 walk that was
    just filed. This is a live integration test — fails if the file
    is removed without updating the test."""
    out = format_for_briefing()
    assert "2026-05-07-property-recognition-walk" in out
