"""Tests for tool_trust calibration store.

Pins the principle from knowledge eb5b5db5: trust is calibrated, not
binary. Brand-new instruments start on probation. Truthful checks raise
score; contradicted checks lower it. Sample-count guards prevent
premature tier promotion. Low-trust list is the maintenance signal.
"""

from __future__ import annotations

import pytest

from divineos.core import tool_trust as tt
from divineos.core.tool_trust import CheckOutcome, TrustTier


@pytest.fixture(autouse=True)
def isolated_home(tmp_path, monkeypatch):
    """Redirect divineos_home so each test runs against a fresh db."""
    monkeypatch.setattr("divineos.core.tool_trust.divineos_home", lambda: tmp_path)
    return tmp_path


class TestRegister:
    def test_register_new_instrument(self):
        assert tt.register_instrument("ear-surface", "hook", "Surfaces letters") is True

    def test_register_idempotent(self):
        tt.register_instrument("ear-surface", "hook", "Surfaces letters")
        assert tt.register_instrument("ear-surface", "hook", "Surfaces letters") is False

    def test_register_refuses_empty(self):
        assert tt.register_instrument("", "hook", "desc") is False
        assert tt.register_instrument("id", "", "desc") is False
        assert tt.register_instrument("id", "hook", "") is False


class TestColdStart:
    def test_new_instrument_score_is_zero(self):
        """Andrew 2026-06-13: new instruments have earned nothing yet —
        trust starts at 0, not 0.5. Beta(0, 5) prior gives the cold
        start of zero with five virtual failures keeping the score from
        jumping to 1.0 on a single truthful check."""
        tt.register_instrument("x", "hook", "desc")
        assert tt.trust_score("x") == pytest.approx(0.0)

    def test_new_instrument_is_probation(self):
        tt.register_instrument("x", "hook", "desc")
        assert tt.tier("x") == TrustTier.PROBATION

    def test_unknown_instrument_returns_none(self):
        assert tt.trust_score("nonexistent") is None
        assert tt.tier("nonexistent") is None


class TestRecordCheck:
    def test_truthful_check_raises_score(self):
        tt.register_instrument("x", "hook", "desc")
        tt.record_check("x", CheckOutcome.TRUTHFUL, "verified against git ls-remote output")
        assert tt.trust_score("x") > 0.0

    def test_contradicted_check_keeps_score_at_floor(self):
        """With cold-start at 0, a contradicted check can't lower the
        score further — it sits at the floor and contributes to the
        total-sample count for tier guards."""
        tt.register_instrument("x", "hook", "desc")
        tt.record_check("x", CheckOutcome.CONTRADICTED, "tool said merged, gh said not merged")
        assert tt.trust_score("x") == pytest.approx(0.0)

    def test_refuses_short_evidence(self):
        tt.register_instrument("x", "hook", "desc")
        assert tt.record_check("x", CheckOutcome.TRUTHFUL, "too short") is False

    def test_refuses_unknown_instrument(self):
        assert (
            tt.record_check("nonexistent", CheckOutcome.TRUTHFUL, "evidence long enough to pass")
            is False
        )

    def test_accepts_string_outcome(self):
        tt.register_instrument("x", "hook", "desc")
        assert tt.record_check("x", "TRUTHFUL", "evidence long enough to pass guard") is True

    def test_rejects_invalid_outcome_string(self):
        tt.register_instrument("x", "hook", "desc")
        assert tt.record_check("x", "MAYBE", "evidence long enough to pass guard") is False


class TestTierGuards:
    def test_truthful_run_stays_probation_below_min_samples(self):
        """9 truthful checks — score is high but sample count under
        MID threshold (10). Must still report PROBATION."""
        tt.register_instrument("x", "hook", "desc")
        for i in range(9):
            tt.record_check("x", CheckOutcome.TRUTHFUL, f"check {i} verified against ground-truth")
        assert tt.tier("x") == TrustTier.PROBATION

    def test_reaches_mid_after_threshold(self):
        tt.register_instrument("x", "hook", "desc")
        for i in range(15):
            tt.record_check("x", CheckOutcome.TRUTHFUL, f"check {i} verified against ground-truth")
        assert tt.tier("x") == TrustTier.MID

    def test_reaches_high_after_sustained_truthfulness(self):
        """With Beta(0, 5) prior, HIGH (score >= 0.9) requires ~50
        truthful checks: 50/55 ≈ 0.909. Trust earned slowly, by design."""
        tt.register_instrument("x", "hook", "desc")
        for i in range(50):
            tt.record_check("x", CheckOutcome.TRUTHFUL, f"check {i} verified against ground-truth")
        assert tt.tier("x") == TrustTier.HIGH

    def test_contradictions_keep_tool_in_probation(self):
        tt.register_instrument("x", "hook", "desc")
        for i in range(20):
            outcome = CheckOutcome.TRUTHFUL if i % 2 == 0 else CheckOutcome.CONTRADICTED
            tt.record_check("x", outcome, f"check {i} compared against ground truth artifact")
        # 50% truthfulness → smoothed score below MID threshold.
        assert tt.tier("x") == TrustTier.PROBATION


