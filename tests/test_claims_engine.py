"""Tests for the claims engine and affect log."""

import os

import pytest
from click.testing import CliRunner

from divineos.core.affect import (
    count_affect_entries,
    get_affect_history,
    get_affect_summary,
    log_affect,
)
from divineos.core.claim_store import (
    STATUS_INVESTIGATING,
    STATUS_OPEN,
    STATUS_SUPPORTED,
    TIER_EMPIRICAL,
    TIER_INFERENTIAL,
    TIER_METAPHYSICAL,
    TIER_SPECULATIVE,
    add_evidence,
    count_claims,
    file_claim,
    get_claim,
    get_evidence_for_claim,
    list_claims,
    search_claims,
    update_claim,
)


@pytest.fixture(autouse=True)
def _isolate_db(tmp_path):
    os.environ["DIVINEOS_DB"] = str(tmp_path / "test.db")
    from divineos.core.ledger import init_db

    init_db()
    yield
    os.environ.pop("DIVINEOS_DB", None)


# ── Claims Store ──────────────────────────────────────────────────────


class TestFileClaim:
    def test_returns_uuid(self):
        cid = file_claim("The moon affects tides")
        assert len(cid) == 36

    def test_defaults(self):
        cid = file_claim("Test claim")
        claim = get_claim(cid)
        assert claim["tier"] == TIER_SPECULATIVE
        assert claim["status"] == STATUS_OPEN
        assert claim["confidence"] == 0.5

    def test_full_fields(self):
        cid = file_claim(
            statement="Dark matter exists",
            tier=TIER_INFERENTIAL,
            context="Gravitational effects observed",
            promotion_criteria="Direct detection in particle accelerator",
            demotion_criteria="Alternative gravity theory explains all effects",
            tags=["physics", "cosmology"],
            session_id="s1",
        )
        claim = get_claim(cid)
        assert claim["statement"] == "Dark matter exists"
        assert claim["tier"] == TIER_INFERENTIAL
        assert claim["tier_label"] == "inferential"
        assert claim["context"] == "Gravitational effects observed"
        assert claim["promotion_criteria"] == "Direct detection in particle accelerator"
        assert "physics" in claim["tags"]

    def test_tier_clamped(self):
        cid = file_claim("test", tier=99)
        assert get_claim(cid)["tier"] == TIER_METAPHYSICAL


class TestAddEvidence:
    def test_adds_evidence(self):
        cid = file_claim("Water boils at 100C at sea level")
        eid = add_evidence(
            cid, "Measured in lab", direction="SUPPORTS", source="empirical", strength=0.9
        )
        assert len(eid) == 36

        evidence = get_evidence_for_claim(cid)
        assert len(evidence) == 1
        assert evidence[0]["direction"] == "SUPPORTS"
        assert evidence[0]["source"] == "empirical"
        assert evidence[0]["strength"] == 0.9

    def test_confidence_recalculated(self):
        cid = file_claim("Test claim")
        add_evidence(cid, "Strong support", direction="SUPPORTS", strength=0.8)
        claim = get_claim(cid)
        assert claim["confidence"] == 1.0  # only supporting evidence

        add_evidence(cid, "Some contradiction", direction="CONTRADICTS", strength=0.4)
        claim = get_claim(cid)
        # 0.8 / (0.8 + 0.4) = 0.667
        assert 0.6 < claim["confidence"] < 0.7

    def test_resonance_source(self):
        cid = file_claim("This architecture feels right")
        add_evidence(
            cid, "Strong pattern coherence", direction="SUPPORTS", source="resonance", strength=0.5
        )
        evidence = get_evidence_for_claim(cid)
        assert evidence[0]["source"] == "resonance"


