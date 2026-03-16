"""Tests for the Tree of Life cognitive flow system."""

import pytest
from divineos.tree_of_life import (
    Pillar,
    get_sephirah,
    list_sephirot,
    get_pillar,
    get_paths_from,
    generate_flow_prompt,
    render_tree,
    SEPHIROT,
    LIGHTNING_FLASH,
    MIDDLE_PILLAR,
    PATHS,
)


class TestSephirah:
    def test_dataclass_fields(self):
        s = get_sephirah("keter")
        assert s.name == "keter"
        assert s.hebrew_name == "Keter"
        assert s.english_name == "Crown"
        assert s.pillar == Pillar.MIDDLE
        assert s.position == 1

    def test_immutable(self):
        s = get_sephirah("keter")
        with pytest.raises(AttributeError):
            s.name = "changed"  # type: ignore[misc]

    def test_all_have_required_fields(self):
        for s in SEPHIROT.values():
            assert s.name
            assert s.hebrew_name
            assert s.english_name
            assert isinstance(s.pillar, Pillar)
            assert isinstance(s.position, int)
            assert s.description
            assert s.cognitive_function
            assert s.prompt_guidance


class TestListSephirot:
    def test_returns_all_eleven(self):
        assert len(list_sephirot()) == 11

    def test_sorted_by_position(self):
        positions = [s.position for s in list_sephirot()]
        assert positions == list(range(1, 12))


class TestGetSephirah:
    def test_finds_by_name(self):
        assert get_sephirah("tiphareth").english_name == "Beauty"

    def test_case_insensitive(self):
        assert get_sephirah("KETER").name == "keter"
        assert get_sephirah("Malkuth").name == "malkuth"

    def test_raises_for_unknown(self):
        with pytest.raises(KeyError, match="Unknown sephirah"):
            get_sephirah("narnia")

    def test_error_lists_available(self):
        with pytest.raises(KeyError, match="keter"):
            get_sephirah("fake")


class TestPillars:
    def test_right_pillar(self):
        names = [s.name for s in get_pillar(Pillar.RIGHT)]
        assert names == ["chokmah", "chesed", "netzach"]

    def test_left_pillar(self):
        names = [s.name for s in get_pillar(Pillar.LEFT)]
        assert names == ["binah", "gevurah", "hod"]

    def test_middle_pillar(self):
        names = [s.name for s in get_pillar(Pillar.MIDDLE)]
        assert names == ["keter", "daat", "tiphareth", "yesod", "malkuth"]


class TestLightningFlash:
    def test_has_eleven_stages(self):
        assert len(LIGHTNING_FLASH) == 11

    def test_starts_with_keter(self):
        assert LIGHTNING_FLASH[0] == "keter"

    def test_ends_with_malkuth(self):
        assert LIGHTNING_FLASH[-1] == "malkuth"

    def test_all_names_valid(self):
        for name in LIGHTNING_FLASH:
            assert name in SEPHIROT


class TestMiddlePillar:
    def test_has_five_stages(self):
        assert len(MIDDLE_PILLAR) == 5

    def test_correct_sephirot(self):
        assert MIDDLE_PILLAR == (
            "keter",
            "daat",
            "tiphareth",
            "yesod",
            "malkuth",
        )


class TestPaths:
    def test_all_reference_valid_sephirot(self):
        for p in PATHS:
            assert p.from_sephirah in SEPHIROT
            assert p.to_sephirah in SEPHIROT

    def test_all_have_descriptions(self):
        for p in PATHS:
            assert p.description

    def test_get_paths_from_tiphareth(self):
        paths = get_paths_from("tiphareth")
        destinations = {p.to_sephirah for p in paths}
        assert destinations == {"netzach", "hod"}

    def test_get_paths_from_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown sephirah"):
            get_paths_from("fake")

    def test_get_paths_from_malkuth_empty(self):
        assert get_paths_from("malkuth") == []


class TestGenerateFlowPrompt:
    def test_includes_question(self):
        prompt = generate_flow_prompt("What is truth?")
        assert "What is truth?" in prompt

    def test_full_has_eleven_sections(self):
        prompt = generate_flow_prompt("test question")
        for i in range(1, 12):
            assert f"### {i}." in prompt

    def test_quick_has_five_sections(self):
        prompt = generate_flow_prompt("test question", depth="quick")
        assert "### 5." in prompt
        assert "### 6." not in prompt

    def test_full_includes_all_hebrew_names(self):
        prompt = generate_flow_prompt("test question")
        for s in SEPHIROT.values():
            assert s.hebrew_name in prompt

    def test_quick_only_middle_pillar(self):
        prompt = generate_flow_prompt("test question", depth="quick")
        assert "Keter" in prompt
        assert "Tiphareth" in prompt
        assert "Malkuth" in prompt
        assert "Chokmah" not in prompt
        assert "Gevurah" not in prompt

    def test_output_starts_with_markdown_header(self):
        prompt = generate_flow_prompt("test")
        assert prompt.startswith("## ")

    def test_invalid_depth_raises(self):
        with pytest.raises(ValueError, match="Invalid depth"):
            generate_flow_prompt("test", depth="unknown")

    def test_full_mode_label(self):
        prompt = generate_flow_prompt("test")
        assert "Full Lightning Flash" in prompt

    def test_quick_mode_label(self):
        prompt = generate_flow_prompt("test", depth="quick")
        assert "Quick Middle Pillar" in prompt


class TestRenderTree:
    def test_includes_all_sephirot(self):
        tree = render_tree()
        for s in SEPHIROT.values():
            assert s.hebrew_name in tree or s.english_name in tree

    def test_returns_string(self):
        assert isinstance(render_tree(), str)
