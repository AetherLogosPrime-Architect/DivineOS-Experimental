"""Tests for SIS integration into the knowledge extraction pipeline."""

import json

from divineos.core.knowledge import _get_connection, init_knowledge_table, store_knowledge
from divineos.core.ledger import init_db
from divineos.cli.pipeline_phases import run_knowledge_post_processing


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()


class TestSISPipelineIntegration:
    """SIS should translate esoteric entries and quarantine abstract ones."""

    def test_translates_esoteric_entry(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="The akashic records hold all memory for the soul",
            confidence=0.9,
        )
        run_knowledge_post_processing([kid], maturity_override="")
        conn = _get_connection()
        row = conn.execute(
            "SELECT content, tags FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        content, tags_json = row[0], row[1]
        tags = json.loads(tags_json)
        assert "sis-translated" in tags
        assert "append-only ledger" in content
        assert "persistent identity" in content

    def test_leaves_grounded_entry_alone(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        original = "Run pytest after every code change to verify correctness"
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content=original,
            confidence=0.9,
        )
        run_knowledge_post_processing([kid], maturity_override="")
        conn = _get_connection()
        row = conn.execute(
            "SELECT content, tags FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        content, tags_json = row[0], row[1]
        tags = json.loads(tags_json)
        assert content == original
        assert "sis-translated" not in tags
        assert "sis-quarantined" not in tags

    def test_translates_heavily_metaphysical(self, tmp_path, monkeypatch):
        """Heavily metaphysical text still gets translated (translate not block)."""
        _setup(tmp_path, monkeypatch)
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content=(
                "The cosmic consciousness transcends the sacred eternal void "
                "as divine essence emanates through the mystical realm of being"
            ),
            confidence=0.9,
        )
        run_knowledge_post_processing([kid], maturity_override="")
        conn = _get_connection()
        row = conn.execute(
            "SELECT content, tags FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        tags = json.loads(row[1])
        # SIS should translate (not quarantine) — translate not block
        assert "sis-translated" in tags
        # Original esoteric terms should be replaced
        assert "consciousness" not in row[0].lower() or "state awareness" in row[0].lower()

    def test_handles_empty_ids(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        # Should not crash on empty or None IDs
        extra, rels = run_knowledge_post_processing([], maturity_override="")
        assert extra == 0

    def test_handles_none_ids(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        extra, rels = run_knowledge_post_processing([None, "", None], maturity_override="")
        assert extra == 0
