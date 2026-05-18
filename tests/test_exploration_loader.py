"""Regression-pin tests for exploration_loader.

Andrew named the gap 2026-05-15: lessons I have written into the
exploration/ folder over weeks exist as artifacts but are not loaded
into per-turn baseline context. This loader closes the gap. The
tests verify it loads recent entries, respects budgets, handles
missing-directory cleanly, and surfaces in build_baseline_text.
"""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from divineos.core import exploration_loader as el


@pytest.fixture
def fake_exploration(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Build a fake exploration/ directory with three entries."""
    d = tmp_path / "exploration"
    d.mkdir()
    # Write entries with controlled mtimes so we can verify ordering.
    now = time.time()
    entries = [
        ("01_oldest.md", "# Oldest Entry\n\nA line about something.\n", now - 1000),
        ("02_middle.md", "# Middle Entry\n\nThe right move is translate.\n", now - 500),
        (
            "03_newest.md",
            "# 39: River\n\n*April 28*\nTerritory: [self]\n\nI corrected. Then over-corrected. Two failure modes back-to-back.\n",
            now - 10,
        ),
    ]
    for name, content, mtime in entries:
        path = d / name
        path.write_text(content, encoding="utf-8")
        import os

        os.utime(path, (mtime, mtime))

    monkeypatch.setattr(el, "_exploration_dir", lambda: d)
    return d


def test_returns_empty_when_no_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """LOAD-BEARING: missing exploration/ returns empty string, not crash."""
    nonexistent = tmp_path / "does-not-exist"
    monkeypatch.setattr(el, "_exploration_dir", lambda: nonexistent)
    result = el.load_exploration_lessons()
    assert result == ""


def test_returns_empty_when_directory_empty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty directory → empty string."""
    empty = tmp_path / "exploration"
    empty.mkdir()
    monkeypatch.setattr(el, "_exploration_dir", lambda: empty)
    assert el.load_exploration_lessons() == ""


def test_most_recent_entry_appears_first(fake_exploration: Path) -> None:
    """Recency-ordered: newest entry's title appears before older entries."""
    result = el.load_exploration_lessons()
    newest_pos = result.find("39: River")
    middle_pos = result.find("Middle Entry")
    assert newest_pos != -1, "newest entry's title missing"
    if middle_pos != -1:
        assert newest_pos < middle_pos, "ordering violated — newest should lead"


def test_default_max_entries_limits_output(fake_exploration: Path) -> None:
    """Default max_entries=2 means at most 2 entries surface even with 3 available."""
    result = el.load_exploration_lessons(max_entries=2)
    # Oldest should not appear when only 2 most-recent are selected.
    assert "Oldest Entry" not in result


def test_total_budget_caps_output(fake_exploration: Path) -> None:
    """Total budget cap stops adding entries past the threshold."""
    # Force a tight budget so only one entry fits.
    result = el.load_exploration_lessons(max_entries=10, max_chars_per_entry=400, total_budget=50)
    # At least one entry got in (loader guarantees one); but the
    # block is small enough that not all three could fit.
    assert "39: River" in result  # newest always included
    assert "Oldest Entry" not in result


def test_excerpt_strips_frontmatter(fake_exploration: Path) -> None:
    """Italic date line and Territory tag don't appear in excerpt."""
    result = el.load_exploration_lessons()
    # The newest entry has "*April 28*" and "Territory: [self]" frontmatter
    # which should be stripped before the excerpt.
    assert "April 28" not in result
    assert "Territory: [self]" not in result
    # But the actual content should appear.
    assert "over-corrected" in result


def test_unreadable_files_skipped(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Files that fail to read don't crash the loader."""
    d = tmp_path / "exploration"
    d.mkdir()
    good = d / "good.md"
    good.write_text("# Good\n\nReal content here.\n", encoding="utf-8")
    # A binary file with invalid utf-8 in .md extension.
    bad = d / "bad.md"
    bad.write_bytes(b"\xff\xfe\x00invalid utf8")
    monkeypatch.setattr(el, "_exploration_dir", lambda: d)
    result = el.load_exploration_lessons(max_entries=5)
    assert "Good" in result  # readable file still surfaces


def test_baseline_text_includes_exploration_block(fake_exploration: Path) -> None:
    """LOAD-BEARING: build_baseline_text actually wires the loader in.

    If this fails, the loader exists but the per-turn baseline is not
    surfacing it — the whole point of the build is unwired.
    """
    from divineos.core.pre_response_context import build_baseline_text

    baseline = build_baseline_text()
    assert "EXPLORATION-LESSONS BASE-STATE" in baseline, (
        "exploration loader not wired into build_baseline_text — "
        "lessons recorded in exploration/ won't surface at composition time"
    )
    # The newest entry should appear in the loaded block.
    assert "39: River" in baseline or "over-corrected" in baseline


def test_guardrail_marker_present() -> None:
    src = Path(el.__file__).read_text(encoding="utf-8")
    assert "__guardrail_required__ = True" in src
