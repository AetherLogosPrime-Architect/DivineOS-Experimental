"""Tests for Observational Compression — merge redundant knowledge."""

from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.knowledge.compression import (
    compress_dedup,
    compress_graph_cluster,
    find_dedup_candidates,
    find_synthesis_candidates,
    format_compression_report,
    run_compression,
    synthesize_cluster,
    _extract_unique_terms,
    _maturity_score,
    _pick_best_entry,
)
from divineos.core.knowledge.crud import store_knowledge


def _setup_db(monkeypatch, tmp_path):
    """Set up a test database."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_knowledge_table()
    return db_path


class TestMaturityScoring:
    """Maturity-aware entry ranking."""

    def test_confirmed_ranks_highest(self):
        assert _maturity_score({"maturity": "CONFIRMED"}) == 4

    def test_raw_ranks_lowest(self):
        assert _maturity_score({"maturity": "RAW"}) == 1

    def test_unknown_defaults_to_raw(self):
        assert _maturity_score({}) == 1

    def test_pick_best_prefers_maturity(self):
        entries = [
            {
                "knowledge_id": "a",
                "maturity": "RAW",
                "confidence": 0.9,
                "access_count": 10,
                "content": "long " * 50,
            },
            {
                "knowledge_id": "b",
                "maturity": "CONFIRMED",
                "confidence": 0.5,
                "access_count": 1,
                "content": "short",
            },
        ]
        best = _pick_best_entry(entries)
        assert best["knowledge_id"] == "b"

    def test_pick_best_breaks_tie_with_confidence(self):
        entries = [
            {
                "knowledge_id": "a",
                "maturity": "TESTED",
                "confidence": 0.6,
                "access_count": 0,
                "content": "x",
            },
            {
                "knowledge_id": "b",
                "maturity": "TESTED",
                "confidence": 0.9,
                "access_count": 0,
                "content": "x",
            },
        ]
        best = _pick_best_entry(entries)
        assert best["knowledge_id"] == "b"


class TestUniqueTerms:
    """Extract what each entry contributes that others don't."""

    def test_finds_unique_words(self):
        entry = {"content": "The database uses connection pooling for performance"}
        others = [{"content": "The database handles queries efficiently"}]
        unique = _extract_unique_terms(entry, others)
        assert "pooling" in unique
        assert "connection" in unique

    def test_common_words_excluded(self):
        entry = {"content": "The system processes data quickly"}
        others = [{"content": "The system handles data well"}]
        unique = _extract_unique_terms(entry, others)
        assert "processes" in unique
        assert "quickly" in unique
        assert "data" not in unique


class TestDedupCompression:
    """Near-identical entries get deduplicated."""

    def test_finds_near_identical(self, tmp_path, monkeypatch):
        _setup_db(monkeypatch, tmp_path)
        store_knowledge("OBSERVATION", "The system uses SQLite for all data storage needs", 0.8)
        store_knowledge(
            "OBSERVATION", "The system uses SQLite for all data storage requirements", 0.6
        )
        candidates = find_dedup_candidates("OBSERVATION", overlap_threshold=0.7)
        assert len(candidates) >= 1
        assert len(candidates[0]) == 2

    def test_compress_keeps_best(self, tmp_path, monkeypatch):
        _setup_db(monkeypatch, tmp_path)
        store_knowledge("OBSERVATION", "The ledger is append-only and never deletes data", 0.9)
        store_knowledge("OBSERVATION", "The ledger is append-only and never deletes entries", 0.5)
        actions = compress_dedup("OBSERVATION", overlap_threshold=0.7)
        assert len(actions) >= 1
        assert actions[0]["action"] == "dedup"
        assert actions[0]["count"] >= 1

    def test_no_dedup_for_different_entries(self, tmp_path, monkeypatch):
        _setup_db(monkeypatch, tmp_path)
        store_knowledge("OBSERVATION", "The weather is sunny today", 0.8)
        store_knowledge("OBSERVATION", "The database schema has twelve columns", 0.8)
        candidates = find_dedup_candidates("OBSERVATION", overlap_threshold=0.7)
        assert len(candidates) == 0


