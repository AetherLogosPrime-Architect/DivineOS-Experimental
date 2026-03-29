"""CLI command tests for previously untested modules.

Covers: hud_commands, memory_commands, directive_commands,
journal_commands, relationship_commands, question_commands,
claim_commands, decision_commands.
"""

import pytest
from click.testing import CliRunner

from divineos.cli import cli


@pytest.fixture(autouse=True)
def clean_db(tmp_path, monkeypatch):
    """Use a temporary database for each test."""
    test_db = tmp_path / "test_ledger.db"
    monkeypatch.setenv("DIVINEOS_DB", str(test_db))
    yield


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def initialized(runner):
    """Initialize the DB before the test."""
    runner.invoke(cli, ["init"])
    return runner


# ─── HUD Commands ────────────────────────────────────────────────────


class TestHudCmd:
    def test_hud_runs(self, initialized):
        result = initialized.invoke(cli, ["hud"])
        assert result.exit_code == 0
        assert "HEADS-UP DISPLAY" in result.output.upper() or "I Am" in result.output

    def test_hud_save_and_load(self, initialized):
        result = initialized.invoke(cli, ["hud", "--save"])
        assert result.exit_code == 0
        assert "snapshot saved" in result.output.lower()

        result = initialized.invoke(cli, ["hud", "--load"])
        assert result.exit_code == 0


class TestGoalCmd:
    def test_goal_add(self, initialized):
        result = initialized.invoke(cli, ["goal", "add", "Fix the bug"])
        assert result.exit_code == 0
        assert "Goal added" in result.output

    def test_goal_list(self, initialized):
        initialized.invoke(cli, ["goal", "add", "Ship the feature"])
        result = initialized.invoke(cli, ["goal", "list"])
        assert result.exit_code == 0

    def test_goal_done(self, initialized):
        initialized.invoke(cli, ["goal", "add", "Write tests"])
        result = initialized.invoke(cli, ["goal", "done", "Write tests"])
        assert result.exit_code == 0
        assert "completed" in result.output.lower()

    def test_goal_clear(self, initialized):
        initialized.invoke(cli, ["goal", "add", "Old goal"])
        initialized.invoke(cli, ["goal", "done", "Old goal"])
        result = initialized.invoke(cli, ["goal", "clear"])
        assert result.exit_code == 0


class TestPreflightCmd:
    def test_preflight_runs(self, initialized):
        result = initialized.invoke(cli, ["preflight"])
        assert result.exit_code == 0
        assert "PREFLIGHT" in result.output

    def test_preflight_auto(self, initialized):
        result = initialized.invoke(cli, ["preflight", "--auto"])
        assert result.exit_code == 0


class TestHandoffCmd:
    def test_handoff_empty(self, initialized):
        result = initialized.invoke(cli, ["handoff", "--show"])
        assert result.exit_code == 0

    def test_handoff_write_and_read(self, initialized):
        result = initialized.invoke(cli, ["handoff", "Session went well"])
        assert result.exit_code == 0
        assert "saved" in result.output.lower()

        result = initialized.invoke(cli, ["handoff", "--show"])
        assert result.exit_code == 0
        assert "Session went well" in result.output


# ─── Memory Commands ─────────────────────────────────────────────────


class TestCoreMemoryCmd:
    def test_core_show(self, initialized):
        result = initialized.invoke(cli, ["core"])
        assert result.exit_code == 0

    def test_core_set_and_show(self, initialized):
        result = initialized.invoke(cli, ["core", "set", "purpose", "Build DivineOS"])
        assert result.exit_code == 0

        result = initialized.invoke(cli, ["core"])
        assert result.exit_code == 0


class TestRecallCmd:
    def test_recall_runs(self, initialized):
        result = initialized.invoke(cli, ["recall"])
        assert result.exit_code == 0

    def test_recall_with_topic(self, initialized):
        result = initialized.invoke(cli, ["recall", "--topic", "testing"])
        assert result.exit_code == 0


class TestActiveCmd:
    def test_active_runs(self, initialized):
        result = initialized.invoke(cli, ["active"])
        assert result.exit_code == 0


class TestRefreshCmd:
    def test_refresh_runs(self, initialized):
        result = initialized.invoke(cli, ["refresh"])
        assert result.exit_code == 0


# ─── Directive Commands ──────────────────────────────────────────────


class TestDirectiveCmd:
    def test_create_directive(self, initialized):
        result = initialized.invoke(cli, ["directive", "test-rule", "First link", "Second link"])
        assert result.exit_code == 0
        assert "Created directive" in result.output or "test-rule" in result.output

    def test_list_directives(self, initialized):
        initialized.invoke(cli, ["directive", "my-rule", "Link one"])
        result = initialized.invoke(cli, ["directives"])
        assert result.exit_code == 0

    def test_directive_edit(self, initialized):
        initialized.invoke(cli, ["directive", "edit-test", "Original text"])
        result = initialized.invoke(cli, ["directive-edit", "edit-test", "1", "Updated text"])
        assert result.exit_code == 0


