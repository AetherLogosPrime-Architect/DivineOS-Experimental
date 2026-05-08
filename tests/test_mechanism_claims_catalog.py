"""Tests for the mechanism-claims catalog at docs/mechanism-claims.md.

Verifies the catalog has the expected structure: 5 priority full entries,
5 stubs, an always-on section, and a discipline-connection section.
Catches regressions where someone adds a malformed entry or removes a
required field.
"""

from __future__ import annotations

from pathlib import Path

CATALOG = Path(__file__).parent.parent / "docs" / "mechanism-claims.md"


def test_catalog_exists():
    assert CATALOG.is_file(), f"catalog missing at {CATALOG}"


def test_catalog_has_priority_section():
    text = CATALOG.read_text(encoding="utf-8")
    assert "## Priority mechanisms (full entries)" in text


def test_catalog_has_stub_section():
    text = CATALOG.read_text(encoding="utf-8")
    assert "## Stub entries" in text


def test_catalog_has_always_on_section():
    text = CATALOG.read_text(encoding="utf-8")
    assert "## Always-on" in text


def test_priority_full_entries_present():
    """All 5 priority mechanisms should be present as full entries."""
    text = CATALOG.read_text(encoding="utf-8")
    expected = [
        "noise_filter_on_extraction",
        "compass_calibration_multi_channel_guard",
        "family_voice_appropriation_operators",
        "sleep_consolidation_pruning",
        "watchmen_self_trigger_prevention",
    ]
    for name in expected:
        assert "### " in text and name in text, f"missing priority entry: {name}"


def test_priority_entries_have_required_fields():
    """Each priority full entry must have Source, Claim, Outcome-metric, Toggle path, Status fields."""
    text = CATALOG.read_text(encoding="utf-8")
    # Take just the priority section for this check
    start = text.index("## Priority mechanisms")
    end = text.index("## Stub entries")
    priority = text[start:end]

    for field in [
        "**Source:**",
        "**Claim:**",
        "**Outcome-metric:**",
        "**Toggle path:**",
        "**Status:**",
    ]:
        # Each field should appear at least 5 times (once per priority entry)
        count = priority.count(field)
        assert count >= 5, f"field {field} appears {count}x in priority section; expected >=5"


def test_stubs_have_status_line():
    """Each stub should be marked status: stub explicitly."""
    text = CATALOG.read_text(encoding="utf-8")
    start = text.index("## Stub entries")
    end = text.index("## Always-on")
    stubs = text[start:end]
    # Each stub has Status: stub
    assert stubs.count("**Status:** stub") >= 5


def test_links_to_design_brief_and_findings():
    """Catalog should reference the design brief and the substrate-credibility finding."""
    text = CATALOG.read_text(encoding="utf-8")
    assert "per-mechanism-ablation-design-brief.md" in text
    assert "prereg-8af86ea36827" in text
    assert "find-07e9f041c051" in text


def test_toggle_convention_documented():
    """The DIVINEOS_DISABLE_ env var convention should be documented."""
    text = CATALOG.read_text(encoding="utf-8")
    assert "DIVINEOS_DISABLE_" in text


def test_chunk_progression_named():
    """The catalog should reference chunks 2 and 3 as forward work."""
    text = CATALOG.read_text(encoding="utf-8")
    assert "chunk 2" in text.lower()
    assert "chunk 3" in text.lower()