class TestUpdateClaim:
    def test_update_status(self):
        cid = file_claim("Test")
        assert update_claim(cid, status=STATUS_INVESTIGATING)
        assert get_claim(cid)["status"] == STATUS_INVESTIGATING

    def test_update_tier(self):
        cid = file_claim("Test", tier=TIER_SPECULATIVE)
        update_claim(cid, tier=TIER_INFERENTIAL)
        assert get_claim(cid)["tier"] == TIER_INFERENTIAL

    def test_update_assessment(self):
        cid = file_claim("Test")
        update_claim(cid, assessment="Evidence strongly supports this")
        assert get_claim(cid)["assessment"] == "Evidence strongly supports this"

    def test_nonexistent_returns_false(self):
        assert update_claim("nonexistent", status="OPEN") is False

    def test_no_op_update_returns_false(self):
        """Updating with values equal to prior is a no-op — no row write,
        no CLAIM_UPDATED emit. Keep-drift-entries pre-reg prereg-75cde9cd07b3:
        emits only happen on real changes, so the audit trail isn't padded
        with empty events."""
        cid = file_claim("Test", tier=TIER_SPECULATIVE)
        assert update_claim(cid, tier=TIER_INFERENTIAL)
        assert update_claim(cid, tier=TIER_INFERENTIAL) is False

    def test_update_emits_claim_updated_event_with_prior(self):
        """update_claim must emit CLAIM_UPDATED to the main event_ledger
        capturing prior and new values for every changed field. Pre-reg
        prereg-75cde9cd07b3: append-only is structural humility — the
        embarrassing prior version of an assessment must be preserved
        in the hash-chained ledger forever, even if the row is later
        overwritten again.

        Falsifier: an update_claim call whose changed fields don't surface
        as a CLAIM_UPDATED event with the prior value in the ledger.
        """
        from divineos.core.ledger import get_events

        cid = file_claim("Test claim for audit-trail check")
        update_claim(cid, assessment="initial assessment, possibly wrong")
        update_claim(cid, assessment="revised assessment, embarrassed")

        events = get_events(limit=50, event_type="CLAIM_UPDATED")
        found_priors = []
        for ev in events:
            payload = ev.get("payload") or {}
            if isinstance(payload, str):
                import json

                payload = json.loads(payload)
            if payload.get("claim_id") == cid:
                changed = payload.get("changed_fields", {})
                if "assessment" in changed:
                    found_priors.append(changed["assessment"]["prior"])

        assert "initial assessment, possibly wrong" in found_priors, (
            f"prior assessment not preserved in CLAIM_UPDATED ledger event; "
            f"found priors: {found_priors}"
        )


class TestGetClaim:
    def test_full_id(self):
        cid = file_claim("Test")
        assert get_claim(cid) is not None

    def test_short_id(self):
        cid = file_claim("Test")
        assert get_claim(cid[:8]) is not None

    def test_not_found(self):
        assert get_claim("nonexistent") is None

    def test_includes_evidence(self):
        cid = file_claim("Test")
        add_evidence(cid, "Evidence 1", direction="SUPPORTS")
        add_evidence(cid, "Evidence 2", direction="CONTRADICTS")
        claim = get_claim(cid)
        assert len(claim["evidence"]) == 2


class TestListClaims:
    def test_empty(self):
        assert list_claims() == []

    def test_newest_first(self):
        file_claim("First")
        file_claim("Second")
        claims = list_claims()
        assert claims[0]["statement"] == "Second"

    def test_filter_by_tier(self):
        file_claim("Empirical", tier=TIER_EMPIRICAL)
        file_claim("Speculative", tier=TIER_SPECULATIVE)
        assert len(list_claims(tier=TIER_EMPIRICAL)) == 1

    def test_filter_by_status(self):
        cid = file_claim("Test")
        update_claim(cid, status=STATUS_SUPPORTED)
        file_claim("Another")
        assert len(list_claims(status=STATUS_SUPPORTED)) == 1


class TestSearchClaims:
    def test_search_by_statement(self):
        file_claim("Dark matter causes gravitational lensing")
        file_claim("Water is wet")
        results = search_claims("gravitational")
        assert len(results) == 1

    def test_search_empty(self):
        assert search_claims("") == []

    def test_no_results(self):
        file_claim("Something about physics")
        assert search_claims("biology") == []


class TestCountClaims:
    def test_empty(self):
        counts = count_claims()
        assert counts["total"] == 0

    def test_counts_by_status(self):
        file_claim("A")
        cid = file_claim("B")
        update_claim(cid, status=STATUS_SUPPORTED)
        counts = count_claims()
        assert counts["total"] == 2
        assert counts[STATUS_OPEN] == 1
        assert counts[STATUS_SUPPORTED] == 1


