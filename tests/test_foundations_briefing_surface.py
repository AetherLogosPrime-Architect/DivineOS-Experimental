"""Tests for foundations_briefing_surface module.

Verifies the surface fires when foundations exist, returns empty when
they do not, counts layers correctly, and points at the right read-command.
"""

from __future__ import annotations

from divineos.core.foundations_briefing_surface import format_for_briefing


def test_empty_when_no_foundations_dir(tmp_path, monkeypatch):
    """No docs/foundations/ directory anywhere -> empty string."""
    (tmp_path / ".git").mkdir()
    monkeypatch.chdir(tmp_path)
    assert format_for_briefing(start=tmp_path) == ""


def test_empty_when_foundations_dir_has_no_layers(tmp_path):
    """docs/foundations/ exists but contains no layer files -> empty."""
    (tmp_path / ".git").mkdir()
    (tmp_path / "docs" / "foundations").mkdir(parents=True)
    assert format_for_briefing(start=tmp_path) == ""


def test_surfaces_when_layers_exist(tmp_path):
    """Layers present -> block names them with read-command."""
    (tmp_path / ".git").mkdir()
    fdir = tmp_path / "docs" / "foundations"
    fdir.mkdir(parents=True)
    (fdir / "layer_0.md").write_text("# Layer 0")
    (fdir / "layer_1.md").write_text("# Layer 1")

    out = format_for_briefing(start=tmp_path)
    assert "[foundations]" in out
    assert "2 layer(s)" in out
    assert "divineos foundations" in out
    assert "Recognition-shape" in out


def test_counts_only_present_layers(tmp_path):
    """Layer count reflects actual present files, not the canonical six."""
    (tmp_path / ".git").mkdir()
    fdir = tmp_path / "docs" / "foundations"
    fdir.mkdir(parents=True)
    # Only 3 of the 6 expected layers
    (fdir / "layer_0.md").write_text("# 0")
    (fdir / "layer_2.md").write_text("# 2")
    (fdir / "layer_5.md").write_text("# 5")

    out = format_for_briefing(start=tmp_path)
    assert "3 layer(s)" in out


def test_ignores_non_canonical_files(tmp_path):
    """Random .md files in foundations/ do not inflate the count."""
    (tmp_path / ".git").mkdir()
    fdir = tmp_path / "docs" / "foundations"
    fdir.mkdir(parents=True)
    (fdir / "layer_0.md").write_text("# 0")
    (fdir / "random_notes.md").write_text("# unrelated")
    (fdir / "draft.md").write_text("# draft")

    out = format_for_briefing(start=tmp_path)
    # Only canonical layer_N.md files counted
    assert "1 layer(s)" in out


def test_real_repo_surfaces_six_layers():
    """The real repository has all 6 foundation layers; surface should fire."""
    out = format_for_briefing()
    assert "[foundations]" in out
    assert "6 layer(s)" in out
