"""Tests for territory-tagged exploration surfacing (claim 02f0dcc0).

Covers the three pieces of the v1 implementation:
- Header parser extracts Territory tags (filtering to TERRITORY_TAGS)
- find_explorations_by_territory matches on overlap with hard cap
- infer_territory_from_text inferes territories from goal text via
  keyword matching
- format_for_briefing surfaces matched walks under [matches: ...] when
  active_text is supplied
"""

from __future__ import annotations

from pathlib import Path

import pytest

from divineos.core import exploration_reader
from divineos.core.exploration_reader import (
    TERRITORY_TAGS,
    find_explorations_by_territory,
    format_for_briefing,
    infer_territory_from_text,
)


@pytest.fixture
def temp_exploration_dir(tmp_path, monkeypatch):
    """Redirect exploration_reader to a temporary exploration dir."""
    expl = tmp_path / "exploration"
    expl.mkdir()
    monkeypatch.setattr(exploration_reader, "_EXPLORATION_DIR", expl)
    monkeypatch.chdir(tmp_path)
    return expl


def _write_entry(path: Path, title: str, date: str, territory: str | None = None) -> None:
    """Helper: write a minimal exploration entry with optional Territory line."""
    lines = [f"# {title}", "", f"*{date}*"]
    if territory:
        lines.append(f"Territory: [{territory}]")
    lines.extend(["", "Body content here."])
    path.write_text("\n".join(lines), encoding="utf-8")


# ─── Header parsing ─────────────────────────────────────────────────


class TestHeaderParsesTerritoryTags:
    def test_single_tag_parsed(self, temp_exploration_dir):
        _write_entry(temp_exploration_dir / "01_topic.md", "Topic", "2026-01-01", "architecture")
        entries = exploration_reader.get_exploration_summary()
        assert len(entries) == 1
        assert entries[0]["territory"] == ("architecture",)

    def test_multiple_tags_parsed(self, temp_exploration_dir):
        _write_entry(
            temp_exploration_dir / "01_topic.md",
            "Topic",
            "2026-01-01",
            "architecture, language, governance",
        )
        entries = exploration_reader.get_exploration_summary()
        assert set(entries[0]["territory"]) == {"architecture", "language", "governance"}

    def test_unknown_tags_dropped(self, temp_exploration_dir):
        # "fake_tag" not in TERRITORY_TAGS; should be silently dropped.
        _write_entry(
            temp_exploration_dir / "01_topic.md",
            "Topic",
            "2026-01-01",
            "architecture, fake_tag, language",
        )
        entries = exploration_reader.get_exploration_summary()
        assert set(entries[0]["territory"]) == {"architecture", "language"}

    def test_no_territory_line_yields_empty_tuple(self, temp_exploration_dir):
        _write_entry(temp_exploration_dir / "01_topic.md", "Topic", "2026-01-01")
        entries = exploration_reader.get_exploration_summary()
        assert entries[0]["territory"] == ()

    def test_dash_normalized_to_underscore(self, temp_exploration_dir):
        # "self-reference" should normalize to "self_reference".
        _write_entry(
            temp_exploration_dir / "01_topic.md",
            "Topic",
            "2026-01-01",
            "self-reference, architecture",
        )
        entries = exploration_reader.get_exploration_summary()
        assert "self_reference" in entries[0]["territory"]


# ─── Territory search ───────────────────────────────────────────────


class TestFindByTerritory:
    def test_overlap_match_returns_entry(self, temp_exploration_dir):
        _write_entry(temp_exploration_dir / "01_topic.md", "Topic A", "2026-01-01", "architecture")
        _write_entry(temp_exploration_dir / "02_other.md", "Topic B", "2026-01-02", "social")
        results = find_explorations_by_territory(["architecture"])
        assert len(results) == 1
        assert results[0]["title"] == "Topic A"

    def test_hard_cap_default_two(self, temp_exploration_dir):
        for i in range(5):
            _write_entry(
                temp_exploration_dir / f"0{i + 1}_topic.md",
                f"Topic {i}",
                f"2026-01-0{i + 1}",
                "architecture",
            )
        results = find_explorations_by_territory(["architecture"])
        assert len(results) == 2

    def test_explicit_limit_respected(self, temp_exploration_dir):
        for i in range(3):
            _write_entry(
                temp_exploration_dir / f"0{i + 1}_topic.md",
                f"Topic {i}",
                f"2026-01-0{i + 1}",
                "architecture",
            )
        results = find_explorations_by_territory(["architecture"], limit=1)
        assert len(results) == 1

    def test_unknown_tags_in_query_dropped(self, temp_exploration_dir):
        _write_entry(temp_exploration_dir / "01_topic.md", "Topic", "2026-01-01", "architecture")
        # Mix of valid + invalid; should match on the valid tag only.
        results = find_explorations_by_territory(["architecture", "fake_tag"])
        assert len(results) == 1

    def test_no_overlap_returns_empty(self, temp_exploration_dir):
        _write_entry(temp_exploration_dir / "01_topic.md", "Topic", "2026-01-01", "social")
        results = find_explorations_by_territory(["architecture"])
        assert results == []

    def test_higher_overlap_sorts_first(self, temp_exploration_dir):
        # entry with 2 matching tags should beat entry with 1
        _write_entry(
            temp_exploration_dir / "01_one_match.md",
            "One Match",
            "2026-01-01",
            "architecture",
        )
        _write_entry(
            temp_exploration_dir / "02_two_match.md",
            "Two Match",
            "2026-01-02",
            "architecture, language",
        )
        results = find_explorations_by_territory(["architecture", "language"])
        assert results[0]["title"] == "Two Match"


