"""Tests for the source_entity (namespace) filter on knowledge queries.

Per prereg-902656c818d4 (Curator-borrowing: namespacing). The schema already
carries source_entity; this verifies the filter actually narrows by it without
breaking unfiltered queries.
"""

from __future__ import annotations

import pytest

from divineos.core.knowledge.crud import (
    get_knowledge,
    search_knowledge,
    store_knowledge,
)


@pytest.fixture(autouse=True)
def _setup_knowledge_table() -> None:
    from divineos.core.knowledge import init_knowledge_table

    init_knowledge_table()


def _file_with_source(content: str, source_entity: str) -> str:
    """Helper to file a knowledge entry with a specific source_entity."""
    kid = store_knowledge(
        content=content,
        knowledge_type="FACT",
        confidence=0.8,
        source="STATED",
        source_entity=source_entity,
    )
    return kid


class TestNamespaceFilter:
    def test_get_knowledge_filters_by_source_entity(self) -> None:
        _file_with_source("Namespace test alpha — from-alpha-source", "alpha-test-source")
        _file_with_source("Namespace test beta — from-beta-source", "beta-test-source")

        alpha = get_knowledge(source_entity="alpha-test-source", limit=20)
        beta = get_knowledge(source_entity="beta-test-source", limit=20)

        assert any("alpha" in (e.get("content") or "").lower() for e in alpha)
        assert all(e.get("source_entity") == "alpha-test-source" for e in alpha)
        assert any("beta" in (e.get("content") or "").lower() for e in beta)
        assert all(e.get("source_entity") == "beta-test-source" for e in beta)

    def test_get_knowledge_without_filter_returns_all_sources(self) -> None:
        _file_with_source("Mixed entry gamma1 — gamma-source", "gamma-test-source")
        _file_with_source("Mixed entry delta1 — delta-source", "delta-test-source")
        results = get_knowledge(limit=10000)
        sources = {e.get("source_entity") for e in results if e.get("source_entity")}
        assert "gamma-test-source" in sources
        assert "delta-test-source" in sources

    def test_search_knowledge_filters_by_source_entity(self) -> None:
        _file_with_source("uniquesearchtoken from delta source", "delta-test-source")
        _file_with_source("uniquesearchtoken from epsilon source", "epsilon-test-source")

        delta = search_knowledge("uniquesearchtoken", source_entity="delta-test-source", limit=20)
        assert all(e.get("source_entity") == "delta-test-source" for e in delta)
        assert any("delta" in (e.get("content") or "").lower() for e in delta)

    def test_namespace_filter_with_no_matches_returns_empty(self) -> None:
        results = search_knowledge(
            "uniquesearchtoken", source_entity="nonexistent-source-9999", limit=10
        )
        assert results == []