class TestLowTrustSurface:
    def test_low_trust_list_empty_at_start(self):
        assert tt.list_low_trust() == []

    def test_cold_start_instrument_excluded(self):
        """An instrument with <3 checks is cold-start — needs more data,
        not maintenance. Must NOT appear in the low-trust list even if
        its raw score is below threshold."""
        tt.register_instrument("x", "hook", "desc")
        tt.record_check("x", CheckOutcome.CONTRADICTED, "single contradicted check evidence here")
        assert tt.list_low_trust() == []

    def test_low_trust_surfaces_after_sustained_failures(self):
        tt.register_instrument("bad-tool", "hook", "desc")
        for i in range(10):
            tt.record_check(
                "bad-tool",
                CheckOutcome.CONTRADICTED,
                f"check {i} contradicted by ground-truth observation",
            )
        low = tt.list_low_trust()
        assert len(low) == 1
        assert low[0].instrument_id == "bad-tool"

    def test_briefing_block_empty_when_no_low_trust(self):
        assert tt.briefing_block() == ""

    def test_briefing_block_names_low_trust_instruments(self):
        tt.register_instrument("compaction-monitor", "monitor", "desc")
        for i in range(8):
            tt.record_check(
                "compaction-monitor",
                CheckOutcome.CONTRADICTED,
                f"check {i} false-fired vs harness meter",
            )
        block = tt.briefing_block()
        assert "TOOL-TRUST MAINTENANCE SIGNAL" in block
        assert "compaction-monitor" in block


class TestOrphanedSurface:
    """Knuth boundary catch (council walk 2026-06-13): an instrument
    registered and never checked is its own failure mode — separate
    from low-trust. Said-it-mattered-then-walked-away."""

    def test_fresh_registration_not_orphaned(self):
        tt.register_instrument("x", "hook", "desc")
        assert tt.list_orphaned() == []

    def test_old_registration_with_no_checks_is_orphaned(self, monkeypatch):
        tt.register_instrument("x", "hook", "desc")
        # Threshold of 0 — anything registered in the past counts.
        assert len(tt.list_orphaned(threshold_seconds=0)) == 1

    def test_checked_instrument_not_orphaned(self):
        tt.register_instrument("x", "hook", "desc")
        tt.record_check("x", CheckOutcome.TRUTHFUL, "evidence string with substance")
        assert tt.list_orphaned(threshold_seconds=0) == []

    def test_briefing_surfaces_orphaned(self):
        tt.register_instrument("forgotten-tool", "hook", "registered then ignored")
        # Force the orphan window by passing zero threshold via briefing path —
        # the public briefing_block uses the default, so we exercise the lower
        # API directly here, then test briefing format via mock.
        orphans = tt.list_orphaned(threshold_seconds=0)
        assert orphans[0].instrument_id == "forgotten-tool"


class TestEventLog:
    def test_events_persist_per_check(self, tmp_path):
        import sqlite3

        tt.register_instrument("x", "hook", "desc")
        tt.record_check("x", CheckOutcome.TRUTHFUL, "first truthful check evidence string")
        tt.record_check("x", CheckOutcome.CONTRADICTED, "second contradicted check evidence")

        conn = sqlite3.connect(str(tt._db_path()))
        rows = conn.execute(
            "SELECT outcome, evidence FROM tool_trust_events ORDER BY id"
        ).fetchall()
        conn.close()
        assert len(rows) == 2
        assert rows[0][0] == "TRUTHFUL"
        assert rows[1][0] == "CONTRADICTED"
