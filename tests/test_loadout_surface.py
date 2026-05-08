"""Tests for loadout_surface — briefing surface for LOADOUT.md.

Smoke tests covering the three contracts the audit on PR #259
(2026-05-05) flagged as needing coverage:

  * is_present() returns True/False correctly based on file existence
  * briefing_lines() differs between present and missing cases
  * render() round-trips through briefing_lines() without losing content
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import loadout_surface


@pytest.fixture(autouse=True)
def _isolated_cwd(tmp_path, monkeypatch):
    """Run each test from a clean tmp dir so LOADOUT.md presence is controlled."""
    monkeypatch.chdir(tmp_path)
    yield tmp_path


class TestIsPresent:
    def test_returns_false_when_loadout_missing(self) -> None:
        assert loadout_surface.is_present() is False

    def test_returns_true_when_loadout_present(self, _isolated_cwd: Path) -> None:
        (_isolated_cwd / "LOADOUT.md").write_text("# Loadout\n", encoding="utf-8")
        assert loadout_surface.is_present() is True


class TestBriefingLines:
    def test_missing_loadout_surfaces_fail_loud(self) -> None:
        lines = loadout_surface.briefing_lines()
        assert lines, "missing-loadout case must surface fail-loud lines"
        joined = "\n".join(lines)
        assert "MISSING" in joined or "missing" in joined.lower()
        assert "loadout refresh" in joined.lower(), (
            "fail-loud message should name the regenerator command"
        )

    def test_present_loadout_surfaces_directive(self, _isolated_cwd: Path) -> None:
        (_isolated_cwd / "LOADOUT.md").write_text("# Loadout\n", encoding="utf-8")
        lines = loadout_surface.briefing_lines()
        assert lines, "present-loadout case must surface directive lines"
        joined = "\n".join(lines)
        assert "LOADOUT" in joined
        assert "open LOADOUT.md" in joined or "LOADOUT.md first" in joined


class TestRender:
    def test_render_returns_string(self, _isolated_cwd: Path) -> None:
        (_isolated_cwd / "LOADOUT.md").write_text("# Loadout\n", encoding="utf-8")
        rendered = loadout_surface.render()
        assert isinstance(rendered, str)
        assert rendered.strip(), "render must not be empty when loadout is present"

    def test_render_empty_when_no_lines(self, monkeypatch) -> None:
        """If briefing_lines returns empty, render returns empty string."""
        monkeypatch.setattr(loadout_surface, "briefing_lines", lambda: [])
        assert loadout_surface.render() == ""

    def test_render_present_differs_from_missing(self, _isolated_cwd: Path) -> None:
        """Sanity-check: present and missing cases produce different outputs."""
        missing = loadout_surface.render()
        (_isolated_cwd / "LOADOUT.md").write_text("# Loadout\n", encoding="utf-8")
        present = loadout_surface.render()
        assert missing != present