# ── Affect Log ────────────────────────────────────────────────────────


class TestLogAffect:
    def test_returns_uuid(self):
        eid = log_affect(0.5, 0.5)
        assert len(eid) == 36

    def test_full_fields(self):
        log_affect(
            valence=0.8,
            arousal=0.7,
            description="Engaged and resonant",
            trigger="Building something meaningful",
            tags=["flow", "creation"],
            session_id="s1",
        )
        history = get_affect_history(limit=1)
        assert len(history) == 1
        entry = history[0]
        assert entry["valence"] == 0.8
        assert entry["arousal"] == 0.7
        assert entry["description"] == "Engaged and resonant"
        assert entry["trigger"] == "Building something meaningful"
        assert "flow" in entry["tags"]

    def test_clamped(self):
        log_affect(valence=5.0, arousal=-3.0)
        entry = get_affect_history(limit=1)[0]
        assert entry["valence"] == 1.0
        assert entry["arousal"] == 0.0

    def test_negative_valence(self):
        log_affect(valence=-0.7, arousal=0.8, description="Dissonance")
        entry = get_affect_history(limit=1)[0]
        assert entry["valence"] == -0.7


class TestAffectHistory:
    def test_empty(self):
        assert get_affect_history() == []

    def test_newest_first(self):
        log_affect(0.3, 0.3, description="First")
        log_affect(0.6, 0.6, description="Second")
        history = get_affect_history()
        assert history[0]["description"] == "Second"

    def test_limit(self):
        for i in range(10):
            log_affect(float(i) / 10, 0.5)
        assert len(get_affect_history(limit=3)) == 3


class TestAffectSummary:
    def test_empty(self):
        summary = get_affect_summary()
        assert summary["count"] == 0
        assert summary["trend"] == "no data"

    def test_averages(self):
        log_affect(0.4, 0.6)
        log_affect(0.8, 0.2)
        summary = get_affect_summary()
        assert summary["count"] == 2
        assert summary["avg_valence"] == 0.6
        assert summary["avg_arousal"] == 0.4

    def test_trend_improving(self):
        # Older entries (logged first) have low valence
        for _ in range(4):
            log_affect(-0.5, 0.5)
        # Recent entries have high valence
        for _ in range(4):
            log_affect(0.8, 0.5)
        summary = get_affect_summary()
        assert summary["trend"] == "improving"

    def test_trend_stable(self):
        for _ in range(8):
            log_affect(0.5, 0.5)
        summary = get_affect_summary()
        assert summary["trend"] == "stable"


class TestCountAffect:
    def test_empty(self):
        assert count_affect_entries() == 0

    def test_counts(self):
        log_affect(0.5, 0.5)
        log_affect(0.3, 0.7)
        assert count_affect_entries() == 2


# ── CLI Tests ─────────────────────────────────────────────────────────


class TestClaimsCLI:
    def test_claim_command(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["claim", "Test claim"])
        assert result.exit_code == 0
        assert "Claim filed" in result.output

    def test_claims_list(self):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["claim", "First claim"])
        result = runner.invoke(cli, ["claims", "list"])
        assert result.exit_code == 0
        assert "First claim" in result.output

    def test_claims_search(self):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["claim", "Gravity bends light"])
        result = runner.invoke(cli, ["claims", "search", "Gravity"])
        assert result.exit_code == 0
        assert "Gravity" in result.output

    def test_claims_tiers(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["claims", "tiers"])
        assert result.exit_code == 0
        assert "EMPIRICAL" in result.output
        assert "METAPHYSICAL" in result.output

    def test_feel_command(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["feel", "-v", "0.7", "-a", "0.5", "-d", "Good flow"])
        assert result.exit_code == 0
        assert "Affect logged" in result.output

    def test_affect_history(self):
        from divineos.cli import cli

        runner = CliRunner()
        runner.invoke(cli, ["feel", "-v", "0.5", "-a", "0.5"])
        result = runner.invoke(cli, ["affect", "history"])
        assert result.exit_code == 0

    def test_affect_summary(self):
        from divineos.cli import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["affect", "summary"])
        assert result.exit_code == 0
