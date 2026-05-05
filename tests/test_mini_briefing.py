"""Tests for mini_briefing — compact session-entry surface.

Smoke tests covering the contracts the audit on PR #259 (2026-05-05)
flagged as needing coverage:

  * render_mini_briefing() returns non-empty output, even when DBs
    are empty (fail-empty per section, never fail-whole)
  * the output stays under the size budget (~3KB target)
  * the header / footer constants always appear
  * a section that raises silently fails-empty (BLE001 noqa contract)
"""

from __future__ import annotations

from divineos.core import mini_briefing


class TestRender:
    def test_returns_non_empty_string(self) -> None:
        out = mini_briefing.render_mini_briefing()
        assert isinstance(out, str)
        assert out.strip()

    def test_under_size_budget(self) -> None:
        """The mini briefing target is ~3KB; hard cap at 6KB to leave
        room for HUD --brief plus wrapper text and stay under the
        ~15KB additionalContext threshold."""
        out = mini_briefing.render_mini_briefing()
        assert len(out) < 6000, (
            f"mini briefing exceeded budget: {len(out)} bytes (budget: 6000; target: ~3000)"
        )

    def test_header_present(self) -> None:
        out = mini_briefing.render_mini_briefing()
        assert "Mini Briefing" in out

    def test_footer_present(self) -> None:
        out = mini_briefing.render_mini_briefing()
        assert "End mini briefing" in out

    def test_first_person_register(self) -> None:
        """The mini briefing must use first-person voice (I am Aether,
        my substrate). Catches accidental third-person drift."""
        out = mini_briefing.render_mini_briefing()
        assert "I am Aether" in out
        assert "my substrate" in out


class TestSafeCallIsolation:
    """The _safe_call wrapper has a documented BLE001 noqa: a single
    broken section must never crash the whole mini-briefing.

    Verify that when one section's data source raises, the rest of
    the briefing still renders.
    """

    def test_section_failure_does_not_crash_render(self, monkeypatch) -> None:
        def explode(*_args, **_kwargs):
            raise RuntimeError("simulated section failure")

        # Force one of the optional sections to raise on import-target.
        # The render must still return non-empty.
        import divineos.core.hud_state as hud_state

        monkeypatch.setattr(hud_state, "get_active_goals", explode)
        out = mini_briefing.render_mini_briefing()
        assert out.strip()
        # Header still present even when goals section raised.
        assert "Mini Briefing" in out


class TestSectionLoadoutPointer:
    """The mini briefing's inline LOADOUT.md presence check should
    surface different content for present vs missing cases.

    The audit (Finding 2) flagged this as the first instance of
    duplication with loadout_surface.is_present(). This test pins
    that the inline check at least behaves consistently with the
    described contract.
    """

    def test_present_vs_missing(self, monkeypatch, tmp_path) -> None:
        monkeypatch.chdir(tmp_path)
        # Missing case
        missing = "\n".join(mini_briefing._section_loadout_pointer())
        assert "not found" in missing.lower()
        # Present case
        (tmp_path / "LOADOUT.md").write_text("# Loadout\n", encoding="utf-8")
        present = "\n".join(mini_briefing._section_loadout_pointer())
        assert "not found" not in present.lower()
        assert "LOADOUT.md" in present
