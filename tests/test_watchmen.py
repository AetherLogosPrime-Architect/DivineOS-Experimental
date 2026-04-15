"""Tests for the Watchmen external validation module."""

import os

import pytest

from divineos.core.ledger import init_db
from divineos.core.knowledge._base import init_knowledge_table
from divineos.core.watchmen._schema import init_watchmen_tables
from divineos.core.watchmen.types import (
    EXTERNAL_ACTORS,
    INTERNAL_ACTORS,
    FindingStatus,
)
from divineos.core.watchmen.store import (
    _validate_actor,
    get_finding,
    get_round,
    list_findings,
    list_rounds,
    resolve_finding,
    submit_finding,
    submit_round,
)
from divineos.core.watchmen.summary import (
    format_watchmen_summary,
    get_watchmen_stats,
    unresolved_findings,
)


@pytest.fixture(autouse=True)
def _watchmen_db(tmp_path):
    """Set up a fresh database for each test."""
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    try:
        init_db()
        init_knowledge_table()
        init_watchmen_tables()
        yield
    finally:
        os.environ.pop("DIVINEOS_DB", None)


# ── Actor Validation ─────────────────────────────────────────────────


class TestActorValidation:
    def test_external_actors_accepted(self):
        for actor in EXTERNAL_ACTORS:
            assert _validate_actor(actor) == actor

    def test_internal_actors_rejected(self):
        for actor in INTERNAL_ACTORS:
            with pytest.raises(ValueError, match="internal component"):
                _validate_actor(actor)

    def test_system_rejected(self):
        with pytest.raises(ValueError, match="internal component"):
            _validate_actor("system")

    def test_pipeline_rejected(self):
        with pytest.raises(ValueError, match="internal component"):
            _validate_actor("pipeline")

    def test_empty_actor_rejected(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            _validate_actor("")

    def test_case_normalization(self):
        assert _validate_actor("GROK") == "grok"
        assert _validate_actor("  User  ") == "user"

    def test_unknown_external_actor_allowed(self):
        # Unknown actors that aren't in INTERNAL_ACTORS are allowed
        result = _validate_actor("new-auditor")
        assert result == "new-auditor"


# ── Round Submission ─────────────────────────────────────────────────


class TestSubmitRound:
    def test_create_round(self):
        rid = submit_round(actor="grok", focus="Dice coefficient impact audit")
        assert rid.startswith("round-")

    def test_round_with_experts(self):
        rid = submit_round(actor="grok", focus="Round 6", expert_count=25, notes="Full council")
        r = get_round(rid)
        assert r is not None
        assert r.expert_count == 25
        assert r.notes == "Full council"
        assert r.actor == "grok"

    def test_internal_actor_blocked(self):
        with pytest.raises(ValueError, match="internal component"):
            submit_round(actor="system", focus="Self-audit attempt")

    def test_list_rounds(self):
        submit_round(actor="grok", focus="Round 1")
        submit_round(actor="user", focus="Round 2")
        rounds = list_rounds()
        assert len(rounds) == 2
        # Most recent first
        assert rounds[0].focus == "Round 2"


# ── Finding Submission ───────────────────────────────────────────────


class TestSubmitFinding:
    def test_basic_finding(self):
        rid = submit_round(actor="grok", focus="Test audit")
        fid = submit_finding(
            round_id=rid,
            actor="grok",
            severity="HIGH",
            category="KNOWLEDGE",
            title="Stemmed overlap still uses min-denominator",
            description="The _compute_stemmed_overlap function was not converted to Dice.",
        )
        assert fid.startswith("find-")

    def test_finding_with_recommendation(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            round_id=rid,
            actor="grok",
            severity="MEDIUM",
            category="ARCHITECTURE",
            title="Magic numbers in relationships.py",
            description="Seven hardcoded thresholds found.",
            recommendation="Replace with constants from constants.py",
            tags=["dice", "thresholds"],
        )
        f = get_finding(fid)
        assert f is not None
        assert f.recommendation == "Replace with constants from constants.py"
        assert "dice" in f.tags

    def test_invalid_round_rejected(self):
        with pytest.raises(ValueError, match="does not exist"):
            submit_finding(
                round_id="nonexistent",
                actor="grok",
                severity="LOW",
                category="KNOWLEDGE",
                title="Test",
                description="Test",
            )

    def test_invalid_severity_rejected(self):
        rid = submit_round(actor="grok", focus="Test")
        with pytest.raises(ValueError, match="Invalid severity"):
            submit_finding(
                round_id=rid,
                actor="grok",
                severity="APOCALYPTIC",
                category="KNOWLEDGE",
                title="Test",
                description="Test",
            )

    def test_invalid_category_rejected(self):
        rid = submit_round(actor="grok", focus="Test")
        with pytest.raises(ValueError, match="Invalid category"):
            submit_finding(
                round_id=rid,
                actor="grok",
                severity="LOW",
                category="NONSENSE",
                title="Test",
                description="Test",
            )

    def test_internal_actor_blocked_on_finding(self):
        rid = submit_round(actor="grok", focus="Test")
        with pytest.raises(ValueError, match="internal component"):
            submit_finding(
                round_id=rid,
                actor="assistant",
                severity="LOW",
                category="KNOWLEDGE",
                title="Self-submitted finding",
                description="The OS trying to audit itself.",
            )

    def test_finding_count_incremented(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(
            round_id=rid,
            actor="grok",
            severity="LOW",
            category="KNOWLEDGE",
            title="F1",
            description="D1",
        )
        submit_finding(
            round_id=rid,
            actor="grok",
            severity="HIGH",
            category="BEHAVIOR",
            title="F2",
            description="D2",
        )
        r = get_round(rid)
        assert r.finding_count == 2


# ── Listing & Filtering ─────────────────────────────────────────────


class TestListFindings:
    def test_filter_by_severity(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        submit_finding(rid, "grok", "LOW", "KNOWLEDGE", "B", "D")
        high = list_findings(severity="HIGH")
        assert len(high) == 1
        assert high[0].title == "A"

    def test_filter_by_category(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        submit_finding(rid, "grok", "HIGH", "BEHAVIOR", "B", "D")
        knowledge = list_findings(category="KNOWLEDGE")
        assert len(knowledge) == 1

    def test_filter_by_status(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        resolve_finding(fid, "RESOLVED", "Fixed it")
        open_findings = list_findings(status="OPEN")
        assert len(open_findings) == 0
        resolved = list_findings(status="RESOLVED")
        assert len(resolved) == 1


# ── Resolution ───────────────────────────────────────────────────────


class TestResolveFinding:
    def test_resolve_existing(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        assert resolve_finding(fid, "RESOLVED", "Converted to Dice")
        f = get_finding(fid)
        assert f.status == FindingStatus.RESOLVED
        assert f.resolution_notes == "Converted to Dice"

    def test_resolve_nonexistent(self):
        assert not resolve_finding("nonexistent", "RESOLVED")

    def test_invalid_status(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        with pytest.raises(ValueError, match="Invalid status"):
            resolve_finding(fid, "EXPLODED")

    def test_wont_fix(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "LOW", "KNOWLEDGE", "A", "D")
        resolve_finding(fid, "WONT_FIX", "By design")
        f = get_finding(fid)
        assert f.status == FindingStatus.WONT_FIX


# ── Summary & Statistics ─────────────────────────────────────────────


class TestSummary:
    def test_empty_stats(self):
        stats = get_watchmen_stats()
        assert stats["total_findings"] == 0
        assert stats["total_rounds"] == 0

    def test_stats_with_data(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        submit_finding(rid, "grok", "CRITICAL", "BEHAVIOR", "B", "D")
        submit_finding(rid, "grok", "LOW", "LEARNING", "C", "D")
        stats = get_watchmen_stats()
        assert stats["total_findings"] == 3
        assert stats["total_rounds"] == 1
        assert stats["by_severity"]["HIGH"] == 1
        assert stats["by_severity"]["CRITICAL"] == 1
        assert stats["open_count"] == 3

    def test_unresolved_ordered_by_severity(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "LOW", "KNOWLEDGE", "Low one", "D")
        submit_finding(rid, "grok", "CRITICAL", "BEHAVIOR", "Critical one", "D")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "High one", "D")
        unresolved = unresolved_findings()
        assert unresolved[0]["severity"] == "CRITICAL"
        assert unresolved[1]["severity"] == "HIGH"
        assert unresolved[2]["severity"] == "LOW"

    def test_resolved_not_in_unresolved(self):
        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        resolve_finding(fid, "RESOLVED")
        assert len(unresolved_findings()) == 0

    def test_format_empty(self):
        assert format_watchmen_summary() == ""

    def test_format_with_findings(self):
        rid = submit_round(actor="grok", focus="Test")
        submit_finding(rid, "grok", "HIGH", "KNOWLEDGE", "A", "D")
        summary = format_watchmen_summary()
        assert "Watchmen" in summary
        assert "high" in summary.lower()


# ── Router ───────────────────────────────────────────────────────────


class TestRouter:
    def test_route_to_knowledge(self):
        from divineos.core.watchmen.router import route_finding

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "MEDIUM",
            "KNOWLEDGE",
            "FTS5 uses AND logic killing recall",
            "The _extract_key_terms function produces space-separated terms that FTS5 treats as implicit AND",
            recommendation="Use _build_fts_query with OR-joined terms",
        )
        finding = get_finding(fid)
        result = route_finding(finding)
        assert result["action"] == "knowledge"
        assert result["id"]  # Got a knowledge_id back

        # Finding should now be ROUTED
        updated = get_finding(fid)
        assert updated.status == FindingStatus.ROUTED

    def test_route_critical_behavior_to_claim(self):
        from divineos.core.watchmen.router import route_finding
        from divineos.core.claim_store import init_claim_tables

        init_claim_tables()

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "CRITICAL",
            "BEHAVIOR",
            "Self-referential evaluation loop",
            "The OS evaluates itself with no external anchor for calibration",
        )
        finding = get_finding(fid)
        result = route_finding(finding)
        assert result["action"] == "claim"
        assert result["id"].startswith("claim-")

    def test_route_learning_to_lesson(self):
        from divineos.core.watchmen.router import route_finding

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "MEDIUM",
            "LEARNING",
            "Maturity pipeline stalled",
            "75% of knowledge entries stuck at RAW maturity level",
        )
        finding = get_finding(fid)
        result = route_finding(finding)
        assert result["action"] == "lesson"

    def test_skip_already_routed(self):
        from divineos.core.watchmen.router import route_finding

        rid = submit_round(actor="grok", focus="Test")
        fid = submit_finding(
            rid,
            "grok",
            "LOW",
            "KNOWLEDGE",
            "Test",
            "Test finding",
        )
        finding = get_finding(fid)
        route_finding(finding)  # First route

        # Try to route again — should skip
        updated = get_finding(fid)
        result = route_finding(updated)
        assert result["action"] == "skipped"

    def test_route_round(self):
        from divineos.core.watchmen.router import route_round

        rid = submit_round(actor="grok", focus="Test round")
        submit_finding(
            rid,
            "grok",
            "HIGH",
            "KNOWLEDGE",
            "Knowledge maturity pipeline stalled at RAW level",
            "Seventy-five percent of knowledge entries remain at RAW maturity with zero promotions observed",
        )
        submit_finding(
            rid,
            "grok",
            "LOW",
            "ARCHITECTURE",
            "Magic numbers scattered across relationship classification",
            "Seven hardcoded threshold values found in the relationship classification module need extraction",
        )
        results = route_round(rid)
        assert len(results) == 2
        routed = sum(1 for r in results if r["action"] != "skipped")
        assert routed >= 1


# ── Self-Trigger Prevention ──────────────────────────────────────────


class TestSelfTriggerPrevention:
    """The three structural guarantees against self-auditing."""

    def test_layer_1_actor_validation(self):
        """Internal actors are rejected at the store level."""
        with pytest.raises(ValueError):
            submit_round(actor="system", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="assistant", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="pipeline", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="divineos", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="hook", focus="Self-audit")
        with pytest.raises(ValueError):
            submit_round(actor="schedule", focus="Self-audit")

    def test_layer_1_finding_also_validates(self):
        """Even if a round exists, internal actors can't submit findings."""
        rid = submit_round(actor="grok", focus="Legit round")
        with pytest.raises(ValueError):
            submit_finding(
                round_id=rid,
                actor="system",
                severity="HIGH",
                category="KNOWLEDGE",
                title="Self-submitted",
                description="Trying to audit myself",
            )