class TestSynthesisCompression:
    """Related-but-distinct entries get synthesized."""

    def test_finds_synthesis_candidates(self, tmp_path, monkeypatch):
        _setup_db(monkeypatch, tmp_path)
        store_knowledge(
            "PRINCIPLE", "Tests should exercise real code paths not mock internals", 0.8
        )
        store_knowledge(
            "PRINCIPLE", "Tests should verify real behavior not mock the system under test", 0.7
        )
        store_knowledge(
            "PRINCIPLE", "Tests must exercise actual code paths and verify real output", 0.9
        )
        candidates = find_synthesis_candidates("PRINCIPLE", min_cluster=3)
        assert isinstance(candidates, list)

    def test_synthesize_cluster_produces_denser_entry(self):
        cluster = [
            {
                "knowledge_id": "a",
                "content": "The knowledge store uses SQLite with full-text search for retrieval",
                "maturity": "CONFIRMED",
                "confidence": 0.9,
                "access_count": 5,
                "knowledge_type": "OBSERVATION",
                "source_events": ["ev1"],
                "tags": ["db"],
            },
            {
                "knowledge_id": "b",
                "content": "The knowledge store indexes entries with BM25 ranking algorithm",
                "maturity": "TESTED",
                "confidence": 0.7,
                "access_count": 2,
                "knowledge_type": "OBSERVATION",
                "source_events": ["ev2"],
                "tags": ["search"],
            },
            {
                "knowledge_id": "c",
                "content": "The knowledge store deduplicates via content hashing before insert",
                "maturity": "RAW",
                "confidence": 0.6,
                "access_count": 1,
                "knowledge_type": "OBSERVATION",
                "source_events": ["ev3"],
                "tags": ["dedup"],
            },
        ]
        result = synthesize_cluster(cluster)
        assert result["knowledge_type"] == "OBSERVATION"
        assert result["confidence"] == 0.9
        assert "compressed" in result["tags"]
        assert len(result["source_entries"]) == 3

    def test_synthesize_preserves_best_maturity(self):
        cluster = [
            {
                "knowledge_id": "a",
                "content": "First observation about testing patterns in codebase",
                "maturity": "RAW",
                "confidence": 0.5,
                "access_count": 0,
                "knowledge_type": "OBSERVATION",
                "source_events": [],
                "tags": [],
            },
            {
                "knowledge_id": "b",
                "content": "Second observation about testing patterns and coverage metrics",
                "maturity": "CONFIRMED",
                "confidence": 0.9,
                "access_count": 10,
                "knowledge_type": "OBSERVATION",
                "source_events": [],
                "tags": [],
            },
            {
                "knowledge_id": "c",
                "content": "Third observation about testing patterns and quality gates",
                "maturity": "TESTED",
                "confidence": 0.7,
                "access_count": 3,
                "knowledge_type": "OBSERVATION",
                "source_events": [],
                "tags": [],
            },
        ]
        result = synthesize_cluster(cluster)
        assert result["maturity"] == "CONFIRMED"


class TestGraphCompression:
    """Entries connected by edges get compressed."""

    def test_compress_graph_cluster(self):
        cluster = {
            "target": {
                "knowledge_id": "principle1",
                "content": "Append-only data stores are more trustworthy than mutable ones",
                "knowledge_type": "PRINCIPLE",
                "confidence": 0.95,
                "maturity": "CONFIRMED",
                "source_events": ["ev1"],
                "tags": ["architecture"],
            },
            "supports": [
                {
                    "knowledge_id": "obs1",
                    "content": "The ledger never deletes events, only appends new ones",
                    "maturity": "TESTED",
                    "tags": [],
                },
                {
                    "knowledge_id": "obs2",
                    "content": "Knowledge supersession marks old entries instead of deleting them",
                    "maturity": "CONFIRMED",
                    "tags": [],
                },
            ],
            "edge_count": 2,
        }
        result = compress_graph_cluster(cluster)
        assert result is not None
        assert "Evidence:" in result["content"]
        assert "graph-compressed" in result["tags"]
        assert len(result["support_ids"]) == 2

    def test_compress_empty_supports_returns_none(self):
        cluster = {
            "target": {
                "knowledge_id": "x",
                "content": "something",
                "knowledge_type": "PRINCIPLE",
                "confidence": 0.5,
                "source_events": [],
                "tags": [],
            },
            "supports": [],
            "edge_count": 0,
        }
        result = compress_graph_cluster(cluster)
        assert result is None

    def test_long_evidence_gets_truncated(self):
        cluster = {
            "target": {
                "knowledge_id": "p1",
                "content": "Short principle",
                "knowledge_type": "PRINCIPLE",
                "confidence": 0.8,
                "source_events": [],
                "tags": [],
            },
            "supports": [
                {"knowledge_id": f"s{i}", "content": "A" * 200, "maturity": "RAW", "tags": []}
                for i in range(5)
            ],
            "edge_count": 5,
        }
        result = compress_graph_cluster(cluster)
        assert result is not None
        assert "..." in result["content"]


class TestCompressionPipeline:
    """Full pipeline runs all strategies."""

    def test_empty_store(self, tmp_path, monkeypatch):
        _setup_db(monkeypatch, tmp_path)
        results = run_compression()
        assert results["total_compressed"] == 0

    def test_selective_strategies(self, tmp_path, monkeypatch):
        _setup_db(monkeypatch, tmp_path)
        results = run_compression(strategies=["dedup"])
        assert "dedup" in results
        assert results["synthesize"] == []
        assert results["graph"] == []


class TestFormatReport:
    """Compression report formatting."""

    def test_empty_report(self):
        results = {"total_compressed": 0, "dedup": [], "synthesize": [], "graph": []}
        output = format_compression_report(results)
        assert "already dense" in output

    def test_dedup_report(self):
        results = {
            "total_compressed": 3,
            "dedup": [{"action": "dedup", "kept_content": "Best entry", "count": 3}],
            "synthesize": [],
            "graph": [],
        }
        output = format_compression_report(results)
        assert "Compressed 3 entries" in output
        assert "Dedup" in output

    def test_mixed_report(self):
        results = {
            "total_compressed": 8,
            "dedup": [{"action": "dedup", "kept_content": "Kept", "count": 2}],
            "synthesize": [{"action": "synthesize", "source_count": 3, "content_preview": "Synth"}],
            "graph": [{"action": "graph_compress", "support_count": 3, "content_preview": "Graph"}],
        }
        output = format_compression_report(results)
        assert "Compressed 8 entries" in output
        assert "Dedup" in output
        assert "Synthesized" in output
        assert "Graph-compressed" in output
