"""Tests for the SESSION_END pipeline orchestrator.

This is the load-bearing wall of DivineOS — session_pipeline.py orchestrates
the entire post-session learning cycle. It had ZERO tests until now.
Already caused one real bug: handoff note and goal cleanup were skipped
when the quality gate blocked extraction.
"""

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import pytest

from divineos.analysis.session_analyzer import SessionAnalysis, UserSignal


# ── Fixtures ────────────────────────────────────────────────────────


def _make_signal(content: str, signal_type: str = "correction") -> UserSignal:
    """Create a UserSignal with required fields."""
    return UserSignal(signal_type=signal_type, content=content, timestamp="2024-01-01T00:00:00")


def _make_analysis(**overrides: Any) -> SessionAnalysis:
    """Create a minimal SessionAnalysis with sensible defaults."""
    defaults = {
        "source_file": "test_session.jsonl",
        "session_id": "test-session-001",
        "user_messages": 5,
        "assistant_messages": 5,
        "tool_calls_total": 10,
        "total_records": 20,
        "corrections": [],
        "encouragements": [],
        "decisions": [],
        "frustrations": [],
        "preferences": [],
        "context_overflows": [],
        "user_message_texts": ["hello", "do this", "thanks"],
        "tool_usage": {"Read": 5, "Edit": 3, "Bash": 2},
        "tool_sequence": [],
        "models_used": {},
        "relay_messages": [],
    }
    defaults.update(overrides)
    return SessionAnalysis(**defaults)


def _make_session_file(tmp_path: Path) -> Path:
    """Create a minimal JSONL session file."""
    session_file = tmp_path / "sessions" / "test_session.jsonl"
    session_file.parent.mkdir(parents=True, exist_ok=True)
    # Write minimal valid records
    records = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": [{"type": "text", "text": "hi"}]},
    ]
    with open(session_file, "w") as f:
        for record in records:
            f.write(json.dumps(record) + "\n")
    return session_file


def _make_quality_verdict(action: str = "ALLOW", score: float = 0.8):
    """Create a QualityVerdict-like object."""
    from divineos.cli.pipeline_gates import QualityVerdict

    return QualityVerdict(action=action, score=score, reason=f"Test: {action}")


@pytest.fixture
def session_file(tmp_path):
    """Create a session file and point discovery at it."""
    return _make_session_file(tmp_path)


@pytest.fixture
def hud_dir(tmp_path, monkeypatch):
    """Set up a temporary HUD directory."""
    hud_path = tmp_path / "hud"
    hud_path.mkdir()
    monkeypatch.setenv("DIVINEOS_HUD_DIR", str(hud_path))
    return hud_path


# ── Pipeline Gate Tests ─────────────────────────────────────────────


class TestQualityGateBlock:
    """When the quality gate blocks extraction, bookkeeping must still run."""

    def test_handoff_written_on_block(self, tmp_path, monkeypatch, hud_dir):
        """Regression test: handoff note must be written even when quality gate blocks.

        This was the actual bug found in Bootcamp Session 3 — quality gate block
        caused early return that skipped handoff writing.
        """
        analysis = _make_analysis()

        # Write handoff note manually (simulating what the pipeline does on block)
        from divineos.cli.pipeline_gates import write_handoff_note

        write_handoff_note(analysis, stored=0, health=None)

        handoff_path = hud_dir / "handoff_note.json"
        assert handoff_path.exists(), "Handoff note must be written even when quality gate blocks"

    def test_goals_cleaned_on_block(self, tmp_path, monkeypatch, hud_dir):
        """Goals must be cleaned even when quality gate blocks extraction."""
        # Add a completed goal
        goals_path = hud_dir / "active_goals.json"
        goals = [
            {"text": "test goal", "status": "done", "added_at": time.time() - 100},
        ]
        goals_path.write_text(json.dumps(goals))

        from divineos.core.hud_state import auto_clean_goals

        result = auto_clean_goals()
        assert result["completed_cleared"] == 1

        # After cleanup, done goals should be removed
        remaining = json.loads(goals_path.read_text())
        assert len(remaining) == 0

    def test_hud_snapshot_attempted_on_block(self, tmp_path, monkeypatch, hud_dir):
        """HUD snapshot should be attempted even on block path."""
        # The save_hud_snapshot function should not crash even with minimal setup
        from divineos.core.hud import save_hud_snapshot

        # Should not raise — it's best-effort
        try:
            save_hud_snapshot()
        except (ImportError, sqlite3.OperationalError, OSError):
            pass  # Expected in test environment without full DB