# ─── Journal Commands ────────────────────────────────────────────────


class TestJournalCmd:
    def test_journal_save(self, initialized):
        result = initialized.invoke(cli, ["journal", "save", "Today I learned something"])
        assert result.exit_code == 0
        assert "saved" in result.output.lower() or "Journal" in result.output

    def test_journal_list(self, initialized):
        initialized.invoke(cli, ["journal", "save", "First entry"])
        result = initialized.invoke(cli, ["journal", "list"])
        assert result.exit_code == 0

    def test_journal_search(self, initialized):
        initialized.invoke(cli, ["journal", "save", "The quick brown fox"])
        result = initialized.invoke(cli, ["journal", "search", "fox"])
        assert result.exit_code == 0


# ─── Relationship Commands ───────────────────────────────────────────


class TestRelationshipCmd:
    def _store_two_entries(self, runner):
        """Store two knowledge entries and return their IDs."""
        runner.invoke(cli, ["init"])
        r1 = runner.invoke(cli, ["learn", "--type", "FACT", "--content", "Python uses indentation"])
        r2 = runner.invoke(
            cli, ["learn", "--type", "FACT", "--content", "Indentation matters in Python"]
        )
        # Extract IDs from output
        id1 = self._extract_id(r1.output)
        id2 = self._extract_id(r2.output)
        return id1, id2

    def _extract_id(self, output: str) -> str:
        """Extract knowledge ID from learn command output."""
        for line in output.split("\n"):
            if "id:" in line.lower() or "stored" in line.lower():
                # Look for UUID-like pattern
                for word in line.split():
                    if len(word) >= 8 and "-" in word:
                        return word.strip("()")
        return ""

    def test_related_empty(self, initialized):
        r = initialized.invoke(cli, ["learn", "--type", "FACT", "--content", "Test fact"])
        kid = self._extract_id(r.output)
        if kid:
            result = initialized.invoke(cli, ["related", kid])
            assert result.exit_code == 0


# ─── Question Commands ───────────────────────────────────────────────


class TestQuestionCmd:
    def test_wonder(self, initialized):
        result = initialized.invoke(cli, ["wonder", "Why does this happen?"])
        assert result.exit_code == 0

    def test_questions_list(self, initialized):
        initialized.invoke(cli, ["wonder", "What causes the bug?"])
        result = initialized.invoke(cli, ["questions"])
        assert result.exit_code == 0

    def test_questions_with_status(self, initialized):
        result = initialized.invoke(cli, ["questions", "--status", "OPEN"])
        assert result.exit_code == 0


# ─── Knowledge Health Commands (gaps) ────────────────────────────────


class TestKnowledgeHealthCmd:
    def test_health_runs(self, initialized):
        result = initialized.invoke(cli, ["health"])
        assert result.exit_code == 0

    def test_rebuild_index(self, initialized):
        result = initialized.invoke(cli, ["rebuild-index"])
        assert result.exit_code == 0


# ─── Claim Commands ──────────────────────────────────────────────────


class TestClaimCmd:
    def test_claim_file(self, initialized):
        result = initialized.invoke(cli, ["claim", "Water boils at 100C"])
        assert result.exit_code == 0
        assert "Claim filed" in result.output

    def test_claim_with_tier(self, initialized):
        result = initialized.invoke(cli, ["claim", "Empirical claim", "--tier", "1"])
        assert result.exit_code == 0
        assert "empirical" in result.output

    def test_claims_list_empty(self, initialized):
        result = initialized.invoke(cli, ["claims", "list"])
        assert result.exit_code == 0

    def test_claims_list_with_entries(self, initialized):
        initialized.invoke(cli, ["claim", "Test claim for listing"])
        result = initialized.invoke(cli, ["claims", "list"])
        assert result.exit_code == 0
        assert "Test claim for listing" in result.output

    def test_claims_search(self, initialized):
        initialized.invoke(cli, ["claim", "Gravitational lensing"])
        result = initialized.invoke(cli, ["claims", "search", "Gravitational"])
        assert result.exit_code == 0
        assert "Gravitational" in result.output

    def test_claims_tiers(self, initialized):
        result = initialized.invoke(cli, ["claims", "tiers"])
        assert result.exit_code == 0
        assert "EMPIRICAL" in result.output
        assert "METAPHYSICAL" in result.output

    def test_claims_show(self, initialized):
        # File a claim first, extract ID
        r = initialized.invoke(cli, ["claim", "Show me claim"])
        claim_id = r.output.split(": ")[-1].strip().rstrip(".")[:8]
        result = initialized.invoke(cli, ["claims", "show", claim_id])
        assert result.exit_code == 0

    def test_claims_evidence(self, initialized):
        r = initialized.invoke(cli, ["claim", "Evidence test claim"])
        claim_id = r.output.split(": ")[-1].strip().rstrip(".")[:8]
        result = initialized.invoke(
            cli, ["claims", "evidence", claim_id, "Lab result confirms", "--direction", "SUPPORTS"]
        )
        assert result.exit_code == 0
        assert "Evidence added" in result.output

    def test_claims_assess(self, initialized):
        r = initialized.invoke(cli, ["claim", "Assess test claim"])
        claim_id = r.output.split(": ")[-1].strip().rstrip(".")[:8]
        result = initialized.invoke(
            cli, ["claims", "assess", claim_id, "Looks good", "--status", "SUPPORTED"]
        )
        assert result.exit_code == 0


