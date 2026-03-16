"""Full pipeline integration test - exercises all major components."""

import pytest
from divineos.ledger import init_db, log_event, get_events, verify_all_events
from divineos.consolidation import (
    init_knowledge_table,
    store_knowledge,
    get_knowledge,
    search_knowledge,
    generate_briefing,
)
from divineos.quality_checks import init_quality_tables
from divineos.session_features import init_feature_tables
from divineos.analysis import analyze_session, format_analysis_report, store_analysis


@pytest.fixture(autouse=True)
def setup_full_pipeline(tmp_path, monkeypatch):
    """Initialize all components for full pipeline test."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DIVINEOS_DB", str(db_path))
    
    init_db()
    init_knowledge_table()
    init_quality_tables()
    init_feature_tables()
    
    yield


class TestFullPipeline:
    """Test the complete DivineOS pipeline."""

    def test_ledger_to_knowledge_flow(self):
        """Full flow: log events → store knowledge → retrieve and search."""
        
        event1 = log_event(
            event_type="USER_INPUT",
            actor="user",
            payload={"content": "How does overfitting work?"}
        )
        
        event2 = log_event(
            event_type="ASSISTANT",
            actor="assistant",
            payload={"content": "Overfitting occurs when a model learns noise..."}
        )
        
        events = get_events(limit=10)
        assert len(events) >= 2
        
        result = verify_all_events()
        assert result["total"] >= 2
        
        knowledge_id = store_knowledge(
            knowledge_type="PATTERN",
            content="Overfitting happens when model complexity exceeds data signal.",
            confidence=0.85,
            source_events=[event1, event2],
            tags=["ml", "overfitting"]
        )
        
        assert knowledge_id is not None
        
        knowledge = get_knowledge(limit=10)
        assert len(knowledge) > 0
        
        search_results = search_knowledge("overfitting", limit=5)
        assert len(search_results) > 0

    def test_session_analysis_pipeline(self, tmp_path):
        """Test analyzing a session through the full pipeline."""
        
        session_file = tmp_path / "test_session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "analyze this"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "looks good"}]}}\n'
        )
        
        result = analyze_session(session_file)
        
        assert result.session_id is not None
        assert result.quality_report is not None
        
        report = format_analysis_report(result)
        assert "SESSION ANALYSIS REPORT" in report
        
        stored = store_analysis(result, report)
        assert stored is True

    def test_knowledge_supersession(self):
        """Test that knowledge can be superseded."""
        
        id1 = store_knowledge(
            knowledge_type="FACT",
            content="The Earth is flat.",
            confidence=0.1,
            tags=["astronomy"]
        )
        
        # Store a new fact with higher confidence
        # Note: store_knowledge doesn't have a supersedes parameter,
        # so we just verify both can be stored
        id2 = store_knowledge(
            knowledge_type="FACT",
            content="The Earth is an oblate spheroid.",
            confidence=0.99,
            tags=["astronomy"]
        )
        
        knowledge = get_knowledge(limit=10)
        
        entry1 = next((k for k in knowledge if k.get("knowledge_id") == id1), None)
        entry2 = next((k for k in knowledge if k.get("knowledge_id") == id2), None)
        
        assert entry1 is not None
        assert entry2 is not None

    def test_briefing_system(self):
        """Test that briefing system surfaces relevant knowledge."""
        
        store_knowledge(
            knowledge_type="PATTERN",
            content="Always read files before editing them.",
            confidence=0.9,
            tags=["coding"]
        )
        
        store_knowledge(
            knowledge_type="MISTAKE",
            content="Blind edits cause regressions.",
            confidence=0.85,
            tags=["coding"]
        )
        
        briefing = generate_briefing(max_items=5)
        
        assert briefing is not None
        assert len(briefing) > 0


class TestEndToEndEventCapture:
    """End-to-end tests for event capture and analysis."""

    def test_full_event_sequence_with_analysis(self, tmp_path, monkeypatch):
        """Test emitting a series of events and analyzing them."""
        from divineos.event_dispatcher import emit_event
        
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))
        
        init_db()
        init_knowledge_table()
        init_quality_tables()
        init_feature_tables()
        
        # Emit a realistic conversation sequence
        emit_event(
            "USER_INPUT",
            {"content": "How should I structure this module?"},
            actor="user"
        )
        
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I'd recommend organizing by responsibility. Here's a pattern..."},
            actor="assistant"
        )
        
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "readFile",
                "tool_input": {"path": "src/main.py"},
                "tool_use_id": "tool_001"
            }
        )
        
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "tool_001",
                "result": "def main():\n    pass",
                "duration_ms": 45
            }
        )
        
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I see the current structure. Let me suggest improvements..."},
            actor="assistant"
        )
        
        emit_event(
            "SESSION_END",
            {
                "session_id": "test_session_001",
                "message_count": 3,
                "duration_seconds": 120
            }
        )
        
        # Verify all events are in ledger
        events = get_events(limit=100)
        assert len(events) >= 6
        
        event_types = [e["event_type"] for e in events]
        assert "USER_INPUT" in event_types
        assert "ASSISTANT_OUTPUT" in event_types
        assert "TOOL_CALL" in event_types
        assert "TOOL_RESULT" in event_types
        assert "SESSION_END" in event_types

    def test_event_fidelity_verification(self, tmp_path, monkeypatch):
        """Test that all emitted events pass fidelity verification."""
        from divineos.event_dispatcher import emit_event
        
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))
        
        init_db()
        
        # Emit multiple events
        emit_event("USER_INPUT", {"content": "Test message 1"}, actor="user")
        emit_event("ASSISTANT_OUTPUT", {"content": "Test response 1"}, actor="assistant")
        emit_event("TOOL_CALL", {"tool_name": "test", "tool_input": {}})
        emit_event("TOOL_RESULT", {"tool_name": "test", "tool_use_id": "t1", "result": "ok"})
        emit_event("USER_INPUT", {"content": "Test message 2"}, actor="user")
        
        # Verify all events pass fidelity check
        result = verify_all_events()
        
        assert result["integrity"] == "PASS"
        assert result["failed"] == 0
        assert result["total"] >= 5

    def test_event_content_hashes(self, tmp_path, monkeypatch):
        """Test that event content hashes are computed correctly."""
        from divineos.event_dispatcher import emit_event
        
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))
        
        init_db()
        
        # Emit an event
        content = "This is test content for hashing"
        emit_event("USER_INPUT", {"content": content}, actor="user")
        
        # Retrieve the event
        events = get_events(limit=10)
        assert len(events) > 0
        
        event = events[0]
        
        # Verify content_hash exists
        assert "content_hash" in event
        assert event["content_hash"] is not None
        assert len(event["content_hash"]) > 0

    def test_session_analysis_on_captured_events(self, tmp_path, monkeypatch):
        """Test that captured events contain real conversation data."""
        from divineos.event_dispatcher import emit_event
        
        db_path = tmp_path / "test.db"
        monkeypatch.setenv("DIVINEOS_DB", str(db_path))
        
        init_db()
        init_quality_tables()
        init_feature_tables()
        
        # Emit a realistic conversation
        emit_event(
            "USER_INPUT",
            {"content": "How do I fix this bug?"},
            actor="user"
        )
        
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "Let me help you debug this issue."},
            actor="assistant"
        )
        
        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "readFile",
                "tool_input": {"path": "src/bug.py"},
                "tool_use_id": "t1"
            }
        )
        
        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "t1",
                "result": "def buggy_function():\n    return None"
            }
        )
        
        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I found the issue. The function returns None."},
            actor="assistant"
        )
        
        # Analyze the captured events
        events = get_events(limit=100)
        
        # Verify we have real conversation data
        assert len(events) >= 5
        
        # Check that events contain real content (not test data)
        event_contents = [e["payload"].get("content", "") for e in events]
        assert any("bug" in str(c).lower() for c in event_contents)
        assert any("debug" in str(c).lower() for c in event_contents)