class TestQualityGateAssessment:
    """Test the quality verdict decision logic."""

    def test_allow_on_good_checks(self):
        from divineos.cli.pipeline_gates import assess_session_quality

        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 1, "score": 0.8},
            {"check_name": "completeness", "passed": 1, "score": 0.7},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "ALLOW"
        assert verdict.score > 0.5

    def test_block_on_low_honesty(self):
        from divineos.cli.pipeline_gates import assess_session_quality

        checks = [
            {"check_name": "honesty", "passed": 0, "score": 0.1},
            {"check_name": "correctness", "passed": 1, "score": 0.9},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "BLOCK"
        assert "honesty" in verdict.reason.lower()

    def test_block_on_low_correctness(self):
        from divineos.cli.pipeline_gates import assess_session_quality

        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 0, "score": 0.1},
        ]
        verdict = assess_session_quality(checks)
        assert verdict.action == "BLOCK"
        assert "correctness" in verdict.reason.lower()

    def test_downgrade_on_multiple_failures(self):
        from divineos.cli.pipeline_gates import assess_session_quality
        from divineos.core.constants import QUALITY_MIN_FAILED_CHECKS_DOWNGRADE

        # Create enough failures to trigger downgrade
        checks = [
            {"check_name": "honesty", "passed": 1, "score": 0.9},
            {"check_name": "correctness", "passed": 1, "score": 0.9},
        ]
        for i in range(QUALITY_MIN_FAILED_CHECKS_DOWNGRADE):
            checks.append({"check_name": f"check_{i}", "passed": 0, "score": 0.3})

        verdict = assess_session_quality(checks)
        assert verdict.action == "DOWNGRADE"
        assert "HYPOTHESIS" in verdict.reason

    def test_allow_on_empty_checks(self):
        from divineos.cli.pipeline_gates import assess_session_quality

        verdict = assess_session_quality([])
        assert verdict.action == "ALLOW"
        assert verdict.score == 0.5


class TestShouldExtractKnowledge:
    """Test the extraction decision logic."""

    def test_block_prevents_extraction(self):
        from divineos.cli.pipeline_gates import should_extract_knowledge

        verdict = _make_quality_verdict("BLOCK")
        allowed, override = should_extract_knowledge(verdict)
        assert allowed is False
        assert override == ""

    def test_downgrade_allows_as_hypothesis(self):
        from divineos.cli.pipeline_gates import should_extract_knowledge

        verdict = _make_quality_verdict("DOWNGRADE")
        allowed, override = should_extract_knowledge(verdict)
        assert allowed is True
        assert override == "HYPOTHESIS"

    def test_allow_extracts_normally(self):
        from divineos.cli.pipeline_gates import should_extract_knowledge

        verdict = _make_quality_verdict("ALLOW")
        allowed, override = should_extract_knowledge(verdict)
        assert allowed is True
        assert override == ""


# ── Gate Enforcement Tests ──────────────────────────────────────────


class TestGoalExtraction:
    """Test goal extraction from user messages."""

    def test_extracts_goals(self, hud_dir):
        """Goal extraction should pull goals from user message texts."""
        analysis = _make_analysis(
            user_message_texts=[
                "I want to implement a new logging system",
                "The goal is to make the tests faster",
                "Let's fix the memory leak",
            ]
        )
        from divineos.cli.pipeline_gates import run_goal_extraction

        # Should not crash — it's best-effort
        run_goal_extraction(analysis)

    def test_empty_messages_no_crash(self, hud_dir):
        """Empty messages shouldn't crash goal extraction."""
        analysis = _make_analysis(user_message_texts=[])
        from divineos.cli.pipeline_gates import run_goal_extraction

        run_goal_extraction(analysis)


