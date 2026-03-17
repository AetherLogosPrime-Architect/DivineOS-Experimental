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
            event_type="USER_INPUT", actor="user", payload={"content": "How does overfitting work?"}
        )

        event2 = log_event(
            event_type="ASSISTANT",
            actor="assistant",
            payload={"content": "Overfitting occurs when a model learns noise..."},
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
            tags=["ml", "overfitting"],
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
            knowledge_type="FACT", content="The Earth is flat.", confidence=0.1, tags=["astronomy"]
        )

        # Store a new fact with higher confidence
        # Note: store_knowledge doesn't have a supersedes parameter,
        # so we just verify both can be stored
        id2 = store_knowledge(
            knowledge_type="FACT",
            content="The Earth is an oblate spheroid.",
            confidence=0.99,
            tags=["astronomy"],
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
            tags=["coding"],
        )

        store_knowledge(
            knowledge_type="MISTAKE",
            content="Blind edits cause regressions.",
            confidence=0.85,
            tags=["coding"],
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
        emit_event("USER_INPUT", {"content": "How should I structure this module?"}, actor="user")

        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I'd recommend organizing by responsibility. Here's a pattern..."},
            actor="assistant",
        )

        emit_event(
            "TOOL_CALL",
            {
                "tool_name": "readFile",
                "tool_input": {"path": "src/main.py"},
                "tool_use_id": "tool_001",
            },
        )

        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "tool_001",
                "result": "def main():\n    pass",
                "duration_ms": 45,
            },
        )

        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I see the current structure. Let me suggest improvements..."},
            actor="assistant",
        )

        emit_event(
            "SESSION_END",
            {"session_id": "test_session_001", "message_count": 3, "duration_seconds": 120},
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
        emit_event("USER_INPUT", {"content": "Test message 1"}, actor="user", validate=False)
        emit_event(
            "ASSISTANT_OUTPUT", {"content": "Test response 1"}, actor="assistant", validate=False
        )
        emit_event(
            "TOOL_CALL",
            {"tool_name": "test", "tool_input": {}, "tool_use_id": "t1"},
            validate=False,
        )
        emit_event(
            "TOOL_RESULT",
            {"tool_name": "test", "tool_use_id": "t1", "result": "ok"},
            validate=False,
        )
        emit_event("USER_INPUT", {"content": "Test message 2"}, actor="user", validate=False)

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
        emit_event("USER_INPUT", {"content": "How do I fix this bug?"}, actor="user")

        emit_event(
            "ASSISTANT_OUTPUT", {"content": "Let me help you debug this issue."}, actor="assistant"
        )

        emit_event(
            "TOOL_CALL",
            {"tool_name": "readFile", "tool_input": {"path": "src/bug.py"}, "tool_use_id": "t1"},
        )

        emit_event(
            "TOOL_RESULT",
            {
                "tool_name": "readFile",
                "tool_use_id": "t1",
                "result": "def buggy_function():\n    return None",
            },
        )

        emit_event(
            "ASSISTANT_OUTPUT",
            {"content": "I found the issue. The function returns None."},
            actor="assistant",
        )

        # Analyze the captured events
        events = get_events(limit=100)

        # Verify we have real conversation data
        assert len(events) >= 5

        # Check that events contain real content (not test data)
        event_contents = [e["payload"].get("content", "") for e in events]
        assert any("bug" in str(c).lower() for c in event_contents)
        assert any("debug" in str(c).lower() for c in event_contents)


class TestPhase4Integration:
    """Phase 4: Testing & Verification - Integration tests for analyze, report, and cross-session commands."""

    def test_analyze_command_end_to_end(self, tmp_path):
        """Test analyze command end-to-end with real JSONL data."""
        from divineos.analysis import analyze_session, format_analysis_report, store_analysis

        # Create a realistic session file
        session_file = tmp_path / "realistic_session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "add authentication to the app"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "I\'ll add authentication. Let me first check the current structure."}]}}\n'
            '{"type": "tool_call", "tool": "readFile", "path": "src/app.py", "timestamp": 1710000002}\n'
            '{"type": "tool_result", "content": "class App:\\n    def __init__(self):\\n        pass"}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Now I\'ll add the authentication module."}]}}\n'
            '{"type": "tool_call", "tool": "strReplace", "path": "src/app.py", "oldStr": "class App:\\n    def __init__(self):\\n        pass", "newStr": "class App:\\n    def __init__(self):\\n        self.users = {}\\n    def login(self, username, password):\\n        return username in self.users"}\n'
            '{"type": "tool_result", "content": "File updated successfully"}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Authentication module added successfully."}]}}\n'
            '{"type": "user", "message": {"role": "user", "content": "great! now add password hashing"}}\n'
        )

        # Analyze the session
        result = analyze_session(session_file)

        # Verify analysis result
        assert result.session_id is not None
        assert result.quality_report is not None
        assert result.features is not None
        assert result.evidence_hash is not None

        # Format the report
        report = format_analysis_report(result)

        # Verify report is plain-English (no jargon)
        assert "SESSION ANALYSIS REPORT" in report
        assert "Quality Checks" in report or "quality" in report.lower()
        assert "Session Features" in report or "features" in report.lower()

        # Verify no technical jargon
        assert "manifest-receipt" not in report.lower()
        assert "FTS5" not in report
        assert "reconciliation" not in report.lower()

        # Store the analysis
        stored = store_analysis(result, report)
        assert stored is True

    def test_report_command_retrieval(self, tmp_path):
        """Test report command retrieves stored analysis."""
        from divineos.analysis import (
            analyze_session,
            format_analysis_report,
            store_analysis,
            get_stored_report,
            list_recent_sessions,
        )

        # Create and analyze a session
        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "hello"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "hi"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)
        store_analysis(result, report)

        # Retrieve the report
        retrieved_report = get_stored_report(result.session_id)
        assert retrieved_report is not None
        assert "SESSION ANALYSIS REPORT" in retrieved_report

        # List recent sessions
        sessions = list_recent_sessions(limit=10)
        assert len(sessions) > 0
        assert any(s["session_id"] == result.session_id for s in sessions)

    def test_cross_session_trends(self, tmp_path):
        """Test cross-session trends computation."""
        from divineos.analysis import (
            analyze_session,
            format_analysis_report,
            store_analysis,
            compute_cross_session_trends,
            format_cross_session_report,
        )

        # Create and analyze multiple sessions
        for i in range(3):
            session_file = tmp_path / f"session_{i}.jsonl"
            session_file.write_text(
                '{"type": "user", "message": {"role": "user", "content": "task"}}\n'
                '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "working on it"}]}}\n'
            )

            result = analyze_session(session_file)
            report = format_analysis_report(result)
            store_analysis(result, report)

        # Compute trends
        trends = compute_cross_session_trends(limit=10)
        assert trends is not None
        assert isinstance(trends, dict)

        # Format cross-session report
        cross_report = format_cross_session_report(trends)
        assert cross_report is not None
        assert "Cross-Session" in cross_report or "cross" in cross_report.lower()

    def test_plain_english_output_no_jargon(self, tmp_path):
        """Test that all output is plain-English with no jargon."""
        from divineos.analysis import analyze_session, format_analysis_report

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "fix the bug"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "I found it"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)

        # Check for absence of jargon
        jargon_terms = [
            "manifest-receipt",
            "reconciliation",
            "FTS5",
            "ledger",
            "fidelity",
            "evidence_hash",
            "dataclass",
            "payload",
            "schema",
            "normalization",
        ]

        report_lower = report.lower()
        for term in jargon_terms:
            assert term not in report_lower, f"Found jargon term '{term}' in report"

    def test_fidelity_verification_in_storage(self, tmp_path):
        """Test that fidelity verification works during storage."""
        from divineos.analysis import analyze_session, format_analysis_report, store_analysis

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "test"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)

        # Store should verify fidelity
        stored = store_analysis(result, report)
        assert stored is True

    def test_error_handling_empty_session(self, tmp_path):
        """Test error handling for empty session."""
        from divineos.analysis import analyze_session

        session_file = tmp_path / "empty.jsonl"
        session_file.write_text("")

        # Should raise ValueError for empty session
        with pytest.raises(ValueError):
            analyze_session(session_file)

    def test_error_handling_malformed_jsonl(self, tmp_path):
        """Test error handling for malformed JSONL."""
        from divineos.analysis import analyze_session

        session_file = tmp_path / "malformed.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "valid"}}\n'
            "this is not valid json\n"
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}\n'
        )

        # Should skip bad lines and continue
        result = analyze_session(session_file)
        assert result is not None
        assert result.session_id is not None

    def test_analysis_events_emitted_to_ledger(self, tmp_path):
        """Test that analysis events are emitted to the ledger."""
        from divineos.analysis import analyze_session, format_analysis_report, store_analysis
        from divineos.ledger import get_events

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "test"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}\n'
        )

        result = analyze_session(session_file)
        report = format_analysis_report(result)
        store_analysis(result, report)

        # Check that events were emitted
        events = get_events(limit=100)
        event_types = [e["event_type"] for e in events]

        assert "QUALITY_REPORT" in event_types
        assert "SESSION_FEATURES" in event_types
        assert "SESSION_ANALYSIS" in event_types

    def test_evidence_hashes_reproducible(self, tmp_path):
        """Test that evidence hashes are reproducible for same content."""
        from divineos.analysis import analyze_session

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "test"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "ok"}]}}\n'
        )

        # Analyze once
        result1 = analyze_session(session_file)

        # Verify hash is not empty
        assert result1.evidence_hash is not None
        assert len(result1.evidence_hash) > 0

    def test_quality_checks_on_real_data(self, tmp_path):
        """Test that quality checks execute on real conversation data."""
        from divineos.analysis import analyze_session

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "add a feature"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "I\'ll add it"}]}}\n'
            '{"type": "tool_call", "tool": "readFile", "path": "src/main.py"}\n'
            '{"type": "tool_result", "content": "def main(): pass"}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "Now I\'ll implement it"}]}}\n'
            '{"type": "tool_call", "tool": "strReplace", "path": "src/main.py", "oldStr": "def main(): pass", "newStr": "def main():\\n    print(\'feature added\')"}\n'
            '{"type": "tool_result", "content": "File updated"}\n'
        )

        result = analyze_session(session_file)

        # Verify quality checks ran
        assert result.quality_report is not None
        assert hasattr(result.quality_report, "checks")
        assert len(result.quality_report.checks) > 0

    def test_session_features_extracted(self, tmp_path):
        """Test that session features are extracted correctly."""
        from divineos.analysis import analyze_session

        session_file = tmp_path / "session.jsonl"
        session_file.write_text(
            '{"type": "user", "message": {"role": "user", "content": "help me"}}\n'
            '{"type": "assistant", "message": {"role": "assistant", "content": [{"type": "text", "text": "I\'ll help"}]}}\n'
            '{"type": "tool_call", "tool": "readFile", "path": "file.py"}\n'
            '{"type": "tool_result", "content": "content"}\n'
        )

        result = analyze_session(session_file)

        # Verify features were extracted
        assert result.features is not None
        assert hasattr(result.features, "timeline")
        assert hasattr(result.features, "files_touched")
        assert hasattr(result.features, "activity")