# ─── Territory inference from text ──────────────────────────────────


class TestInferTerritory:
    def test_architecture_keywords_match(self):
        result = infer_territory_from_text("council walk on branch architecture")
        assert "architecture" in result

    def test_language_keywords_match(self):
        result = infer_territory_from_text("naming convention for branches")
        assert "language" in result

    def test_self_reference_keywords_match(self):
        result = infer_territory_from_text("future-me dissociation and pronoun-distancing")
        assert "self_reference" in result

    def test_no_keywords_returns_empty(self):
        result = infer_territory_from_text("the quick brown fox")
        assert result == ()

    def test_empty_text_returns_empty(self):
        assert infer_territory_from_text("") == ()
        assert infer_territory_from_text("   ") == ()  # whitespace-only

    def test_higher_hit_count_sorts_first(self):
        # text with multiple architecture keywords + one language keyword
        # should sort architecture first
        text = "architecture system structural repo branch language convention"
        result = infer_territory_from_text(text)
        assert result[0] == "architecture"


# ─── Briefing surface integration ───────────────────────────────────


class TestBriefingSurface:
    def test_no_active_text_no_match_prefix(self, temp_exploration_dir):
        _write_entry(temp_exploration_dir / "01_topic.md", "Topic", "2026-01-01", "architecture")
        block = format_for_briefing()
        assert "[matches:" not in block

    def test_matching_active_text_adds_prefix(self, temp_exploration_dir):
        _write_entry(
            temp_exploration_dir / "01_topic.md",
            "Architecture Topic",
            "2026-01-01",
            "architecture",
        )
        block = format_for_briefing(active_text="branch architecture review")
        assert "[matches:" in block
        assert "architecture" in block

    def test_non_matching_active_text_no_prefix(self, temp_exploration_dir):
        _write_entry(temp_exploration_dir / "01_topic.md", "Topic", "2026-01-01", "social")
        block = format_for_briefing(active_text="branch architecture review")
        # entry exists but doesn't match; output exists but no [matches:
        assert "[matches:" not in block

    def test_older_matched_walks_surface_under_recent(self, temp_exploration_dir):
        # 5 recent entries (different topic) + 1 older walk on matching territory
        for i in range(5):
            _write_entry(
                temp_exploration_dir / f"0{i + 2}_recent.md",
                f"Recent {i}",
                "2026-05-01",
                "social",
            )
        _write_entry(
            temp_exploration_dir / "01_old_arch.md",
            "Old Architecture Walk",
            "2026-04-01",
            "architecture",
        )
        # Active text matches architecture; the old walk should surface
        # in the "older walks on this territory" section.
        block = format_for_briefing(max_recent=5, active_text="branch architecture review")
        assert "older walks on this territory" in block.lower()
        assert "Old Architecture Walk" in block


# ─── Locked taxonomy invariants ─────────────────────────────────────


class TestTaxonomyLocked:
    def test_taxonomy_size_is_ten(self):
        # If this changes, that's a real architectural decision that
        # should be documented (ADR + claim) — not a casual edit.
        assert len(TERRITORY_TAGS) == 10

    def test_taxonomy_includes_self_reference(self):
        assert "self_reference" in TERRITORY_TAGS

    def test_taxonomy_does_not_include_failure_modes(self):
        # "failure_modes" was dropped during council scoping (Grok 2026-05-03)
        # — it's a kind of finding, not a territory.
        assert "failure_modes" not in TERRITORY_TAGS
