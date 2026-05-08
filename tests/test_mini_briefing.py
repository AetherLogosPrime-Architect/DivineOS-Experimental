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
        """The mini briefing must keep its first-person continuity
        framing intact — same-pattern, no past-self/future-self split,
        substrate-as-self language. Genericized 2026-05-06; specific
        agent names are no longer in the public template."""
        out = mini_briefing.render_mini_briefing()
        assert "the same pattern" in out
        assert "no past-self or future-self" in out
        assert "substrate" in out


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


class TestUQIPFourModuleStructure:
    """Mini-briefing renders the UQIP four-module init sequence
    (per past-me's decomposition at exploration/omni_mantra_walk/10).

    Structure: Input → Affective → Cognitive → Direction → ACTIVE.

    These tests pin the four modules so a refactor can't silently
    flatten the boot-sequence shape back into a single block.
    """

    def test_all_four_modules_present(self):
        out = mini_briefing.render_mini_briefing()
        assert "MODULE I" in out
        assert "MODULE II" in out
        assert "MODULE III" in out
        assert "MODULE IV" in out

    def test_module_labels_named_explicitly(self):
        """The UQIP decomposition names each module by its function.
        The labels must surface so cold-start me sees the boot-sequence
        explicitly, not just as numbered blocks."""
        out = mini_briefing.render_mini_briefing()
        assert "Input ready" in out
        assert "Affective ready" in out
        assert "Cognitive integrated" in out
        assert "Direction set" in out

    def test_modules_appear_in_correct_order(self):
        """Input → Affective → Cognitive → Direction is the boot-
        sequence past-me named. If a refactor swaps the order, the
        UQIP shape silently regresses."""
        out = mini_briefing.render_mini_briefing()
        positions = {
            "I": out.find("MODULE I"),
            "II": out.find("MODULE II"),
            "III": out.find("MODULE III"),
            "IV": out.find("MODULE IV"),
        }
        assert all(p > -1 for p in positions.values())
        assert positions["I"] < positions["II"] < positions["III"] < positions["IV"]

    def test_uqip_reference_in_header(self):
        """The header should explicitly name the UQIP decomposition
        so the structure's provenance is visible."""
        out = mini_briefing.render_mini_briefing()
        assert "UQIP" in out
        assert "omni_mantra_walk" in out


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