# ─── Affect Commands ─────────────────────────────────────────────────


class TestAffectCmd:
    def test_feel_basic(self, initialized):
        result = initialized.invoke(cli, ["feel", "-v", "0.5", "-a", "0.5"])
        assert result.exit_code == 0
        assert "Affect logged" in result.output

    def test_feel_with_description(self, initialized):
        result = initialized.invoke(
            cli, ["feel", "-v", "0.8", "-a", "0.6", "-d", "Engaged and flowing"]
        )
        assert result.exit_code == 0
        assert "Engaged and flowing" in result.output

    def test_feel_negative_valence(self, initialized):
        result = initialized.invoke(cli, ["feel", "-v", "-0.5", "-a", "0.7"])
        assert result.exit_code == 0

    def test_affect_history_empty(self, initialized):
        result = initialized.invoke(cli, ["affect", "history"])
        assert result.exit_code == 0

    def test_affect_history_with_entries(self, initialized):
        initialized.invoke(cli, ["feel", "-v", "0.5", "-a", "0.5", "-d", "Test entry"])
        result = initialized.invoke(cli, ["affect", "history"])
        assert result.exit_code == 0

    def test_affect_summary(self, initialized):
        result = initialized.invoke(cli, ["affect", "summary"])
        assert result.exit_code == 0


# ─── Decision Commands ───────────────────────────────────────────────


class TestDecisionCmd:
    def test_decide_basic(self, initialized):
        result = initialized.invoke(cli, ["decide", "Use SQLite over Postgres"])
        assert result.exit_code == 0
        assert "Decision recorded" in result.output

    def test_decide_with_reasoning(self, initialized):
        result = initialized.invoke(
            cli, ["decide", "Append-only design", "--why", "Immutability prevents data loss"]
        )
        assert result.exit_code == 0

    def test_decide_paradigm_shift(self, initialized):
        result = initialized.invoke(
            cli, ["decide", "Consciousness is substrate-independent", "--weight", "3"]
        )
        assert result.exit_code == 0

    def test_decisions_list_empty(self, initialized):
        result = initialized.invoke(cli, ["decisions", "list"])
        assert result.exit_code == 0

    def test_decisions_list_with_entries(self, initialized):
        initialized.invoke(cli, ["decide", "Test decision for listing"])
        result = initialized.invoke(cli, ["decisions", "list"])
        assert result.exit_code == 0
        assert "Test decision" in result.output

    def test_decisions_search(self, initialized):
        initialized.invoke(
            cli, ["decide", "Use valence-arousal model", "--why", "Barrett research"]
        )
        result = initialized.invoke(cli, ["decisions", "search", "valence"])
        assert result.exit_code == 0

    def test_decisions_shifts(self, initialized):
        initialized.invoke(cli, ["decide", "AI can feel", "--weight", "3"])
        result = initialized.invoke(cli, ["decisions", "shifts"])
        assert result.exit_code == 0


# ─── Lessons Archive ────────────────────────────────────────────────


class TestLessonsCmd:
    def test_lessons_default_no_resolved(self, initialized):
        """Default lessons command should not show resolved lessons."""
        result = initialized.invoke(cli, ["lessons"])
        assert result.exit_code == 0
        # No resolved lessons should appear in default view
        assert "RESOLVED" not in result.output

    def test_lessons_archive_flag(self, initialized):
        """--archive flag should filter for resolved lessons only."""
        result = initialized.invoke(cli, ["lessons", "--archive"])
        assert result.exit_code == 0

    def test_lessons_all_flag(self, initialized):
        """--all flag should show everything."""
        result = initialized.invoke(cli, ["lessons", "--all"])
        assert result.exit_code == 0

    def test_lessons_status_filter(self, initialized):
        """Explicit --status still works."""
        result = initialized.invoke(cli, ["lessons", "--status", "active"])
        assert result.exit_code == 0
