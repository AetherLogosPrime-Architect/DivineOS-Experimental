"""Tests for the CLI commands."""

import pytest
from click.testing import CliRunner
from divineos.cli import cli
import divineos.ledger as ledger_mod


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setattr(ledger_mod, "DB_PATH", test_db)
    yield


@pytest.fixture
def runner():
    return CliRunner()


class TestInit:
    def test_init_succeeds(self, runner):
        result = runner.invoke(cli, ["init"])
        assert result.exit_code == 0
        assert "initialized" in result.output.lower()


class TestLog:
    def test_log_event(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "user", "--content", "hello"]
        )
        assert result.exit_code == 0
        assert "Logged event" in result.output

    def test_log_json_content(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "system", "--content", '{"key": "value"}']
        )
        assert result.exit_code == 0


class TestList:
    def test_empty_list(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["list"])
        assert "No events" in result.output

    def test_list_after_log(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["log", "--type", "TEST", "--actor", "user", "--content", "hello world"])
        result = runner.invoke(cli, ["list"])
        assert result.exit_code == 0
        assert "hello world" in result.output


class TestSearch:
    def test_search_found(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "user", "--content", "the quick brown fox"]
        )
        result = runner.invoke(cli, ["search", "fox"])
        assert result.exit_code == 0
        assert "fox" in result.output

    def test_search_not_found(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["search", "nonexistent"])
        assert "No events" in result.output


class TestStats:
    def test_stats_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["stats"])
        assert result.exit_code == 0
        assert "Total events: 0" in result.output

    def test_stats_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["log", "--type", "USER_INPUT", "--actor", "user", "--content", "hi"])
        runner.invoke(cli, ["log", "--type", "ERROR", "--actor", "system", "--content", "oops"])
        result = runner.invoke(cli, ["stats"])
        assert "Total events: 2" in result.output


class TestVerify:
    def test_verify_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["verify"])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_verify_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["log", "--type", "TEST", "--actor", "user", "--content", "test data"])
        result = runner.invoke(cli, ["verify"])
        assert "PASS" in result.output


class TestContext:
    def test_context_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["context"])
        assert "No events" in result.output

    def test_context_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(
            cli, ["log", "--type", "TEST", "--actor", "user", "--content", "recent event"]
        )
        result = runner.invoke(cli, ["context", "--n", "5"])
        assert result.exit_code == 0
        assert "recent event" in result.output


class TestLearn:
    def test_learn_fact(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(
            cli, ["learn", "--type", "FACT", "--content", "Python uses indentation"]
        )
        assert result.exit_code == 0
        assert "Stored knowledge" in result.output

    def test_learn_invalid_type(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["learn", "--type", "INVALID", "--content", "nope"])
        assert result.exit_code != 0


class TestKnowledgeCmd:
    def test_knowledge_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["knowledge"])
        assert "No knowledge" in result.output


class TestBriefingCmd:
    def test_briefing_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["briefing"])
        assert result.exit_code == 0
        assert "No knowledge" in result.output

    def test_briefing_with_data(self, runner):
        runner.invoke(cli, ["init"])
        runner.invoke(cli, ["learn", "--type", "FACT", "--content", "pytest is the test runner"])
        result = runner.invoke(cli, ["briefing"])
        assert "FACTS" in result.output
        assert "pytest" in result.output


class TestConsolidateStats:
    def test_stats_empty(self, runner):
        runner.invoke(cli, ["init"])
        result = runner.invoke(cli, ["consolidate-stats"])
        assert result.exit_code == 0
        assert "Total knowledge: 0" in result.output


class TestSessionsCmd:
    def test_sessions_runs(self, runner):
        result = runner.invoke(cli, ["sessions"])
        assert result.exit_code == 0


class TestAnalyzeCmd:
    def test_analyze_nonexistent(self, runner, tmp_path):
        # Test with a nonexistent file
        result = runner.invoke(cli, ["analyze", "/nonexistent/file.jsonl"])
        # Should fail gracefully
        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "error" in result.output.lower()

    def test_analyze_file(self, runner, tmp_path):
        import json

        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": "2025-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "perfect work"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))
        result = runner.invoke(cli, ["analyze", str(session_file)])
        assert result.exit_code == 0
        assert "Session Analysis" in result.output


class TestScanCmd:
    def test_scan_without_store(self, runner, tmp_path):
        import json

        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": "2025-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "no thats wrong"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))
        result = runner.invoke(cli, ["scan", str(session_file)])
        assert result.exit_code == 0
        assert "--store" in result.output

    def test_scan_with_store(self, runner, tmp_path):
        import json

        # Init DB first
        runner.invoke(cli, ["init"])

        session_file = tmp_path / "test.jsonl"
        records = [
            {
                "type": "user",
                "timestamp": "2025-01-01T00:00:00Z",
                "message": {"content": [{"type": "text", "text": "perfect amazing"}]},
            },
        ]
        session_file.write_text("\n".join(json.dumps(r) for r in records))
        result = runner.invoke(cli, ["scan", "--store", str(session_file)])
        assert result.exit_code == 0
        assert "Stored" in result.output
