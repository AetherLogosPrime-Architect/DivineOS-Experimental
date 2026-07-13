"""Tests for ablation_summary briefing surface."""

from __future__ import annotations

from pathlib import Path

from divineos.core.ablation_summary import (
    _count_priority_mechanisms,
    format_for_briefing,
)

NL = chr(10)


def _build_catalog(*sections: str) -> str:
    return NL.join(sections) + NL


CATALOG_3_PRIORITY = _build_catalog(
    "# Catalog",
    "",
    "## Priority mechanisms (full entries)",
    "",
    "### 1. mech_a",
    "content",
    "### 2. mech_b",
    "### 3. mech_c",
    "",
    "## Stub entries",
    "### 4. mech_d",
)

CATALOG_NO_PRIORITY = _build_catalog(
    "# Catalog",
    "## Stub entries",
    "### 1. mech_a",
)

CATALOG_EMPTY_PRIORITY = _build_catalog(
    "# Catalog",
    "## Priority mechanisms (full entries)",
    "## Stub entries",
    "### 1. mech_a",
)


class TestCatalogParsing:
    def test_count_priority_mechanisms_basic(self):
        assert _count_priority_mechanisms(CATALOG_3_PRIORITY) == 3

    def test_count_zero_when_no_priority_section(self):
        assert _count_priority_mechanisms(CATALOG_NO_PRIORITY) == 0

    def test_count_zero_when_priority_empty(self):
        assert _count_priority_mechanisms(CATALOG_EMPTY_PRIORITY) == 0


def _setup_repo_with_catalog(tmp_path: Path, content: str) -> None:
    (tmp_path / ".git").mkdir(exist_ok=True)
    (tmp_path / "docs").mkdir(exist_ok=True)
    (tmp_path / "docs" / "mechanism-claims.md").write_text(content, encoding="utf-8")


class TestSurface:
    def test_returns_empty_when_no_catalog(self, tmp_path):
        (tmp_path / ".git").mkdir()
        out = format_for_briefing(start=tmp_path)
        assert out == ""

    def test_returns_block_when_catalog_present(self, tmp_path):
        _setup_repo_with_catalog(tmp_path, CATALOG_3_PRIORITY)
        out = format_for_briefing(start=tmp_path)
        assert "[ablation evidence]" in out
        assert "of 3 priority mechanisms" in out

    def test_block_mentions_runner_command(self, tmp_path):
        _setup_repo_with_catalog(tmp_path, CATALOG_3_PRIORITY)
        out = format_for_briefing(start=tmp_path)
        assert "scripts/ablation_runner.py" in out

    def test_block_references_brief_and_finding(self, tmp_path):
        _setup_repo_with_catalog(tmp_path, CATALOG_3_PRIORITY)
        out = format_for_briefing(start=tmp_path)
        assert "prereg-8af86ea36827" in out
        assert "find-07e9f041c051" in out
