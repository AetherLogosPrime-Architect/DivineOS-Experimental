"""Tests for the decision journal — capturing the WHY behind choices."""

import os

import pytest
from click.testing import CliRunner

from divineos.core.decision_journal import (
    WEIGHT_PARADIGM,
    WEIGHT_ROUTINE,
    WEIGHT_SIGNIFICANT,
    count_decisions,
    get_decision,
    get_paradigm_shifts,
    link_knowledge,
    list_decisions,
    record_decision,
    search_decisions,
)


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    """Each test gets its own database."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    from divineos.core.ledger import init_db

    init_db()
    yield
    os.environ.pop("DIVINEOS_DB", None)


class TestRecordDecision:
    def test_returns_uuid(self):
        did = record_decision("Use SQLite for storage")
        assert len(did) == 36  # UUID format

    def test_minimal_fields(self):
        did = record_decision("Choose approach A")
        entry = get_decision(did)
        assert entry is not None
        assert entry["content"] == "Choose approach A"
        assert entry["reasoning"] == ""
        assert entry["alternatives"] == []
        assert entry["emotional_weight"] == WEIGHT_ROUTINE

    def test_full_fields(self):
        did = record_decision(
            content="Build decision journal before knowledge gaps",
            reasoning="Decisions capture reasoning that knowledge entries lose",
            alternatives=["Build knowledge gap map first", "Extend personal journal"],
            context="User asked what would be most useful for me",
            emotional_weight=WEIGHT_SIGNIFICANT,
            tags=["architecture", "prioritization"],
            linked_knowledge_ids=["abc-123", "def-456"],
            session_id="test-session-1",
        )
        entry = get_decision(did)
        assert entry["reasoning"] == "Decisions capture reasoning that knowledge entries lose"
        assert len(entry["alternatives"]) == 2
        assert "Build knowledge gap map first" in entry["alternatives"]
        assert entry["context"] == "User asked what would be most useful for me"
        assert entry["emotional_weight"] == WEIGHT_SIGNIFICANT
        assert entry["tags"] == ["architecture", "prioritization"]
        assert entry["linked_knowledge_ids"] == ["abc-123", "def-456"]
        assert entry["session_id"] == "test-session-1"

    def test_weight_clamped(self):
        did = record_decision("test", emotional_weight=99)
        entry = get_decision(did)
        assert entry["emotional_weight"] == WEIGHT_PARADIGM


class TestListDecisions:
    def test_empty(self):
        assert list_decisions() == []

    def test_newest_first(self):
        record_decision("First")
        record_decision("Second")
        record_decision("Third")
        entries = list_decisions()
        assert entries[0]["content"] == "Third"
        assert entries[-1]["content"] == "First"

    def test_limit(self):
        for i in range(10):
            record_decision(f"Decision {i}")
        assert len(list_decisions(limit=3)) == 3

    def test_min_weight_filter(self):
        record_decision("Routine choice", emotional_weight=WEIGHT_ROUTINE)
        record_decision("Big decision", emotional_weight=WEIGHT_SIGNIFICANT)
        record_decision("Everything changed", emotional_weight=WEIGHT_PARADIGM)

        all_entries = list_decisions()
        assert len(all_entries) == 3

        significant_plus = list_decisions(min_weight=WEIGHT_SIGNIFICANT)
        assert len(significant_plus) == 2

        paradigm_only = list_decisions(min_weight=WEIGHT_PARADIGM)
        assert len(paradigm_only) == 1
        assert paradigm_only[0]["content"] == "Everything changed"


class TestSearchDecisions:
    def test_search_by_content(self):
        record_decision("Use SQLite for the ledger")
        record_decision("Use PostgreSQL for production")
        results = search_decisions("SQLite")
        assert len(results) == 1
        assert "SQLite" in results[0]["content"]

    def test_search_by_reasoning(self):
        record_decision(
            "Choose approach A",
            reasoning="Approach A has better test coverage and simpler error handling",
        )
        results = search_decisions("test coverage")
        assert len(results) == 1

    def test_search_by_context(self):
        record_decision("Build preflight gate", context="Audit found enforcement gap")
        results = search_decisions("audit")
        assert len(results) == 1

    def test_empty_query(self):
        assert search_decisions("") == []

    def test_no_results(self):
        record_decision("Something about databases")
        assert search_decisions("quantum") == []


class TestGetDecision:
    def test_full_id(self):
        did = record_decision("Test entry")
        assert get_decision(did) is not None

    def test_short_id(self):
        did = record_decision("Test entry")
        assert get_decision(did[:8]) is not None

    def test_not_found(self):
        assert get_decision("nonexistent-id") is None


class TestParadigmShifts:
    def test_only_returns_weight_3(self):
        record_decision("Routine", emotional_weight=WEIGHT_ROUTINE)
        record_decision("Significant", emotional_weight=WEIGHT_SIGNIFICANT)
        record_decision("Paradigm shift", emotional_weight=WEIGHT_PARADIGM)

        shifts = get_paradigm_shifts()
        assert len(shifts) == 1
        assert shifts[0]["content"] == "Paradigm shift"

    def test_empty_when_none(self):
        record_decision("Just a routine choice")
        assert get_paradigm_shifts() == []


class TestLinkKnowledge:
    def test_link_adds_id(self):
        did = record_decision("Test")
        assert link_knowledge(did, "knowledge-abc")
        entry = get_decision(did)
        assert "knowledge-abc" in entry["linked_knowledge_ids"]

    def test_link_no_duplicates(self):
        did = record_decision("Test")
        link_knowledge(did, "knowledge-abc")
        link_knowledge(did, "knowledge-abc")
        entry = get_decision(did)
        assert entry["linked_knowledge_ids"].count("knowledge-abc") == 1

    def test_link_nonexistent_decision(self):
        assert link_knowledge("nonexistent", "knowledge-abc") is False


class TestCountDecisions:
    def test_empty(self):
        assert count_decisions() == 0

    def test_counts_correctly(self):
        record_decision("One")
        record_decision("Two")
        record_decision("Three")
        assert count_decisions() == 3


class TestDecisionCLI:
    def test_decide_command(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["decide", "Test decision", "--why", "Because testing"])
        assert result.exit_code == 0
        assert "Decision recorded" in result.output

    def test_decide_with_weight(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["decide", "Paradigm shift", "--weight", "3"])
        assert result.exit_code == 0
        assert "paradigm shift" in result.output

    def test_decisions_list(self):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["decide", "First decision"])
        result = runner.invoke(cli, ["decisions", "list"])
        assert result.exit_code == 0
        assert "First decision" in result.output

    def test_decisions_search(self):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["decide", "SQLite is the right choice", "--why", "Simplicity matters"])
        result = runner.invoke(cli, ["decisions", "search", "SQLite"])
        assert result.exit_code == 0
        assert "SQLite" in result.output

    def test_decisions_shifts_empty(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["decisions", "shifts"])
        assert result.exit_code == 0
        assert "No paradigm shifts" in result.output

    def test_decisions_show(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(
            cli,
            ["decide", "Important choice", "--why", "Full reasoning here", "--weight", "3"],
        )
        # Extract decision ID from output
        assert result.exit_code == 0

        # List and verify show works
        result = runner.invoke(cli, ["decisions", "shifts"])
        assert "Important choice" in result.output
        assert "Full reasoning here" in result.output
