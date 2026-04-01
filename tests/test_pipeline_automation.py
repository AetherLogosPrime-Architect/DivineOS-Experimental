"""Tests for pipeline automation: auto-distill, auto-warrant, auto-context briefing."""

from divineos.core.knowledge import _get_connection, init_knowledge_table, store_knowledge
from divineos.core.ledger import init_db


def _setup(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    init_db()
    init_knowledge_table()


class TestAutoDistill:
    """Phase 5e: raw entries with prefixes get auto-distilled."""

    def test_distills_correction_prefix(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="I was corrected: dont use mocks in tests.. we got burned last time lol",
            confidence=0.9,
        )
        from divineos.cli.pipeline_phases import run_knowledge_quality_cycle

        # Need a minimal analysis object
        class FakeAnalysis:
            session_id = "test-session-123"
            corrections = []
            encouragements = []
            context_overflows = []
            tool_calls_total = 10
            user_messages = 5

        run_knowledge_quality_cycle([kid], FakeAnalysis())
        conn = _get_connection()
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        content = row[0]
        # Should have stripped the "I was corrected:" prefix
        assert not content.startswith("I was corrected:")
        # Should have cleaned casual markers
        assert "lol" not in content.lower()

    def test_distills_should_prefix(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        kid = store_knowledge(
            knowledge_type="DIRECTION",
            content="I should: please make sure to always read files before editing them",
            confidence=0.9,
        )
        from divineos.cli.pipeline_phases import run_knowledge_quality_cycle

        class FakeAnalysis:
            session_id = "test-session-456"
            corrections = []
            encouragements = []
            context_overflows = []
            tool_calls_total = 10
            user_messages = 5

        run_knowledge_quality_cycle([kid], FakeAnalysis())
        conn = _get_connection()
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        content = row[0]
        assert not content.startswith("I should:")

    def test_leaves_clean_entries_alone(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        original = "Always run tests after code changes."
        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content=original,
            confidence=0.9,
        )
        from divineos.cli.pipeline_phases import run_knowledge_quality_cycle

        class FakeAnalysis:
            session_id = "test-session-789"
            corrections = []
            encouragements = []
            context_overflows = []
            tool_calls_total = 10
            user_messages = 5

        run_knowledge_quality_cycle([kid], FakeAnalysis())
        conn = _get_connection()
        row = conn.execute(
            "SELECT content FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn.close()
        assert row[0] == original


class TestAutoWarrantBackfill:
    """Phase 5f: new entries get INHERITED warrants automatically."""

    def test_new_entry_gets_warrant(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        # Create warrant table
        from divineos.core.logic.warrants import get_warrants, init_warrant_table

        init_warrant_table()

        kid = store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Testing is important.",
            confidence=0.9,
        )
        # No warrant yet
        assert len(get_warrants(kid)) == 0

        from divineos.cli.pipeline_phases import run_knowledge_quality_cycle

        class FakeAnalysis:
            session_id = "test-warrant-session"
            corrections = []
            encouragements = []
            context_overflows = []
            tool_calls_total = 10
            user_messages = 5

        run_knowledge_quality_cycle([kid], FakeAnalysis())

        # Now should have an INHERITED warrant
        warrants = get_warrants(kid)
        assert len(warrants) >= 1


class TestBriefingAutoContext:
    """Briefing should auto-derive context from handoff + goals."""

    def test_briefing_runs_without_context_hint(self, tmp_path, monkeypatch):
        """Briefing should work even when no context hint is provided."""
        _setup(tmp_path, monkeypatch)
        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Always read files before editing.",
            confidence=1.0,
        )
        from divineos.core.knowledge import generate_briefing

        output = generate_briefing(max_items=5)
        assert "Session Briefing" in output

    def test_briefing_with_explicit_context_hint(self, tmp_path, monkeypatch):
        _setup(tmp_path, monkeypatch)
        store_knowledge(
            knowledge_type="PRINCIPLE",
            content="Always read files before editing.",
            confidence=1.0,
        )
        from divineos.core.knowledge import generate_briefing

        output = generate_briefing(max_items=5, context_hint="editing files")
        assert "Session Briefing" in output