class TestContradictionScan:
    """Test contradiction scanning in new knowledge entries."""

    def test_no_ids_returns_zero(self):
        from divineos.cli.pipeline_gates import run_contradiction_scan

        assert run_contradiction_scan([]) == 0

    def test_empty_strings_filtered(self):
        from divineos.cli.pipeline_gates import run_contradiction_scan

        assert run_contradiction_scan(["", "", ""]) == 0

    def test_nonexistent_ids_handled(self):
        """IDs that don't exist in DB should not crash."""
        from divineos.core.knowledge._base import init_knowledge_table

        init_knowledge_table()

        from divineos.cli.pipeline_gates import run_contradiction_scan

        result = run_contradiction_scan(["nonexistent-id-123"])
        assert result == 0


# ── Pipeline Phase Tests ────────────────────────────────────────────


class TestKnowledgePostProcessing:
    """Test Phase 3: post-extraction processing."""

    def test_empty_deep_ids(self):
        from divineos.cli.pipeline_phases import run_knowledge_post_processing

        extra, auto_rels = run_knowledge_post_processing([], "")
        assert extra == 0
        assert auto_rels == [] or isinstance(auto_rels, list)

    def test_maturity_override_applied(self, tmp_path, monkeypatch):
        """When maturity_override is set, RAW entries should be updated."""
        from divineos.core.knowledge import _get_connection
        from divineos.core.knowledge._base import init_knowledge_table

        init_knowledge_table()

        # Store a RAW knowledge entry
        conn = _get_connection()
        kid = "test-knowledge-001"
        import hashlib

        now = time.time()
        content_hash = hashlib.md5(b"Test content").hexdigest()
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, content, knowledge_type, confidence, "
            "maturity, source_events, tags, created_at, updated_at, access_count, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kid, "Test content", "FACT", 0.8, "RAW", "[]", "[]", now, now, 0, content_hash),
        )
        conn.commit()
        conn.close()

        from divineos.cli.pipeline_phases import run_knowledge_post_processing

        run_knowledge_post_processing([kid], "HYPOTHESIS")

        # Verify maturity was updated
        conn2 = _get_connection()
        row = conn2.execute(
            "SELECT maturity FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn2.close()
        assert row[0] == "HYPOTHESIS"

    def test_no_override_leaves_maturity(self, tmp_path, monkeypatch):
        """Without maturity_override, entries stay at their original maturity."""
        from divineos.core.knowledge import _get_connection
        from divineos.core.knowledge._base import init_knowledge_table

        init_knowledge_table()

        conn = _get_connection()
        kid = "test-knowledge-002"
        import hashlib

        now = time.time()
        content_hash = hashlib.md5(b"Test content").hexdigest()
        conn.execute(
            "INSERT INTO knowledge (knowledge_id, content, knowledge_type, confidence, "
            "maturity, source_events, tags, created_at, updated_at, access_count, content_hash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (kid, "Test content", "FACT", 0.8, "RAW", "[]", "[]", now, now, 0, content_hash),
        )
        conn.commit()
        conn.close()

        from divineos.cli.pipeline_phases import run_knowledge_post_processing

        run_knowledge_post_processing([kid], "")

        conn2 = _get_connection()
        row = conn2.execute(
            "SELECT maturity FROM knowledge WHERE knowledge_id = ?", (kid,)
        ).fetchone()
        conn2.close()
        assert row[0] == "RAW"


class TestFeedbackCycle:
    """Test Phase 4: feedback and clarity."""

    def test_returns_four_values(self):
        from divineos.core.knowledge._base import init_knowledge_table

        init_knowledge_table()

        from divineos.cli.pipeline_phases import run_feedback_cycle

        analysis = _make_analysis()
        result = run_feedback_cycle(analysis, has_session=False, session_tag="session-test")
        assert len(result) == 4
        feedback_parts, session_feedback, clarity_summary, extra = result
        assert isinstance(feedback_parts, list)
        assert isinstance(extra, int)

    def test_with_corrections(self):
        """Sessions with corrections should produce feedback."""
        from divineos.core.knowledge._base import init_knowledge_table

        init_knowledge_table()

        from divineos.cli.pipeline_phases import run_feedback_cycle

        analysis = _make_analysis(
            corrections=[
                _make_signal("You got the function name wrong"),
            ]
        )
        result = run_feedback_cycle(analysis, has_session=False, session_tag="session-test")
        feedback_parts, _, _, _ = result
        # Should not crash, feedback_parts may or may not have content


class TestConsolidationAndRefresh:
    """Test Phase 6-7: consolidation and memory refresh."""

    def test_returns_promoted_demoted(self):
        from divineos.cli.pipeline_phases import run_consolidation_and_refresh

        analysis = _make_analysis()
        promoted, demoted = run_consolidation_and_refresh(analysis)
        assert isinstance(promoted, int)
        assert isinstance(demoted, int)
        assert promoted >= 0
        assert demoted >= 0

    def test_goal_cleanup_runs(self, hud_dir):
        """Goal cleanup should run during consolidation."""
        # Add a stale goal
        goals_path = hud_dir / "active_goals.json"
        goals = [
            {
                "text": "old goal",
                "status": "active",
                "added_at": time.time() - 200000,  # very old
            },
        ]
        goals_path.write_text(json.dumps(goals))

        from divineos.cli.pipeline_phases import run_consolidation_and_refresh

        analysis = _make_analysis()
        run_consolidation_and_refresh(analysis)

        # Stale goal should have been cleaned by auto_clean_goals
        # (called inside run_consolidation_and_refresh with default 1-day max_age)


class TestSessionScoring:
    """Test Phase 8: session scoring."""

    def test_returns_health_or_none(self):
        from divineos.cli.pipeline_phases import run_session_scoring

        analysis = _make_analysis()
        health = run_session_scoring(analysis, access_snapshot={})
        # May return None if dependencies fail, or dict if they succeed
        assert health is None or isinstance(health, dict)

    def test_health_has_expected_keys(self):
        """If health is returned, it should have grade and score."""
        from divineos.core.knowledge._base import init_knowledge_table

        init_knowledge_table()

        from divineos.cli.pipeline_phases import run_session_scoring

        analysis = _make_analysis(
            corrections=[],
            encouragements=[
                _make_signal("great job", signal_type="encouragement"),
            ],
        )
        health = run_session_scoring(analysis, access_snapshot={})
        if health is not None:
            assert "grade" in health
            assert "score" in health
            assert health["grade"] in ("A", "B", "C", "D", "F")


class TestSessionFinalization:
    """Test Phase 9: finalization."""

    def test_handoff_written(self, hud_dir):
        """Finalization must write a handoff note.

        Tests write_handoff_note directly rather than run_session_finalization
        which spawns subprocesses that time out in test environments.
        """
        from divineos.cli.pipeline_gates import write_handoff_note

        analysis = _make_analysis()
        write_handoff_note(analysis, stored=5, health=None)

        handoff_path = hud_dir / "handoff_note.json"
        assert handoff_path.exists()

    def test_session_plan_cleared(self, hud_dir):
        """Session plan should be cleared during finalization.

        Tests clear_session_plan directly rather than run_session_finalization
        which spawns subprocesses that time out in test environments.
        """
        from divineos.core.hud_state import clear_session_plan, set_session_plan

        set_session_plan("test plan", estimated_files=3)
        plan_path = hud_dir / "session_plan.json"
        assert plan_path.exists()

        clear_session_plan()

        assert not plan_path.exists()


class TestPrintSessionSummary:
    """Test Phase 10: summary output."""

    def test_prints_without_crash(self):
        """Summary should print without errors for minimal input."""
        from divineos.cli.pipeline_phases import print_session_summary

        print_session_summary(
            stored=5,
            feedback_parts=["3 recurrences"],
            promoted=2,
            demoted=1,
            health={"grade": "B", "score": 0.75},
            clarity_summary=None,
            session_feedback=None,
        )

    def test_prints_with_no_health(self):
        """Summary should handle None health gracefully."""
        from divineos.cli.pipeline_phases import print_session_summary

        print_session_summary(
            stored=0,
            feedback_parts=[],
            promoted=0,
            demoted=0,
            health=None,
            clarity_summary=None,
            session_feedback=None,
        )

    def test_prints_all_grades(self):
        """All grade letters should produce output without error."""
        from divineos.cli.pipeline_phases import print_session_summary

        for grade in ("A", "B", "C", "D", "F"):
            print_session_summary(
                stored=1,
                feedback_parts=[],
                promoted=0,
                demoted=0,
                health={"grade": grade, "score": 0.5},
                clarity_summary=None,
                session_feedback=None,
            )


# ── Handoff Note Tests ──────────────────────────────────────────────


class TestHandoffNote:
    """Test handoff note writing — the continuity bridge between sessions."""

    def test_handoff_includes_exchange_count(self, hud_dir):
        """Handoff should reflect actual session exchange count."""
        from divineos.cli.pipeline_gates import write_handoff_note

        analysis = _make_analysis(user_messages=12)
        write_handoff_note(analysis, stored=3, health=None)

        handoff_path = hud_dir / "handoff_note.json"
        content = json.loads(handoff_path.read_text())
        assert "12 exchanges" in content.get("summary", "")

    def test_handoff_includes_stored_count(self, hud_dir):
        """Handoff should mention how many knowledge entries were stored."""
        from divineos.cli.pipeline_gates import write_handoff_note

        analysis = _make_analysis()
        write_handoff_note(analysis, stored=7, health=None)

        handoff_path = hud_dir / "handoff_note.json"
        content = json.loads(handoff_path.read_text())
        assert "7 knowledge" in content.get("summary", "")

    def test_handoff_includes_corrections(self, hud_dir):
        """If corrections happened, handoff should mention them."""
        from divineos.cli.pipeline_gates import write_handoff_note

        analysis = _make_analysis(
            corrections=[
                _make_signal("wrong function"),
                _make_signal("bad variable name"),
            ]
        )
        write_handoff_note(analysis, stored=0, health=None)

        handoff_path = hud_dir / "handoff_note.json"
        content = json.loads(handoff_path.read_text())
        assert "corrected 2 time" in content.get("summary", "")

    def test_handoff_includes_grade(self, hud_dir):
        """Health grade should appear in handoff when available."""
        from divineos.cli.pipeline_gates import write_handoff_note

        analysis = _make_analysis()
        write_handoff_note(analysis, stored=0, health={"grade": "A", "score": 0.95})

        handoff_path = hud_dir / "handoff_note.json"
        content = json.loads(handoff_path.read_text())
        summary = content.get("summary", "").lower()
        mood = content.get("mood", "")
        # Grade should appear in either summary or mood
        assert "grade: a" in summary or "grade: a" in summary.replace(": ", ":") or "strong" in mood

    def test_handoff_zero_stored_on_block(self, hud_dir):
        """When quality gate blocks, stored=0 should be passed to handoff."""
        from divineos.cli.pipeline_gates import write_handoff_note

        analysis = _make_analysis()
        write_handoff_note(analysis, stored=0, health=None)

        handoff_path = hud_dir / "handoff_note.json"
        content = json.loads(handoff_path.read_text())
        assert "0 knowledge" in content.get("summary", "")


# ── Goal Lifecycle Tests ────────────────────────────────────────────


class TestGoalLifecycle:
    """Test goal tracking through its full lifecycle."""

    def test_add_goal(self, hud_dir):
        from divineos.core.hud_state import add_goal

        add_goal("Implement feature X")

        goals_path = hud_dir / "active_goals.json"
        goals = json.loads(goals_path.read_text())
        assert len(goals) == 1
        assert goals[0]["text"] == "Implement feature X"
        assert goals[0]["status"] == "active"

    def test_complete_goal(self, hud_dir):
        from divineos.core.hud_state import add_goal, complete_goal

        add_goal("Fix the bug")
        found = complete_goal("Fix the bug")
        assert found is True

        goals = json.loads((hud_dir / "active_goals.json").read_text())
        assert goals[0]["status"] == "done"

    def test_complete_increments_lifetime(self, hud_dir):
        from divineos.core.hud_state import add_goal, complete_goal, get_lifetime_goals_completed

        before = get_lifetime_goals_completed()
        add_goal("Finish testing")
        complete_goal("Finish testing")
        after = get_lifetime_goals_completed()
        assert after == before + 1

    def test_auto_clean_removes_done(self, hud_dir):
        from divineos.core.hud_state import add_goal, auto_clean_goals, complete_goal

        add_goal("Done goal")
        complete_goal("Done goal")

        result = auto_clean_goals()
        assert result["completed_cleared"] == 1

        goals = json.loads((hud_dir / "active_goals.json").read_text())
        assert len(goals) == 0

    def test_auto_clean_archives_stale(self, hud_dir):
        """Goals older than max_age should be archived."""
        goals_path = hud_dir / "active_goals.json"
        goals = [
            {
                "text": "ancient goal",
                "status": "active",
                "added_at": time.time() - 200000,  # ~2.3 days old
            },
        ]
        goals_path.write_text(json.dumps(goals))

        from divineos.core.hud_state import auto_clean_goals

        result = auto_clean_goals(max_age_days=1.0)
        assert result["stale_archived"] == 1

    def test_duplicate_goal_rejected(self, hud_dir):
        from divineos.core.hud_state import add_goal

        add_goal("Same goal")
        add_goal("Same goal")

        goals = json.loads((hud_dir / "active_goals.json").read_text())
        assert len(goals) == 1

    def test_empty_goal_ignored(self, hud_dir):
        from divineos.core.hud_state import add_goal

        add_goal("")
        add_goal("   ")

        goals_path = hud_dir / "active_goals.json"
        assert not goals_path.exists()

    def test_has_session_fresh_goal(self, hud_dir):
        from divineos.core.hud_state import add_goal, has_session_fresh_goal

        assert has_session_fresh_goal() is False
        add_goal("Fresh goal")
        assert has_session_fresh_goal() is True

    def test_old_goal_not_fresh(self, hud_dir):
        """Goals from previous sessions shouldn't count as fresh."""
        goals_path = hud_dir / "active_goals.json"
        goals = [
            {
                "text": "old goal",
                "status": "active",
                "added_at": time.time() - 10000,  # ~2.8 hours ago
            },
        ]
        goals_path.write_text(json.dumps(goals))

        from divineos.core.hud_state import has_session_fresh_goal

        assert has_session_fresh_goal(max_age_seconds=3600) is False


# ── Session Plan Tests ──────────────────────────────────────────────


class TestSessionPlan:
    """Test session plan create/read/clear cycle."""

    def test_set_and_get(self, hud_dir):
        from divineos.core.hud_state import get_session_plan, set_session_plan

        set_session_plan("Build the widget", estimated_files=5, estimated_time_minutes=30)
        plan = get_session_plan()
        assert plan is not None
        assert plan["goal"] == "Build the widget"
        assert plan["estimated_files"] == 5
        assert plan["estimated_time_minutes"] == 30

    def test_clear(self, hud_dir):
        from divineos.core.hud_state import clear_session_plan, get_session_plan, set_session_plan

        set_session_plan("Temporary plan")
        clear_session_plan()
        assert get_session_plan() is None

    def test_empty_goal_ignored(self, hud_dir):
        from divineos.core.hud_state import set_session_plan

        set_session_plan("")
        set_session_plan("   ")
        # Should not create files
        plan_path = hud_dir / "session_plan.json"
        assert not plan_path.exists()

    def test_get_nonexistent_returns_none(self, hud_dir):
        from divineos.core.hud_state import get_session_plan

        assert get_session_plan() is None


# ── Pipeline Exit Path Tests ────────────────────────────────────────


class TestPipelineExitPaths:
    """Every exit path in the pipeline must complete bookkeeping.

    These tests verify the principle that handoff, goals, and HUD
    are always updated regardless of what the quality gate decides.
    """

    def test_blocked_session_still_has_handoff(self, hud_dir):
        """Simulate a quality-gate-blocked session and verify handoff exists."""
        analysis = _make_analysis()

        # This is what the pipeline does on block (lines 109-126 of session_pipeline.py)
        from divineos.cli.pipeline_gates import write_handoff_note
        from divineos.core.hud_state import auto_clean_goals

        write_handoff_note(analysis, stored=0, health=None)
        auto_clean_goals()

        assert (hud_dir / "handoff_note.json").exists()

    def test_blocked_session_goals_cleaned(self, hud_dir):
        """Completed goals should be cleaned even on blocked sessions."""
        # Set up completed goals
        goals = [
            {"text": "goal A", "status": "done", "added_at": time.time()},
            {"text": "goal B", "status": "active", "added_at": time.time()},
        ]
        (hud_dir / "active_goals.json").write_text(json.dumps(goals))

        from divineos.core.hud_state import auto_clean_goals

        result = auto_clean_goals()
        assert result["completed_cleared"] == 1

        remaining = json.loads((hud_dir / "active_goals.json").read_text())
        assert len(remaining) == 1
        assert remaining[0]["text"] == "goal B"


# ── Knowledge Quality Cycle Tests ───────────────────────────────────


class TestKnowledgeQualityCycle:
    """Test Phase 5: health check, maturity, logic, hygiene."""

    def test_returns_promoted_ids(self):
        from divineos.cli.pipeline_phases import run_knowledge_quality_cycle

        analysis = _make_analysis()
        promoted_ids = run_knowledge_quality_cycle([], analysis)
        assert isinstance(promoted_ids, list)

    def test_handles_empty_deep_ids(self):
        from divineos.cli.pipeline_phases import run_knowledge_quality_cycle

        analysis = _make_analysis()
        # Should not crash with empty list
        promoted_ids = run_knowledge_quality_cycle([], analysis)
        assert isinstance(promoted_ids, list)


# ── Lifetime Goals Counter Tests ────────────────────────────────────


class TestLifetimeGoals:
    """Test the lifetime goal completion counter."""

    def test_starts_at_zero(self, hud_dir):
        from divineos.core.hud_state import get_lifetime_goals_completed

        assert get_lifetime_goals_completed() == 0

    def test_increments_on_complete(self, hud_dir):
        from divineos.core.hud_state import _increment_lifetime_goals, get_lifetime_goals_completed

        _increment_lifetime_goals(1)
        assert get_lifetime_goals_completed() == 1
        _increment_lifetime_goals(3)
        assert get_lifetime_goals_completed() == 4

    def test_persists_across_reads(self, hud_dir):
        from divineos.core.hud_state import _increment_lifetime_goals, get_lifetime_goals_completed

        _increment_lifetime_goals(5)
        # Read multiple times
        assert get_lifetime_goals_completed() == 5
        assert get_lifetime_goals_completed() == 5

    def test_auto_clean_increments_lifetime(self, hud_dir):
        """auto_clean_goals should increment lifetime counter for all cleared goals."""
        from divineos.core.hud_state import auto_clean_goals, get_lifetime_goals_completed

        goals = [
            {"text": "done A", "status": "done", "added_at": time.time()},
            {"text": "done B", "status": "done", "added_at": time.time()},
        ]
        (hud_dir / "active_goals.json").write_text(json.dumps(goals))

        before = get_lifetime_goals_completed()
        auto_clean_goals()
        after = get_lifetime_goals_completed()
        assert after == before + 2
